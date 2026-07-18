import re
from typing import Any

import numpy as np
import pandas as pd

from services.forecast_model_service import (
    fit_best_model_and_forecast
)
from services.forecast_explainability_service import (
    generate_forecast_explanation
)
from services.business_risk_service import (
    calculate_business_risks
)
from services.business_recommendation_service import (
    generate_business_recommendations
)
from services.executive_summary_service import (
    generate_executive_summary
)

DATE_KEYWORDS = [
    "date",
    "month",
    "year",
    "time",
    "period",
    "timestamp"
]

BUSINESS_VALUE_KEYWORDS = [
    "sales",
    "revenue",
    "profit",
    "income",
    "amount",
    "quantity",
    "demand",
    "orders",
    "cost",
    "price",
    "expense",
    "stock",
    "inventory"
]


def normalize_column_name(column: Any) -> str:
    """
    Convert a column name into a normalized searchable format.
    """

    return re.sub(
        r"\s+",
        " ",
        str(column).lower().replace("_", " ").strip()
    )


def find_date_columns(df: pd.DataFrame) -> list[str]:
    """
    Find columns that can be interpreted as dates.
    """

    date_columns = []

    for column in df.columns:
        normalized_name = normalize_column_name(column)

        has_date_keyword = any(
            keyword in normalized_name
            for keyword in DATE_KEYWORDS
        )

        if not has_date_keyword:
            continue

        converted = pd.to_datetime(
            df[column],
            errors="coerce"
        )

        valid_count = int(converted.notna().sum())

        if valid_count >= max(
            2,
            int(len(df) * 0.25)
        ):
            date_columns.append(column)

    # Fallback: inspect text columns
    if not date_columns:
        object_columns = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()

        for column in object_columns:
            converted = pd.to_datetime(
                df[column],
                errors="coerce"
            )

            valid_count = int(
                converted.notna().sum()
            )

            if valid_count >= max(
                2,
                int(len(df) * 0.70)
            ):
                date_columns.append(column)

    return date_columns


def find_numeric_columns(df: pd.DataFrame) -> list[str]:
    """
    Return useful numeric columns while avoiding ID-like columns.
    """

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    filtered_columns = []

    for column in numeric_columns:
        normalized_name = normalize_column_name(
            column
        )

        id_like = any(
            keyword in normalized_name
            for keyword in [
                "row id",
                "postal code",
                "zip code",
                "customer id",
                "order id",
                "product id"
            ]
        )

        if not id_like:
            filtered_columns.append(column)

    return filtered_columns


def select_default_value_column(
    df: pd.DataFrame,
    numeric_columns: list[str]
) -> str | None:
    """
    Select the most business-relevant numeric column.
    """

    for keyword in BUSINESS_VALUE_KEYWORDS:
        for column in numeric_columns:
            normalized_name = normalize_column_name(
                column
            )

            if keyword in normalized_name:
                return column

    return (
        numeric_columns[0]
        if numeric_columns
        else None
    )


def prepare_monthly_series(
    df: pd.DataFrame,
    date_column: str,
    value_column: str
) -> pd.DataFrame:
    """
    Convert raw rows into a continuous monthly time series.
    """

    if date_column not in df.columns:
        raise ValueError(
            f"Date column '{date_column}' was not found."
        )

    if value_column not in df.columns:
        raise ValueError(
            f"Value column '{value_column}' was not found."
        )

    working_df = df[
        [date_column, value_column]
    ].copy()

    working_df[date_column] = pd.to_datetime(
        working_df[date_column],
        errors="coerce"
    )

    working_df[value_column] = pd.to_numeric(
        working_df[value_column],
        errors="coerce"
    )

    working_df = working_df.dropna(
        subset=[
            date_column,
            value_column
        ]
    )

    if working_df.empty:
        raise ValueError(
            "No valid date and numeric value pairs were found."
        )

    working_df["Period"] = (
        working_df[date_column]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    monthly_data = (
        working_df
        .groupby(
            "Period",
            as_index=False
        )[value_column]
        .sum()
        .sort_values("Period")
        .reset_index(drop=True)
    )

    if len(monthly_data) < 4:
        raise ValueError(
            "At least four monthly periods are required "
            "for model comparison."
        )

    full_period_range = pd.date_range(
        start=monthly_data["Period"].min(),
        end=monthly_data["Period"].max(),
        freq="MS"
    )

    monthly_data = (
        monthly_data
        .set_index("Period")
        .reindex(full_period_range)
        .rename_axis("Period")
        .reset_index()
    )

    monthly_data[value_column] = (
        monthly_data[value_column]
        .fillna(0)
    )

    return monthly_data


def calculate_trend_information(
    values: pd.Series
) -> dict[str, Any]:
    """
    Calculate historical growth and recent movement.
    """

    numeric_values = pd.to_numeric(
        values,
        errors="coerce"
    ).dropna()

    if numeric_values.empty:
        return {
            "direction": "stable",
            "growth_rate": 0.0,
            "recent_change": 0.0
        }

    first_value = float(
        numeric_values.iloc[0]
    )

    last_value = float(
        numeric_values.iloc[-1]
    )

    if first_value != 0:
        growth_rate = (
            (last_value - first_value)
            / abs(first_value)
        ) * 100
    else:
        growth_rate = 0.0

    if len(numeric_values) >= 2:
        previous_value = float(
            numeric_values.iloc[-2]
        )

        if previous_value != 0:
            recent_change = (
                (last_value - previous_value)
                / abs(previous_value)
            ) * 100
        else:
            recent_change = 0.0
    else:
        recent_change = 0.0

    if growth_rate > 2:
        direction = "upward"
    elif growth_rate < -2:
        direction = "downward"
    else:
        direction = "stable"

    return {
        "direction": direction,
        "growth_rate": round(
            growth_rate,
            2
        ),
        "recent_change": round(
            recent_change,
            2
        )
    }


def is_non_negative_metric(
    value_column: str
) -> bool:
    """
    Determine whether predictions should be prevented
    from becoming negative.
    """

    normalized_name = normalize_column_name(
        value_column
    )

    non_negative_keywords = [
        "sales",
        "revenue",
        "quantity",
        "orders",
        "inventory",
        "stock",
        "amount",
        "cost",
        "price",
        "demand",
        "customers",
        "units",
        "volume"
    ]

    return any(
        keyword in normalized_name
        for keyword in non_negative_keywords
    )


def build_forecast_summary(
    value_column: str,
    trend_info: dict[str, Any],
    future_values: list[float],
    confidence_score: float,
    best_model_name: str,
    validation_metrics: dict[str, Any]
) -> str:
    """
    Build a natural-language forecast summary.
    """

    if not future_values:
        return "No forecast values were generated."

    first_forecast = future_values[0]
    last_forecast = future_values[-1]

    if first_forecast != 0:
        forecast_change = (
            (last_forecast - first_forecast)
            / abs(first_forecast)
        ) * 100
    else:
        forecast_change = 0.0

    if forecast_change > 2:
        future_direction = "increase"
    elif forecast_change < -2:
        future_direction = "decrease"
    else:
        future_direction = (
            "remain relatively stable"
        )

    mape = validation_metrics.get(
        "mape",
        0
    )

    return (
        f"The historical {value_column} trend is "
        f"{trend_info['direction']}. "
        f"The system selected {best_model_name} after comparing "
        f"multiple forecasting models on unseen recent periods. "
        f"The forecast indicates that {value_column} may "
        f"{future_direction} over the selected future period. "
        f"The estimated change from the first forecast month "
        f"to the final forecast month is "
        f"{abs(forecast_change):.2f}%. "
        f"The validation score is {confidence_score:.2f}% "
        f"with a MAPE of {mape:.2f}%."
    )


def generate_risk_alerts(
    trend_info: dict[str, Any],
    future_values: list[float],
    confidence_score: float,
    validation_metrics: dict[str, Any],
    prediction_width: float
) -> list[str]:
    """
    Generate forecast-related risk messages.
    """

    risks = []

    if trend_info["direction"] == "downward":
        risks.append(
            "The historical data shows a downward trend."
        )

    if trend_info["recent_change"] < -10:
        risks.append(
            "The latest period declined by more than 10%."
        )

    if future_values and any(
        value < 0
        for value in future_values
    ):
        risks.append(
            "The forecast contains negative values and should be reviewed."
        )

    mape = validation_metrics.get(
        "mape",
        0
    )

    if mape > 30:
        risks.append(
            "Validation percentage error is high, indicating an unstable series."
        )

    if confidence_score < 50:
        risks.append(
            "Forecast confidence is low. Use the predictions cautiously."
        )
    elif confidence_score < 70:
        risks.append(
            "Forecast confidence is moderate. Use the result with business judgment."
        )

    if prediction_width > 0:
        risks.append(
            "Prediction intervals represent uncertainty and actual values may fall anywhere within those limits."
        )

    if not risks:
        risks.append(
            "No major forecast risk was automatically detected."
        )

    return risks


def generate_forecast_recommendations(
    trend_info: dict[str, Any],
    confidence_score: float,
    best_model_name: str
) -> list[str]:
    """
    Generate business recommendations based on the forecast.
    """

    recommendations = []

    if trend_info["direction"] == "upward":
        recommendations.append(
            "Prepare resources and inventory for expected growth."
        )

    elif trend_info["direction"] == "downward":
        recommendations.append(
            "Investigate the causes of decline and prepare a recovery plan."
        )

    else:
        recommendations.append(
            "Maintain current operating levels while monitoring new changes."
        )

    if trend_info["recent_change"] > 15:
        recommendations.append(
            "Validate the recent growth spike before increasing long-term commitments."
        )

    if trend_info["recent_change"] < -15:
        recommendations.append(
            "Create an alert for further decline in the next reporting period."
        )

    if confidence_score < 70:
        recommendations.append(
            "Add more historical periods to improve forecast reliability."
        )

    recommendations.append(
        f"The selected model is {best_model_name}. "
        "Continue comparing its predictions against actual results."
    )

    recommendations.extend([
        "Compare forecast values with actual results each month.",
        "Refresh the forecast whenever new data is uploaded.",
        "Use prediction intervals when making risk-sensitive decisions.",
        "Use the forecast as decision support, not as a guaranteed outcome."
    ])

    return recommendations


def generate_ai_forecast(
    df: pd.DataFrame,
    date_column: str | None = None,
    value_column: str | None = None,
    periods: int = 6
) -> dict[str, Any]:
    """
    Compare several forecasting models, select the best model,
    and generate future predictions with confidence intervals.
    """

    if df is None or df.empty:
        return {
            "success": False,
            "message": "The dataset is empty."
        }

    try:
        periods = int(periods)
    except (TypeError, ValueError):
        periods = 6

    periods = max(
        1,
        min(periods, 24)
    )

    available_date_columns = (
        find_date_columns(df)
    )

    available_numeric_columns = (
        find_numeric_columns(df)
    )

    selected_date_column = (
        date_column
        if date_column
        in available_date_columns
        else (
            available_date_columns[0]
            if available_date_columns
            else None
        )
    )

    selected_value_column = (
        value_column
        if value_column
        in available_numeric_columns
        else select_default_value_column(
            df,
            available_numeric_columns
        )
    )

    if selected_date_column is None:
        return {
            "success": False,
            "message": (
                "No suitable date column was detected. "
                "The dataset requires a valid date column."
            ),
            "date_columns": (
                available_date_columns
            ),
            "numeric_columns": (
                available_numeric_columns
            )
        }

    if selected_value_column is None:
        return {
            "success": False,
            "message": (
                "No suitable numeric KPI column was detected."
            ),
            "date_columns": (
                available_date_columns
            ),
            "numeric_columns": (
                available_numeric_columns
            )
        }

    try:
        monthly_data = prepare_monthly_series(
            df=df,
            date_column=selected_date_column,
            value_column=selected_value_column
        )

        y_values = monthly_data[
            selected_value_column
        ].to_numpy(dtype=float)

        model_result = (
            fit_best_model_and_forecast(
                values=y_values,
                periods=periods
            )
        )

        fitted_values = model_result[
            "fitted_values"
        ]

        future_predictions = model_result[
            "future_predictions"
        ]

        lower_bounds = model_result[
            "lower_bounds"
        ]

        upper_bounds = model_result[
            "upper_bounds"
        ]

        if is_non_negative_metric(
            selected_value_column
        ):
            future_predictions = np.maximum(
                future_predictions,
                0
            )

            lower_bounds = np.maximum(
                lower_bounds,
                0
            )

            upper_bounds = np.maximum(
                upper_bounds,
                0
            )

        last_period = monthly_data[
            "Period"
        ].max()

        future_dates = pd.date_range(
            start=(
                last_period
                + pd.offsets.MonthBegin(1)
            ),
            periods=periods,
            freq="MS"
        )

        trend_info = (
            calculate_trend_information(
                monthly_data[
                    selected_value_column
                ]
            )
        )

        confidence_score = float(
            model_result[
                "validation_score"
            ]
        )

        validation_metrics = (
            model_result[
                "validation_metrics"
            ]
        )

        best_model_name = (
            model_result[
                "best_model_name"
            ]
        )

        future_value_list = [
            round(float(value), 2)
            for value in future_predictions
        ]

        lower_bound_list = [
            round(float(value), 2)
            for value in lower_bounds
        ]

        upper_bound_list = [
            round(float(value), 2)
            for value in upper_bounds
        ]

        historical_records = []

        for index, row in monthly_data.iterrows():
            historical_records.append({
                "period": (
                    row["Period"].strftime(
                        "%Y-%m"
                    )
                ),
                "value": round(
                    float(
                        row[
                            selected_value_column
                        ]
                    ),
                    2
                ),
                "fitted_value": round(
                    float(
                        fitted_values[index]
                    ),
                    2
                )
            })

        forecast_records = []

        for (
            forecast_date,
            forecast_value,
            lower_value,
            upper_value
        ) in zip(
            future_dates,
            future_value_list,
            lower_bound_list,
            upper_bound_list
        ):
            forecast_records.append({
                "period": (
                    forecast_date.strftime(
                        "%Y-%m"
                    )
                ),
                "forecast": forecast_value,
                "lower_bound": lower_value,
                "upper_bound": upper_value
            })

        if future_value_list:
            interval_width = float(
                np.mean(
                    np.asarray(
                        upper_bound_list
                    )
                    - np.asarray(
                        lower_bound_list
                    )
                )
            )
        else:
            interval_width = 0.0

        summary = build_forecast_summary(
            value_column=(
                selected_value_column
            ),
            trend_info=trend_info,
            future_values=(
                future_value_list
            ),
            confidence_score=(
                confidence_score
            ),
            best_model_name=(
                best_model_name
            ),
            validation_metrics=(
                validation_metrics
            )
        )

        risks = generate_risk_alerts(
            trend_info=trend_info,
            future_values=(
                future_value_list
            ),
            confidence_score=(
                confidence_score
            ),
            validation_metrics=(
                validation_metrics
            ),
            prediction_width=(
                interval_width
            )
        )

        recommendations = (
            generate_forecast_recommendations(
                trend_info=trend_info,
                confidence_score=(
                    confidence_score
                ),
                best_model_name=(
                    best_model_name
                )
            )
        )

        forecast_result = {
            "success": True,
            "message": (
                "Forecast generated successfully."
            ),
            "date_column": (
                selected_date_column
            ),
            "value_column": (
                selected_value_column
            ),
            "periods": periods,

            "best_model_name": (
                best_model_name
            ),
            "best_model_key": (
                model_result[
                    "best_model_key"
                ]
            ),
            "model_comparison": (
                model_result[
                    "model_comparison"
                ]
            ),
            "validation_metrics": (
                validation_metrics
            ),
            "train_size": (
                model_result[
                    "train_size"
                ]
            ),
            "test_size": (
                model_result[
                    "test_size"
                ]
            ),
            "residual_standard_deviation": (
                model_result[
                    "residual_standard_deviation"
                ]
            ),

            "historical": (
                historical_records
            ),
            "forecast": (
                forecast_records
            ),

            "metrics": {
                "r2_score": (
                    validation_metrics.get(
                        "r2_score",
                        0
                    )
                ),
                "mae": (
                    validation_metrics.get(
                        "mae",
                        0
                    )
                ),
                "rmse": (
                    validation_metrics.get(
                        "rmse",
                        0
                    )
                ),
                "mape": (
                    validation_metrics.get(
                        "mape",
                        0
                    )
                ),
                "confidence_score": (
                    confidence_score
                ),
                "trend_direction": (
                    trend_info[
                        "direction"
                    ]
                ),
                "historical_growth_rate": (
                    trend_info[
                        "growth_rate"
                    ]
                ),
                "recent_change": (
                    trend_info[
                        "recent_change"
                    ]
                )
            },

            "summary": summary,
            "risks": risks,
            "recommendations": (
                recommendations
            ),
            "date_columns": (
                available_date_columns
            ),
            "numeric_columns": (
                available_numeric_columns
            )
        }

        forecast_result["explainability"] = (
            generate_forecast_explanation(
                forecast_result
            )
        )

        forecast_result["business_risk"] = (
            calculate_business_risks(
                forecast_result
            )
        )

        forecast_result["ai_recommendations"] = (
            generate_business_recommendations(
                forecast_result
            )
        )

        forecast_result["executive_summary"] = (
            generate_executive_summary(
                forecast_result
            )
        )

        return forecast_result

    except Exception as error:
        return {
            "success": False,
            "message": (
                "Forecast generation failed: "
                f"{str(error)}"
            ),
            "date_columns": (
                available_date_columns
            ),
            "numeric_columns": (
                available_numeric_columns
            )
        }


def get_forecast_options(
    df: pd.DataFrame
) -> dict[str, Any]:
    """
    Return selectable date and numeric columns for the UI.
    """

    date_columns = find_date_columns(df)
    numeric_columns = find_numeric_columns(df)

    return {
        "date_columns": date_columns,
        "numeric_columns": numeric_columns,
        "default_date_column": (
            date_columns[0]
            if date_columns
            else None
        ),
        "default_value_column": (
            select_default_value_column(
                df,
                numeric_columns
            )
        )
    }