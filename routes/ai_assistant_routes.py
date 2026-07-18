
from __future__ import annotations

import os

from flask import Blueprint, current_app, jsonify, request, session

from services.ai_data_assistant_service import (
    answer_dataset_question,
)
from services.data_service import load_dataset


ai_bp = Blueprint(
    "ai",
    __name__,
    url_prefix="/ai",
)


@ai_bp.get("/health")
def ai_health():
    return jsonify({
        "success": True,
        "service": "AI Dataset Assistant",
        "version": "2.1",
    })


@ai_bp.post("/chat")
def ai_chat():
    payload = request.get_json(silent=True) or {}

    question = str(
        payload.get("question", "")
    ).strip()

    filename = (
        str(payload.get("filename", "")).strip()
        or session.get("uploaded_file")
    )

    if not question:
        return jsonify({
            "success": False,
            "answer": "Please enter a question.",
            "response_type": "error",
            "data": {},
            "suggestions": [],
        }), 400

    if not filename:
        return jsonify({
            "success": False,
            "answer": (
                "No uploaded dataset is active. "
                "Upload a dataset first."
            ),
            "response_type": "error",
            "data": {},
            "suggestions": [],
        }), 400

    safe_filename = os.path.basename(filename)

    try:
        dataframe = load_dataset(safe_filename)

        return jsonify(
            answer_dataset_question(
                dataframe,
                question,
            )
        )

    except FileNotFoundError:
        return jsonify({
            "success": False,
            "answer": (
                f"Dataset '{safe_filename}' could not be found."
            ),
            "response_type": "error",
            "data": {},
            "suggestions": [],
        }), 404

    except Exception as error:
        current_app.logger.exception(
            "AI assistant request failed"
        )

        return jsonify({
            "success": False,
            "answer": (
                "The AI assistant could not analyze the dataset."
            ),
            "response_type": "error",
            "details": (
                str(error)
                if current_app.debug
                else None
            ),
            "data": {},
            "suggestions": [],
        }), 500
