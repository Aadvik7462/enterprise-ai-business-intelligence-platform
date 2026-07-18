
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def detect_date_columns(dataframe: pd.DataFrame) -> list[str]:
    detected = []

    for column in dataframe.columns:
        if pd.api.types.is_datetime64_any_dtype(dataframe[column]):
            detected.append(str(column))
            continue

        converted = pd.to_datetime(
            dataframe[column],
            errors="coerce",
        )

        if converted.notna().mean() >= 0.7:
            detected.append(str(column))

    return detected


def numeric_columns(dataframe: pd.DataFrame) -> list[str]:
    return (
        dataframe.select_dtypes(include="number")
        .columns.astype(str)
        .tolist()
    )


def create_forecast(
    dataframe: pd.DataFrame,
    date_column: str,
    value_column: str,
    periods: int = 12,
) -> dict[str, Any]:
    if date_column not in dataframe.columns:
        raise ValueError("The selected date column does not exist.")

    if value_column not in dataframe.columns:
        raise ValueError("The selected value column does not exist.")

    working = dataframe[
        [
            date_column,
            value_column,
        ]
    ].copy()

    working[date_column] = pd.to_datetime(
        working[date_column],
        errors="coerce",
    )

    working[value_column] = pd.to_numeric(
        working[value_column],
        errors="coerce",
    )

    working = (
        working.dropna()
        .sort_values(date_column)
    )

    if len(working) < 10:
        raise ValueError(
            "At least 10 valid dated observations are required."
        )

    grouped = (
        working.set_index(date_column)[value_column]
        .resample("MS")
        .sum()
        .dropna()
    )

    if len(grouped) < 6:
        grouped = (
            working.set_index(date_column)[value_column]
            .resample("D")
            .sum()
            .dropna()
        )

    if len(grouped) < 6:
        raise ValueError(
            "The dataset does not contain enough time periods."
        )

    x = np.arange(
        len(grouped)
    ).reshape(-1, 1)

    y = grouped.values.astype(float)

    model = LinearRegression()
    model.fit(
        x,
        y,
    )

    fitted = model.predict(
        x
    )

    future_x = np.arange(
        len(grouped),
        len(grouped) + periods,
    ).reshape(-1, 1)

    future_values = model.predict(
        future_x
    )

    inferred_frequency = pd.infer_freq(
        grouped.index
    ) or "MS"

    future_dates = pd.date_range(
        start=grouped.index[-1],
        periods=periods + 1,
        freq=inferred_frequency,
    )[1:]

    residual_std = float(
        np.std(
            y - fitted
        )
    )

    lower = future_values - 1.96 * residual_std
    upper = future_values + 1.96 * residual_std

    return {
        "success": True,
        "metrics": {
            "r2_score": round(
                float(
                    r2_score(
                        y,
                        fitted,
                    )
                ),
                4,
            ),
            "mae": round(
                float(
                    mean_absolute_error(
                        y,
                        fitted,
                    )
                ),
                4,
            ),
            "rmse": round(
                float(
                    np.sqrt(
                        mean_squared_error(
                            y,
                            fitted,
                        )
                    )
                ),
                4,
            ),
        },
        "history": {
            "dates": [
                date.isoformat()
                for date in grouped.index
            ],
            "values": [
                float(value)
                for value in y
            ],
            "fitted": [
                float(value)
                for value in fitted
            ],
        },
        "forecast": {
            "dates": [
                date.isoformat()
                for date in future_dates
            ],
            "values": [
                float(value)
                for value in future_values
            ],
            "lower": [
                float(value)
                for value in lower
            ],
            "upper": [
                float(value)
                for value in upper
            ],
        },
        "scenario": {
            "optimistic": [
                float(value * 1.1)
                for value in future_values
            ],
            "base": [
                float(value)
                for value in future_values
            ],
            "conservative": [
                float(value * 0.9)
                for value in future_values
            ],
        },
    }
