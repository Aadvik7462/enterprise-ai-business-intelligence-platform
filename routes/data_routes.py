import os

from flask import (
    Blueprint,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    render_template
)

from werkzeug.utils import secure_filename

from services.data_service import (
    load_dataset,
    get_dataset_stats,
    get_column_summary,
    get_numeric_summary,
    get_chart_data
)

from utils.clean_data import clean_dataset
from services.insight_service import generate_insights


data_bp = Blueprint("data", __name__)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@data_bp.route("/upload", methods=["POST"])
def upload_file():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    if "dataset" not in request.files:
        flash("No file selected", "error")
        return redirect(url_for("dashboard.dashboard"))

    file = request.files["dataset"]

    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("dashboard.dashboard"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        filepath = os.path.join(
            current_app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(filepath)

        session["uploaded_file"] = filename

        flash("Dataset uploaded successfully!", "success")

        return redirect(
            url_for("data.preview_dataset", filename=filename)
        )

    flash("Invalid file type. Please upload CSV or Excel file.", "error")
    return redirect(url_for("dashboard.dashboard"))


@data_bp.route("/preview/<filename>")
def preview_dataset(filename):
    if "user" not in session:
        return redirect(url_for("auth.login"))

    filepath = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

    if not os.path.exists(filepath):
        flash("File not found", "error")
        return redirect(url_for("dashboard.dashboard"))

    try:
        df = load_dataset(filepath)

        preview_data = df.head(10).to_html(
            classes="data-table",
            index=False,
            border=0
        )

        stats = get_dataset_stats(df, filepath)
        column_summary = get_column_summary(df)
        numeric_summary = get_numeric_summary(df)
        chart_data = get_chart_data(df)
        insights = generate_insights(df, stats)

        return render_template(
            "preview.html",
            filename=filename,
            preview_data=preview_data,
            stats=stats,
            column_summary=column_summary,
            numeric_summary=numeric_summary,
            chart_data=chart_data,
            insights=insights,
            cleaning_report=session.get("cleaning_report"),
            active_page="upload"
        )

    except Exception as e:
        flash(f"Error reading file: {str(e)}", "error")
        return redirect(url_for("dashboard.dashboard"))


@data_bp.route("/clean/<filename>")
def clean_file(filename):
    if "user" not in session:
        return redirect(url_for("auth.login"))

    filepath = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

    if not os.path.exists(filepath):
        flash("File not found", "error")
        return redirect(url_for("dashboard.dashboard"))

    try:
        df = load_dataset(filepath)

        cleaned_df, cleaning_report = clean_dataset(df)

        cleaned_filename = "cleaned_" + filename

        cleaned_filepath = os.path.join(
            current_app.config["UPLOAD_FOLDER"],
            cleaned_filename
        )

        if cleaned_filename.endswith(".csv"):
            cleaned_df.to_csv(cleaned_filepath, index=False)
        else:
            cleaned_df.to_excel(cleaned_filepath, index=False)

        session["cleaning_report"] = cleaning_report
        session["cleaned_file"] = cleaned_filename

        flash("Dataset cleaned successfully!", "success")

        return redirect(
            url_for("data.preview_dataset", filename=cleaned_filename)
        )

    except Exception as e:
        flash(f"Error cleaning file: {str(e)}", "error")
        return redirect(
            url_for("data.preview_dataset", filename=filename)
        )