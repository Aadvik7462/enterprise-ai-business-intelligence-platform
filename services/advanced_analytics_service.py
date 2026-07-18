from __future__ import annotations

from typing import Any
import pandas as pd


def get_numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.select_dtypes(include="number").columns]


def generate_correlation_matrix(df: pd.DataFrame) -> dict[str, Any]:
    columns = get_numeric_columns(df)
    if len(columns) < 2:
        return {"success": False, "message": "At least two numeric columns are required.", "columns": [], "matrix": []}
    matrix = df[columns].corr().fillna(0).round(4)
    return {"success": True, "columns": columns, "matrix": matrix.values.tolist()}


def detect_outliers(df: pd.DataFrame, column: str | None = None) -> dict[str, Any]:
    numeric = get_numeric_columns(df)
    selected = [column] if column in numeric else numeric
    results = []
    for name in selected:
        series = pd.to_numeric(df[name], errors="coerce").dropna()
        if series.empty:
            continue
        q1, q3 = float(series.quantile(.25)), float(series.quantile(.75))
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = series[(series < lower) | (series > upper)]
        results.append({
            "column": name,
            "outlier_count": int(len(outliers)),
            "outlier_percent": round(len(outliers) / max(1, len(series)) * 100, 2),
            "lower_bound": round(lower, 4),
            "upper_bound": round(upper, 4),
        })
    return {"success": True, "results": results}


def analyze_missing_values(df: pd.DataFrame) -> dict[str, Any]:
    total_rows = max(1, len(df))
    results = []
    for column in df.columns:
        count = int(df[column].isna().sum())
        results.append({"column": str(column), "missing_count": count, "missing_percent": round(count / total_rows * 100, 2)})
    results.sort(key=lambda item: item["missing_count"], reverse=True)
    return {"success": True, "total_missing": int(df.isna().sum().sum()), "results": results}


def generate_feature_importance(df: pd.DataFrame, target_column: str) -> dict[str, Any]:
    numeric = get_numeric_columns(df)
    if target_column not in numeric:
        return {"success": False, "message": "Target column must be numeric.", "features": []}
    features = [c for c in numeric if c != target_column]
    clean = df[features + [target_column]].apply(pd.to_numeric, errors="coerce").dropna()
    if clean.empty or not features:
        return {"success": False, "message": "Not enough complete numeric records are available.", "features": []}
    target = clean[target_column]
    output = []
    for feature in features:
        corr = clean[feature].corr(target)
        corr = 0.0 if pd.isna(corr) else float(corr)
        output.append({"feature": feature, "importance": round(abs(corr), 4), "direction": "positive" if corr >= 0 else "negative"})
    output.sort(key=lambda item: item["importance"], reverse=True)
    return {"success": True, "target_column": target_column, "features": output}


def generate_statistical_summary(df: pd.DataFrame) -> dict[str, Any]:
    rows = []
    for column in get_numeric_columns(df):
        s = pd.to_numeric(df[column], errors="coerce").dropna()
        if s.empty:
            continue
        rows.append({
            "column": column,
            "count": int(s.count()),
            "mean": round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "std": round(float(s.std()), 4),
            "minimum": round(float(s.min()), 4),
            "maximum": round(float(s.max()), 4),
            "skewness": round(float(s.skew()), 4),
            "kurtosis": round(float(s.kurt()), 4),
        })
    return {"success": True, "summaries": rows}
