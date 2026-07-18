from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from services.workspace_service import get_saved_dashboard
from services.workspace_version_service import create_dashboard_version, get_dashboard_version, list_dashboard_versions

workspace_version_bp = Blueprint("workspace_version", __name__)


def _user() -> str | None:
    user = session.get("user")
    if user is None:
        return None
    if isinstance(user, dict):
        return str(user.get("id") or user.get("email") or user.get("username") or user.get("name") or "").strip() or None
    return str(user).strip() or None


@workspace_version_bp.route("/api/dashboards/<int:dashboard_id>/versions", methods=["GET", "POST"])
def versions(dashboard_id: int):
    owner = _user()
    if owner is None:
        return jsonify({"success": False, "message": "Please log in again."}), 401
    dashboard = get_saved_dashboard(dashboard_id=dashboard_id, owner_id=owner)
    if dashboard is None:
        return jsonify({"success": False, "message": "Dashboard not found."}), 404
    if request.method == "GET":
        return jsonify({"success": True, "versions": list_dashboard_versions(dashboard_id, owner)})
    payload = request.get_json(silent=True) or {}
    item = create_dashboard_version(dashboard_id, owner, payload.get("dashboard_state", dashboard.get("dashboard_state", {})), str(payload.get("change_summary", "")))
    return jsonify({"success": True, "version": item}), 201


@workspace_version_bp.route("/api/dashboard-versions/<int:version_id>")
def version(version_id: int):
    owner = _user()
    if owner is None:
        return jsonify({"success": False, "message": "Please log in again."}), 401
    item = get_dashboard_version(version_id, owner)
    if item is None:
        return jsonify({"success": False, "message": "Version not found."}), 404
    return jsonify({"success": True, "version": item})
