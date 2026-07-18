import pandas as pd
from sklearn.linear_model import LinearRegression


def prepare_forecast_columns(df):
    date_columns = []
    numeric_columns = []

    for col in df.columns:
        try:
            pd.to_datetime(df[col])
            date_columns.append(col)
        except Exception:
            pass

    numeric_columns = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

    return date_columns, numeric_columns


def generate_forecast(df, date_col, value_col, periods=7):
    data = df[[date_col, value_col]].copy()

    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    data[value_col] = pd.to_numeric(data[value_col], errors="coerce")

    data = data.dropna()
    data = data.sort_values(date_col)

    daily_data = data.groupby(date_col)[value_col].sum().reset_index()

    daily_data["day_number"] = range(len(daily_data))

    X = daily_data[["day_number"]]
    y = daily_data[value_col]

    model = LinearRegression()
    model.fit(X, y)

    future_days = []
    future_values = []

    last_day_number = daily_data["day_number"].max()
    last_date = daily_data[date_col].max()

    for i in range(1, periods + 1):
        future_day = last_day_number + i
        future_date = last_date + pd.Timedelta(days=i)
        predicted_value = model.predict([[future_day]])[0]

        future_days.append(future_date.strftime("%Y-%m-%d"))
        future_values.append(round(predicted_value, 2))

    historical_dates = daily_data[date_col].dt.strftime("%Y-%m-%d").tolist()
    historical_values = daily_data[value_col].round(2).tolist()

    return {
        "historical_dates": historical_dates,
        "historical_values": historical_values,
        "future_dates": future_days,
        "future_values": future_values
    }