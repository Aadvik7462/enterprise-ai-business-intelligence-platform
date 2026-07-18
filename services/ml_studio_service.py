
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    silhouette_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass
class MLResult:
    success: bool
    message: str
    task_type: str = ""
    model_name: str = ""
    metrics: dict[str, Any] | None = None
    feature_importance: list[dict[str, Any]] | None = None
    preview: list[dict[str, Any]] | None = None
    chart: dict[str, Any] | None = None
    model_bytes: bytes | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "task_type": self.task_type,
            "model_name": self.model_name,
            "metrics": self.metrics or {},
            "feature_importance": self.feature_importance or [],
            "preview": self.preview or [],
            "chart": self.chart or {},
        }


def infer_task(dataframe, target_column, requested_task):
    if requested_task in {"classification", "regression", "clustering"}:
        return requested_task

    if not target_column:
        return "clustering"

    target = dataframe[target_column]

    if pd.api.types.is_numeric_dtype(target) and target.nunique(dropna=True) > 15:
        return "regression"

    return "classification"


def build_preprocessor(features):
    numeric = features.select_dtypes(include="number").columns.astype(str).tolist()
    categorical = [str(column) for column in features.columns if str(column) not in numeric]

    transformers = []

    if numeric:
        transformers.append((
            "numeric",
            Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]),
            numeric,
        ))

    if categorical:
        transformers.append((
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]),
            categorical,
        ))

    return ColumnTransformer(transformers=transformers), numeric, categorical


def get_feature_names(pipeline, numeric, categorical):
    names = list(numeric)

    if categorical:
        encoder = (
            pipeline.named_steps["preprocessor"]
            .named_transformers_["categorical"]
            .named_steps["encoder"]
        )
        names.extend(encoder.get_feature_names_out(categorical).tolist())

    return names


def get_importance(pipeline, numeric, categorical):
    model = pipeline.named_steps["model"]

    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_)
        values = np.mean(np.abs(coef), axis=0) if coef.ndim > 1 else np.abs(coef)
    else:
        return []

    names = get_feature_names(pipeline, numeric, categorical)

    output = [
        {"feature": str(name), "importance": round(float(value), 6)}
        for name, value in zip(names, values)
    ]

    output.sort(key=lambda item: item["importance"], reverse=True)
    return output[:20]


def train_supervised(dataframe, target_column, task_type, model_name, test_size):
    working = dataframe.dropna(subset=[target_column]).copy()

    if len(working) < 20:
        return MLResult(False, "At least 20 valid rows are required.")

    features = working.drop(columns=[target_column])
    target = working[target_column]

    preprocessor, numeric, categorical = build_preprocessor(features)

    if task_type == "classification":
        if target.nunique(dropna=True) < 2:
            return MLResult(False, "Classification requires at least two target classes.")

        model = (
            LogisticRegression(max_iter=1200, class_weight="balanced")
            if model_name == "logistic_regression"
            else RandomForestClassifier(
                n_estimators=250,
                random_state=42,
                class_weight="balanced",
                n_jobs=-1,
            )
        )

        stratify = target if target.value_counts().min() >= 2 else None

    else:
        target = pd.to_numeric(target, errors="coerce")
        valid = target.notna()
        features = features.loc[valid]
        target = target.loc[valid]

        if len(target) < 20:
            return MLResult(False, "Regression requires at least 20 numeric target values.")

        model = (
            LinearRegression()
            if model_name == "linear_regression"
            else RandomForestRegressor(
                n_estimators=250,
                random_state=42,
                n_jobs=-1,
            )
        )

        stratify = None

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=max(0.1, min(float(test_size), 0.4)),
        random_state=42,
        stratify=stratify,
    )

    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("model", model),
    ])

    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)

    if task_type == "classification":
        metrics = {
            "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
            "precision": round(float(precision_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, predictions, average="weighted", zero_division=0)), 4),
        }

        preview = pd.DataFrame({
            "actual": y_test.astype(str).head(30).tolist(),
            "predicted": pd.Series(predictions).astype(str).head(30).tolist(),
        }).to_dict(orient="records")

        chart = {
            "type": "classification",
            "title": "Actual vs Predicted Classes",
            "actual": [str(value) for value in y_test.head(100)],
            "predicted": [str(value) for value in pd.Series(predictions).head(100)],
        }

    else:
        metrics = {
            "r2_score": round(float(r2_score(y_test, predictions)), 4),
            "mae": round(float(mean_absolute_error(y_test, predictions)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, predictions))), 4),
        }

        preview = pd.DataFrame({
            "actual": y_test.astype(float).head(30).tolist(),
            "predicted": pd.Series(predictions).astype(float).head(30).tolist(),
        }).to_dict(orient="records")

        chart = {
            "type": "scatter",
            "title": "Actual vs Predicted",
            "x": y_test.astype(float).head(200).tolist(),
            "y": pd.Series(predictions).astype(float).head(200).tolist(),
        }

    buffer = io.BytesIO()
    joblib.dump({
        "pipeline": pipeline,
        "task_type": task_type,
        "model_name": model_name,
        "target_column": target_column,
        "feature_columns": features.columns.astype(str).tolist(),
    }, buffer)

    return MLResult(
        True,
        "Model training completed successfully.",
        task_type=task_type,
        model_name=model_name,
        metrics=metrics,
        feature_importance=get_importance(pipeline, numeric, categorical),
        preview=preview,
        chart=chart,
        model_bytes=buffer.getvalue(),
    )


def train_clustering(dataframe, cluster_count):
    numeric = dataframe.select_dtypes(include="number").replace([np.inf, -np.inf], np.nan)

    if numeric.shape[1] < 2:
        return MLResult(False, "Clustering requires at least two numeric columns.")

    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()

    values = imputer.fit_transform(numeric)
    scaled = scaler.fit_transform(values)

    clusters = max(2, min(int(cluster_count), min(10, len(numeric) - 1)))

    model = KMeans(n_clusters=clusters, random_state=42, n_init=10)
    labels = model.fit_predict(scaled)

    score = silhouette_score(scaled, labels) if len(set(labels)) > 1 else 0

    result = numeric.copy()
    result["cluster"] = labels

    summary = (
        result.groupby("cluster")
        .mean(numeric_only=True)
        .reset_index()
        .round(4)
    )

    first, second = numeric.columns[:2]

    chart = {
        "type": "cluster_scatter",
        "title": f"Clusters: {first} vs {second}",
        "x": result[first].head(300).astype(float).tolist(),
        "y": result[second].head(300).astype(float).tolist(),
        "labels": result["cluster"].head(300).astype(int).tolist(),
        "x_label": str(first),
        "y_label": str(second),
    }

    buffer = io.BytesIO()
    joblib.dump({
        "model": model,
        "imputer": imputer,
        "scaler": scaler,
        "feature_columns": numeric.columns.astype(str).tolist(),
        "task_type": "clustering",
    }, buffer)

    importance = [
        {"feature": str(column), "importance": round(float(numeric[column].var()), 6)}
        for column in numeric.columns
    ]
    importance.sort(key=lambda item: item["importance"], reverse=True)

    return MLResult(
        True,
        "Clustering completed successfully.",
        task_type="clustering",
        model_name="kmeans",
        metrics={
            "cluster_count": clusters,
            "silhouette_score": round(float(score), 4),
        },
        feature_importance=importance[:20],
        preview=summary.to_dict(orient="records"),
        chart=chart,
        model_bytes=buffer.getvalue(),
    )


def train_ml_model(
    dataframe,
    requested_task,
    target_column,
    model_name,
    test_size=0.2,
    cluster_count=4,
):
    task_type = infer_task(dataframe, target_column, requested_task)

    if task_type == "clustering":
        return train_clustering(dataframe, cluster_count)

    if not target_column:
        return MLResult(False, "Select a target column.")

    return train_supervised(
        dataframe,
        target_column,
        task_type,
        model_name,
        test_size,
    )
