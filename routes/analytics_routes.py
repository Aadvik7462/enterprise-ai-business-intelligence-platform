import os
from flask import Blueprint, render_template, redirect, url_for, session, flash, current_app

from services.data_service import load_dataset, get_dataset_stats
from services.chart_service import generate_auto_charts


analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics/<filename>")
def analytics_dashboard(filename):
    if "user" not in session:
        return redirect(url_for("auth.login"))

    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    if not os.path.exists(filepath):
        flash("File not found", "error")
        return redirect(url_for("dashboard.dashboard"))

    df = load_dataset(filepath)

    stats = get_dataset_stats(df, filepath)
    charts = generate_auto_charts(df)

    return render_template(
        "analytics.html",
        filename=filename,
        stats=stats,
        charts=charts,
        active_page="analytics"
    )