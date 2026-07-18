
from __future__ import annotations

from typing import Any

import pandas as pd


def _safe_number(value: Any) -> int | float | None:
    if pd.isna(value):
        return None

    number = float(value)

    if number.is_integer():
        return int(number)

    return round(number, 2)


def _find_column(
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
            if keyword in str(column).lower():
                return str(column)

    return None


def _detect_date_column(
    dataframe: pd.DataFrame,
) -> str | None:
    for column in dataframe.columns:
        name = str(column)

        if any(
            token in name.lower()
            for token in (
                "date",
                "month",
                "year",
                "time",
            )
        ):
            parsed = pd.to_datetime(
                dataframe[column],
                errors="coerce",
            )

            if parsed.notna().sum() >= max(
                3,
                int(len(dataframe) * 0.25),
            ):
                return name

    return None


def _build_kpis(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    sales_column = _find_column(
        dataframe,
        ("sales", "revenue", "amount"),
        numeric_only=True,
    )

    profit_column = _find_column(
        dataframe,
        ("profit", "income"),
        numeric_only=True,
    )

    quantity_column = _find_column(
        dataframe,
        ("quantity", "units"),
        numeric_only=True,
    )

    order_column = _find_column(
        dataframe,
        ("order id", "order_id", "order"),
    )

    customer_column = _find_column(
        dataframe,
        ("customer id", "customer_id", "customer"),
    )

    if sales_column:
        cards.append({
            "title": "Total Sales",
            "value": _safe_number(
                pd.to_numeric(
                    dataframe[sales_column],
                    errors="coerce",
                ).sum()
            ),
            "source": sales_column,
            "format": "number",
            "icon": "₹",
        })

    if profit_column:
        cards.append({
            "title": "Total Profit",
            "value": _safe_number(
                pd.to_numeric(
                    dataframe[profit_column],
                    errors="coerce",
                ).sum()
            ),
            "source": profit_column,
            "format": "number",
            "icon": "↗",
        })

    if sales_column and profit_column:
        total_sales = float(
            pd.to_numeric(
                dataframe[sales_column],
                errors="coerce",
            ).sum()
        )

        total_profit = float(
            pd.to_numeric(
                dataframe[profit_column],
                errors="coerce",
            ).sum()
        )

        margin = (
            (total_profit / total_sales) * 100
            if total_sales
            else 0
        )

        cards.append({
            "title": "Profit Margin",
            "value": round(margin, 2),
            "source": (
                f"{profit_column} / {sales_column}"
            ),
            "format": "percent",
            "icon": "%",
        })

    if quantity_column:
        cards.append({
            "title": "Total Quantity",
            "value": _safe_number(
                pd.to_numeric(
                    dataframe[quantity_column],
                    errors="coerce",
                ).sum()
            ),
            "source": quantity_column,
            "format": "integer",
            "icon": "▦",
        })

    if order_column:
        cards.append({
            "title": "Orders",
            "value": int(
                dataframe[order_column].nunique(
                    dropna=True
                )
            ),
            "source": order_column,
            "format": "integer",
            "icon": "#",
        })

    if customer_column:
        cards.append({
            "title": "Customers",
            "value": int(
                dataframe[customer_column].nunique(
                    dropna=True
                )
            ),
            "source": customer_column,
            "format": "integer",
            "icon": "◎",
        })

    if not cards:
        for column in (
            dataframe.select_dtypes(
                include="number"
            ).columns[:4]
        ):
            cards.append({
                "title": f"Total {column}",
                "value": _safe_number(
                    pd.to_numeric(
                        dataframe[column],
                        errors="coerce",
                    ).sum()
                ),
                "source": str(column),
                "format": "number",
                "icon": "◆",
            })

    return cards[:6]


def _build_charts(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []

    numeric_columns = (
        dataframe.select_dtypes(
            include="number"
        ).columns.astype(str).tolist()
    )

    categorical_columns = (
        dataframe.select_dtypes(
            exclude="number"
        ).columns.astype(str).tolist()
    )

    date_column = _detect_date_column(
        dataframe
    )

    sales_column = _find_column(
        dataframe,
        ("sales", "revenue", "amount"),
        numeric_only=True,
    )

    profit_column = _find_column(
        dataframe,
        ("profit", "income"),
        numeric_only=True,
    )

    primary_metric = (
        sales_column
        or profit_column
        or (
            numeric_columns[0]
            if numeric_columns
            else None
        )
    )

    low_cardinality_categories = [
        column
        for column in categorical_columns
        if 2 <= dataframe[column].nunique(
            dropna=True
        ) <= 20
    ]

    if (
        primary_metric
        and low_cardinality_categories
    ):
        category = low_cardinality_categories[0]

        grouped = (
            pd.DataFrame({
                category: dataframe[category],
                primary_metric: pd.to_numeric(
                    dataframe[primary_metric],
                    errors="coerce",
                ),
            })
            .dropna()
            .groupby(category)[primary_metric]
            .sum()
            .sort_values(ascending=False)
            .head(12)
            .reset_index()
        )

        charts.append({
            "id": "category-performance",
            "title": (
                f"{primary_metric} by {category}"
            ),
            "description": (
                "Automatically selected category comparison."
            ),
            "type": "bar",
            "x": category,
            "y": primary_metric,
            "records": grouped.to_dict(
                orient="records"
            ),
        })

    if (
        date_column
        and primary_metric
    ):
        working = pd.DataFrame({
            "date": pd.to_datetime(
                dataframe[date_column],
                errors="coerce",
            ),
            primary_metric: pd.to_numeric(
                dataframe[primary_metric],
                errors="coerce",
            ),
        }).dropna()

        if not working.empty:
            trend = (
                working
                .set_index("date")[primary_metric]
                .resample("MS")
                .sum()
                .dropna()
                .tail(24)
                .reset_index()
            )

            trend["date"] = (
                trend["date"]
                .dt.strftime("%b %Y")
            )

            charts.append({
                "id": "trend",
                "title": (
                    f"Monthly {primary_metric} trend"
                ),
                "description": (
                    "Automatic time-series trend analysis."
                ),
                "type": "line",
                "x": "date",
                "y": primary_metric,
                "records": trend.to_dict(
                    orient="records"
                ),
            })

    if len(numeric_columns) >= 2:
        first = numeric_columns[0]
        second = numeric_columns[1]

        scatter = (
            dataframe[[first, second]]
            .apply(
                pd.to_numeric,
                errors="coerce",
            )
            .dropna()
            .head(400)
        )

        charts.append({
            "id": "relationship",
            "title": (
                f"{second} vs {first}"
            ),
            "description": (
                "Automatic numeric relationship analysis."
            ),
            "type": "scatter",
            "x": first,
            "y": second,
            "records": scatter.to_dict(
                orient="records"
            ),
        })

    if low_cardinality_categories:
        category = low_cardinality_categories[0]

        counts = (
            dataframe[category]
            .fillna("Missing")
            .astype(str)
            .value_counts()
            .head(8)
            .rename_axis(category)
            .reset_index(name="count")
        )

        charts.append({
            "id": "distribution",
            "title": (
                f"{category} distribution"
            ),
            "description": (
                "Automatic category composition."
            ),
            "type": (
                "pie"
                if len(counts) <= 6
                else "bar"
            ),
            "x": category,
            "y": "count",
            "records": counts.to_dict(
                orient="records"
            ),
        })

    return charts[:4]


def _build_insights(
    dataframe: pd.DataFrame,
    kpis: list[dict[str, Any]],
    charts: list[dict[str, Any]],
) -> list[str]:
    insights = []

    missing = int(
        dataframe.isna().sum().sum()
    )

    duplicates = int(
        dataframe.duplicated().sum()
    )

    if missing == 0:
        insights.append(
            "The dataset has no missing values."
        )
    else:
        insights.append(
            f"The dataset contains {missing:,} missing values "
            "that should be reviewed."
        )

    if duplicates == 0:
        insights.append(
            "No duplicate rows were detected."
        )
    else:
        insights.append(
            f"{duplicates:,} duplicate rows were detected."
        )

    if kpis:
        strongest = kpis[0]

        insights.append(
            f"The dashboard selected '{strongest['title']}' "
            "as a primary executive KPI."
        )

    if charts:
        insights.append(
            f"{len(charts)} visualizations were generated "
            "automatically from the dataset structure."
        )

    return insights


def build_ai_dashboard(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    if dataframe.empty:
        raise ValueError(
            "Cannot build a dashboard from an empty dataset."
        )

    kpis = _build_kpis(
        dataframe
    )

    charts = _build_charts(
        dataframe
    )

    insights = _build_insights(
        dataframe,
        kpis,
        charts,
    )

    return {
        "title": "AI Generated Dashboard",
        "subtitle": (
            "Automatically generated from the uploaded dataset"
        ),
        "dataset": {
            "rows": int(
                dataframe.shape[0]
            ),
            "columns": int(
                dataframe.shape[1]
            ),
            "missing_values": int(
                dataframe.isna().sum().sum()
            ),
            "duplicate_rows": int(
                dataframe.duplicated().sum()
            ),
        },
        "kpis": kpis,
        "charts": charts,
        "insights": insights,
        "preview": {
            "columns": (
                dataframe.columns
                .astype(str)
                .tolist()
            ),
            "rows": (
                dataframe.head(10)
                .where(
                    dataframe.head(10).notna(),
                    None,
                )
                .to_dict(
                    orient="records"
                )
            ),
        },
    }
