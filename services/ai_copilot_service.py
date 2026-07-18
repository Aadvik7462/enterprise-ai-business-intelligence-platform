import re

import pandas as pd


def _normalize_question(question):
    return re.sub(r"\s+", " ", question.strip().lower())


def _find_column(df, keywords):
    for column in df.columns:
        normalized_column = str(column).lower().replace("_", " ").strip()

        for keyword in keywords:
            if keyword in normalized_column:
                return column

    return None


def _format_number(value):
    try:
        numeric_value = float(value)

        if numeric_value.is_integer():
            return f"{int(numeric_value):,}"

        return f"{numeric_value:,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _dataset_summary(df, stats):
    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    categorical_columns = df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    return (
        f"The dataset contains {stats['rows']:,} rows and "
        f"{stats['columns']:,} columns. "
        f"It has {len(numeric_columns)} numeric columns and "
        f"{len(categorical_columns)} text or categorical columns. "
        f"The quality score is {stats['quality_score']}%. "
        f"There are {stats['missing_values']:,} missing values and "
        f"{stats['duplicate_rows']:,} duplicate rows."
    )


def _numeric_columns_response(df):
    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    if not numeric_columns:
        return "No numeric columns were detected in this dataset."

    column_list = ", ".join(map(str, numeric_columns))

    return (
        f"The dataset contains {len(numeric_columns)} numeric columns: "
        f"{column_list}."
    )


def _categorical_columns_response(df):
    categorical_columns = df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    if not categorical_columns:
        return "No categorical columns were detected in this dataset."

    column_list = ", ".join(map(str, categorical_columns))

    return (
        f"The dataset contains {len(categorical_columns)} categorical columns: "
        f"{column_list}."
    )


def _missing_values_response(df, stats):
    missing_by_column = df.isnull().sum()
    missing_by_column = missing_by_column[missing_by_column > 0]

    if missing_by_column.empty:
        return "No missing values were detected in the dataset."

    top_missing = missing_by_column.sort_values(
        ascending=False
    ).head(5)

    details = ", ".join(
        f"{column}: {count:,}"
        for column, count in top_missing.items()
    )

    return (
        f"The dataset contains {stats['missing_values']:,} missing values. "
        f"The columns with the most missing values are: {details}."
    )


def _quality_response(stats):
    score = stats["quality_score"]

    if score >= 95:
        status = "excellent"
    elif score >= 80:
        status = "good"
    elif score >= 60:
        status = "moderate"
    else:
        status = "poor"

    return (
        f"The dataset quality score is {score}%, which is considered "
        f"{status}. Missing values: {stats['missing_values']:,}. "
        f"Duplicate rows: {stats['duplicate_rows']:,}."
    )


def _duplicate_response(stats):
    duplicate_rows = stats["duplicate_rows"]

    if duplicate_rows == 0:
        return "No duplicate rows were detected in the dataset."

    return (
        f"The dataset contains {duplicate_rows:,} duplicate rows. "
        "Removing them is recommended before advanced analysis."
    )


def _recommended_charts(df):
    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    categorical_columns = df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    date_columns = []

    for column in df.columns:
        if "date" in str(column).lower():
            date_columns.append(column)

    recommendations = []

    if categorical_columns and numeric_columns:
        recommendations.append(
            f"Bar chart: {numeric_columns[0]} by {categorical_columns[0]}"
        )

    if categorical_columns:
        recommendations.append(
            f"Donut chart: {categorical_columns[0]} distribution"
        )

    if date_columns and numeric_columns:
        recommendations.append(
            f"Line chart: {numeric_columns[0]} trend over {date_columns[0]}"
        )

    if len(numeric_columns) >= 2:
        recommendations.append(
            f"Scatter chart: {numeric_columns[0]} vs {numeric_columns[1]}"
        )

    if not recommendations:
        return (
            "I could not find enough suitable columns to recommend "
            "standard business charts."
        )

    return "Recommended charts: " + "; ".join(recommendations) + "."


def _top_category_response(df, question):
    sales_column = _find_column(
        df,
        ["sales", "revenue", "amount", "total", "price"]
    )

    profit_column = _find_column(
        df,
        ["profit", "income", "earning", "margin"]
    )

    category_column = _find_column(
        df,
        ["category", "segment", "region", "state", "city", "department"]
    )

    value_column = None

    if "profit" in question:
        value_column = profit_column
    elif "sales" in question or "revenue" in question:
        value_column = sales_column
    else:
        value_column = sales_column or profit_column

    if not value_column or not category_column:
        return None

    working_df = df[[category_column, value_column]].copy()

    working_df[value_column] = pd.to_numeric(
        working_df[value_column],
        errors="coerce"
    )

    working_df = working_df.dropna()

    if working_df.empty:
        return None

    grouped = (
        working_df.groupby(category_column)[value_column]
        .sum()
        .sort_values(ascending=False)
    )

    top_name = grouped.index[0]
    top_value = grouped.iloc[0]

    return (
        f"The highest {value_column} is associated with "
        f"{category_column} '{top_name}', with a total of "
        f"{_format_number(top_value)}."
    )


def _column_statistics_response(df, question):
    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    for column in numeric_columns:
        if str(column).lower() in question:
            series = pd.to_numeric(df[column], errors="coerce").dropna()

            if series.empty:
                return f"No valid numeric values were found in '{column}'."

            return (
                f"For '{column}', the average is {_format_number(series.mean())}, "
                f"the minimum is {_format_number(series.min())}, "
                f"the maximum is {_format_number(series.max())}, "
                f"and the median is {_format_number(series.median())}."
            )

    return None


def answer_dataset_question(question, df, stats):
    normalized_question = _normalize_question(question)

    if not normalized_question:
        return {
            "success": False,
            "answer": "Please enter a question."
        }

    if any(
        phrase in normalized_question
        for phrase in [
            "summarize",
            "summary",
            "overview",
            "describe dataset"
        ]
    ):
        answer = _dataset_summary(df, stats)

    elif "how many rows" in normalized_question or "total rows" in normalized_question:
        answer = f"The dataset contains {stats['rows']:,} rows."

    elif (
        "how many columns" in normalized_question
        or "total columns" in normalized_question
    ):
        answer = f"The dataset contains {stats['columns']:,} columns."

    elif "quality" in normalized_question:
        answer = _quality_response(stats)

    elif "missing" in normalized_question or "null" in normalized_question:
        answer = _missing_values_response(df, stats)

    elif "duplicate" in normalized_question:
        answer = _duplicate_response(stats)

    elif "numeric columns" in normalized_question:
        answer = _numeric_columns_response(df)

    elif (
        "categorical columns" in normalized_question
        or "text columns" in normalized_question
    ):
        answer = _categorical_columns_response(df)

    elif (
        "recommend chart" in normalized_question
        or "best chart" in normalized_question
        or "suggest chart" in normalized_question
    ):
        answer = _recommended_charts(df)

    elif any(
        phrase in normalized_question
        for phrase in [
            "highest sales",
            "highest revenue",
            "highest profit",
            "top category",
            "top region",
            "best category",
            "best region"
        ]
    ):
        answer = _top_category_response(df, normalized_question)

        if answer is None:
            answer = (
                "I could not identify suitable category and value columns "
                "for that question."
            )

    else:
        answer = _column_statistics_response(df, normalized_question)

        if answer is None:
            answer = (
                "I could not understand that question yet. Try asking about "
                "rows, columns, missing values, duplicates, quality score, "
                "numeric columns, chart recommendations, highest sales, "
                "highest profit, or a numeric column's statistics."
            )

    return {
        "success": True,
        "answer": answer
    }