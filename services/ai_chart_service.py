import json
import re

import pandas as pd
import plotly
import plotly.express as px


def normalize_text(value):
    return re.sub(
        r"\s+",
        " ",
        str(value).lower().replace("_", " ").strip()
    )


def find_matching_column(df, question, column_type=None):
    question = normalize_text(question)

    if column_type == "numeric":
        candidate_columns = df.select_dtypes(
            include="number"
        ).columns.tolist()

    elif column_type == "categorical":
        candidate_columns = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()

    else:
        candidate_columns = df.columns.tolist()

    # Exact or partial column-name match
    for column in candidate_columns:
        normalized_column = normalize_text(column)

        if normalized_column in question:
            return column

    # Business keyword matching
    aliases = {
        "sales": ["sales", "revenue", "amount", "turnover"],
        "profit": ["profit", "income", "earning", "margin"],
        "quantity": ["quantity", "qty", "units", "volume"],
        "discount": ["discount"],
        "category": ["category", "department", "product type"],
        "subcategory": ["sub category", "subcategory"],
        "region": ["region", "zone", "territory"],
        "segment": ["segment", "customer type"],
        "state": ["state"],
        "city": ["city"],
        "country": ["country"],
        "customer": ["customer name", "customer"],
        "product": ["product name", "product"],
        "date": ["order date", "date", "month", "year"]
    }

    for alias_name, keywords in aliases.items():
        if any(keyword in question for keyword in keywords):
            for column in candidate_columns:
                normalized_column = normalize_text(column)

                if alias_name == "subcategory":
                    if (
                        "sub category" in normalized_column
                        or "subcategory" in normalized_column
                    ):
                        return column

                elif any(
                    keyword in normalized_column
                    for keyword in keywords
                ):
                    return column

    return None


def detect_date_column(df, question):
    question = normalize_text(question)

    preferred_column = find_matching_column(
        df,
        question,
        column_type=None
    )

    if preferred_column is not None:
        preferred_name = normalize_text(preferred_column)

        if any(
            token in preferred_name
            for token in ["date", "month", "year"]
        ):
            return preferred_column

    for column in df.columns:
        column_name = normalize_text(column)

        if any(
            token in column_name
            for token in ["date", "month", "year"]
        ):
            converted = pd.to_datetime(
                df[column],
                errors="coerce"
            )

            if converted.notna().sum() > 0:
                return column

    return None


def determine_chart_type(question):
    question = normalize_text(question)

    if any(
        keyword in question
        for keyword in [
            "trend",
            "monthly",
            "over time",
            "line chart",
            "time series"
        ]
    ):
        return "line"

    if any(
        keyword in question
        for keyword in [
            "pie",
            "donut",
            "share",
            "distribution",
            "percentage"
        ]
    ):
        return "pie"

    if any(
        keyword in question
        for keyword in [
            "scatter",
            "relationship",
            "correlation",
            " vs ",
            "versus"
        ]
    ):
        return "scatter"

    return "bar"


def apply_plotly_style(fig):
    fig.update_layout(
        template="plotly_white",
        height=430,
        margin=dict(
            l=45,
            r=30,
            t=75,
            b=60
        ),
        title_font=dict(
            size=20
        ),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        legend_title_text=""
    )

    return fig


def create_grouped_chart(
    df,
    category_column,
    value_column,
    chart_type
):
    working_df = df[
        [category_column, value_column]
    ].copy()

    working_df[value_column] = pd.to_numeric(
        working_df[value_column],
        errors="coerce"
    )

    working_df = working_df.dropna()

    if working_df.empty:
        return None

    grouped = (
        working_df
        .groupby(category_column)[value_column]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .reset_index()
    )

    title = f"{value_column} by {category_column}"

    if chart_type == "pie":
        fig = px.pie(
            grouped,
            names=category_column,
            values=value_column,
            hole=0.45,
            title=title
        )

    else:
        fig = px.bar(
            grouped,
            x=category_column,
            y=value_column,
            title=title,
            text_auto=".3s"
        )

        fig.update_xaxes(
            tickangle=-35
        )

    top_row = grouped.iloc[0]

    insight = (
        f"The highest {value_column} is for "
        f"{category_column} '{top_row[category_column]}', "
        f"with a total of {top_row[value_column]:,.2f}."
    )

    return fig, insight


def create_time_chart(
    df,
    date_column,
    value_column
):
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

    working_df = working_df.dropna()

    if working_df.empty:
        return None

    working_df["Period"] = (
        working_df[date_column]
        .dt.to_period("M")
        .astype(str)
    )

    grouped = (
        working_df
        .groupby("Period")[value_column]
        .sum()
        .reset_index()
        .sort_values("Period")
    )

    fig = px.line(
        grouped,
        x="Period",
        y=value_column,
        markers=True,
        title=f"{value_column} Trend Over Time"
    )

    if len(grouped) >= 2:
        first_value = grouped[value_column].iloc[0]
        last_value = grouped[value_column].iloc[-1]

        if first_value != 0:
            change = (
                (last_value - first_value)
                / abs(first_value)
            ) * 100

            direction = (
                "increased"
                if change >= 0
                else "decreased"
            )

            insight = (
                f"{value_column} {direction} by "
                f"{abs(change):.2f}% from the first period "
                f"to the latest period."
            )
        else:
            insight = (
                f"The chart shows the monthly trend "
                f"for {value_column}."
            )
    else:
        insight = (
            f"The chart contains one available period "
            f"for {value_column}."
        )

    return fig, insight


def create_scatter_chart(
    df,
    x_column,
    y_column
):
    working_df = df[
        [x_column, y_column]
    ].copy()

    working_df[x_column] = pd.to_numeric(
        working_df[x_column],
        errors="coerce"
    )

    working_df[y_column] = pd.to_numeric(
        working_df[y_column],
        errors="coerce"
    )

    working_df = working_df.dropna().head(500)

    if working_df.empty:
        return None

    fig = px.scatter(
        working_df,
        x=x_column,
        y=y_column,
        title=f"{x_column} vs {y_column}",
        trendline=None
    )

    correlation = working_df[
        [x_column, y_column]
    ].corr().iloc[0, 1]

    if pd.isna(correlation):
        insight = (
            f"The relationship between {x_column} "
            f"and {y_column} could not be calculated."
        )
    else:
        strength = abs(correlation)

        if strength >= 0.7:
            label = "strong"
        elif strength >= 0.4:
            label = "moderate"
        else:
            label = "weak"

        direction = (
            "positive"
            if correlation >= 0
            else "negative"
        )

        insight = (
            f"{x_column} and {y_column} have a "
            f"{label} {direction} correlation "
            f"of {correlation:.2f}."
        )

    return fig, insight


def generate_chart_from_question(question, df):
    normalized_question = normalize_text(question)
    chart_type = determine_chart_type(normalized_question)

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    categorical_columns = df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    requested_numeric = find_matching_column(
        df,
        normalized_question,
        column_type="numeric"
    )

    requested_category = find_matching_column(
        df,
        normalized_question,
        column_type="categorical"
    )

    date_column = detect_date_column(
        df,
        normalized_question
    )

    if chart_type == "scatter":
        mentioned_numeric = []

        for column in numeric_columns:
            if normalize_text(column) in normalized_question:
                mentioned_numeric.append(column)

        if len(mentioned_numeric) >= 2:
            x_column = mentioned_numeric[0]
            y_column = mentioned_numeric[1]

        elif len(numeric_columns) >= 2:
            x_column = requested_numeric or numeric_columns[0]

            y_column = next(
                (
                    column
                    for column in numeric_columns
                    if column != x_column
                ),
                None
            )

        else:
            return {
                "success": False,
                "message": (
                    "At least two numeric columns are required "
                    "to generate a scatter chart."
                )
            }

        chart_result = create_scatter_chart(
            df,
            x_column,
            y_column
        )

    elif chart_type == "line":
        value_column = (
            requested_numeric
            or (
                numeric_columns[0]
                if numeric_columns
                else None
            )
        )

        if date_column is None or value_column is None:
            return {
                "success": False,
                "message": (
                    "A date column and a numeric column are "
                    "required to generate a trend chart."
                )
            }

        chart_result = create_time_chart(
            df,
            date_column,
            value_column
        )

    else:
        value_column = (
            requested_numeric
            or (
                numeric_columns[0]
                if numeric_columns
                else None
            )
        )

        category_column = (
            requested_category
            or (
                categorical_columns[0]
                if categorical_columns
                else None
            )
        )

        if (
            value_column is None
            or category_column is None
        ):
            return {
                "success": False,
                "message": (
                    "A categorical column and a numeric column "
                    "are required to generate this chart."
                )
            }

        chart_result = create_grouped_chart(
            df,
            category_column,
            value_column,
            chart_type
        )

    if chart_result is None:
        return {
            "success": False,
            "message": (
                "The selected columns did not contain enough "
                "valid data to generate a chart."
            )
        }

    fig, insight = chart_result
    fig = apply_plotly_style(fig)

    return {
        "success": True,
        "message": insight,
        "chart": json.loads(
            json.dumps(
                fig,
                cls=plotly.utils.PlotlyJSONEncoder
            )
        )
    }