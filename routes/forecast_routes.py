import os

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    request,
    jsonify
)

from services.data_service import load_dataset
from services.ai_forecast_service import (
    generate_ai_forecast,
    get_forecast_options
)


forecast_bp = Blueprint("forecasting", __name__)


@forecast_bp.route("/forecast/<filename>")
def forecast_page(filename):
    """
    Open the AI Forecast Studio for the selected dataset.
    """

    if "user" not in session:
        return redirect(url_for("auth.login"))

    filepath = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

    if not os.path.exists(filepath):
        flash("Dataset file not found.", "error")
        return redirect(url_for("dashboard.dashboard"))

    try:
        df = load_dataset(filepath)

        forecast_options = get_forecast_options(df)

        initial_forecast = None

        default_date_column = forecast_options.get(
            "default_date_column"
        )

        default_value_column = forecast_options.get(
            "default_value_column"
        )

        if default_date_column and default_value_column:
            initial_forecast = generate_ai_forecast(
                df=df,
                date_column=default_date_column,
                value_column=default_value_column,
                periods=6
            )

        return render_template(
            "forecast_dashboard.html",
            filename=filename,
            forecast_options=forecast_options,
            initial_forecast=initial_forecast,
            active_page="forecast"
        )

    except Exception as error:
        flash(
            f"Unable to open Forecast Studio: {str(error)}",
            "error"
        )

        return redirect(
            url_for(
                "data.preview_dataset",
                filename=filename
            )
        )


@forecast_bp.route(
    "/api/forecast/<filename>",
    methods=["POST"]
)
def generate_forecast_api(filename):
    """
    Generate forecast data without reloading the page.
    """

    if "user" not in session:
        return jsonify({
            "success": False,
            "message": "Your session has expired. Please log in again."
        }), 401

    filepath = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

    if not os.path.exists(filepath):
        return jsonify({
            "success": False,
            "message": "The selected dataset could not be found."
        }), 404

    request_data = request.get_json(
        silent=True
    ) or {}

    date_column = request_data.get(
        "date_column"
    )

    value_column = request_data.get(
        "value_column"
    )

    periods = request_data.get(
        "periods",
        6
    )

    try:
        df = load_dataset(filepath)

        result = generate_ai_forecast(
            df=df,
            date_column=date_column,
            value_column=value_column,
            periods=periods
        )

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result)

    except Exception as error:
        return jsonify({
            "success": False,
            "message": (
                "Forecast generation failed: "
                f"{str(error)}"
            )
        }), 500