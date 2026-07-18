
from __future__ import annotations

import os

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)

from services.ai_sql_assistant_service import (
    ask_sql_assistant,
    run_manual_sql,
)
from services.data_service import load_dataset


ai_sql_bp = Blueprint(
    "ai_sql",
    __name__,
    url_prefix="/ai-sql",
)


@ai_sql_bp.get("/<filename>")
def ai_sql_page(filename):
    safe_filename = os.path.basename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    session["uploaded_file"] = safe_filename

    schema = [
        {
            "name": str(column),
            "type": str(dataframe[column].dtype),
        }
        for column in dataframe.columns
    ]

    return render_template(
        "ai_sql_assistant.html",
        filename=safe_filename,
        schema=schema,
        row_count=len(dataframe),
    )


@ai_sql_bp.post("/ask")
def ai_sql_ask():
    payload = request.get_json(
        silent=True
    ) or {}

    question = str(
        payload.get(
            "question",
            "",
        )
    ).strip()

    filename = (
        str(
            payload.get(
                "filename",
                "",
            )
        ).strip()
        or session.get(
            "uploaded_file"
        )
    )

    if not question:
        return jsonify({
            "success": False,
            "answer": "Please enter a question.",
        }), 400

    if not filename:
        return jsonify({
            "success": False,
            "answer": (
                "No uploaded dataset is active."
            ),
        }), 400

    try:
        dataframe = load_dataset(
            os.path.basename(
                filename
            )
        )

        result = ask_sql_assistant(
            dataframe,
            question,
        )

        return jsonify(
            result
        ), (
            200
            if result.get("success")
            else 400
        )

    except Exception as error:
        current_app.logger.exception(
            "AI SQL question failed"
        )

        return jsonify({
            "success": False,
            "answer": (
                str(error)
                if current_app.debug
                else "The AI SQL assistant failed."
            ),
        }), 500


@ai_sql_bp.post("/execute")
def ai_sql_execute():
    payload = request.get_json(
        silent=True
    ) or {}

    sql = str(
        payload.get(
            "sql",
            "",
        )
    ).strip()

    filename = (
        str(
            payload.get(
                "filename",
                "",
            )
        ).strip()
        or session.get(
            "uploaded_file"
        )
    )

    if not sql:
        return jsonify({
            "success": False,
            "answer": "SQL query is empty.",
        }), 400

    if not filename:
        return jsonify({
            "success": False,
            "answer": (
                "No uploaded dataset is active."
            ),
        }), 400

    try:
        dataframe = load_dataset(
            os.path.basename(
                filename
            )
        )

        result = run_manual_sql(
            dataframe,
            sql,
        )

        return jsonify(
            result
        ), (
            200
            if result.get("success")
            else 400
        )

    except Exception as error:
        current_app.logger.exception(
            "Manual SQL execution failed"
        )

        return jsonify({
            "success": False,
            "answer": (
                str(error)
                if current_app.debug
                else "The SQL query failed."
            ),
        }), 500
