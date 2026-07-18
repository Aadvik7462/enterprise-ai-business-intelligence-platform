from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from services.copilot_history_service import add_message, create_conversation, delete_conversation, list_conversations, list_messages

copilot_history_bp = Blueprint("copilot_history", __name__)


def _user() -> str | None:
    user = session.get("user")
    if user is None:
        return None
    if isinstance(user, dict):
        return str(user.get("id") or user.get("email") or user.get("username") or user.get("name") or "").strip() or None
    return str(user).strip() or None


@copilot_history_bp.route("/api/copilot-history/<filename>", methods=["GET", "POST"])
def conversations(filename: str):
    owner = _user()
    if owner is None:
        return jsonify({"success": False, "message": "Please log in again."}), 401
    if request.method == "GET":
        return jsonify({"success": True, "conversations": list_conversations(owner, filename)})
    payload = request.get_json(silent=True) or {}
    item = create_conversation(owner, filename, str(payload.get("title", "New Analysis")).strip() or "New Analysis")
    return jsonify({"success": True, "conversation": item}), 201


@copilot_history_bp.route("/api/copilot-history/conversations/<int:conversation_id>/messages", methods=["GET", "POST"])
def messages(conversation_id: int):
    owner = _user()
    if owner is None:
        return jsonify({"success": False, "message": "Please log in again."}), 401
    if request.method == "GET":
        return jsonify({"success": True, "messages": list_messages(conversation_id, owner)})
    payload = request.get_json(silent=True) or {}
    item = add_message(conversation_id, str(payload.get("role", "user")), str(payload.get("content", "")), str(payload.get("response_type", "text")))
    return jsonify({"success": True, "message": item}), 201


@copilot_history_bp.route("/api/copilot-history/conversations/<int:conversation_id>", methods=["DELETE"])
def remove_conversation(conversation_id: int):
    owner = _user()
    if owner is None:
        return jsonify({"success": False, "message": "Please log in again."}), 401
    deleted = delete_conversation(conversation_id, owner)
    return jsonify({"success": deleted, "message": "Conversation deleted." if deleted else "Conversation not found."}), 200 if deleted else 404
