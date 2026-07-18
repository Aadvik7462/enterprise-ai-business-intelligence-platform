
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)

from services.data_service import load_dataset
from services.enterprise_ai_service import (
    copilot_answer,
    executive_report,
    generate_dashboard_charts,
    generate_insights,
    generate_kpis,
    generate_recommendations,
)
from services.forecasting_studio_service import (
    create_forecast,
    detect_date_columns,
    numeric_columns,
)
from services.realtime_analytics_service import (
    realtime_snapshot,
)
from services.enterprise_workspace_service import (
    add_dashboard,
    load_workspace,
)


phase4_bp = Blueprint(
    "phase4",
    __name__,
    url_prefix="/enterprise-ai",
)


def active_filename(
    explicit_filename: str | None = None,
) -> str:
    filename = (
        explicit_filename
        or session.get(
            "uploaded_file"
        )
    )

    if not filename:
        raise ValueError(
            "No active dataset was found."
        )

    return os.path.basename(
        filename
    )


@phase4_bp.get("/hub/<filename>")
def enterprise_ai_hub(filename):
    safe_filename = active_filename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    session["uploaded_file"] = safe_filename

    return render_template(
        "enterprise_ai_hub.html",
        filename=safe_filename,
        row_count=len(
            dataframe
        ),
        column_count=dataframe.shape[1],
    )


@phase4_bp.get("/dashboard-generator/<filename>")
def dashboard_generator_page(filename):
    safe_filename = active_filename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    return render_template(
        "ai_dashboard_generator.html",
        filename=safe_filename,
        kpis=generate_kpis(
            dataframe
        ),
        charts=generate_dashboard_charts(
            dataframe
        ),
        insights=generate_insights(
            dataframe
        ),
    )


@phase4_bp.get("/report-writer/<filename>")
def report_writer_page(filename):
    safe_filename = active_filename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    return render_template(
        "ai_report_writer.html",
        filename=safe_filename,
        report=executive_report(
            dataframe
        ),
    )


@phase4_bp.post("/copilot/chat")
def enterprise_copilot_chat():
    payload = request.get_json(
        silent=True
    ) or {}

    safe_filename = active_filename(
        payload.get(
            "filename"
        )
    )

    dataframe = load_dataset(
        safe_filename
    )

    return jsonify(
        {
            "success": True,
            **copilot_answer(
                dataframe,
                str(
                    payload.get(
                        "question",
                        "",
                    )
                ),
            ),
        }
    )


@phase4_bp.get("/forecasting/<filename>")
def forecasting_page(filename):
    safe_filename = active_filename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    return render_template(
        "forecasting_studio_v4.html",
        filename=safe_filename,
        date_columns=detect_date_columns(
            dataframe
        ),
        numeric_columns=numeric_columns(
            dataframe
        ),
    )


@phase4_bp.post("/forecasting/run")
def forecasting_run():
    payload = request.get_json(
        silent=True
    ) or {}

    safe_filename = active_filename(
        payload.get(
            "filename"
        )
    )

    try:
        dataframe = load_dataset(
            safe_filename
        )

        result = create_forecast(
            dataframe,
            date_column=str(
                payload.get(
                    "date_column",
                    "",
                )
            ),
            value_column=str(
                payload.get(
                    "value_column",
                    "",
                )
            ),
            periods=int(
                payload.get(
                    "periods",
                    12,
                )
            ),
        )

        return jsonify(
            result
        )

    except Exception as error:
        current_app.logger.exception(
            "Forecasting failed"
        )

        return jsonify(
            {
                "success": False,
                "message": str(
                    error
                ),
            }
        ), 400


@phase4_bp.get("/realtime/<filename>")
def realtime_page(filename):
    safe_filename = active_filename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    return render_template(
        "realtime_analytics.html",
        filename=safe_filename,
        snapshot=realtime_snapshot(
            dataframe
        ),
    )


@phase4_bp.get("/realtime/snapshot/<filename>")
def realtime_snapshot_api(filename):
    safe_filename = active_filename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    return jsonify(
        {
            "success": True,
            **realtime_snapshot(
                dataframe
            ),
        }
    )


@phase4_bp.get("/workspace/<filename>")
def workspace_page(filename):
    safe_filename = active_filename(
        filename
    )

    return render_template(
        "enterprise_workspace.html",
        filename=safe_filename,
        workspace=load_workspace(),
    )


@phase4_bp.post("/workspace/publish")
def workspace_publish():
    payload = request.get_json(
        silent=True
    ) or {}

    safe_filename = active_filename(
        payload.get(
            "filename"
        )
    )

    dashboard = add_dashboard(
        name=str(
            payload.get(
                "name",
                "AI Dashboard",
            )
        ).strip()
        or "AI Dashboard",
        filename=safe_filename,
    )

    return jsonify(
        {
            "success": True,
            "dashboard": dashboard,
        }
    )


@phase4_bp.get("/insight-engine/<filename>")
def insight_engine_page(filename):
    safe_filename = active_filename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    return render_template(
        "ai_insight_engine.html",
        filename=safe_filename,
        insights=generate_insights(
            dataframe
        ),
        recommendations=generate_recommendations(
            dataframe
        ),
        kpis=generate_kpis(
            dataframe
        ),
    )
