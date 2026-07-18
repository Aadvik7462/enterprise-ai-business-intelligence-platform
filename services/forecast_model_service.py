from typing import Any

import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
from sklearn.preprocessing import PolynomialFeatures


def safe_mape(
    actual: np.ndarray,
    predicted: np.ndarray
) -> float:
    """
    Calculate Mean Absolute Percentage Error safely.

    Zero actual values are ignored because percentage error
    cannot be calculated when the denominator is zero.
    """

    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    valid_mask = actual != 0

    if not np.any(valid_mask):
        return 100.0

    percentage_errors = np.abs(
        (
            actual[valid_mask]
            - predicted[valid_mask]
        )
        / actual[valid_mask]
    )

    return float(
        np.mean(percentage_errors) * 100
    )


def calculate_model_metrics(
    actual: np.ndarray,
    predicted: np.ndarray
) -> dict[str, float]:
    """
    Calculate common forecast validation metrics.
    """

    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    mae = mean_absolute_error(
        actual,
        predicted
    )

    mse = mean_squared_error(
        actual,
        predicted
    )

    rmse = np.sqrt(mse)

    mape = safe_mape(
        actual,
        predicted
    )

    if len(actual) >= 2:
        r2 = r2_score(
            actual,
            predicted
        )
    else:
        r2 = 0.0

    return {
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "mape": round(float(mape), 2),
        "r2_score": round(float(r2), 4)
    }


def calculate_validation_score(
    metrics: dict[str, float],
    actual: np.ndarray
) -> float:
    """
    Convert model errors into a simple 0–100 score.

    Lower MAE, RMSE, and MAPE produce a higher score.
    """

    actual = np.asarray(actual, dtype=float)

    average_actual = float(
        np.mean(np.abs(actual))
    )

    if average_actual <= 0:
        average_actual = 1.0

    normalized_mae = (
        metrics["mae"] / average_actual
    )

    normalized_rmse = (
        metrics["rmse"] / average_actual
    )

    mape_ratio = (
        metrics["mape"] / 100
    )

    error_component = (
        normalized_mae * 0.35
        + normalized_rmse * 0.35
        + mape_ratio * 0.30
    )

    error_score = max(
        0.0,
        1.0 - error_component
    )

    bounded_r2 = max(
        0.0,
        min(
            1.0,
            metrics["r2_score"]
        )
    )

    final_score = (
        error_score * 0.75
        + bounded_r2 * 0.25
    ) * 100

    return round(
        max(
            0.0,
            min(
                100.0,
                final_score
            )
        ),
        2
    )


def create_train_test_split(
    values: np.ndarray,
    minimum_train_size: int = 6
) -> dict[str, Any]:
    """
    Create a chronological train/test split.

    The final observations are used for validation.
    """

    values = np.asarray(
        values,
        dtype=float
    )

    total_points = len(values)

    if total_points < 4:
        raise ValueError(
            "At least four historical periods are required "
            "for model comparison."
        )

    test_size = max(
        1,
        int(
            round(total_points * 0.20)
        )
    )

    if total_points - test_size < minimum_train_size:
        test_size = max(
            1,
            total_points - minimum_train_size
        )

    if test_size <= 0:
        test_size = 1

    split_index = (
        total_points - test_size
    )

    train_values = values[
        :split_index
    ]

    test_values = values[
        split_index:
    ]

    train_indexes = np.arange(
        len(train_values)
    ).reshape(-1, 1)

    test_indexes = np.arange(
        len(train_values),
        total_points
    ).reshape(-1, 1)

    return {
        "train_values": train_values,
        "test_values": test_values,
        "train_indexes": train_indexes,
        "test_indexes": test_indexes,
        "split_index": split_index
    }


def evaluate_linear_regression(
    train_indexes: np.ndarray,
    train_values: np.ndarray,
    test_indexes: np.ndarray,
    test_values: np.ndarray
) -> dict[str, Any]:
    """
    Train and evaluate a Linear Regression model.
    """

    model = LinearRegression()

    model.fit(
        train_indexes,
        train_values
    )

    test_predictions = model.predict(
        test_indexes
    )

    metrics = calculate_model_metrics(
        test_values,
        test_predictions
    )

    score = calculate_validation_score(
        metrics,
        test_values
    )

    return {
        "name": "Linear Regression",
        "key": "linear",
        "model": model,
        "transformer": None,
        "test_predictions": test_predictions,
        "metrics": metrics,
        "validation_score": score
    }


def evaluate_polynomial_regression(
    train_indexes: np.ndarray,
    train_values: np.ndarray,
    test_indexes: np.ndarray,
    test_values: np.ndarray,
    degree: int = 2
) -> dict[str, Any]:
    """
    Train and evaluate a Polynomial Regression model.
    """

    transformer = PolynomialFeatures(
        degree=degree,
        include_bias=False
    )

    transformed_train = (
        transformer.fit_transform(
            train_indexes
        )
    )

    transformed_test = (
        transformer.transform(
            test_indexes
        )
    )

    model = LinearRegression()

    model.fit(
        transformed_train,
        train_values
    )

    test_predictions = model.predict(
        transformed_test
    )

    metrics = calculate_model_metrics(
        test_values,
        test_predictions
    )

    score = calculate_validation_score(
        metrics,
        test_values
    )

    return {
        "name": (
            f"Polynomial Regression "
            f"(Degree {degree})"
        ),
        "key": "polynomial",
        "model": model,
        "transformer": transformer,
        "test_predictions": test_predictions,
        "metrics": metrics,
        "validation_score": score
    }


def moving_average_predictions(
    historical_values: np.ndarray,
    steps: int,
    window: int = 3
) -> np.ndarray:
    """
    Generate recursive moving-average predictions.
    """

    history = list(
        np.asarray(
            historical_values,
            dtype=float
        )
    )

    predictions = []

    effective_window = min(
        window,
        len(history)
    )

    for _ in range(steps):
        recent_values = history[
            -effective_window:
        ]

        prediction = float(
            np.mean(recent_values)
        )

        predictions.append(
            prediction
        )

        history.append(
            prediction
        )

    return np.asarray(
        predictions,
        dtype=float
    )


def evaluate_moving_average(
    train_values: np.ndarray,
    test_values: np.ndarray,
    window: int = 3
) -> dict[str, Any]:
    """
    Evaluate a recursive Moving Average model.
    """

    test_predictions = (
        moving_average_predictions(
            historical_values=train_values,
            steps=len(test_values),
            window=window
        )
    )

    metrics = calculate_model_metrics(
        test_values,
        test_predictions
    )

    score = calculate_validation_score(
        metrics,
        test_values
    )

    return {
        "name": (
            f"Moving Average "
            f"(Window {window})"
        ),
        "key": "moving_average",
        "model": None,
        "transformer": None,
        "window": window,
        "test_predictions": test_predictions,
        "metrics": metrics,
        "validation_score": score
    }


def compare_forecast_models(
    values: np.ndarray
) -> dict[str, Any]:
    """
    Compare Linear Regression, Polynomial Regression,
    and Moving Average using chronological validation.
    """

    values = np.asarray(
        values,
        dtype=float
    )

    split_data = create_train_test_split(
        values
    )

    train_values = split_data[
        "train_values"
    ]

    test_values = split_data[
        "test_values"
    ]

    train_indexes = split_data[
        "train_indexes"
    ]

    test_indexes = split_data[
        "test_indexes"
    ]

    model_results = []

    model_results.append(
        evaluate_linear_regression(
            train_indexes=train_indexes,
            train_values=train_values,
            test_indexes=test_indexes,
            test_values=test_values
        )
    )

    if len(train_values) >= 5:
        try:
            model_results.append(
                evaluate_polynomial_regression(
                    train_indexes=train_indexes,
                    train_values=train_values,
                    test_indexes=test_indexes,
                    test_values=test_values,
                    degree=2
                )
            )
        except Exception:
            pass

    for window in [2, 3, 4]:
        if len(train_values) >= window:
            try:
                model_results.append(
                    evaluate_moving_average(
                        train_values=train_values,
                        test_values=test_values,
                        window=window
                    )
                )
            except Exception:
                pass

    if not model_results:
        raise ValueError(
            "No forecasting model could be evaluated."
        )

    best_result = max(
        model_results,
        key=lambda item: item[
            "validation_score"
        ]
    )

    public_results = []

    for result in model_results:
        public_results.append({
            "name": result["name"],
            "key": result["key"],
            "validation_score": result[
                "validation_score"
            ],
            "metrics": result["metrics"]
        })

    return {
        "best_model": best_result,
        "model_comparison": public_results,
        "train_size": len(train_values),
        "test_size": len(test_values),
        "split_index": split_data[
            "split_index"
        ]
    }


def fit_best_model_and_forecast(
    values: np.ndarray,
    periods: int
) -> dict[str, Any]:
    """
    Compare models, select the best one, refit it using
    all historical data, and generate future predictions.
    """

    values = np.asarray(
        values,
        dtype=float
    )

    comparison = compare_forecast_models(
        values
    )

    best_result = comparison[
        "best_model"
    ]

    full_indexes = np.arange(
        len(values)
    ).reshape(-1, 1)

    future_indexes = np.arange(
        len(values),
        len(values) + periods
    ).reshape(-1, 1)

    if best_result["key"] == "linear":
        final_model = LinearRegression()

        final_model.fit(
            full_indexes,
            values
        )

        fitted_values = final_model.predict(
            full_indexes
        )

        future_predictions = final_model.predict(
            future_indexes
        )

    elif best_result["key"] == "polynomial":
        transformer = PolynomialFeatures(
            degree=2,
            include_bias=False
        )

        transformed_full = (
            transformer.fit_transform(
                full_indexes
            )
        )

        transformed_future = (
            transformer.transform(
                future_indexes
            )
        )

        final_model = LinearRegression()

        final_model.fit(
            transformed_full,
            values
        )

        fitted_values = final_model.predict(
            transformed_full
        )

        future_predictions = final_model.predict(
            transformed_future
        )

    elif best_result[
        "key"
    ] == "moving_average":
        window = best_result.get(
            "window",
            3
        )

        fitted_values = np.full(
            len(values),
            np.nan
        )

        for index in range(
            window,
            len(values)
        ):
            fitted_values[index] = np.mean(
                values[
                    index - window:index
                ]
            )

        fitted_values[
            :window
        ] = values[
            :window
        ]

        future_predictions = (
            moving_average_predictions(
                historical_values=values,
                steps=periods,
                window=window
            )
        )

    else:
        raise ValueError(
            "Unsupported best-model type."
        )

    residuals = (
        values - fitted_values
    )

    valid_residuals = residuals[
        ~np.isnan(residuals)
    ]

    residual_std = float(
        np.std(valid_residuals)
    ) if len(valid_residuals) > 0 else 0.0

    confidence_margin = (
        1.96 * residual_std
    )

    lower_bounds = (
        future_predictions
        - confidence_margin
    )

    upper_bounds = (
        future_predictions
        + confidence_margin
    )

    return {
        "best_model_name": best_result[
            "name"
        ],
        "best_model_key": best_result[
            "key"
        ],
        "validation_score": best_result[
            "validation_score"
        ],
        "validation_metrics": best_result[
            "metrics"
        ],
        "model_comparison": comparison[
            "model_comparison"
        ],
        "train_size": comparison[
            "train_size"
        ],
        "test_size": comparison[
            "test_size"
        ],
        "fitted_values": np.asarray(
            fitted_values,
            dtype=float
        ),
        "future_predictions": np.asarray(
            future_predictions,
            dtype=float
        ),
        "lower_bounds": np.asarray(
            lower_bounds,
            dtype=float
        ),
        "upper_bounds": np.asarray(
            upper_bounds,
            dtype=float
        ),
        "residual_standard_deviation": round(
            residual_std,
            2
        )
    }