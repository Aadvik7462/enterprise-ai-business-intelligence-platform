from __future__ import annotations

import os
from flask import Blueprint, current_app, make_response, redirect, render_template, session, url_for
from services.data_service import load_dataset
from services.reporting_center_service import build_reporting_summary, render_report_html

reporting_center_bp = Blueprint("reporting_center", __name__)


@reporting_center_bp.route("/reporting-center/<filename>")
def reporting_center_page(filename: str):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        return redirect(url_for("dashboard.dashboard"))
    report = build_reporting_summary(load_dataset(path), filename)
    return render_template("reporting_center.html", filename=filename, report=report, user=session["user"], active_page="reports")


@reporting_center_bp.route("/reporting-center/<filename>/download")
def download_report(filename: str):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        return redirect(url_for("dashboard.dashboard"))
    report = build_reporting_summary(load_dataset(path), filename)
    response = make_response(render_report_html(report))
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}_enterprise_report.html"'
    return response
