import os
from flask import Blueprint, render_template, redirect, url_for, session, current_app

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    upload_folder = current_app.config["UPLOAD_FOLDER"]

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    uploaded_files = os.listdir(upload_folder)

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        user=session["user"],
        uploaded_count=len(uploaded_files)
    )