from typing import Any


def format_number(value: Any) -> str:
    """
    Convert a numeric value into a readable formatted string.
    """

    try:
        numeric_value = float(value)
        return f"{numeric_value:,.2f}"

    except (TypeError, ValueError):
        return str(value)


def explain_model_selection(
    best_model_name: str,
    model_comparison: list[dict[str, Any]]
) -> str:
    """
    Explain why the selected forecasting model was chosen.
    """

    if not model_comparison:
        return (
            "The forecasting model was selected using the available "
            "historical data and validation results."
        )

    sorted_models = sorted(
        model_comparison,
        key=lambda model: model.get(
            "validation_score",
            0
        ),
        reverse=True
    )

    best_model = sorted_models[0]

    best_score = float(
        best_model.get(
            "validation_score",
            0
        )
    )

    if len(sorted_models) > 1:
        second_model = sorted_models[1]

        second_score = float(
            second_model.get(
                "validation_score",
                0
            )
        )

        score_difference = (
            best_score - second_score
        )

        return (
            f"{best_model_name} was selected because it achieved "
            f"the highest validation score of "
            f"{best_score:.2f}%. "
            f"It outperformed the next-best model by "
            f"{score_difference:.2f} percentage points on recent "
            f"unseen periods."
        )

    return (
        f"{best_model_name} was selected because it achieved "
        f"the highest available validation score of "
        f"{best_score:.2f}%."
    )


def explain_model_behavior(
    best_model_key: str,
    best_model_name: str
) -> str:
    """
    Explain how the selected model behaves in simple language.
    """

    if best_model_key == "linear":
        return (
            f"{best_model_name} assumes that the KPI changes at a "
            f"relatively consistent rate over time. It works well when "
            f"the historical series follows a clear upward or downward "
            f"trend."
        )

    if best_model_key == "polynomial":
        return (
            f"{best_model_name} captures curved or accelerating patterns. "
            f"It is useful when the rate of growth or decline changes "
            f"over time."
        )

    if best_model_key == "moving_average":
        return (
            f"{best_model_name} gives more importance to recent historical "
            f"periods. It is useful when the latest observations are more "
            f"representative than the long-term trend."
        )

    return (
        f"{best_model_name} was selected because it produced the strongest "
        f"validation performance for the uploaded dataset."
    )


def explain_validation_metrics(
    validation_metrics: dict[str, Any],
    confidence_score: float
) -> list[str]:
    """
    Explain forecast validation metrics in business language.
    """

    explanations: list[str] = []

    mae = float(
        validation_metrics.get(
            "mae",
            0
        )
    )

    rmse = float(
        validation_metrics.get(
            "rmse",
            0
        )
    )

    mape = float(
        validation_metrics.get(
            "mape",
            0
        )
    )

    r2_score = float(
        validation_metrics.get(
            "r2_score",
            0
        )
    )

    explanations.append(
        f"MAE is {format_number(mae)}, meaning the model's predictions "
        f"differed from actual validation values by approximately "
        f"{format_number(mae)} units on average."
    )

    explanations.append(
        f"RMSE is {format_number(rmse)}. This metric gives more weight "
        f"to larger forecasting errors."
    )

    if mape <= 10:
        mape_label = "very accurate"

    elif mape <= 20:
        mape_label = "reasonably accurate"

    elif mape <= 40:
        mape_label = "moderately accurate"

    else:
        mape_label = "highly uncertain"

    explanations.append(
        f"MAPE is {mape:.2f}%, so the forecast is considered "
        f"{mape_label} based on percentage error."
    )

    if r2_score >= 0.75:
        r2_label = "strong"

    elif r2_score >= 0.40:
        r2_label = "moderate"

    elif r2_score >= 0:
        r2_label = "weak"

    else:
        r2_label = "poor"

    explanations.append(
        f"The validation R² is {r2_score:.4f}, indicating a "
        f"{r2_label} fit on unseen recent periods."
    )

    if confidence_score >= 80:
        confidence_label = "high"

    elif confidence_score >= 60:
        confidence_label = "moderate"

    else:
        confidence_label = "low"

    explanations.append(
        f"The overall forecast confidence is "
        f"{confidence_score:.2f}%, which is considered "
        f"{confidence_label}."
    )

    return explanations


def explain_trend(
    metrics: dict[str, Any],
    forecast: list[dict[str, Any]],
    value_column: str
) -> str:
    """
    Explain historical and future trend movement.
    """

    historical_direction = metrics.get(
        "trend_direction",
        "stable"
    )

    historical_growth = float(
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

    if forecast:
        first_forecast = float(
            forecast[0].get(
                "forecast",
                0
            )
        )

        last_forecast = float(
            forecast[-1].get(
                "forecast",
                0
            )
        )

        if first_forecast != 0:
            future_change = (
                (
                    last_forecast
                    - first_forecast
                )
                / abs(first_forecast)
            ) * 100

        else:
            future_change = 0.0

    else:
        future_change = 0.0

    if future_change > 2:
        forecast_direction = "increase"

    elif future_change < -2:
        forecast_direction = "decrease"

    else:
        forecast_direction = "remain relatively stable"

    return (
        f"The historical {value_column} trend is "
        f"{historical_direction}, with an overall historical change of "
        f"{historical_growth:.2f}%. The latest period changed by "
        f"{recent_change:.2f}%. The selected model expects "
        f"{value_column} to {forecast_direction} over the forecast horizon, "
        f"with an estimated first-to-last forecast change of "
        f"{abs(future_change):.2f}%."
    )


def explain_prediction_interval(
    forecast: list[dict[str, Any]]
) -> str:
    """
    Explain the purpose and size of prediction intervals.
    """

    if not forecast:
        return (
            "No prediction interval explanation is available because "
            "forecast values were not generated."
        )

    interval_widths: list[float] = []

    for item in forecast:
        forecast_value = float(
            item.get(
                "forecast",
                0
            )
        )

        lower_bound = float(
            item.get(
                "lower_bound",
                forecast_value
            )
        )

        upper_bound = float(
            item.get(
                "upper_bound",
                forecast_value
            )
        )

        interval_widths.append(
            upper_bound - lower_bound
        )

    average_width = (
        sum(interval_widths)
        / len(interval_widths)
    )

    average_forecast = (
        sum(
            float(
                item.get(
                    "forecast",
                    0
                )
            )
            for item in forecast
        )
        / len(forecast)
    )

    if average_forecast != 0:
        relative_width = (
            average_width
            / abs(average_forecast)
        ) * 100

    else:
        relative_width = 0.0

    if relative_width <= 20:
        uncertainty = "narrow"

    elif relative_width <= 50:
        uncertainty = "moderate"

    else:
        uncertainty = "wide"

    return (
        f"The average prediction interval width is "
        f"{format_number(average_width)}, which is approximately "
        f"{relative_width:.2f}% of the average forecast value. "
        f"This represents a {uncertainty} level of forecast uncertainty. "
        f"Actual results may fall anywhere between the lower and "
        f"upper bounds."
    )


def build_business_interpretation(
    value_column: str,
    metrics: dict[str, Any],
    confidence_score: float
) -> str:
    """
    Create a short executive interpretation.
    """

    direction = metrics.get(
        "trend_direction",
        "stable"
    )

    recent_change = float(
        metrics.get(
            "recent_change",
            0
        )
    )

    if direction == "upward":
        impact = (
            "The business should prepare for potential growth in demand, "
            "resources, or capacity."
        )

    elif direction == "downward":
        impact = (
            "The business should investigate the drivers of decline and "
            "prepare corrective actions."
        )

    else:
        impact = (
            "The KPI is broadly stable, so operational levels can be "
            "maintained while monitoring future changes."
        )

    if abs(recent_change) >= 15:
        recent_warning = (
            "The latest period changed sharply, so recent movement should "
            "be validated before major decisions are made."
        )

    else:
        recent_warning = (
            "The latest period did not show an extreme change."
        )

    if confidence_score < 60:
        confidence_warning = (
            "Forecast confidence is limited, so the result should be used "
            "as decision support rather than a firm target."
        )

    else:
        confidence_warning = (
            "Forecast confidence is sufficient for planning, but actual "
            "performance should still be monitored."
        )

    return (
        f"For {value_column}, the detected direction is {direction}. "
        f"{impact} {recent_warning} {confidence_warning}"
    )


def generate_forecast_explanation(
    result: dict[str, Any]
) -> dict[str, Any]:
    """
    Generate a complete explainability package from a forecast result.
    """

    if not result.get("success"):
        return {
            "success": False,
            "message": (
                "A successful forecast result is required "
                "to generate explanations."
            )
        }

    best_model_name = result.get(
        "best_model_name",
        "Selected forecasting model"
    )

    best_model_key = result.get(
        "best_model_key",
        ""
    )

    model_comparison = result.get(
        "model_comparison",
        []
    )

    validation_metrics = result.get(
        "validation_metrics",
        {}
    )

    metrics = result.get(
        "metrics",
        {}
    )

    forecast = result.get(
        "forecast",
        []
    )

    value_column = result.get(
        "value_column",
        "selected KPI"
    )

    confidence_score = float(
        metrics.get(
            "confidence_score",
            0
        )
    )

    return {
        "success": True,

        "model_selection": explain_model_selection(
            best_model_name=best_model_name,
            model_comparison=model_comparison
        ),

        "model_behavior": explain_model_behavior(
            best_model_key=best_model_key,
            best_model_name=best_model_name
        ),

        "validation_explanations": explain_validation_metrics(
            validation_metrics=validation_metrics,
            confidence_score=confidence_score
        ),

        "trend_explanation": explain_trend(
            metrics=metrics,
            forecast=forecast,
            value_column=value_column
        ),

        "interval_explanation": explain_prediction_interval(
            forecast=forecast
        ),

        "business_interpretation": build_business_interpretation(
            value_column=value_column,
            metrics=metrics,
            confidence_score=confidence_score
        )
    }