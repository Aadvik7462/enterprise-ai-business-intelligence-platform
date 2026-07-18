from __future__ import annotations

import os
from flask import Blueprint, current_app, redirect, render_template, session, url_for
from services.advanced_analytics_service import get_numeric_columns
from services.data_service import load_dataset

advanced_analytics_page_bp = Blueprint("advanced_analytics_page", __name__)


@advanced_analytics_page_bp.route("/advanced-analytics/<filename>")
def advanced_analytics_page(filename: str):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        return redirect(url_for("dashboard.dashboard"))
    df = load_dataset(path)
    return render_template(
        "advanced_analytics.html",
        filename=filename,
        numeric_columns=get_numeric_columns(df),
        user=session["user"],
        active_page="advanced_analytics",
    )
