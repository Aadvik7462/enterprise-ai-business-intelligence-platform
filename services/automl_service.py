
from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


@dataclass
class AutoMLResult:
    success: bool
    message: str
    task_type: str = ""
    target_column: str = ""
    leaderboard: list[dict[str, Any]] | None = None
    best_model: dict[str, Any] | None = None
    feature_importance: list[dict[str, Any]] | None = None
    preview: list[dict[str, Any]] | None = None
    model_bytes: bytes | None = None
    predictions_csv: bytes | None = None
    leaderboard_csv: bytes | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "task_type": self.task_type,
            "target_column": self.target_column,
            "leaderboard": self.leaderboard or [],
            "best_model": self.best_model or {},
            "feature_importance": self.feature_importance or [],
            "preview": self.preview or [],
        }


def detect_task_type(dataframe: pd.DataFrame, target_column: str) -> str:
    target = dataframe[target_column]

    if pd.api.types.is_numeric_dtype(target) and target.nunique(dropna=True) > 15:
        return "regression"

    return "classification"


def build_preprocessor(features: pd.DataFrame):
    numeric_columns = (
        features.select_dtypes(include="number")
        .columns.astype(str)
        .tolist()
    )

    categorical_columns = [
        str(column)
        for column in features.columns
        if str(column) not in numeric_columns
    ]

    transformers = []

    if numeric_columns:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns,
            )
        )

    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="most_frequent"),
                        ),
                        (
                            "encoder",
                            OneHotEncoder(
                                handle_unknown="ignore",
                                sparse_output=False,
                            ),
                        ),
                    ]
                ),
                categorical_columns,
            )
        )

    return (
        ColumnTransformer(
            transformers=transformers,
            remainder="drop",
        ),
        numeric_columns,
        categorical_columns,
    )


def get_models(task_type: str) -> dict[str, Any]:
    if task_type == "classification":
        return {
            "Logistic Regression": LogisticRegression(
                max_iter=1200,
                class_weight="balanced",
            ),
            "Decision Tree": DecisionTreeClassifier(
                random_state=42,
                class_weight="balanced",
                max_depth=12,
            ),
            "Random Forest": RandomForestClassifier(
                n_estimators=220,
                random_state=42,
                class_weight="balanced",
                n_jobs=-1,
            ),
            "Extra Trees": ExtraTreesClassifier(
                n_estimators=220,
                random_state=42,
                class_weight="balanced",
                n_jobs=-1,
            ),
            "Gradient Boosting": GradientBoostingClassifier(
                random_state=42,
            ),
        }

    return {
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(alpha=1.0),
        "Decision Tree": DecisionTreeRegressor(
            random_state=42,
            max_depth=12,
        ),
        "Random Forest": RandomForestRegressor(
            n_estimators=220,
            random_state=42,
            n_jobs=-1,
        ),
        "Extra Trees": ExtraTreesRegressor(
            n_estimators=220,
            random_state=42,
            n_jobs=-1,
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            random_state=42,
        ),
    }


def get_feature_names(
    pipeline: Pipeline,
    numeric_columns: list[str],
    categorical_columns: list[str],
) -> list[str]:
    names = list(numeric_columns)

    if categorical_columns:
        encoder = (
            pipeline.named_steps["preprocessor"]
            .named_transformers_["categorical"]
            .named_steps["encoder"]
        )

        names.extend(
            encoder.get_feature_names_out(
                categorical_columns
            ).tolist()
        )

    return names


def extract_feature_importance(
    pipeline: Pipeline,
    numeric_columns: list[str],
    categorical_columns: list[str],
) -> list[dict[str, Any]]:
    model = pipeline.named_steps["model"]

    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_)
        values = (
            np.mean(np.abs(coef), axis=0)
            if coef.ndim > 1
            else np.abs(coef)
        )
    else:
        return []

    names = get_feature_names(
        pipeline,
        numeric_columns,
        categorical_columns,
    )

    output = [
        {
            "feature": str(name),
            "importance": round(float(value), 6),
        }
        for name, value in zip(names, values)
    ]

    output.sort(
        key=lambda item: item["importance"],
        reverse=True,
    )

    return output[:20]


def classification_metrics(y_true, predictions) -> dict[str, float]:
    return {
        "accuracy": round(
            float(
                accuracy_score(
                    y_true,
                    predictions,
                )
            ),
            4,
        ),
        "precision": round(
            float(
                precision_score(
                    y_true,
                    predictions,
                    average="weighted",
                    zero_division=0,
                )
            ),
            4,
        ),
        "recall": round(
            float(
                recall_score(
                    y_true,
                    predictions,
                    average="weighted",
                    zero_division=0,
                )
            ),
            4,
        ),
        "f1_score": round(
            float(
                f1_score(
                    y_true,
                    predictions,
                    average="weighted",
                    zero_division=0,
                )
            ),
            4,
        ),
    }


def regression_metrics(y_true, predictions) -> dict[str, float]:
    return {
        "r2_score": round(
            float(
                r2_score(
                    y_true,
                    predictions,
                )
            ),
            4,
        ),
        "mae": round(
            float(
                mean_absolute_error(
                    y_true,
                    predictions,
                )
            ),
            4,
        ),
        "rmse": round(
            float(
                np.sqrt(
                    mean_squared_error(
                        y_true,
                        predictions,
                    )
                )
            ),
            4,
        ),
    }


def run_automl(
    dataframe: pd.DataFrame,
    target_column: str,
    test_size: float = 0.2,
) -> AutoMLResult:
    if target_column not in dataframe.columns:
        return AutoMLResult(
            success=False,
            message="The selected target column does not exist.",
        )

    working = dataframe.dropna(
        subset=[target_column]
    ).drop_duplicates().copy()

    if len(working) < 30:
        return AutoMLResult(
            success=False,
            message="AutoML requires at least 30 valid rows.",
        )

    task_type = detect_task_type(
        working,
        target_column,
    )

    features = working.drop(
        columns=[target_column]
    )

    target = working[target_column]

    if features.shape[1] == 0:
        return AutoMLResult(
            success=False,
            message="No feature columns are available.",
        )

    if task_type == "regression":
        target = pd.to_numeric(
            target,
            errors="coerce",
        )

        valid_mask = target.notna()
        features = features.loc[valid_mask]
        target = target.loc[valid_mask]

        stratify = None

    else:
        if target.nunique(dropna=True) < 2:
            return AutoMLResult(
                success=False,
                message="Classification requires at least two classes.",
            )

        stratify = (
            target
            if target.value_counts().min() >= 2
            else None
        )

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=max(
            0.1,
            min(
                float(test_size),
                0.4,
            ),
        ),
        random_state=42,
        stratify=stratify,
    )

    preprocessor, numeric_columns, categorical_columns = (
        build_preprocessor(
            x_train
        )
    )

    leaderboard: list[dict[str, Any]] = []
    fitted_models: dict[str, Pipeline] = {}
    prediction_map: dict[str, np.ndarray] = {}

    for model_name, estimator in get_models(
        task_type
    ).items():
        started = time.perf_counter()

        pipeline = Pipeline(
            [
                (
                    "preprocessor",
                    preprocessor,
                ),
                (
                    "model",
                    estimator,
                ),
            ]
        )

        try:
            pipeline.fit(
                x_train,
                y_train,
            )

            predictions = pipeline.predict(
                x_test
            )

            elapsed = time.perf_counter() - started

            metrics = (
                classification_metrics(
                    y_test,
                    predictions,
                )
                if task_type == "classification"
                else regression_metrics(
                    y_test,
                    predictions,
                )
            )

            score = (
                metrics["f1_score"]
                if task_type == "classification"
                else metrics["r2_score"]
            )

            row = {
                "model_name": model_name,
                "status": "Success",
                "score": round(
                    float(score),
                    4,
                ),
                "training_time": round(
                    float(elapsed),
                    3,
                ),
                **metrics,
            }

            leaderboard.append(
                row
            )

            fitted_models[model_name] = pipeline
            prediction_map[model_name] = predictions

        except Exception as error:
            leaderboard.append(
                {
                    "model_name": model_name,
                    "status": "Failed",
                    "score": -999999,
                    "training_time": round(
                        float(
                            time.perf_counter()
                            - started
                        ),
                        3,
                    ),
                    "error": str(error),
                }
            )

    successful = [
        row
        for row in leaderboard
        if row["status"] == "Success"
    ]

    if not successful:
        return AutoMLResult(
            success=False,
            message="All AutoML models failed to train.",
            task_type=task_type,
            target_column=target_column,
            leaderboard=leaderboard,
        )

    successful.sort(
        key=lambda row: row["score"],
        reverse=True,
    )

    failed = [
        row
        for row in leaderboard
        if row["status"] != "Success"
    ]

    leaderboard = successful + failed

    best_row = successful[0]
    best_name = best_row["model_name"]
    best_pipeline = fitted_models[best_name]
    best_predictions = prediction_map[best_name]

    feature_importance = extract_feature_importance(
        best_pipeline,
        numeric_columns,
        categorical_columns,
    )

    preview_dataframe = pd.DataFrame(
        {
            "actual": (
                y_test.astype(str).tolist()
                if task_type == "classification"
                else y_test.astype(float).tolist()
            ),
            "predicted": (
                pd.Series(best_predictions).astype(str).tolist()
                if task_type == "classification"
                else pd.Series(best_predictions).astype(float).tolist()
            ),
        }
    )

    preview = (
        preview_dataframe
        .head(50)
        .to_dict(
            orient="records"
        )
    )

    model_buffer = io.BytesIO()

    joblib.dump(
        {
            "pipeline": best_pipeline,
            "task_type": task_type,
            "target_column": target_column,
            "model_name": best_name,
            "feature_columns": features.columns.astype(str).tolist(),
        },
        model_buffer,
    )

    leaderboard_csv = (
        pd.DataFrame(
            leaderboard
        )
        .to_csv(
            index=False
        )
        .encode(
            "utf-8"
        )
    )

    predictions_csv = (
        preview_dataframe
        .to_csv(
            index=False
        )
        .encode(
            "utf-8"
        )
    )

    best_model = {
        **best_row,
        "selection_reason": (
            "Highest weighted F1 score among successful models."
            if task_type == "classification"
            else "Highest R² score among successful models."
        ),
        "training_rows": int(
            len(
                x_train
            )
        ),
        "testing_rows": int(
            len(
                x_test
            )
        ),
        "feature_count": int(
            features.shape[1]
        ),
    }

    return AutoMLResult(
        success=True,
        message="AutoML training completed successfully.",
        task_type=task_type,
        target_column=target_column,
        leaderboard=leaderboard,
        best_model=best_model,
        feature_importance=feature_importance,
        preview=preview,
        model_bytes=model_buffer.getvalue(),
        predictions_csv=predictions_csv,
        leaderboard_csv=leaderboard_csv,
    )
