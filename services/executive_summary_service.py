"""
Executive Decision Summary Service

Combines forecast results, model confidence, business risk,
explainability, and AI recommendations into a concise
management-ready decision brief.
"""

from typing import Any


def _safe_float(
    value: Any,
    default: float = 0.0
) -> float:
    try:
        return float(value)

    except (TypeError, ValueError):
        return default


def _clamp_score(
    value: float
) -> float:
    return round(
        max(
            0.0,
            min(
                100.0,
                value
            )
        ),
        2
    )


def _get_top_risks(
    business_risk: dict[str, Any],
    limit: int = 3
) -> list[dict[str, Any]]:
    risks = business_risk.get(
        "risks",
        []
    )

    valid_risks = [
        risk
        for risk in risks
        if isinstance(
            risk,
            dict
        )
    ]

    valid_risks.sort(
        key=lambda item: _safe_float(
            item.get(
                "score",
                0
            )
        ),
        reverse=True
    )

    return valid_risks[:limit]


def _get_top_recommendations(
    recommendation_result: dict[str, Any],
    limit: int = 3
) -> list[dict[str, Any]]:
    recommendations = (
        recommendation_result.get(
            "recommendations",
            []
        )
    )

    priority_rank = {
        "High": 3,
        "Medium": 2,
        "Low": 1
    }

    valid_recommendations = [
        recommendation
        for recommendation in recommendations
        if isinstance(
            recommendation,
            dict
        )
    ]

    valid_recommendations.sort(
        key=lambda item: (
            priority_rank.get(
                item.get(
                    "priority",
                    "Low"
                ),
                0
            ),
            _safe_float(
                item.get(
                    "confidence",
                    0
                )
            )
        ),
        reverse=True
    )

    return valid_recommendations[:limit]


def calculate_decision_confidence(
    forecast_result: dict[str, Any]
) -> float:
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

    confidence = _safe_float(
        metrics.get(
            "confidence_score",
            0
        )
    )

    mape = _safe_float(
        validation_metrics.get(
            "mape",
            100
        )
    )

    error_score = max(
        0.0,
        100.0 - mape
    )

    return _clamp_score(
        confidence * 0.70
        + error_score * 0.30
    )


def calculate_business_health_score(
    forecast_result: dict[str, Any]
) -> float:
    business_risk = (
        forecast_result.get(
            "business_risk",
            {}
        )
    )

    overall_risk = _safe_float(
        business_risk.get(
            "overall_score",
            100
        )
    )

    return _clamp_score(
        100.0 - overall_risk
    )


def calculate_forecast_reliability(
    forecast_result: dict[str, Any]
) -> float:
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

    confidence = _safe_float(
        metrics.get(
            "confidence_score",
            0
        )
    )

    r2_score = _safe_float(
        validation_metrics.get(
            "r2_score",
            0
        )
    )

    bounded_r2 = max(
        0.0,
        min(
            1.0,
            r2_score
        )
    ) * 100

    return _clamp_score(
        confidence * 0.75
        + bounded_r2 * 0.25
    )


def calculate_ai_readiness(
    forecast_result: dict[str, Any]
) -> float:
    component_scores = []

    if forecast_result.get(
        "best_model_name"
    ):
        component_scores.append(
            100
        )

    if forecast_result.get(
        "model_comparison"
    ):
        component_scores.append(
            100
        )

    if forecast_result.get(
        "explainability",
        {}
    ).get(
        "success"
    ):
        component_scores.append(
            100
        )

    if forecast_result.get(
        "business_risk"
    ):
        component_scores.append(
            100
        )

    if forecast_result.get(
        "ai_recommendations",
        {}
    ).get(
        "success"
    ):
        component_scores.append(
            100
        )

    if not component_scores:
        return 0.0

    return _clamp_score(
        sum(component_scores)
        / 5
    )


def build_forecast_outlook(
    forecast_result: dict[str, Any]
) -> str:
    metrics = forecast_result.get(
        "metrics",
        {}
    )

    value_column = str(
        forecast_result.get(
            "value_column",
            "selected KPI"
        )
    )

    periods = int(
        forecast_result.get(
            "periods",
            0
        )
    )

    direction = str(
        metrics.get(
            "trend_direction",
            "stable"
        )
    )

    growth_rate = _safe_float(
        metrics.get(
            "historical_growth_rate",
            0
        )
    )

    recent_change = _safe_float(
        metrics.get(
            "recent_change",
            0
        )
    )

    return (
        f"The {value_column} outlook is {direction} over the selected "
        f"{periods}-month forecast horizon. Historical performance changed "
        f"by {growth_rate:.2f}% from the first to the latest period, while "
        f"the most recent period changed by {recent_change:.2f}%."
    )


def build_strategic_conclusion(
    forecast_result: dict[str, Any],
    decision_confidence: float,
    business_health_score: float
) -> str:
    recommendation_result = (
        forecast_result.get(
            "ai_recommendations",
            {}
        )
    )

    action_level = str(
        recommendation_result.get(
            "overall_action_level",
            "Monitor and Maintain"
        )
    )

    risk_level = str(
        forecast_result.get(
            "business_risk",
            {}
        ).get(
            "overall_level",
            "Unknown"
        )
    )

    if action_level == "Immediate Action Required":
        action_text = (
            "Management should prioritize immediate corrective and "
            "risk-mitigation actions."
        )

    elif action_level == "Management Review Recommended":
        action_text = (
            "Management review is recommended before finalizing operational "
            "or financial commitments."
        )

    else:
        action_text = (
            "Current operations can be maintained while monitoring future "
            "actual results."
        )

    return (
        f"The overall business-risk status is {risk_level}, with a business "
        f"health score of {business_health_score:.2f}%. Decision confidence "
        f"is {decision_confidence:.2f}%. {action_text}"
    )


def build_copyable_brief(
    forecast_result: dict[str, Any],
    outlook: str,
    strategic_conclusion: str,
    top_risks: list[dict[str, Any]],
    top_recommendations: list[dict[str, Any]]
) -> str:
    best_model = str(
        forecast_result.get(
            "best_model_name",
            "Not available"
        )
    )

    risk_lines = []

    for risk in top_risks:
        risk_lines.append(
            f"- {risk.get('name', 'Risk')}: "
            f"{risk.get('level', 'Unknown')} "
            f"({risk.get('score', 0)}%)"
        )

    recommendation_lines = []

    for recommendation in top_recommendations:
        recommendation_lines.append(
            f"- {recommendation.get('title', 'Recommendation')}: "
            f"{recommendation.get('action', '')}"
        )

    return (
        "EXECUTIVE FORECAST BRIEF\n\n"
        f"Selected Model: {best_model}\n\n"
        f"Forecast Outlook:\n{outlook}\n\n"
        "Top Risks:\n"
        + (
            "\n".join(
                risk_lines
            )
            if risk_lines
            else "- No major risks available."
        )
        + "\n\nTop Recommendations:\n"
        + (
            "\n".join(
                recommendation_lines
            )
            if recommendation_lines
            else "- No recommendations available."
        )
        + "\n\nStrategic Conclusion:\n"
        + strategic_conclusion
    )


def generate_executive_summary(
    forecast_result: dict[str, Any]
) -> dict[str, Any]:
    """
    Generate a complete executive decision summary.
    """

    if not forecast_result.get(
        "success"
    ):
        return {
            "success": False,
            "message": (
                "A successful forecast result is required "
                "to generate an executive summary."
            )
        }

    decision_confidence = (
        calculate_decision_confidence(
            forecast_result
        )
    )

    business_health_score = (
        calculate_business_health_score(
            forecast_result
        )
    )

    forecast_reliability = (
        calculate_forecast_reliability(
            forecast_result
        )
    )

    ai_readiness = (
        calculate_ai_readiness(
            forecast_result
        )
    )

    top_risks = _get_top_risks(
        forecast_result.get(
            "business_risk",
            {}
        )
    )

    top_recommendations = (
        _get_top_recommendations(
            forecast_result.get(
                "ai_recommendations",
                {}
            )
        )
    )

    outlook = build_forecast_outlook(
        forecast_result
    )

    strategic_conclusion = (
        build_strategic_conclusion(
            forecast_result=forecast_result,
            decision_confidence=decision_confidence,
            business_health_score=business_health_score
        )
    )

    copyable_brief = build_copyable_brief(
        forecast_result=forecast_result,
        outlook=outlook,
        strategic_conclusion=strategic_conclusion,
        top_risks=top_risks,
        top_recommendations=top_recommendations
    )

    return {
        "success": True,

        "headline": (
            forecast_result.get(
                "ai_recommendations",
                {}
            ).get(
                "overall_action_level",
                "Monitor and Maintain"
            )
        ),

        "overview": (
            forecast_result.get(
                "summary",
                outlook
            )
        ),

        "forecast_outlook": outlook,

        "strategic_conclusion": (
            strategic_conclusion
        ),

        "top_risks": top_risks,

        "top_recommendations": (
            top_recommendations
        ),

        "kpis": {
            "decision_confidence": (
                decision_confidence
            ),
            "business_health_score": (
                business_health_score
            ),
            "forecast_reliability": (
                forecast_reliability
            ),
            "ai_readiness": (
                ai_readiness
            )
        },

        "copyable_brief": (
            copyable_brief
        )
    }