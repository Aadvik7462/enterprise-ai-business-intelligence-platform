def generate_insights(df, stats):
    insights = []

    rows = stats["rows"]
    columns = stats["columns"]
    missing = stats["missing_values"]
    duplicates = stats["duplicate_rows"]
    quality = stats["quality_score"]

    insights.append(f"The dataset contains {rows} rows and {columns} columns.")

    if quality >= 95:
        insights.append("Dataset quality is excellent and suitable for analysis.")
    elif quality >= 80:
        insights.append("Dataset quality is good, but some cleaning may improve accuracy.")
    else:
        insights.append("Dataset quality is low. Cleaning is recommended before analysis.")

    if missing > 0:
        insights.append(f"There are {missing} missing values. Missing data should be handled before modeling.")
    else:
        insights.append("No missing values were found in the dataset.")

    if duplicates > 0:
        insights.append(f"{duplicates} duplicate rows were detected and should be removed.")
    else:
        insights.append("No duplicate rows were detected.")

    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns

    for col in numeric_cols[:3]:
        avg = round(df[col].mean(), 2)
        max_val = round(df[col].max(), 2)
        min_val = round(df[col].min(), 2)

        insights.append(
            f"The column '{col}' has an average value of {avg}, ranging from {min_val} to {max_val}."
        )

    categorical_cols = df.select_dtypes(include=["object"]).columns

    for col in categorical_cols[:3]:
        top_value = df[col].mode()[0]
        count = df[col].value_counts().iloc[0]

        insights.append(
            f"In '{col}', the most frequent value is '{top_value}' with {count} records."
        )

    return insights