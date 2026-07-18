from __future__ import annotations

import html
import math
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd


# =====================================================
# COMMON HELPERS
# =====================================================

def _safe_float(value: Any) -> float:
    try:
        number = float(value)

        if math.isnan(number) or math.isinf(number):
            return 0.0

        return number

    except (TypeError, ValueError):
        return 0.0


def _format_number(value: Any) -> str:
    number = _safe_float(value)
    absolute = abs(number)

    if absolute >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"

    if absolute >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"

    if absolute >= 1_000:
        return f"{number / 1_000:.2f}K"

    return f"{number:,.2f}"


def _require_numeric_column(
    dataframe: pd.DataFrame,
    column: str,
) -> pd.Series:
    column = str(column or "").strip()

    if not column:
        raise ValueError(
            "Please select a numeric metric column."
        )

    if column not in dataframe.columns:
        raise ValueError(
            f"Column '{column}' was not found."
        )

    series = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    ).dropna()

    if series.empty:
        raise ValueError(
            f"Column '{column}' has no valid numeric values."
        )

    return series


def get_numeric_columns(
    dataframe: pd.DataFrame,
) -> list[str]:
    return (
        dataframe.select_dtypes(include="number")
        .columns.astype(str)
        .tolist()
    )


# =====================================================
# PHASE 4 GENERAL ENTERPRISE AI FUNCTIONS
# =====================================================

def dataset_profile(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    numeric = dataframe.select_dtypes(
        include="number"
    )

    categorical = dataframe.select_dtypes(
        exclude="number"
    )

    total_cells = max(
        int(dataframe.size),
        1,
    )

    missing_values = int(
        dataframe.isna().sum().sum()
    )

    return {
        "rows": int(len(dataframe)),
        "columns": int(dataframe.shape[1]),
        "numeric_columns": int(numeric.shape[1]),
        "categorical_columns": int(categorical.shape[1]),
        "missing_values": missing_values,
        "duplicates": int(
            dataframe.duplicated().sum()
        ),
        "completeness": round(
            100 * (
                1
                - missing_values / total_cells
            ),
            2,
        ),
    }


def generate_kpis(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]]:
    profile = dataset_profile(
        dataframe
    )

    kpis = [
        {
            "title": "Total Rows",
            "value": f"{profile['rows']:,}",
            "subtitle": "Records available",
        },
        {
            "title": "Data Completeness",
            "value": f"{profile['completeness']}%",
            "subtitle": "Non-missing cells",
        },
        {
            "title": "Numeric Fields",
            "value": str(
                profile["numeric_columns"]
            ),
            "subtitle": "Quantitative columns",
        },
        {
            "title": "Duplicates",
            "value": f"{profile['duplicates']:,}",
            "subtitle": "Repeated records",
        },
    ]

    numeric = dataframe.select_dtypes(
        include="number"
    )

    for column in numeric.columns[:4]:
        series = pd.to_numeric(
            numeric[column],
            errors="coerce",
        ).dropna()

        if series.empty:
            continue

        kpis.append(
            {
                "title": f"Total {column}",
                "value": _format_number(
                    series.sum()
                ),
                "subtitle": (
                    f"Average "
                    f"{_format_number(series.mean())}"
                ),
            }
        )

    return kpis[:8]


def generate_dashboard_charts(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]]:
    numeric_columns = get_numeric_columns(
        dataframe
    )

    categorical_columns = [
        str(column)
        for column in dataframe.columns
        if str(column) not in numeric_columns
    ]

    charts: list[dict[str, Any]] = []

    if numeric_columns:
        column = numeric_columns[0]

        series = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        ).dropna()

        if not series.empty:
            bin_count = min(
                12,
                max(
                    5,
                    int(
                        math.sqrt(
                            len(series)
                        )
                    ),
                ),
            )

            counts, edges = np.histogram(
                series,
                bins=bin_count,
            )

            charts.append(
                {
                    "type": "bar",
                    "title": (
                        f"Distribution of {column}"
                    ),
                    "x": [
                        (
                            f"{edges[index]:.1f}–"
                            f"{edges[index + 1]:.1f}"
                        )
                        for index in range(
                            len(edges) - 1
                        )
                    ],
                    "y": counts.astype(int).tolist(),
                }
            )

    if categorical_columns:
        column = categorical_columns[0]

        counts = (
            dataframe[column]
            .astype(str)
            .value_counts()
            .head(10)
        )

        charts.append(
            {
                "type": "pie",
                "title": f"Top {column}",
                "labels": (
                    counts.index
                    .astype(str)
                    .tolist()
                ),
                "values": (
                    counts.values
                    .astype(int)
                    .tolist()
                ),
            }
        )

    if (
        numeric_columns
        and categorical_columns
    ):
        numeric = numeric_columns[0]
        category = categorical_columns[0]

        grouped = (
            dataframe.groupby(
                category,
                dropna=False,
            )[numeric]
            .sum(min_count=1)
            .sort_values(
                ascending=False
            )
            .head(10)
        )

        charts.append(
            {
                "type": "bar",
                "title": (
                    f"{numeric} by {category}"
                ),
                "x": (
                    grouped.index
                    .astype(str)
                    .tolist()
                ),
                "y": [
                    _safe_float(value)
                    for value in grouped.values
                ],
            }
        )

    if len(numeric_columns) >= 2:
        x_column = numeric_columns[0]
        y_column = numeric_columns[1]

        subset = (
            dataframe[
                [
                    x_column,
                    y_column,
                ]
            ]
            .apply(
                pd.to_numeric,
                errors="coerce",
            )
            .dropna()
            .head(500)
        )

        charts.append(
            {
                "type": "scatter",
                "title": (
                    f"{y_column} vs {x_column}"
                ),
                "x": (
                    subset[x_column]
                    .astype(float)
                    .tolist()
                ),
                "y": (
                    subset[y_column]
                    .astype(float)
                    .tolist()
                ),
                "x_label": x_column,
                "y_label": y_column,
            }
        )

    return charts


def generate_insights(
    dataframe: pd.DataFrame,
) -> list[dict[str, str]]:
    profile = dataset_profile(
        dataframe
    )

    insights: list[
        dict[str, str]
    ] = []

    if profile["missing_values"] > 0:
        insights.append(
            {
                "title": (
                    "Data quality issue detected"
                ),
                "message": (
                    f"The dataset contains "
                    f"{profile['missing_values']:,} "
                    "missing values."
                ),
                "severity": "warning",
            }
        )
    else:
        insights.append(
            {
                "title": (
                    "Strong data completeness"
                ),
                "message": (
                    "No missing values were "
                    "detected."
                ),
                "severity": "positive",
            }
        )

    if profile["duplicates"] > 0:
        insights.append(
            {
                "title": (
                    "Duplicate records detected"
                ),
                "message": (
                    f"{profile['duplicates']:,} "
                    "duplicate rows may influence "
                    "totals and model training."
                ),
                "severity": "warning",
            }
        )

    numeric = dataframe.select_dtypes(
        include="number"
    )

    for column in numeric.columns[:4]:
        series = pd.to_numeric(
            numeric[column],
            errors="coerce",
        ).dropna()

        if len(series) < 5:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        if iqr <= 0:
            continue

        outliers = series[
            (series < q1 - 1.5 * iqr)
            | (series > q3 + 1.5 * iqr)
        ]

        if len(outliers) > 0:
            insights.append(
                {
                    "title": (
                        f"Outliers in {column}"
                    ),
                    "message": (
                        f"{len(outliers):,} "
                        "potential outliers were "
                        f"detected in {column}."
                    ),
                    "severity": "info",
                }
            )

    if len(numeric.columns) >= 2:
        correlation = numeric.corr(
            numeric_only=True
        ).abs()

        if not correlation.empty:
            np.fill_diagonal(
                correlation.values,
                0,
            )

            maximum = correlation.max().max()

            if (
                not pd.isna(maximum)
                and maximum > 0
            ):
                row_index, column_index = np.where(
                    correlation.values
                    == maximum
                )

                first = correlation.index[
                    row_index[0]
                ]

                second = correlation.columns[
                    column_index[0]
                ]

                insights.append(
                    {
                        "title": (
                            "Strongest numeric "
                            "relationship"
                        ),
                        "message": (
                            f"{first} and {second} "
                            "have an absolute "
                            f"correlation of "
                            f"{maximum:.2f}."
                        ),
                        "severity": "positive",
                    }
                )

    return insights[:8]


def generate_recommendations(
    dataframe: pd.DataFrame,
) -> list[str]:
    profile = dataset_profile(
        dataframe
    )

    recommendations: list[str] = []

    if profile["missing_values"] > 0:
        recommendations.append(
            "Treat missing values before "
            "publishing dashboards or "
            "training models."
        )

    if profile["duplicates"] > 0:
        recommendations.append(
            "Review or remove duplicate rows "
            "before calculating final totals."
        )

    if profile["numeric_columns"] >= 2:
        recommendations.append(
            "Use correlation and feature "
            "importance analysis to identify "
            "important business drivers."
        )

    recommendations.extend(
        [
            (
                "Validate generated insights "
                "with business stakeholders."
            ),
            (
                "Schedule periodic dataset "
                "refreshes when source data "
                "changes."
            ),
        ]
    )

    return recommendations


def executive_report(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    profile = dataset_profile(
        dataframe
    )

    return {
        "summary": (
            f"The dataset contains "
            f"{profile['rows']:,} records and "
            f"{profile['columns']} columns with "
            f"{profile['completeness']}% "
            "completeness."
        ),
        "profile": profile,
        "insights": generate_insights(
            dataframe
        ),
        "recommendations": (
            generate_recommendations(
                dataframe
            )
        ),
        "kpis": generate_kpis(
            dataframe
        ),
    }


def copilot_answer(
    dataframe: pd.DataFrame,
    question: str,
) -> dict[str, Any]:
    question_lower = str(
        question or ""
    ).lower().strip()

    profile = dataset_profile(
        dataframe
    )

    if not question_lower:
        return {
            "answer": (
                "Ask a question about the "
                "active dataset."
            )
        }

    if (
        "summary" in question_lower
        or "overview" in question_lower
    ):
        report = executive_report(
            dataframe
        )

        return {
            "answer": report["summary"],
            "data": report,
        }

    if "missing" in question_lower:
        missing = (
            dataframe.isna()
            .sum()
            .sort_values(
                ascending=False
            )
        )

        return {
            "answer": (
                f"The dataset contains "
                f"{profile['missing_values']:,} "
                "missing values."
            ),
            "rows": [
                {
                    "column": str(column),
                    "missing": int(value),
                }
                for column, value
                in missing.items()
                if value > 0
            ][:20],
        }

    if "duplicate" in question_lower:
        return {
            "answer": (
                f"The dataset contains "
                f"{profile['duplicates']:,} "
                "duplicate rows."
            )
        }

    for operation in [
        "sum",
        "average",
        "mean",
        "maximum",
        "minimum",
    ]:
        if operation not in question_lower:
            continue

        for column in get_numeric_columns(
            dataframe
        ):
            if column.lower() not in question_lower:
                continue

            series = _require_numeric_column(
                dataframe,
                column,
            )

            if operation == "sum":
                value = series.sum()
            elif operation in {
                "average",
                "mean",
            }:
                value = series.mean()
            elif operation == "maximum":
                value = series.max()
            else:
                value = series.min()

            return {
                "answer": (
                    f"The {operation} of "
                    f"{column} is "
                    f"{_format_number(value)}."
                )
            }

    return {
        "answer": (
            "Try asking for a dataset summary, "
            "missing values, duplicate count, "
            "or a sum/average/minimum/maximum "
            "of a numeric column."
        )
    }


# =====================================================
# FUNCTIONS REQUIRED BY enterprise_ai_routes.py
# =====================================================

def calculate_business_health(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    profile = dataset_profile(
        dataframe
    )

    completeness_score = float(
        profile["completeness"]
    )

    duplicate_rate = (
        profile["duplicates"]
        / max(
            profile["rows"],
            1,
        )
    ) * 100

    duplicate_score = max(
        0.0,
        100.0 - duplicate_rate,
    )

    numeric_score = min(
        100.0,
        (
            profile["numeric_columns"]
            / max(
                profile["columns"],
                1,
            )
        )
        * 100
        + 25,
    )

    health_score = round(
        (
            completeness_score * 0.55
            + duplicate_score * 0.30
            + numeric_score * 0.15
        ),
        2,
    )

    if health_score >= 85:
        status = "Excellent"
    elif health_score >= 70:
        status = "Good"
    elif health_score >= 50:
        status = "Needs Attention"
    else:
        status = "Critical"

    return {
        "success": True,
        "health_score": health_score,
        "status": status,
        "profile": profile,
        "components": {
            "data_completeness": round(
                completeness_score,
                2,
            ),
            "duplicate_quality": round(
                duplicate_score,
                2,
            ),
            "analytical_readiness": round(
                numeric_score,
                2,
            ),
        },
        "recommendations": (
            generate_recommendations(
                dataframe
            )
        ),
    }


def generate_kpi_narration(
    dataframe: pd.DataFrame,
    metric_column: str,
) -> dict[str, Any]:
    series = _require_numeric_column(
        dataframe,
        metric_column,
    )

    total = _safe_float(
        series.sum()
    )

    average = _safe_float(
        series.mean()
    )

    minimum = _safe_float(
        series.min()
    )

    maximum = _safe_float(
        series.max()
    )

    median = _safe_float(
        series.median()
    )

    standard_deviation = _safe_float(
        series.std()
    )

    narration = (
        f"{metric_column} has a total value of "
        f"{_format_number(total)} across "
        f"{len(series):,} valid records. "
        f"The average is "
        f"{_format_number(average)}, while the "
        f"median is {_format_number(median)}. "
        f"Values range from "
        f"{_format_number(minimum)} to "
        f"{_format_number(maximum)}."
    )

    if average != 0:
        variability = (
            standard_deviation
            / abs(average)
        ) * 100

        if variability > 100:
            narration += (
                " The metric shows very high "
                "variability."
            )
        elif variability > 50:
            narration += (
                " The metric shows moderate to "
                "high variability."
            )
        else:
            narration += (
                " The metric appears relatively "
                "stable."
            )

    return {
        "success": True,
        "metric_column": metric_column,
        "narration": narration,
        "statistics": {
            "count": int(
                len(series)
            ),
            "total": total,
            "average": average,
            "median": median,
            "minimum": minimum,
            "maximum": maximum,
            "standard_deviation": (
                standard_deviation
            ),
        },
    }


def run_what_if_analysis(
    dataframe: pd.DataFrame,
    metric_column: str,
    change_percent: float,
) -> dict[str, Any]:
    series = _require_numeric_column(
        dataframe,
        metric_column,
    )

    change_percent = _safe_float(
        change_percent
    )

    base_total = _safe_float(
        series.sum()
    )

    multiplier = (
        1
        + change_percent / 100
    )

    projected_total = (
        base_total * multiplier
    )

    absolute_change = (
        projected_total - base_total
    )

    return {
        "success": True,
        "metric_column": metric_column,
        "change_percent": change_percent,
        "base_total": base_total,
        "projected_total": projected_total,
        "absolute_change": absolute_change,
        "direction": (
            "increase"
            if absolute_change > 0
            else (
                "decrease"
                if absolute_change < 0
                else "no change"
            )
        ),
        "narration": (
            f"A {change_percent:.2f}% change in "
            f"{metric_column} would move the "
            f"total from "
            f"{_format_number(base_total)} to "
            f"{_format_number(projected_total)}, "
            f"a difference of "
            f"{_format_number(absolute_change)}."
        ),
    }


def build_scenario_comparison(
    dataframe: pd.DataFrame,
    metric_column: str,
    optimistic_percent: float = 10,
    expected_percent: float = 0,
    pessimistic_percent: float = -10,
) -> dict[str, Any]:
    series = _require_numeric_column(
        dataframe,
        metric_column,
    )

    base_total = _safe_float(
        series.sum()
    )

    definitions = [
        (
            "Optimistic",
            _safe_float(
                optimistic_percent
            ),
        ),
        (
            "Expected",
            _safe_float(
                expected_percent
            ),
        ),
        (
            "Pessimistic",
            _safe_float(
                pessimistic_percent
            ),
        ),
    ]

    scenarios = []

    for name, change_percent in definitions:
        projected_total = (
            base_total
            * (
                1
                + change_percent / 100
            )
        )

        scenarios.append(
            {
                "name": name,
                "change_percent": (
                    change_percent
                ),
                "projected_total": (
                    projected_total
                ),
                "absolute_change": (
                    projected_total
                    - base_total
                ),
            }
        )

    return {
        "success": True,
        "metric_column": metric_column,
        "base_total": base_total,
        "scenarios": scenarios,
    }


def evaluate_goal_progress(
    current_value: float,
    target_value: float,
) -> dict[str, Any]:
    current = _safe_float(
        current_value
    )

    target = _safe_float(
        target_value
    )

    if target == 0:
        progress_percent = (
            100.0
            if current >= 0
            else 0.0
        )
    else:
        progress_percent = (
            current / target
        ) * 100

    display_percent = round(
        max(
            0.0,
            progress_percent,
        ),
        2,
    )

    remaining = (
        target - current
    )

    if progress_percent >= 100:
        status = "Completed"
    elif progress_percent >= 75:
        status = "On Track"
    elif progress_percent >= 40:
        status = "In Progress"
    else:
        status = "At Risk"

    return {
        "current_value": current,
        "target_value": target,
        "progress_percent": (
            display_percent
        ),
        "remaining_value": remaining,
        "status": status,
        "is_completed": (
            progress_percent >= 100
        ),
    }


def generate_executive_report(
    dataframe: pd.DataFrame,
    filename: str,
    metric_column: str | None = None,
) -> dict[str, Any]:
    numeric_columns = get_numeric_columns(
        dataframe
    )

    selected_metric = str(
        metric_column or ""
    ).strip()

    if not selected_metric:
        selected_metric = (
            numeric_columns[0]
            if numeric_columns
            else ""
        )

    report = {
        "success": True,
        "filename": filename,
        "generated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "health": (
            calculate_business_health(
                dataframe
            )
        ),
        "profile": dataset_profile(
            dataframe
        ),
        "kpis": generate_kpis(
            dataframe
        ),
        "insights": generate_insights(
            dataframe
        ),
        "recommendations": (
            generate_recommendations(
                dataframe
            )
        ),
        "metric_column": (
            selected_metric
            if selected_metric
            else None
        ),
        "metric_narration": None,
    }

    if selected_metric:
        report[
            "metric_narration"
        ] = generate_kpi_narration(
            dataframe,
            selected_metric,
        )

    return report


def render_executive_report_html(
    report: dict[str, Any],
) -> str:
    filename = html.escape(
        str(
            report.get(
                "filename",
                "Dataset",
            )
        )
    )

    generated_at = html.escape(
        str(
            report.get(
                "generated_at",
                "",
            )
        )
    )

    health = report.get(
        "health",
        {},
    )

    profile = report.get(
        "profile",
        {},
    )

    kpi_cards = "".join(
        (
            '<div class="kpi">'
            f"<span>{html.escape(str(kpi.get('title', '')))}</span>"
            f"<strong>{html.escape(str(kpi.get('value', '')))}</strong>"
            f"<small>{html.escape(str(kpi.get('subtitle', '')))}</small>"
            "</div>"
        )
        for kpi in report.get(
            "kpis",
            [],
        )
    )

    insight_cards = "".join(
        (
            '<article class="item">'
            f"<h3>{html.escape(str(item.get('title', '')))}</h3>"
            f"<p>{html.escape(str(item.get('message', '')))}</p>"
            "</article>"
        )
        for item in report.get(
            "insights",
            [],
        )
    )

    recommendation_items = "".join(
        (
            "<li>"
            f"{html.escape(str(item))}"
            "</li>"
        )
        for item in report.get(
            "recommendations",
            [],
        )
    )

    narration_data = report.get(
        "metric_narration"
    )

    narration_section = ""

    if narration_data:
        narration_section = (
            '<section class="panel">'
            "<h2>Metric Narration</h2>"
            f"<p>{html.escape(str(narration_data.get('narration', '')))}</p>"
            "</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Executive AI Report - {filename}</title>
<style>
body {{
    margin: 0;
    padding: 36px;
    font-family: Arial, sans-serif;
    color: #0f172a;
    background: #f8fafc;
}}
.hero {{
    padding: 28px;
    border-radius: 20px;
    color: white;
    background: linear-gradient(135deg, #0f172a, #2563eb, #7c3aed);
}}
.hero h1 {{
    margin: 0 0 8px;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin: 22px 0;
}}
.kpi, .panel, .item {{
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    background: white;
}}
.kpi {{
    padding: 18px;
}}
.kpi span, .kpi small, .kpi strong {{
    display: block;
}}
.kpi strong {{
    margin: 8px 0;
    color: #1d4ed8;
    font-size: 26px;
}}
.panel {{
    padding: 22px;
    margin-bottom: 18px;
}}
.item {{
    padding: 14px;
    margin-bottom: 10px;
}}
small, .muted {{
    color: #64748b;
}}
</style>
</head>
<body>
<section class="hero">
<h1>Executive AI Report</h1>
<p>{filename}</p>
<p>Generated: {generated_at}</p>
</section>

<section class="panel">
<h2>Business Health</h2>
<p>
<strong>{html.escape(str(health.get("health_score", 0)))}/100</strong>
— {html.escape(str(health.get("status", "Unknown")))}
</p>
<p>
Rows: {html.escape(str(profile.get("rows", 0)))} |
Columns: {html.escape(str(profile.get("columns", 0)))} |
Completeness: {html.escape(str(profile.get("completeness", 0)))}%
</p>
</section>

<div class="grid">
{kpi_cards}
</div>

{narration_section}

<section class="panel">
<h2>Key Insights</h2>
{insight_cards or "<p>No insights were generated.</p>"}
</section>

<section class="panel">
<h2>Recommendations</h2>
<ol>
{recommendation_items}
</ol>
</section>
</body>
</html>"""


__all__ = [
    "build_scenario_comparison",
    "calculate_business_health",
    "copilot_answer",
    "dataset_profile",
    "evaluate_goal_progress",
    "executive_report",
    "generate_dashboard_charts",
    "generate_executive_report",
    "generate_insights",
    "generate_kpi_narration",
    "generate_kpis",
    "generate_recommendations",
    "get_numeric_columns",
    "render_executive_report_html",
    "run_what_if_analysis",
]