"""
Business Risk Assessment Service

This module converts forecasting results into
business-oriented risk indicators.
"""

from typing import Any


def _risk_level(score: float) -> str:
    if score >= 75:
        return "High"

    if score >= 45:
        return "Medium"

    return "Low"


def _confidence_risk(confidence: float) -> dict:
    score = max(0, 100 - confidence)

    return {
        "name": "Forecast Confidence",
        "score": round(score, 2),
        "level": _risk_level(score),
        "description":
            "Lower confidence increases uncertainty "
            "in future planning."
    }


def _volatility_risk(metrics: dict) -> dict:
    growth = abs(
        float(
            metrics.get(
                "historical_growth_rate",
                0
            )
        )
    )

    recent = abs(
        float(
            metrics.get(
                "recent_change",
                0
            )
        )
    )

    score = min(
        100,
        (growth * 0.35)
        +
        (recent * 1.6)
    )

    return {
        "name": "Business Volatility",
        "score": round(score, 2),
        "level": _risk_level(score),
        "description":
            "Large historical movement increases planning risk."
    }


def _forecast_uncertainty(forecast: list) -> dict:

    if not forecast:
        return {
            "name": "Prediction Interval",
            "score": 0,
            "level": "Low",
            "description":
                "No forecast available."
        }

    widths = []

    for item in forecast:

        upper = float(
            item.get(
                "upper_bound",
                item["forecast"]
            )
        )

        lower = float(
            item.get(
                "lower_bound",
                item["forecast"]
            )
        )

        widths.append(
            upper - lower
        )

    avg_width = (
        sum(widths)
        / len(widths)
    )

    avg_forecast = (
        sum(
            float(x["forecast"])
            for x in forecast
        )
        / len(forecast)
    )

    if avg_forecast != 0:
        score = min(
            100,
            abs(
                avg_width
                /
                avg_forecast
            ) * 100
        )
    else:
        score = 0

    return {
        "name": "Forecast Uncertainty",
        "score": round(score, 2),
        "level": _risk_level(score),
        "description":
            "Wide prediction intervals increase business uncertainty."
    }


def _trend_risk(metrics: dict) -> dict:

    direction = metrics.get(
        "trend_direction",
        "stable"
    )

    growth = float(
        metrics.get(
            "historical_growth_rate",
            0
        )
    )

    if direction == "downward":
        score = 85

    elif abs(growth) > 30:
        score = 70

    elif abs(growth) > 15:
        score = 45

    else:
        score = 20

    return {
        "name": "Trend Risk",
        "score": score,
        "level": _risk_level(score),
        "description":
            "Strong declines or unstable growth may require business action."
    }


def calculate_business_risks(
    forecast_result: dict[str, Any]
) -> dict[str, Any]:

    metrics = forecast_result.get(
        "metrics",
        {}
    )

    forecast = forecast_result.get(
        "forecast",
        []
    )

    confidence = float(
        metrics.get(
            "confidence_score",
            0
        )
    )

    risks = [

        _confidence_risk(
            confidence
        ),

        _volatility_risk(
            metrics
        ),

        _forecast_uncertainty(
            forecast
        ),

        _trend_risk(
            metrics
        )

    ]

    overall_score = (
        sum(
            risk["score"]
            for risk in risks
        )
        / len(risks)
    )

    if overall_score >= 70:
        outlook = "Critical"

    elif overall_score >= 50:
        outlook = "Warning"

    elif overall_score >= 30:
        outlook = "Moderate"

    else:
        outlook = "Healthy"

    return {

        "overall_score":
            round(
                overall_score,
                2
            ),

        "overall_level":
            outlook,

        "risks":
            risks

    }