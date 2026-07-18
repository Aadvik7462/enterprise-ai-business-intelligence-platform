
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class Result:
    answer: str
    response_type: str = "text"
    data: dict[str, Any] | None = None
    suggestions: list[str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": True,
            "answer": self.answer,
            "response_type": self.response_type,
            "data": self.data or {},
            "suggestions": self.suggestions or [],
        }


def normalise(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def safe_number(value: Any) -> int | float | None:
    if pd.isna(value):
        return None

    number = float(value)

    if not math.isfinite(number):
        return None

    if number.is_integer():
        return int(number)

    return round(number, 4)


def safe_records(
    dataframe: pd.DataFrame,
    limit: int = 25,
) -> list[dict[str, Any]]:
    clean = (
        dataframe.head(limit)
        .copy()
        .replace({
            np.nan: None,
            np.inf: None,
            -np.inf: None,
        })
    )

    return clean.to_dict(orient="records")


def find_column(
    dataframe: pd.DataFrame,
    text: str,
    numeric_only: bool = False,
) -> str | None:
    question = normalise(text)

    columns = (
        dataframe.select_dtypes(include="number").columns
        if numeric_only
        else dataframe.columns
    )

    exact = [
        str(column)
        for column in columns
        if normalise(column) in question
    ]

    if exact:
        return max(exact, key=len)

    question_tokens = set(re.findall(r"[a-z0-9]+", question))
    scored = []

    for column in columns:
        column_name = str(column)
        column_tokens = set(
            re.findall(r"[a-z0-9]+", normalise(column_name))
        )
        score = len(question_tokens & column_tokens)

        if score:
            scored.append((score, len(column_name), column_name))

    if scored:
        scored.sort(reverse=True)
        return scored[0][2]

    return None


def find_keyword_column(
    dataframe: pd.DataFrame,
    keywords: tuple[str, ...],
    numeric_only: bool = False,
) -> str | None:
    columns = (
        dataframe.select_dtypes(include="number").columns
        if numeric_only
        else dataframe.columns
    )

    for keyword in keywords:
        for column in columns:
            if keyword in normalise(column):
                return str(column)

    return None


def numeric_columns(dataframe: pd.DataFrame) -> list[str]:
    return dataframe.select_dtypes(
        include="number"
    ).columns.astype(str).tolist()


def categorical_columns(dataframe: pd.DataFrame) -> list[str]:
    return dataframe.select_dtypes(
        exclude="number"
    ).columns.astype(str).tolist()


def detect_date_column(
    dataframe: pd.DataFrame,
    question: str = "",
) -> str | None:
    mentioned = find_column(dataframe, question)

    if mentioned:
        series = dataframe[mentioned]

        if (
            pd.api.types.is_datetime64_any_dtype(series)
            or any(
                keyword in normalise(mentioned)
                for keyword in ("date", "month", "year", "time")
            )
        ):
            converted = pd.to_datetime(series, errors="coerce")

            if converted.notna().sum() >= 3:
                return mentioned

    for column in dataframe.columns:
        name = str(column)

        if any(
            keyword in normalise(name)
            for keyword in ("date", "month", "year", "time")
        ):
            converted = pd.to_datetime(
                dataframe[column],
                errors="coerce",
            )

            if converted.notna().sum() >= max(
                3,
                int(len(dataframe) * 0.25),
            ):
                return name

    return None


def detect_metric_column(
    dataframe: pd.DataFrame,
    question: str,
) -> str | None:
    mentioned = find_column(
        dataframe,
        question,
        numeric_only=True,
    )

    if mentioned:
        return mentioned

    return find_keyword_column(
        dataframe,
        (
            "sales",
            "revenue",
            "profit",
            "amount",
            "quantity",
            "cost",
        ),
        numeric_only=True,
    ) or (
        numeric_columns(dataframe)[0]
        if numeric_columns(dataframe)
        else None
    )


def percentage_change(
    current: float,
    previous: float,
) -> float | None:
    if previous == 0:
        return None

    return round(
        ((current - previous) / abs(previous)) * 100,
        2,
    )


def dataset_summary(dataframe: pd.DataFrame) -> Result:
    missing = int(dataframe.isna().sum().sum())
    duplicates = int(dataframe.duplicated().sum())
    total_values = dataframe.shape[0] * dataframe.shape[1]

    completeness = (
        round(
            ((total_values - missing) / total_values) * 100,
            2,
        )
        if total_values
        else 0
    )

    return Result(
        answer=(
            f"The dataset contains {len(dataframe):,} rows and "
            f"{len(dataframe.columns):,} columns. It has "
            f"{len(numeric_columns(dataframe))} numeric columns, "
            f"{missing:,} missing values, and {duplicates:,} "
            f"duplicate rows. Completeness is {completeness}%."
        ),
        data={
            "rows": len(dataframe),
            "columns": len(dataframe.columns),
            "missing_values": missing,
            "duplicate_rows": duplicates,
            "completeness": completeness,
        },
        suggestions=[
            "Show executive KPIs",
            "Show correlation heatmap",
            "Generate executive recommendations",
            "Forecast sales",
        ],
    )


def missing_analysis(dataframe: pd.DataFrame) -> Result:
    missing = dataframe.isna().sum().sort_values(ascending=False)
    missing = missing[missing > 0]

    if missing.empty:
        return Result(
            answer="No missing values were detected."
        )

    rows = [
        {
            "column": str(column),
            "missing_values": int(value),
            "missing_percent": round(
                (int(value) / len(dataframe)) * 100,
                2,
            ) if len(dataframe) else 0,
        }
        for column, value in missing.items()
    ]

    return Result(
        answer=(
            f"The dataset contains {int(missing.sum()):,} missing "
            f"values across {len(rows)} columns."
        ),
        response_type="table",
        data={
            "columns": [
                "column",
                "missing_values",
                "missing_percent",
            ],
            "rows": rows,
        },
    )


def grouped_analysis(
    dataframe: pd.DataFrame,
    question: str,
) -> Result | None:
    q = normalise(question)

    match = re.search(
        r"(?:show|compare|plot|chart|sum|total|average|mean)?\s*"
        r"(.+?)\s+by\s+(.+)",
        q,
    )

    if not match:
        return None

    metric = find_column(
        dataframe,
        match.group(1),
        numeric_only=True,
    )
    group = find_column(
        dataframe,
        match.group(2),
    )

    if not metric or not group or metric == group:
        return None

    operation = (
        "mean"
        if any(word in q for word in ("average", "mean"))
        else "sum"
    )

    working = pd.DataFrame({
        group: dataframe[group],
        metric: pd.to_numeric(
            dataframe[metric],
            errors="coerce",
        ),
    }).dropna()

    grouped = (
        working.groupby(group)[metric]
        .agg(operation)
        .sort_values(ascending=False)
        .head(20)
        .reset_index()
    )

    grouped[metric] = grouped[metric].map(safe_number)

    if grouped.empty:
        return None

    top_group = grouped.iloc[0][group]
    top_value = grouped.iloc[0][metric]

    return Result(
        answer=(
            f"{'Average' if operation == 'mean' else 'Total'} "
            f"'{metric}' by '{group}' has been calculated. "
            f"{top_group} is the leading group with {top_value}."
        ),
        response_type="chart",
        data={
            "chart": {
                "type": "bar",
                "x": group,
                "y": metric,
                "title": (
                    f"{'Average' if operation == 'mean' else 'Total'} "
                    f"{metric} by {group}"
                ),
                "records": safe_records(grouped, 20),
            },
            "table": {
                "columns": grouped.columns.astype(str).tolist(),
                "rows": safe_records(grouped, 20),
            },
        },
        suggestions=[
            f"Top 5 rows by {metric}",
            f"Forecast {metric}",
            "Show executive KPIs",
        ],
    )


def ranking_analysis(
    dataframe: pd.DataFrame,
    question: str,
) -> Result | None:
    q = normalise(question)

    if not any(
        word in q
        for word in (
            "top",
            "bottom",
            "highest",
            "lowest",
            "best",
            "worst",
        )
    ):
        return None

    metric = find_column(
        dataframe,
        question,
        numeric_only=True,
    )

    if not metric:
        return None

    match = re.search(r"\b(?:top|bottom)\s+(\d+)\b", q)
    limit = max(
        1,
        min(int(match.group(1)) if match else 10, 50),
    )

    ascending = any(
        word in q
        for word in ("bottom", "lowest", "worst")
    )

    ranked = (
        dataframe.assign(
            **{
                metric: pd.to_numeric(
                    dataframe[metric],
                    errors="coerce",
                )
            }
        )
        .dropna(subset=[metric])
        .sort_values(metric, ascending=ascending)
        .head(limit)
    )

    return Result(
        answer=(
            f"Here are the {'bottom' if ascending else 'top'} "
            f"{limit} rows ranked by '{metric}'."
        ),
        response_type="table",
        data={
            "columns": ranked.columns.astype(str).tolist(),
            "rows": safe_records(ranked, limit),
        },
    )


def metric_analysis(
    dataframe: pd.DataFrame,
    question: str,
) -> Result | None:
    q = normalise(question)
    column = find_column(
        dataframe,
        question,
        numeric_only=True,
    )

    if not column:
        return None

    series = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    ).dropna()

    operations = [
        (("average", "mean"), "average", series.mean()),
        (("sum", "total"), "total", series.sum()),
        (("maximum", "max"), "maximum", series.max()),
        (("minimum", "min"), "minimum", series.min()),
        (("median",), "median", series.median()),
    ]

    for keywords, label, value in operations:
        if any(keyword in q for keyword in keywords):
            result = safe_number(value)

            return Result(
                answer=f"The {label} of '{column}' is {result}.",
                data={
                    "column": column,
                    "metric": label,
                    "value": result,
                },
            )

    return None


def correlation_table(dataframe: pd.DataFrame) -> Result:
    numeric = dataframe.select_dtypes(include="number")

    if numeric.shape[1] < 2:
        return Result(
            answer=(
                "At least two numeric columns are required "
                "for correlation analysis."
            )
        )

    correlation = numeric.corr(numeric_only=True)
    pairs = []

    for index, left in enumerate(correlation.columns):
        for right in correlation.columns[index + 1:]:
            value = correlation.loc[left, right]

            if pd.notna(value):
                pairs.append({
                    "column_1": str(left),
                    "column_2": str(right),
                    "correlation": round(float(value), 4),
                    "strength": abs(float(value)),
                })

    pairs.sort(
        key=lambda item: item["strength"],
        reverse=True,
    )

    rows = [
        {
            "column_1": item["column_1"],
            "column_2": item["column_2"],
            "correlation": item["correlation"],
        }
        for item in pairs[:10]
    ]

    if not rows:
        return Result(
            answer="No valid correlations were found."
        )

    strongest = rows[0]

    return Result(
        answer=(
            f"The strongest relationship is between "
            f"'{strongest['column_1']}' and "
            f"'{strongest['column_2']}' with correlation "
            f"{strongest['correlation']}."
        ),
        response_type="table",
        data={
            "columns": [
                "column_1",
                "column_2",
                "correlation",
            ],
            "rows": rows,
        },
    )


def correlation_heatmap(dataframe: pd.DataFrame) -> Result:
    numeric = (
        dataframe.select_dtypes(include="number")
        .dropna(axis=1, how="all")
    )

    if numeric.shape[1] < 2:
        return Result(
            answer=(
                "At least two numeric columns are required "
                "for a correlation heatmap."
            )
        )

    if numeric.shape[1] > 15:
        selected = (
            numeric.var(numeric_only=True)
            .sort_values(ascending=False)
            .head(15)
            .index
        )
        numeric = numeric[selected]

    correlation = numeric.corr(numeric_only=True)
    labels = correlation.columns.astype(str).tolist()

    return Result(
        answer=(
            "The interactive correlation heatmap has been generated."
        ),
        response_type="heatmap",
        data={
            "chart": {
                "type": "heatmap",
                "title": "Correlation heatmap",
                "x": labels,
                "y": labels,
                "z": [
                    [
                        round(float(value), 4)
                        if pd.notna(value)
                        else None
                        for value in row
                    ]
                    for row in correlation.values
                ],
            },
        },
        suggestions=[
            "Find strongest correlations",
            "Show outliers",
            "Show executive KPIs",
        ],
    )


def forecast_analysis(
    dataframe: pd.DataFrame,
    question: str,
) -> Result:
    metric = detect_metric_column(dataframe, question)
    date_column = detect_date_column(dataframe, question)

    if not metric:
        return Result(
            answer="A numeric metric is required for forecasting."
        )

    if not date_column:
        return Result(
            answer=(
                "A valid date column is required for forecasting."
            )
        )

    working = pd.DataFrame({
        "date": pd.to_datetime(
            dataframe[date_column],
            errors="coerce",
        ),
        "value": pd.to_numeric(
            dataframe[metric],
            errors="coerce",
        ),
    }).dropna()

    if len(working) < 4:
        return Result(
            answer=(
                "At least four valid dated observations are "
                "required for forecasting."
            )
        )

    working = working.set_index("date").sort_index()
    span = (working.index.max() - working.index.min()).days

    if span > 730:
        frequency = "QS"
        label = "quarter"
    elif span > 90:
        frequency = "MS"
        label = "month"
    else:
        frequency = "D"
        label = "day"

    series = (
        working["value"]
        .resample(frequency)
        .sum()
        .dropna()
    )

    if len(series) < 4:
        return Result(
            answer=(
                f"Not enough {label}-level observations "
                "were available."
            )
        )

    x = np.arange(len(series), dtype=float)
    slope, intercept = np.polyfit(
        x,
        series.values.astype(float),
        1,
    )

    periods = 6
    future_x = np.arange(
        len(series),
        len(series) + periods,
        dtype=float,
    )
    forecast = np.maximum(
        slope * future_x + intercept,
        0,
    )

    last_date = series.index[-1]

    if frequency == "QS":
        future_dates = pd.date_range(
            last_date + pd.offsets.QuarterBegin(),
            periods=periods,
            freq="QS",
        )
    elif frequency == "MS":
        future_dates = pd.date_range(
            last_date + pd.offsets.MonthBegin(),
            periods=periods,
            freq="MS",
        )
    else:
        future_dates = pd.date_range(
            last_date + pd.Timedelta(days=1),
            periods=periods,
            freq="D",
        )

    records = [
        {
            "period": date.strftime("%Y-%m-%d"),
            "actual": safe_number(value),
            "forecast": None,
        }
        for date, value in series.tail(24).items()
    ]

    records.extend([
        {
            "period": date.strftime("%Y-%m-%d"),
            "actual": None,
            "forecast": safe_number(value),
        }
        for date, value in zip(future_dates, forecast)
    ])

    direction = (
        "upward"
        if slope > 0
        else "downward"
        if slope < 0
        else "stable"
    )

    final_value = safe_number(forecast[-1])
    growth = percentage_change(
        float(forecast[-1]),
        float(series.iloc[-1]),
    )

    answer = (
        f"The '{metric}' trend is {direction}. "
        f"The final forecasted {label} is {final_value}."
    )

    if growth is not None:
        answer += (
            f" This is {abs(growth)}% "
            f"{'above' if growth >= 0 else 'below'} "
            "the latest actual period."
        )

    return Result(
        answer=answer,
        response_type="forecast",
        data={
            "chart": {
                "type": "line",
                "x": "period",
                "series": [
                    {
                        "key": "actual",
                        "label": "Actual",
                    },
                    {
                        "key": "forecast",
                        "label": "Forecast",
                    },
                ],
                "title": f"{metric} trend and forecast",
                "records": records,
            },
            "metric_column": metric,
            "date_column": date_column,
            "trend": direction,
        },
        suggestions=[
            f"Profile {metric}",
            "Show executive KPIs",
            "Generate executive recommendations",
        ],
    )


def outlier_analysis(
    dataframe: pd.DataFrame,
    question: str,
) -> Result:
    column = detect_metric_column(dataframe, question)

    if not column:
        return Result(
            answer=(
                "A numeric column is required for outlier analysis."
            )
        )

    values = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )
    clean = values.dropna()

    if len(clean) < 4:
        return Result(
            answer=(
                f"Column '{column}' does not contain enough values."
            )
        )

    q1 = clean.quantile(0.25)
    q3 = clean.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    mask = (values < lower) | (values > upper)
    outliers = dataframe.loc[mask]

    return Result(
        answer=(
            f"I detected {len(outliers):,} outliers in "
            f"'{column}'. The expected range is "
            f"{safe_number(lower)} to {safe_number(upper)}."
        ),
        response_type="table",
        data={
            "columns": outliers.columns.astype(str).tolist(),
            "rows": safe_records(outliers, 20),
            "outlier_count": len(outliers),
            "lower_bound": safe_number(lower),
            "upper_bound": safe_number(upper),
        },
    )


def executive_kpis(dataframe: pd.DataFrame) -> Result:
    cards = []

    sales = find_keyword_column(
        dataframe,
        ("sales", "revenue", "amount"),
        numeric_only=True,
    )
    profit = find_keyword_column(
        dataframe,
        ("profit", "income"),
        numeric_only=True,
    )
    quantity = find_keyword_column(
        dataframe,
        ("quantity", "units"),
        numeric_only=True,
    )
    order = find_keyword_column(
        dataframe,
        ("order id", "order_id", "order"),
    )
    customer = find_keyword_column(
        dataframe,
        ("customer id", "customer_id", "customer"),
    )

    if sales:
        total_sales = pd.to_numeric(
            dataframe[sales],
            errors="coerce",
        ).sum()

        cards.append({
            "label": "Total Sales",
            "value": safe_number(total_sales),
            "column": sales,
            "format": "number",
        })

    if profit:
        total_profit = pd.to_numeric(
            dataframe[profit],
            errors="coerce",
        ).sum()

        cards.append({
            "label": "Total Profit",
            "value": safe_number(total_profit),
            "column": profit,
            "format": "number",
        })

    if sales and profit:
        sales_total = float(
            pd.to_numeric(
                dataframe[sales],
                errors="coerce",
            ).sum()
        )
        profit_total = float(
            pd.to_numeric(
                dataframe[profit],
                errors="coerce",
            ).sum()
        )

        margin = (
            (profit_total / sales_total) * 100
            if sales_total
            else 0
        )

        cards.append({
            "label": "Profit Margin",
            "value": round(margin, 2),
            "column": f"{profit} / {sales}",
            "format": "percent",
        })

    if quantity:
        cards.append({
            "label": "Total Quantity",
            "value": safe_number(
                pd.to_numeric(
                    dataframe[quantity],
                    errors="coerce",
                ).sum()
            ),
            "column": quantity,
            "format": "integer",
        })

    if order:
        cards.append({
            "label": "Orders",
            "value": int(
                dataframe[order].nunique(dropna=True)
            ),
            "column": order,
            "format": "integer",
        })

    if customer:
        cards.append({
            "label": "Customers",
            "value": int(
                dataframe[customer].nunique(dropna=True)
            ),
            "column": customer,
            "format": "integer",
        })

    if not cards:
        for column in numeric_columns(dataframe)[:4]:
            cards.append({
                "label": f"Total {column}",
                "value": safe_number(
                    pd.to_numeric(
                        dataframe[column],
                        errors="coerce",
                    ).sum()
                ),
                "column": column,
                "format": "number",
            })

    return Result(
        answer=(
            f"I generated {len(cards)} executive KPI cards."
        ),
        response_type="kpi",
        data={
            "cards": cards[:6],
        },
        suggestions=[
            "Generate executive recommendations",
            "Show correlation heatmap",
            "Forecast sales",
        ],
    )


def executive_recommendations(
    dataframe: pd.DataFrame,
) -> Result:
    recommendations = []

    missing = int(dataframe.isna().sum().sum())
    duplicates = int(dataframe.duplicated().sum())

    if missing:
        recommendations.append({
            "priority": "High",
            "title": "Improve data completeness",
            "message": (
                f"Resolve {missing:,} missing values before "
                "using the dataset for critical decisions."
            ),
        })

    if duplicates:
        recommendations.append({
            "priority": "High",
            "title": "Remove duplicate records",
            "message": (
                f"Review {duplicates:,} duplicate rows to prevent "
                "inflated KPIs."
            ),
        })

    sales = find_keyword_column(
        dataframe,
        ("sales", "revenue"),
        numeric_only=True,
    )
    profit = find_keyword_column(
        dataframe,
        ("profit",),
        numeric_only=True,
    )
    category = find_keyword_column(
        dataframe,
        ("category", "segment", "region"),
    )

    if sales and category:
        grouped = (
            pd.DataFrame({
                category: dataframe[category],
                sales: pd.to_numeric(
                    dataframe[sales],
                    errors="coerce",
                ),
            })
            .dropna()
            .groupby(category)[sales]
            .sum()
            .sort_values(ascending=False)
        )

        if not grouped.empty:
            recommendations.append({
                "priority": "Opportunity",
                "title": f"Scale the strongest {category}",
                "message": (
                    f"{grouped.index[0]} generates the highest "
                    f"{sales}. Prioritize inventory, campaigns, "
                    "or sales resources there."
                ),
            })

    if profit and category:
        grouped = (
            pd.DataFrame({
                category: dataframe[category],
                profit: pd.to_numeric(
                    dataframe[profit],
                    errors="coerce",
                ),
            })
            .dropna()
            .groupby(category)[profit]
            .sum()
            .sort_values()
        )

        if not grouped.empty:
            recommendations.append({
                "priority": (
                    "High"
                    if float(grouped.iloc[0]) < 0
                    else "Medium"
                ),
                "title": f"Review the weakest {category}",
                "message": (
                    f"{grouped.index[0]} has the lowest {profit}. "
                    "Review pricing, discounting, costs, and mix."
                ),
            })

    if not recommendations:
        recommendations.append({
            "priority": "Medium",
            "title": "Track performance trends",
            "message": (
                "Create monthly trend monitoring for important "
                "numeric metrics and investigate major changes."
            ),
        })

    return Result(
        answer=(
            f"I generated {len(recommendations)} executive "
            "recommendations."
        ),
        response_type="recommendations",
        data={
            "recommendations": recommendations,
        },
        suggestions=[
            "Show executive KPIs",
            "Forecast sales",
            "Show correlation heatmap",
        ],
    )


def chart_recommendations(
    dataframe: pd.DataFrame,
) -> Result:
    numeric = numeric_columns(dataframe)
    categorical = categorical_columns(dataframe)
    date_column = detect_date_column(dataframe)

    rows = []

    if numeric and categorical:
        rows.append({
            "chart": "Bar chart",
            "purpose": "Compare metrics across categories",
            "example": f"Total {numeric[0]} by {categorical[0]}",
        })

    if numeric and date_column:
        rows.append({
            "chart": "Line chart",
            "purpose": "Analyze trends and forecast values",
            "example": f"Forecast {numeric[0]}",
        })

    if len(numeric) >= 2:
        rows.append({
            "chart": "Correlation heatmap",
            "purpose": "Compare numeric relationships",
            "example": "Show correlation heatmap",
        })

        rows.append({
            "chart": "Scatter chart",
            "purpose": "Inspect two numeric variables",
            "example": f"Compare {numeric[0]} and {numeric[1]}",
        })

    return Result(
        answer=(
            f"I identified {len(rows)} useful chart options."
        ),
        response_type="table",
        data={
            "columns": ["chart", "purpose", "example"],
            "rows": rows,
        },
    )


def answer_dataset_question(
    dataframe: pd.DataFrame,
    question: str,
) -> dict[str, Any]:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")

    if dataframe.empty:
        return Result(
            answer="The uploaded dataset is empty."
        ).as_dict()

    q = normalise(question)

    if not q:
        return {
            "success": False,
            "answer": "Please enter a question.",
            "response_type": "error",
            "data": {},
            "suggestions": [],
        }

    if any(
        phrase in q
        for phrase in (
            "summarize",
            "summary",
            "overview",
            "describe dataset",
        )
    ):
        return dataset_summary(dataframe).as_dict()

    if any(
        phrase in q
        for phrase in (
            "show all columns",
            "list columns",
            "column names",
        )
    ):
        return Result(
            answer=(
                f"The dataset has {len(dataframe.columns)} columns."
            ),
            response_type="list",
            data={
                "items": dataframe.columns.astype(str).tolist(),
            },
        ).as_dict()

    if "numeric columns" in q:
        columns = numeric_columns(dataframe)

        return Result(
            answer=f"I found {len(columns)} numeric columns.",
            response_type="list",
            data={"items": columns},
        ).as_dict()

    if "missing" in q or "null" in q:
        return missing_analysis(dataframe).as_dict()

    if "duplicate" in q:
        count = int(dataframe.duplicated().sum())

        return Result(
            answer=(
                f"The dataset contains {count:,} duplicate rows."
            ),
            data={"duplicate_rows": count},
        ).as_dict()

    if any(
        phrase in q
        for phrase in (
            "show executive kpis",
            "show kpis",
            "generate kpis",
            "kpi cards",
        )
    ):
        return executive_kpis(dataframe).as_dict()

    if any(
        phrase in q
        for phrase in (
            "executive recommendations",
            "business recommendations",
            "generate executive recommendations",
            "recommend actions",
        )
    ):
        return executive_recommendations(dataframe).as_dict()

    if any(
        phrase in q
        for phrase in (
            "forecast",
            "predict",
            "future trend",
            "trend analysis",
        )
    ):
        return forecast_analysis(
            dataframe,
            question,
        ).as_dict()

    if "heatmap" in q:
        return correlation_heatmap(dataframe).as_dict()

    if any(
        phrase in q
        for phrase in (
            "show outliers",
            "find outliers",
            "detect outliers",
            "anomaly",
            "anomalies",
        )
    ):
        return outlier_analysis(
            dataframe,
            question,
        ).as_dict()

    if any(
        phrase in q
        for phrase in (
            "recommend charts",
            "suggest charts",
            "best charts",
        )
    ):
        return chart_recommendations(dataframe).as_dict()

    if "correlation" in q:
        return correlation_table(dataframe).as_dict()

    grouped = grouped_analysis(dataframe, question)

    if grouped:
        return grouped.as_dict()

    ranked = ranking_analysis(dataframe, question)

    if ranked:
        return ranked.as_dict()

    metric = metric_analysis(dataframe, question)

    if metric:
        return metric.as_dict()

    return Result(
        answer=(
            "I could not confidently interpret that question. "
            "Try a summary, grouped chart, forecast, heatmap, "
            "KPI request, recommendation request, outlier analysis, "
            "ranking, or numeric calculation."
        ),
        suggestions=[
            "Summarize this dataset",
            "Show executive KPIs",
            "Generate executive recommendations",
            "Show correlation heatmap",
            "Forecast sales",
        ],
    ).as_dict()
