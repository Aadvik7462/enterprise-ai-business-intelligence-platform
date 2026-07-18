import json
import pandas as pd
import plotly
import plotly.express as px


def find_column(df, keywords):
    for col in df.columns:
        col_lower = col.lower().replace("_", " ").strip()

        for keyword in keywords:
            if keyword in col_lower:
                return col

    return None


def get_numeric_columns(df):
    return df.select_dtypes(include=["int64", "float64"]).columns.tolist()


def get_categorical_columns(df):
    return df.select_dtypes(include=["object", "category"]).columns.tolist()


def get_date_columns(df):
    date_columns = []

    for col in df.columns:
        try:
            converted = pd.to_datetime(df[col], errors="coerce")

            if converted.notna().sum() > len(df) * 0.5:
                date_columns.append(col)

        except Exception:
            pass

    return date_columns


def style_plotly(fig):
    fig.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=40, r=40, t=70, b=50),
        title_font=dict(size=20),
        paper_bgcolor="white",
        plot_bgcolor="white"
    )

    return fig


def generate_auto_charts(df):
    charts = []

    numeric_cols = get_numeric_columns(df)
    categorical_cols = get_categorical_columns(df)
    date_cols = get_date_columns(df)

    sales_col = find_column(df, ["sales", "revenue", "amount", "price", "total"])
    profit_col = find_column(df, ["profit", "margin", "income", "earning"])
    category_col = find_column(df, ["category", "segment", "department", "type"])
    region_col = find_column(df, ["region", "state", "city", "country", "location"])
    date_col = find_column(df, ["date", "month", "year"]) or (
        date_cols[0] if date_cols else None
    )

    main_value_col = sales_col or profit_col or (
        numeric_cols[0] if numeric_cols else None
    )

    main_category_col = category_col or region_col or (
        categorical_cols[0] if categorical_cols else None
    )

    if main_category_col and main_value_col:
        grouped = (
            df.groupby(main_category_col)[main_value_col]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        charts.append({
            "id": "main_bar_chart",
            "title": f"{main_value_col} by {main_category_col}",
            "type": "bar",
            "labels": grouped.index.astype(str).tolist(),
            "values": grouped.values.round(2).tolist()
        })

    if main_category_col:
        counts = df[main_category_col].value_counts().head(8)

        charts.append({
            "id": "category_distribution",
            "title": f"{main_category_col} Distribution",
            "type": "doughnut",
            "labels": counts.index.astype(str).tolist(),
            "values": counts.values.tolist()
        })

    if date_col and main_value_col:
        temp = df[[date_col, main_value_col]].copy()
        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
        temp[main_value_col] = pd.to_numeric(temp[main_value_col], errors="coerce")
        temp = temp.dropna()

        if not temp.empty:
            temp["Period"] = temp[date_col].dt.to_period("M").astype(str)

            grouped = (
                temp.groupby("Period")[main_value_col]
                .sum()
                .reset_index()
            )

            charts.append({
                "id": "time_trend",
                "title": f"{main_value_col} Trend Over Time",
                "type": "line",
                "labels": grouped["Period"].astype(str).tolist(),
                "values": grouped[main_value_col].round(2).tolist()
            })

    if len(numeric_cols) >= 2:
        x_col = sales_col or numeric_cols[0]
        y_col = profit_col or numeric_cols[1]

        sample = df[[x_col, y_col]].dropna().head(150)

        charts.append({
            "id": "numeric_relationship",
            "title": f"{x_col} vs {y_col}",
            "type": "scatter",
            "x_values": sample[x_col].round(2).tolist(),
            "y_values": sample[y_col].round(2).tolist()
        })

    return charts


def generate_plotly_charts(df):
    charts = []

    numeric_cols = get_numeric_columns(df)
    categorical_cols = get_categorical_columns(df)
    date_cols = get_date_columns(df)

    sales_col = find_column(df, ["sales", "revenue", "amount", "price", "total"])
    profit_col = find_column(df, ["profit", "margin", "income", "earning"])
    category_col = find_column(df, ["category", "segment", "department", "type"])
    region_col = find_column(df, ["region", "state", "city", "country", "location"])
    date_col = find_column(df, ["date", "month", "year"]) or (
        date_cols[0] if date_cols else None
    )

    main_value_col = sales_col or profit_col or (
        numeric_cols[0] if numeric_cols else None
    )

    main_category_col = category_col or region_col or (
        categorical_cols[0] if categorical_cols else None
    )

    if main_category_col and main_value_col:
        grouped = (
            df.groupby(main_category_col)[main_value_col]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )

        fig = px.bar(
            grouped,
            x=main_category_col,
            y=main_value_col,
            title=f"{main_value_col} by {main_category_col}",
            text_auto=".2s"
        )

        charts.append(
            json.dumps(style_plotly(fig), cls=plotly.utils.PlotlyJSONEncoder)
        )

    if main_category_col:
        counts = df[main_category_col].value_counts().head(8).reset_index()
        counts.columns = [main_category_col, "Count"]

        fig = px.pie(
            counts,
            names=main_category_col,
            values="Count",
            hole=0.45,
            title=f"{main_category_col} Distribution"
        )

        charts.append(
            json.dumps(style_plotly(fig), cls=plotly.utils.PlotlyJSONEncoder)
        )

    if date_col and main_value_col:
        temp = df[[date_col, main_value_col]].copy()
        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
        temp[main_value_col] = pd.to_numeric(temp[main_value_col], errors="coerce")
        temp = temp.dropna()

        if not temp.empty:
            temp["Period"] = temp[date_col].dt.to_period("M").astype(str)

            grouped = (
                temp.groupby("Period")[main_value_col]
                .sum()
                .reset_index()
            )

            fig = px.line(
                grouped,
                x="Period",
                y=main_value_col,
                markers=True,
                title=f"{main_value_col} Trend Over Time"
            )

            charts.append(
                json.dumps(style_plotly(fig), cls=plotly.utils.PlotlyJSONEncoder)
            )

    if len(numeric_cols) >= 2:
        x_col = sales_col or numeric_cols[0]
        y_col = profit_col or numeric_cols[1]

        sample = df[[x_col, y_col]].dropna().head(250)

        fig = px.scatter(
            sample,
            x=x_col,
            y=y_col,
            title=f"{x_col} vs {y_col}"
        )

        charts.append(
            json.dumps(style_plotly(fig), cls=plotly.utils.PlotlyJSONEncoder)
        )

    return charts