"""
Enterprise BI Copilot Service

Provides deterministic, dataset-grounded answers and Plotly-ready chart
specifications without requiring an external AI API.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from services.ai_forecast_service import (
    generate_ai_forecast,
    get_forecast_options,
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _format_number(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)

    if abs(numeric) >= 10_000_000:
        return f"{numeric / 10_000_000:.2f} Cr"
    if abs(numeric) >= 100_000:
        return f"{numeric / 100_000:.2f} L"
    if abs(numeric) >= 1_000:
        return f"{numeric / 1_000:.2f}K"

    return f"{numeric:,.2f}"


def _column_lookup(df: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}

    for column in df.columns:
        normalized = _normalize(
            str(column).replace("_", " ")
        )
        lookup[normalized] = str(column)

    return lookup


def _find_column_in_question(
    df: pd.DataFrame,
    question: str,
    numeric_only: bool = False,
    categorical_only: bool = False,
) -> str | None:
    normalized_question = _normalize(question)

    candidates = list(df.columns)

    if numeric_only:
        candidates = df.select_dtypes(
            include="number"
        ).columns.tolist()

    if categorical_only:
        candidates = df.select_dtypes(
            exclude="number"
        ).columns.tolist()

    ordered_candidates = sorted(
        candidates,
        key=lambda column: len(str(column)),
        reverse=True,
    )

    for column in ordered_candidates:
        normalized_column = _normalize(
            str(column).replace("_", " ")
        )

        if normalized_column in normalized_question:
            return str(column)

    return None


def _detect_business_numeric_column(
    df: pd.DataFrame,
    question: str = "",
) -> str | None:
    explicit = _find_column_in_question(
        df,
        question,
        numeric_only=True,
    )

    if explicit:
        return explicit

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    preferred_keywords = [
        "sales",
        "revenue",
        "profit",
        "amount",
        "quantity",
        "cost",
        "price",
        "income",
        "orders",
        "demand",
        "inventory",
    ]

    for keyword in preferred_keywords:
        for column in numeric_columns:
            if keyword in _normalize(
                str(column).replace("_", " ")
            ):
                return str(column)

    return (
        str(numeric_columns[0])
        if numeric_columns
        else None
    )


def _detect_categorical_column(
    df: pd.DataFrame,
    question: str = "",
) -> str | None:
    explicit = _find_column_in_question(
        df,
        question,
        categorical_only=True,
    )

    if explicit:
        return explicit

    categorical_columns = df.select_dtypes(
        exclude="number"
    ).columns.tolist()

    preferred_keywords = [
        "category",
        "region",
        "segment",
        "product",
        "customer",
        "state",
        "city",
        "country",
        "department",
        "channel",
    ]

    for keyword in preferred_keywords:
        for column in categorical_columns:
            if keyword in _normalize(
                str(column).replace("_", " ")
            ):
                return str(column)

    return (
        str(categorical_columns[0])
        if categorical_columns
        else None
    )


def _dataset_quality(df: pd.DataFrame) -> dict[str, Any]:
    rows = int(len(df))
    columns = int(len(df.columns))
    total_cells = max(1, rows * columns)

    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())

    completeness = max(
        0.0,
        100.0 - missing / total_cells * 100.0,
    )

    duplicate_penalty = (
        duplicates / max(1, rows) * 100.0
    )

    quality_score = max(
        0.0,
        min(
            100.0,
            completeness - duplicate_penalty,
        ),
    )

    return {
        "rows": rows,
        "columns": columns,
        "missing": missing,
        "duplicates": duplicates,
        "quality_score": round(quality_score, 2),
    }


def _text_response(
    answer: str,
    intent: str,
    suggestions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "response_type": "text",
        "intent": intent,
        "answer": answer,
        "suggestions": suggestions or [],
    }


def _chart_response(
    answer: str,
    chart: dict[str, Any],
    intent: str,
    suggestions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "response_type": "chart",
        "intent": intent,
        "answer": answer,
        "chart": chart,
        "suggestions": suggestions or [],
    }


def _summary_answer(df: pd.DataFrame) -> dict[str, Any]:
    quality = _dataset_quality(df)
    numeric = df.select_dtypes(
        include="number"
    ).columns.tolist()
    categorical = df.select_dtypes(
        exclude="number"
    ).columns.tolist()

    answer = (
        f"This dataset contains {quality['rows']:,} rows and "
        f"{quality['columns']} columns. It has "
        f"{len(numeric)} numeric columns and "
        f"{len(categorical)} categorical or date-like columns. "
        f"There are {quality['missing']:,} missing values and "
        f"{quality['duplicates']:,} duplicate rows. "
        f"The estimated data-quality score is "
        f"{quality['quality_score']:.2f}%."
    )

    business_column = _detect_business_numeric_column(df)

    if business_column:
        series = pd.to_numeric(
            df[business_column],
            errors="coerce",
        ).dropna()

        if not series.empty:
            answer += (
                f" For {business_column}, the total is "
                f"{_format_number(series.sum())}, the average is "
                f"{_format_number(series.mean())}, and the maximum is "
                f"{_format_number(series.max())}."
            )

    return _text_response(
        answer,
        intent="dataset_summary",
        suggestions=[
            "Show missing values",
            "Recommend the best charts",
            "Which columns are numeric?",
            "Show the top category",
        ],
    )


def _quality_answer(df: pd.DataFrame) -> dict[str, Any]:
    quality = _dataset_quality(df)

    if quality["quality_score"] >= 90:
        label = "excellent"
    elif quality["quality_score"] >= 75:
        label = "good"
    elif quality["quality_score"] >= 60:
        label = "moderate"
    else:
        label = "needs cleaning"

    answer = (
        f"The dataset-quality score is "
        f"{quality['quality_score']:.2f}%, which is {label}. "
        f"I found {quality['missing']:,} missing values and "
        f"{quality['duplicates']:,} duplicate rows across "
        f"{quality['rows']:,} records."
    )

    return _text_response(
        answer,
        intent="dataset_quality",
        suggestions=[
            "Which columns have missing values?",
            "Summarize this dataset",
        ],
    )


def _missing_values_answer(df: pd.DataFrame) -> dict[str, Any]:
    missing = (
        df.isna()
        .sum()
        .sort_values(ascending=False)
    )

    missing = missing[missing > 0]

    if missing.empty:
        return _text_response(
            "No missing values were detected in the dataset.",
            intent="missing_values",
        )

    top_missing = missing.head(12)

    chart = {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "x": [
                    int(value)
                    for value in top_missing.values[::-1]
                ],
                "y": [
                    str(value)
                    for value in top_missing.index[::-1]
                ],
                "name": "Missing Values",
                "hovertemplate": (
                    "<b>%{y}</b><br>"
                    "Missing: %{x:,}<extra></extra>"
                ),
            }
        ],
        "layout": {
            "template": "plotly_white",
            "title": {
                "text": "Missing Values by Column",
                "x": 0.02,
            },
            "height": max(
                360,
                len(top_missing) * 42,
            ),
            "margin": {
                "l": 170,
                "r": 30,
                "t": 60,
                "b": 50,
            },
            "xaxis": {
                "title": "Missing value count",
            },
            "yaxis": {
                "automargin": True,
            },
            "showlegend": False,
        },
    }

    answer = (
        f"The dataset contains {int(missing.sum()):,} missing values. "
        f"The most affected column is {missing.index[0]} with "
        f"{int(missing.iloc[0]):,} missing values."
    )

    return _chart_response(
        answer,
        chart,
        intent="missing_values_chart",
        suggestions=[
            "Summarize this dataset",
            "Show dataset quality",
        ],
    )


def _column_answer(
    df: pd.DataFrame,
    column_type: str,
) -> dict[str, Any]:
    if column_type == "numeric":
        columns = df.select_dtypes(
            include="number"
        ).columns.tolist()
        label = "numeric"
    elif column_type == "categorical":
        columns = df.select_dtypes(
            exclude="number"
        ).columns.tolist()
        label = "categorical or date-like"
    else:
        columns = list(df.columns)
        label = "available"

    if not columns:
        return _text_response(
            f"No {label} columns were detected.",
            intent=f"{column_type}_columns",
        )

    answer = (
        f"I found {len(columns)} {label} columns: "
        + ", ".join(map(str, columns))
        + "."
    )

    return _text_response(
        answer,
        intent=f"{column_type}_columns",
    )


def _top_group_answer(
    df: pd.DataFrame,
    question: str,
    ascending: bool = False,
) -> dict[str, Any]:
    value_column = _detect_business_numeric_column(
        df,
        question,
    )
    category_column = _detect_categorical_column(
        df,
        question,
    )

    if not value_column or not category_column:
        return _text_response(
            "I could not identify both a numeric KPI and a categorical column for this comparison.",
            intent="group_comparison_unavailable",
            suggestions=[
                "Which columns are numeric?",
                "List categorical columns",
            ],
        )

    working = df[
        [category_column, value_column]
    ].copy()

    working[value_column] = pd.to_numeric(
        working[value_column],
        errors="coerce",
    )

    grouped = (
        working.dropna()
        .groupby(category_column)[value_column]
        .sum()
        .sort_values(ascending=ascending)
        .head(10)
    )

    if grouped.empty:
        return _text_response(
            "There was not enough valid data to create this comparison.",
            intent="group_comparison_empty",
        )

    best_name = str(grouped.index[0])
    best_value = float(grouped.iloc[0])

    chart = {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "x": [
                    float(value)
                    for value in grouped.values[::-1]
                ],
                "y": [
                    str(value)
                    for value in grouped.index[::-1]
                ],
                "name": value_column,
                "hovertemplate": (
                    "<b>%{y}</b><br>"
                    f"{value_column}: "
                    "%{x:,.2f}<extra></extra>"
                ),
            }
        ],
        "layout": {
            "template": "plotly_white",
            "title": {
                "text": (
                    f"{'Bottom' if ascending else 'Top'} "
                    f"{category_column} by {value_column}"
                ),
                "x": 0.02,
            },
            "height": max(
                390,
                len(grouped) * 45,
            ),
            "margin": {
                "l": 190,
                "r": 35,
                "t": 65,
                "b": 55,
            },
            "xaxis": {
                "title": value_column,
            },
            "yaxis": {
                "automargin": True,
            },
            "showlegend": False,
        },
    }

    answer = (
        f"The {'lowest' if ascending else 'highest'} "
        f"{category_column} by {value_column} is "
        f"{best_name}, with {_format_number(best_value)}."
    )

    return _chart_response(
        answer,
        chart,
        intent="group_comparison",
        suggestions=[
            f"Show bottom {category_column} by {value_column}",
            f"Summarize {value_column}",
        ],
    )


def _numeric_stat_answer(
    df: pd.DataFrame,
    question: str,
    operation: str,
) -> dict[str, Any]:
    column = _detect_business_numeric_column(
        df,
        question,
    )

    if not column:
        return _text_response(
            "No suitable numeric column was found.",
            intent="numeric_stat_unavailable",
        )

    series = pd.to_numeric(
        df[column],
        errors="coerce",
    ).dropna()

    if series.empty:
        return _text_response(
            f"The column {column} has no valid numeric values.",
            intent="numeric_stat_empty",
        )

    operations = {
        "sum": (
            float(series.sum()),
            "total",
        ),
        "mean": (
            float(series.mean()),
            "average",
        ),
        "max": (
            float(series.max()),
            "maximum",
        ),
        "min": (
            float(series.min()),
            "minimum",
        ),
        "median": (
            float(series.median()),
            "median",
        ),
    }

    value, label = operations[operation]

    return _text_response(
        f"The {label} {column} is {_format_number(value)}.",
        intent=f"numeric_{operation}",
    )


def _correlation_answer(
    df: pd.DataFrame,
    question: str,
) -> dict[str, Any]:
    numeric_df = df.select_dtypes(
        include="number"
    ).copy()

    if numeric_df.shape[1] < 2:
        return _text_response(
            "At least two numeric columns are required for correlation analysis.",
            intent="correlation_unavailable",
        )

    first_column = _find_column_in_question(
        df,
        question,
        numeric_only=True,
    )

    remaining_question = question

    if first_column:
        remaining_question = re.sub(
            re.escape(first_column),
            " ",
            remaining_question,
            flags=re.IGNORECASE,
        )

    second_column = _find_column_in_question(
        df.drop(
            columns=[first_column],
            errors="ignore",
        ),
        remaining_question,
        numeric_only=True,
    )

    if first_column and second_column:
        pair = (
            numeric_df[
                [first_column, second_column]
            ]
            .dropna()
        )

        if pair.empty:
            return _text_response(
                "The selected columns do not have enough overlapping numeric values.",
                intent="correlation_empty",
            )

        correlation = float(
            pair[first_column].corr(
                pair[second_column]
            )
        )

        chart = {
            "data": [
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": pair[first_column].tolist(),
                    "y": pair[second_column].tolist(),
                    "name": "Observations",
                    "hovertemplate": (
                        f"{first_column}: %{{x:,.2f}}<br>"
                        f"{second_column}: %{{y:,.2f}}"
                        "<extra></extra>"
                    ),
                }
            ],
            "layout": {
                "template": "plotly_white",
                "title": {
                    "text": (
                        f"{first_column} vs {second_column}"
                    ),
                    "x": 0.02,
                },
                "height": 440,
                "xaxis": {
                    "title": first_column,
                },
                "yaxis": {
                    "title": second_column,
                },
                "showlegend": False,
            },
        }

        strength = (
            "strong"
            if abs(correlation) >= 0.7
            else "moderate"
            if abs(correlation) >= 0.4
            else "weak"
        )

        direction = (
            "positive"
            if correlation > 0
            else "negative"
            if correlation < 0
            else "neutral"
        )

        answer = (
            f"The correlation between {first_column} and "
            f"{second_column} is {correlation:.3f}, indicating a "
            f"{strength} {direction} relationship."
        )

        return _chart_response(
            answer,
            chart,
            intent="correlation_pair",
        )

    correlation_matrix = numeric_df.corr(
        numeric_only=True
    )

    pairs: list[tuple[str, str, float]] = []

    columns = correlation_matrix.columns.tolist()

    for first_index, first in enumerate(columns):
        for second in columns[first_index + 1:]:
            correlation = correlation_matrix.loc[
                first,
                second,
            ]

            if pd.notna(correlation):
                pairs.append(
                    (
                        str(first),
                        str(second),
                        float(correlation),
                    )
                )

    if not pairs:
        return _text_response(
            "No valid numeric correlations were found.",
            intent="correlation_empty",
        )

    strongest = max(
        pairs,
        key=lambda item: abs(item[2]),
    )

    answer = (
        f"The strongest numeric relationship is between "
        f"{strongest[0]} and {strongest[1]}, with a correlation of "
        f"{strongest[2]:.3f}."
    )

    return _text_response(
        answer,
        intent="correlation_summary",
    )


def _chart_recommendation_answer(
    df: pd.DataFrame,
) -> dict[str, Any]:
    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()
    categorical_columns = df.select_dtypes(
        exclude="number"
    ).columns.tolist()

    recommendations: list[str] = []

    if numeric_columns and categorical_columns:
        recommendations.append(
            "Use a bar chart to compare a numeric KPI across categories."
        )

    if len(numeric_columns) >= 2:
        recommendations.append(
            "Use a scatter plot to examine relationships between numeric columns."
        )

    date_columns = []

    for column in df.columns:
        converted = pd.to_datetime(
            df[column],
            errors="coerce",
        )

        if converted.notna().mean() >= 0.7:
            date_columns.append(str(column))

    if date_columns and numeric_columns:
        recommendations.append(
            "Use a line chart to show a numeric KPI over time."
        )

    if categorical_columns:
        recommendations.append(
            "Use a pie chart only when a categorical column has a small number of meaningful groups."
        )

    if not recommendations:
        recommendations.append(
            "Start with a histogram for a numeric column or a count chart for categories."
        )

    return _text_response(
        " ".join(recommendations),
        intent="chart_recommendation",
        suggestions=[
            "Show the top category",
            "Show a correlation",
        ],
    )


def _forecast_answer(
    df: pd.DataFrame,
    question: str,
) -> dict[str, Any]:
    options = get_forecast_options(df)

    date_column = _find_column_in_question(
        df,
        question,
    )

    if date_column not in options.get(
        "date_columns",
        [],
    ):
        date_column = options.get(
            "default_date_column"
        )

    value_column = _detect_business_numeric_column(
        df,
        question,
    )

    if value_column not in options.get(
        "numeric_columns",
        [],
    ):
        value_column = options.get(
            "default_value_column"
        )

    period_match = re.search(
        r"\b(\d{1,2})\s*(?:month|months|period|periods)\b",
        _normalize(question),
    )

    periods = (
        int(period_match.group(1))
        if period_match
        else 6
    )

    periods = max(
        1,
        min(
            periods,
            24,
        ),
    )

    forecast_result = generate_ai_forecast(
        df=df,
        date_column=date_column,
        value_column=value_column,
        periods=periods,
    )

    if not forecast_result.get("success"):
        return _text_response(
            forecast_result.get(
                "message",
                "Forecast generation failed.",
            ),
            intent="forecast_failed",
        )

    forecast_records = forecast_result.get(
        "forecast",
        [],
    )

    historical_records = forecast_result.get(
        "historical",
        [],
    )

    chart = {
        "data": [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": [
                    item["period"]
                    for item in historical_records
                ],
                "y": [
                    item["value"]
                    for item in historical_records
                ],
                "name": "Historical",
            },
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": [
                    item["period"]
                    for item in forecast_records
                ],
                "y": [
                    item["forecast"]
                    for item in forecast_records
                ],
                "name": "Forecast",
                "line": {
                    "dash": "dash",
                },
            },
        ],
        "layout": {
            "template": "plotly_white",
            "title": {
                "text": (
                    f"{value_column} Forecast"
                ),
                "x": 0.02,
            },
            "height": 440,
            "xaxis": {
                "title": "Period",
            },
            "yaxis": {
                "title": value_column,
            },
            "legend": {
                "orientation": "h",
            },
            "hovermode": "x unified",
        },
    }

    summary = forecast_result.get(
        "summary",
        "Forecast generated successfully.",
    )

    executive_summary = forecast_result.get(
        "executive_summary",
        {},
    )

    if executive_summary.get("strategic_conclusion"):
        summary += (
            " "
            + executive_summary[
                "strategic_conclusion"
            ]
        )

    return _chart_response(
        summary,
        chart,
        intent="forecast",
        suggestions=[
            "What are the top business risks?",
            "What should management do next?",
        ],
    )


def _risk_answer(
    df: pd.DataFrame,
) -> dict[str, Any]:
    options = get_forecast_options(df)

    forecast_result = generate_ai_forecast(
        df=df,
        date_column=options.get(
            "default_date_column"
        ),
        value_column=options.get(
            "default_value_column"
        ),
        periods=6,
    )

    if not forecast_result.get("success"):
        return _text_response(
            forecast_result.get(
                "message",
                "Risk analysis is unavailable.",
            ),
            intent="risk_failed",
        )

    business_risk = forecast_result.get(
        "business_risk",
        {},
    )

    risks = business_risk.get(
        "risks",
        [],
    )

    risk_text = "; ".join(
        (
            f"{risk.get('name', 'Risk')}: "
            f"{risk.get('level', 'Unknown')} "
            f"({risk.get('score', 0)}%)"
        )
        for risk in risks
    )

    answer = (
        f"The overall business-risk level is "
        f"{business_risk.get('overall_level', 'Unknown')} with a score of "
        f"{business_risk.get('overall_score', 0)}%. "
        f"{risk_text}"
    )

    return _text_response(
        answer,
        intent="business_risk",
        suggestions=[
            "What should management do next?",
            "Generate a six month forecast",
        ],
    )


def _recommendation_answer(
    df: pd.DataFrame,
) -> dict[str, Any]:
    options = get_forecast_options(df)

    forecast_result = generate_ai_forecast(
        df=df,
        date_column=options.get(
            "default_date_column"
        ),
        value_column=options.get(
            "default_value_column"
        ),
        periods=6,
    )

    if not forecast_result.get("success"):
        return _text_response(
            forecast_result.get(
                "message",
                "Recommendations are unavailable.",
            ),
            intent="recommendations_failed",
        )

    result = forecast_result.get(
        "ai_recommendations",
        {},
    )

    recommendations = result.get(
        "recommendations",
        [],
    )[:5]

    if not recommendations:
        return _text_response(
            "No business recommendations were generated.",
            intent="recommendations_empty",
        )

    answer = (
        f"Overall action level: "
        f"{result.get('overall_action_level', 'Unknown')}. "
    )

    answer += " ".join(
        (
            f"{index + 1}. "
            f"{recommendation.get('title', 'Recommendation')} — "
            f"{recommendation.get('action', '')}"
        )
        for index, recommendation in enumerate(
            recommendations
        )
    )

    return _text_response(
        answer,
        intent="business_recommendations",
        suggestions=[
            "What are the top business risks?",
            "Summarize this dataset",
        ],
    )


def answer_copilot_question(
    df: pd.DataFrame,
    question: str,
) -> dict[str, Any]:
    """
    Main Enterprise BI Copilot entry point.
    """

    if df is None or df.empty:
        return {
            "success": False,
            "response_type": "text",
            "intent": "empty_dataset",
            "answer": "The uploaded dataset is empty.",
        }

    normalized = _normalize(question)

    if not normalized:
        return {
            "success": False,
            "response_type": "text",
            "intent": "empty_question",
            "answer": "Please enter a question about the dataset.",
        }

    if any(
        phrase in normalized
        for phrase in [
            "summarize",
            "summary",
            "overview",
            "describe dataset",
            "about this dataset",
        ]
    ):
        return _summary_answer(df)

    if any(
        phrase in normalized
        for phrase in [
            "quality score",
            "dataset quality",
            "data quality",
            "health score",
        ]
    ):
        return _quality_answer(df)

    if any(
        phrase in normalized
        for phrase in [
            "missing",
            "null",
            "empty values",
        ]
    ):
        return _missing_values_answer(df)

    if (
        "numeric column" in normalized
        or "numerical column" in normalized
    ):
        return _column_answer(
            df,
            "numeric",
        )

    if any(
        phrase in normalized
        for phrase in [
            "categorical column",
            "category columns",
            "text column",
        ]
    ):
        return _column_answer(
            df,
            "categorical",
        )

    if any(
        phrase in normalized
        for phrase in [
            "all columns",
            "list columns",
            "column names",
        ]
    ):
        return _column_answer(
            df,
            "all",
        )

    if any(
        phrase in normalized
        for phrase in [
            "recommend chart",
            "best chart",
            "chart suggestion",
            "which chart",
        ]
    ):
        return _chart_recommendation_answer(df)

    if any(
        phrase in normalized
        for phrase in [
            "correlation",
            "relationship between",
            "related to",
        ]
    ):
        return _correlation_answer(
            df,
            question,
        )

    if any(
        phrase in normalized
        for phrase in [
            "forecast",
            "predict",
            "prediction",
            "future value",
            "next month",
            "next quarter",
            "next year",
        ]
    ):
        return _forecast_answer(
            df,
            question,
        )

    if any(
        phrase in normalized
        for phrase in [
            "business risk",
            "top risk",
            "risk level",
            "forecast risk",
        ]
    ):
        return _risk_answer(df)

    if any(
        phrase in normalized
        for phrase in [
            "what should management",
            "recommendation",
            "recommend actions",
            "what should we do",
            "next action",
        ]
    ):
        return _recommendation_answer(df)

    if any(
        phrase in normalized
        for phrase in [
            "bottom",
            "lowest category",
            "worst category",
        ]
    ):
        return _top_group_answer(
            df,
            question,
            ascending=True,
        )

    if any(
        phrase in normalized
        for phrase in [
            "top",
            "highest category",
            "best category",
            "highest value",
            "best performing",
        ]
    ):
        return _top_group_answer(
            df,
            question,
            ascending=False,
        )

    if any(
        phrase in normalized
        for phrase in [
            "average",
            "mean",
        ]
    ):
        return _numeric_stat_answer(
            df,
            question,
            "mean",
        )

    if "median" in normalized:
        return _numeric_stat_answer(
            df,
            question,
            "median",
        )

    if any(
        phrase in normalized
        for phrase in [
            "maximum",
            "highest",
            "max ",
        ]
    ):
        return _numeric_stat_answer(
            df,
            question,
            "max",
        )

    if any(
        phrase in normalized
        for phrase in [
            "minimum",
            "lowest",
            "min ",
        ]
    ):
        return _numeric_stat_answer(
            df,
            question,
            "min",
        )

    if any(
        phrase in normalized
        for phrase in [
            "total",
            "sum",
        ]
    ):
        return _numeric_stat_answer(
            df,
            question,
            "sum",
        )

    return _text_response(
        (
            "I could not confidently map that question to a supported "
            "analysis. Try asking for a dataset summary, missing values, "
            "numeric columns, top categories, correlations, forecasts, "
            "business risks, or management recommendations."
        ),
        intent="unsupported_question",
        suggestions=[
            "Summarize this dataset",
            "Show missing values",
            "Recommend the best charts",
            "Generate a six month forecast",
            "What are the top business risks?",
        ],
    )