import os

import pandas as pd

from flask import current_app


# ==========================================================
# Resolve Dataset Path
# ==========================================================

def resolve_dataset_path(filepath):
    """
    Resolve a dataset filename or filepath into an existing absolute path.

    Supported inputs:

    - superstore.csv
    - uploads/superstore.csv
    - C:/project/uploads/superstore.csv

    The function first checks the supplied path directly.
    If it does not exist, it checks Flask's configured
    UPLOAD_FOLDER.
    """

    if not filepath:
        raise FileNotFoundError(
            "No dataset filename or filepath was provided."
        )

    filepath = str(filepath).strip()

    # ------------------------------------------------------
    # Check the supplied filepath directly
    # ------------------------------------------------------

    if os.path.isfile(filepath):
        return os.path.abspath(filepath)

    # ------------------------------------------------------
    # Check Flask configured upload folder
    # ------------------------------------------------------

    try:
        upload_folder = current_app.config.get(
            "UPLOAD_FOLDER",
            "uploads"
        )
    except RuntimeError:
        # current_app is unavailable outside Flask context
        upload_folder = "uploads"

    # Convert relative upload folder into an absolute path
    if not os.path.isabs(upload_folder):
        try:
            upload_folder = os.path.join(
                current_app.root_path,
                upload_folder
            )
        except RuntimeError:
            upload_folder = os.path.abspath(
                upload_folder
            )

    filename = os.path.basename(
        filepath
    )

    upload_filepath = os.path.join(
        upload_folder,
        filename
    )

    if os.path.isfile(upload_filepath):
        return os.path.abspath(
            upload_filepath
        )

    # ------------------------------------------------------
    # Check project-root uploads directory
    # ------------------------------------------------------

    fallback_filepath = os.path.abspath(
        os.path.join(
            "uploads",
            filename
        )
    )

    if os.path.isfile(fallback_filepath):
        return fallback_filepath

    raise FileNotFoundError(
        f"Dataset '{filename}' could not be found. "
        f"Checked supplied path, configured upload folder, "
        f"and project uploads directory."
    )


# ==========================================================
# Load Dataset
# ==========================================================

def load_dataset(filepath):
    """
    Load a CSV or Excel dataset.

    filepath may be either:

    - A complete filepath
    - A relative filepath
    - A filename stored inside UPLOAD_FOLDER
    """

    resolved_filepath = resolve_dataset_path(
        filepath
    )

    if "." not in resolved_filepath:
        raise ValueError(
            "The dataset does not have a valid file extension."
        )

    file_extension = resolved_filepath.rsplit(
        ".",
        1
    )[1].lower()

    if file_extension == "csv":
        return pd.read_csv(
            resolved_filepath
        )

    if file_extension in [
        "xlsx",
        "xls"
    ]:
        return pd.read_excel(
            resolved_filepath
        )

    raise ValueError(
        f"Unsupported file format: {file_extension}"
    )


# ==========================================================
# Dataset Statistics
# ==========================================================

def get_dataset_stats(df, filepath=None):
    """
    Generate high-level dataset statistics.

    filepath is optional and retained for compatibility
    with existing routes.
    """

    total_values = (
        df.shape[0] *
        df.shape[1]
    )

    missing_values = int(
        df.isnull().sum().sum()
    )

    duplicate_rows = int(
        df.duplicated().sum()
    )

    if total_values > 0:
        quality_score = round(
            (
                (
                    total_values -
                    missing_values
                ) /
                total_values
            ) *
            100,
            2
        )
    else:
        quality_score = 0

    memory_usage = round(
        df.memory_usage(
            deep=True
        ).sum() /
        (
            1024 *
            1024
        ),
        2
    )

    numeric_columns = df.select_dtypes(
        include="number"
    ).shape[1]

    categorical_columns = df.select_dtypes(
        include=[
            "object",
            "category",
            "string"
        ]
    ).shape[1]

    return {
        "rows": int(
            df.shape[0]
        ),
        "columns": int(
            df.shape[1]
        ),
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
        "numeric_columns": int(
            numeric_columns
        ),
        "categorical_columns": int(
            categorical_columns
        ),
        "memory_usage": memory_usage,
        "quality_score": quality_score
    }


# ==========================================================
# Column Summary
# ==========================================================

def get_column_summary(df):
    """
    Generate summary information for each dataset column.
    """

    summary = []

    total_rows = len(
        df
    )

    for column in df.columns:
        missing_count = int(
            df[column].isnull().sum()
        )

        if total_rows > 0:
            missing_percent = round(
                (
                    missing_count /
                    total_rows
                ) *
                100,
                2
            )
        else:
            missing_percent = 0

        summary.append({
            "column": str(
                column
            ),
            "dtype": str(
                df[column].dtype
            ),
            "missing_count": missing_count,
            "missing_percent": missing_percent,
            "unique_count": int(
                df[column].nunique(
                    dropna=True
                )
            )
        })

    return summary


# ==========================================================
# Numeric Summary
# ==========================================================

def get_numeric_summary(df):
    """
    Generate descriptive statistics for numeric columns.
    """

    numeric_df = df.select_dtypes(
        include="number"
    )

    if numeric_df.empty:
        return []

    description = numeric_df.describe().T

    summary = []

    for column in description.index:
        summary.append({
            "column": str(
                column
            ),
            "count": round(
                float(
                    description.loc[
                        column,
                        "count"
                    ]
                ),
                2
            ),
            "mean": round(
                float(
                    description.loc[
                        column,
                        "mean"
                    ]
                ),
                2
            ),
            "std": round(
                float(
                    description.loc[
                        column,
                        "std"
                    ]
                ),
                2
            ),
            "min": round(
                float(
                    description.loc[
                        column,
                        "min"
                    ]
                ),
                2
            ),
            "q1": round(
                float(
                    description.loc[
                        column,
                        "25%"
                    ]
                ),
                2
            ),
            "median": round(
                float(
                    description.loc[
                        column,
                        "50%"
                    ]
                ),
                2
            ),
            "q3": round(
                float(
                    description.loc[
                        column,
                        "75%"
                    ]
                ),
                2
            ),
            "max": round(
                float(
                    description.loc[
                        column,
                        "max"
                    ]
                ),
                2
            )
        })

    return summary


# ==========================================================
# Chart Data
# ==========================================================

def get_chart_data(df):
    """
    Prepare chart data for data-type and missing-value charts.
    """

    dtype_counts = (
        df.dtypes
        .astype(str)
        .value_counts()
    )

    missing_values = (
        df.isnull()
        .sum()
    )

    missing_values = missing_values[
        missing_values > 0
    ]

    return {
        "dtype_labels": dtype_counts.index.tolist(),
        "dtype_values": [
            int(value)
            for value in dtype_counts.values.tolist()
        ],
        "missing_labels": [
            str(label)
            for label in missing_values.index.tolist()
        ],
        "missing_values": [
            int(value)
            for value in missing_values.values.tolist()
        ]
    }


# ==========================================================
# Save Uploaded Dataset
# ==========================================================

def save_uploaded_file(
    file,
    upload_folder,
    filename
):
    """
    Save an uploaded dataset inside the configured upload folder.
    """

    if not filename:
        raise ValueError(
            "A filename is required."
        )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    safe_filename = os.path.basename(
        filename
    )

    filepath = os.path.join(
        upload_folder,
        safe_filename
    )

    file.save(
        filepath
    )

    return os.path.abspath(
        filepath
    )