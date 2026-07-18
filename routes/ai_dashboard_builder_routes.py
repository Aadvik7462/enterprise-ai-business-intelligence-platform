
from __future__ import annotations

import os

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    session,
)

from services.ai_dashboard_builder_service import (
    build_ai_dashboard,
)
from services.data_service import load_dataset


ai_dashboard_builder_bp = Blueprint(
    "ai_dashboard_builder",
    __name__,
    url_prefix="/ai-dashboard-builder",
)


@ai_dashboard_builder_bp.get("/<filename>")
def ai_dashboard_builder_page(filename):
    safe_filename = os.path.basename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    dashboard = build_ai_dashboard(
        dataframe
    )

    session["uploaded_file"] = safe_filename

    return render_template(
        "ai_dashboard_builder.html",
        filename=safe_filename,
        dashboard=dashboard,
    )


@ai_dashboard_builder_bp.get("/api/<filename>")
def ai_dashboard_builder_api(filename):
    safe_filename = os.path.basename(
        filename
    )

    try:
        dataframe = load_dataset(
            safe_filename
        )

        return jsonify({
            "success": True,
            "dashboard": build_ai_dashboard(
                dataframe
            ),
        })

    except Exception as error:
        current_app.logger.exception(
            "AI dashboard generation failed"
        )

        return jsonify({
            "success": False,
            "message": (
                "The AI dashboard could not be generated."
            ),
            "details": (
                str(error)
                if current_app.debug
                else None
            ),
        }), 500
