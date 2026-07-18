"""
AI Business Recommendation Service

This module converts forecasting results and business-risk
signals into prioritized, actionable recommendations.
"""

from typing import Any


def _normalize_level(value: str) -> str:
    return str(value or "").strip().lower()


def _priority_rank(priority: str) -> int:
    ranking = {
        "High": 3,
        "Medium": 2,
        "Low": 1
    }

    return ranking.get(
        priority,
        0
    )


def _build_recommendation(
    title: str,
    category: str,
    priority: str,
    action: str,
    rationale: str,
    expected_impact: str,
    timeline: str,
    confidence: float
) -> dict[str, Any]:
    return {
        "title": title,
        "category": category,
        "priority": priority,
        "action": action,
        "rationale": rationale,
        "expected_impact": expected_impact,
        "timeline": timeline,
        "confidence": round(
            max(
                0,
                min(
                    100,
                    float(confidence)
                )
            ),
            2
        )
    }


def _trend_recommendations(
    metrics: dict[str, Any],
    confidence_score: float,
    value_column: str
) -> list[dict[str, Any]]:
    recommendations = []

    direction = _normalize_level(
        metrics.get(
            "trend_direction",
            "stable"
        )
    )

    growth_rate = float(
        metrics.get(
            "historical_growth_rate",
            0
        )
    )

    recent_change = float(
        metrics.get(
            "recent_change",
            0
        )
    )

    if direction == "upward":
        recommendations.append(
            _build_recommendation(
                title="Prepare for KPI Growth",
                category="Growth Opportunity",
                priority=(
                    "High"
                    if growth_rate >= 20
                    else "Medium"
                ),
                action=(
                    f"Increase operational capacity, inventory, "
                    f"or supporting resources for {value_column}."
                ),
                rationale=(
                    f"The historical direction is upward with "
                    f"a growth rate of {growth_rate:.2f}%."
                ),
                expected_impact=(
                    "Improved readiness for higher demand and "
                    "reduced risk of capacity constraints."
                ),
                timeline="Next 30–60 days",
                confidence=confidence_score
            )
        )

    elif direction == "downward":
        recommendations.append(
            _build_recommendation(
                title="Launch Decline Recovery Plan",
                category="Risk Mitigation",
                priority="High",
                action=(
                    f"Investigate the causes of declining "
                    f"{value_column} and define corrective actions."
                ),
                rationale=(
                    f"The historical trend is downward with "
                    f"a growth rate of {growth_rate:.2f}%."
                ),
                expected_impact=(
                    "Earlier identification of performance issues "
                    "and faster recovery."
                ),
                timeline="Immediate",
                confidence=confidence_score
            )
        )

    else:
        recommendations.append(
            _build_recommendation(
                title="Maintain Stable Operations",
                category="Operational Planning",
                priority="Low",
                action=(
                    f"Maintain current operating levels for "
                    f"{value_column} while monitoring new changes."
                ),
                rationale=(
                    "The historical trend is relatively stable."
                ),
                expected_impact=(
                    "Avoids unnecessary operational changes while "
                    "preserving monitoring discipline."
                ),
                timeline="Ongoing",
                confidence=confidence_score
            )
        )

    if recent_change >= 15:
        recommendations.append(
            _build_recommendation(
                title="Validate Recent Growth Spike",
                category="Data Validation",
                priority="Medium",
                action=(
                    "Check whether the latest increase is caused by "
                    "seasonality, a one-time event, or genuine growth."
                ),
                rationale=(
                    f"The latest period increased by "
                    f"{recent_change:.2f}%."
                ),
                expected_impact=(
                    "Reduces the risk of overcommitting resources "
                    "based on a temporary spike."
                ),
                timeline="Within 2 weeks",
                confidence=max(
                    50,
                    confidence_score - 5
                )
            )
        )

    elif recent_change <= -15:
        recommendations.append(
            _build_recommendation(
                title="Create Decline Alert",
                category="Monitoring",
                priority="High",
                action=(
                    "Set an alert for continued decline in the next "
                    "reporting period."
                ),
                rationale=(
                    f"The latest period declined by "
                    f"{abs(recent_change):.2f}%."
                ),
                expected_impact=(
                    "Supports faster intervention if the decline "
                    "continues."
                ),
                timeline="Immediate",
                confidence=confidence_score
            )
        )

    return recommendations


def _risk_recommendations(
    business_risk: dict[str, Any],
    confidence_score: float
) -> list[dict[str, Any]]:
    recommendations = []

    risks = business_risk.get(
        "risks",
        []
    )

    for risk in risks:
        risk_name = str(
            risk.get(
                "name",
                ""
            )
        )

        risk_level = str(
            risk.get(
                "level",
                "Low"
            )
        )

        risk_score = float(
            risk.get(
                "score",
                0
            )
        )

        priority = (
            "High"
            if risk_level == "High"
            else "Medium"
            if risk_level == "Medium"
            else "Low"
        )

        if risk_name == "Forecast Confidence":
            if risk_score >= 45:
                recommendations.append(
                    _build_recommendation(
                        title="Improve Forecast Reliability",
                        category="Model Reliability",
                        priority=priority,
                        action=(
                            "Add more historical periods, review missing "
                            "months, and refresh the model regularly."
                        ),
                        rationale=(
                            f"Forecast-confidence risk is "
                            f"{risk_score:.2f}%."
                        ),
                        expected_impact=(
                            "More reliable forecasts and stronger "
                            "planning confidence."
                        ),
                        timeline="Before next planning cycle",
                        confidence=max(
                            40,
                            confidence_score
                        )
                    )
                )

        elif risk_name == "Business Volatility":
            if risk_score >= 30:
                recommendations.append(
                    _build_recommendation(
                        title="Build a Volatility Buffer",
                        category="Operational Risk",
                        priority=priority,
                        action=(
                            "Maintain a safety buffer in inventory, "
                            "capacity, or working capital."
                        ),
                        rationale=(
                            f"Business-volatility risk is "
                            f"{risk_score:.2f}%."
                        ),
                        expected_impact=(
                            "Improved resilience against sudden changes."
                        ),
                        timeline="Next 30 days",
                        confidence=confidence_score
                    )
                )

        elif risk_name == "Forecast Uncertainty":
            if risk_score >= 30:
                recommendations.append(
                    _build_recommendation(
                        title="Use Scenario-Based Planning",
                        category="Decision Planning",
                        priority=priority,
                        action=(
                            "Plan using lower-bound, expected, and "
                            "upper-bound forecast scenarios."
                        ),
                        rationale=(
                            f"Forecast-uncertainty risk is "
                            f"{risk_score:.2f}%."
                        ),
                        expected_impact=(
                            "Reduces overreliance on a single forecast value."
                        ),
                        timeline="Current planning cycle",
                        confidence=confidence_score
                    )
                )

        elif risk_name == "Trend Risk":
            if risk_score >= 45:
                recommendations.append(
                    _build_recommendation(
                        title="Review Trend Drivers",
                        category="Strategic Review",
                        priority=priority,
                        action=(
                            "Analyze products, regions, customers, or "
                            "operational factors driving the trend."
                        ),
                        rationale=(
                            f"Trend risk is {risk_score:.2f}%."
                        ),
                        expected_impact=(
                            "Improves understanding of root causes and "
                            "supports targeted action."
                        ),
                        timeline="Within 30 days",
                        confidence=confidence_score
                    )
                )

    return recommendations


def _confidence_recommendations(
    confidence_score: float,
    validation_metrics: dict[str, Any]
) -> list[dict[str, Any]]:
    recommendations = []

    mape = float(
        validation_metrics.get(
            "mape",
            0
        )
    )

    if confidence_score < 50:
        recommendations.append(
            _build_recommendation(
                title="Treat Forecast as Directional",
                category="Decision Confidence",
                priority="High",
                action=(
                    "Use the forecast as directional guidance rather "
                    "than a fixed operating target."
                ),
                rationale=(
                    f"Forecast confidence is only "
                    f"{confidence_score:.2f}%."
                ),
                expected_impact=(
                    "Reduces the risk of making rigid decisions from "
                    "an uncertain forecast."
                ),
                timeline="Immediate",
                confidence=confidence_score
            )
        )

    elif confidence_score < 70:
        recommendations.append(
            _build_recommendation(
                title="Apply Management Review",
                category="Governance",
                priority="Medium",
                action=(
                    "Review forecast assumptions with business owners "
                    "before final approval."
                ),
                rationale=(
                    f"Forecast confidence is moderate at "
                    f"{confidence_score:.2f}%."
                ),
                expected_impact=(
                    "Combines model results with operational context."
                ),
                timeline="Before approval",
                confidence=confidence_score
            )
        )

    if mape > 30:
        recommendations.append(
            _build_recommendation(
                title="Investigate Forecast Error",
                category="Model Improvement",
                priority="High",
                action=(
                    "Check for seasonality, outliers, structural breaks, "
                    "and inconsistent historical data."
                ),
                rationale=(
                    f"MAPE is high at {mape:.2f}%."
                ),
                expected_impact=(
                    "May reduce forecast error and improve model selection."
                ),
                timeline="Before next forecast run",
                confidence=max(
                    40,
                    confidence_score
                )
            )
        )

    return recommendations


def generate_business_recommendations(
    forecast_result: dict[str, Any]
) -> dict[str, Any]:
    """
    Generate prioritized business recommendations from a
    successful forecast result.
    """

    if not forecast_result.get(
        "success"
    ):
        return {
            "success": False,
            "message": (
                "A successful forecast result is required "
                "to generate recommendations."
            ),
            "recommendations": []
        }

    metrics = forecast_result.get(
        "metrics",
        {}
    )

    validation_metrics = (
        forecast_result.get(
            "validation_metrics",
            {}
        )
    )

    business_risk = (
        forecast_result.get(
            "business_risk",
            {}
        )
    )

    value_column = str(
        forecast_result.get(
            "value_column",
            "selected KPI"
        )
    )

    confidence_score = float(
        metrics.get(
            "confidence_score",
            0
        )
    )

    recommendations = []

    recommendations.extend(
        _trend_recommendations(
            metrics=metrics,
            confidence_score=confidence_score,
            value_column=value_column
        )
    )

    recommendations.extend(
        _risk_recommendations(
            business_risk=business_risk,
            confidence_score=confidence_score
        )
    )

    recommendations.extend(
        _confidence_recommendations(
            confidence_score=confidence_score,
            validation_metrics=validation_metrics
        )
    )

    unique_recommendations = []
    seen_titles = set()

    for recommendation in recommendations:
        title = recommendation[
            "title"
        ]

        if title in seen_titles:
            continue

        seen_titles.add(title)
        unique_recommendations.append(
            recommendation
        )

    unique_recommendations.sort(
        key=lambda item: (
            _priority_rank(
                item["priority"]
            ),
            item["confidence"]
        ),
        reverse=True
    )

    high_priority_count = sum(
        1
        for item in unique_recommendations
        if item["priority"] == "High"
    )

    medium_priority_count = sum(
        1
        for item in unique_recommendations
        if item["priority"] == "Medium"
    )

    low_priority_count = sum(
        1
        for item in unique_recommendations
        if item["priority"] == "Low"
    )

    if high_priority_count > 0:
        overall_action_level = (
            "Immediate Action Required"
        )
    elif medium_priority_count > 0:
        overall_action_level = (
            "Management Review Recommended"
        )
    else:
        overall_action_level = (
            "Monitor and Maintain"
        )

    return {
        "success": True,
        "overall_action_level": (
            overall_action_level
        ),
        "total_recommendations": len(
            unique_recommendations
        ),
        "priority_summary": {
            "high": high_priority_count,
            "medium": medium_priority_count,
            "low": low_priority_count
        },
        "recommendations": (
            unique_recommendations[:10]
        )
    }