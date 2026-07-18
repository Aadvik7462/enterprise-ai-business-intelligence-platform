import os
import pandas as pd


def load_dataset(filepath):
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath)

    if filepath.endswith(".xlsx") or filepath.endswith(".xls"):
        return pd.read_excel(filepath)

    raise ValueError("Unsupported file format")


def get_dataset_stats(df, filepath):
    rows = df.shape[0]
    columns = df.shape[1]

    missing_values = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    numeric_columns = len(df.select_dtypes(include=["int64", "float64"]).columns)
    categorical_columns = len(df.select_dtypes(include=["object"]).columns)
    date_columns = len(df.select_dtypes(include=["datetime64"]).columns)

    memory_usage = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
    file_size = round(os.path.getsize(filepath) / (1024 * 1024), 2)

    total_cells = rows * columns
    missing_percent = (missing_values / total_cells) * 100 if total_cells > 0 else 0
    duplicate_percent = (duplicate_rows / rows) * 100 if rows > 0 else 0

    quality_score = 100 - missing_percent - duplicate_percent
    quality_score = max(0, round(quality_score, 2))

    return {
        "rows": rows,
        "columns": columns,
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "date_columns": date_columns,
        "memory_usage": memory_usage,
        "file_size": file_size,
        "quality_score": quality_score
    }


def get_column_summary(df):
    summary = []

    for column in df.columns:
        missing_count = int(df[column].isnull().sum())
        missing_percent = round((missing_count / len(df)) * 100, 2) if len(df) > 0 else 0
        unique_count = int(df[column].nunique())

        summary.append({
            "column": column,
            "dtype": str(df[column].dtype),
            "missing_count": missing_count,
            "missing_percent": missing_percent,
            "unique_count": unique_count
        })

    return summary


def get_numeric_summary(df):
    numeric_df = df.select_dtypes(include=["int64", "float64"])

    if numeric_df.empty:
        return []

    stats = numeric_df.describe().T.reset_index()
    stats = stats.rename(columns={
        "index": "column",
        "count": "count",
        "mean": "mean",
        "std": "std",
        "min": "min",
        "25%": "q1",
        "50%": "median",
        "75%": "q3",
        "max": "max"
    })

    stats = stats.round(2)

    return stats.to_dict(orient="records")


def get_chart_data(df):
    dtype_counts = {
        "Numeric": len(df.select_dtypes(include=["int64", "float64"]).columns),
        "Text": len(df.select_dtypes(include=["object"]).columns),
        "Date": len(df.select_dtypes(include=["datetime64"]).columns),
        "Boolean": len(df.select_dtypes(include=["bool"]).columns)
    }

    missing_by_column = df.isnull().sum()
    missing_by_column = missing_by_column[missing_by_column > 0].sort_values(ascending=False).head(10)

    return {
        "dtype_labels": list(dtype_counts.keys()),
        "dtype_values": list(dtype_counts.values()),
        "missing_labels": list(missing_by_column.index),
        "missing_values": [int(v) for v in missing_by_column.values]
    }
def clean_dataset(df):
    original_rows = df.shape[0]
    original_columns = df.shape[1]
    original_missing = int(df.isnull().sum().sum())
    original_duplicates = int(df.duplicated().sum())

    cleaned_df = df.copy()

    # Standardize column names
    cleaned_df.columns = (
        cleaned_df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    # Remove fully empty rows
    cleaned_df = cleaned_df.dropna(how="all")

    # Remove duplicate rows
    cleaned_df = cleaned_df.drop_duplicates()

    # Trim text columns
    text_columns = cleaned_df.select_dtypes(include=["object"]).columns
    for col in text_columns:
        cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
        cleaned_df[col] = cleaned_df[col].replace("nan", None)

    # Fill missing numeric values with median
    numeric_columns = cleaned_df.select_dtypes(include=["int64", "float64"]).columns
    for col in numeric_columns:
        if cleaned_df[col].isnull().sum() > 0:
            cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].median())

    # Fill missing text values with mode
    text_columns = cleaned_df.select_dtypes(include=["object"]).columns
    for col in text_columns:
        if cleaned_df[col].isnull().sum() > 0:
            mode_value = cleaned_df[col].mode()
            if not mode_value.empty:
                cleaned_df[col] = cleaned_df[col].fillna(mode_value[0])
            else:
                cleaned_df[col] = cleaned_df[col].fillna("Unknown")

    cleaned_rows = cleaned_df.shape[0]
    cleaned_columns = cleaned_df.shape[1]
    cleaned_missing = int(cleaned_df.isnull().sum().sum())
    cleaned_duplicates = int(cleaned_df.duplicated().sum())

    report = {
        "original_rows": original_rows,
        "original_columns": original_columns,
        "original_missing": original_missing,
        "original_duplicates": original_duplicates,
        "cleaned_rows": cleaned_rows,
        "cleaned_columns": cleaned_columns,
        "cleaned_missing": cleaned_missing,
        "cleaned_duplicates": cleaned_duplicates,
        "rows_removed": original_rows - cleaned_rows,
        "missing_fixed": original_missing - cleaned_missing,
        "duplicates_removed": original_duplicates - cleaned_duplicates
    }

    return cleaned_df, report