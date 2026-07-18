from __future__ import annotations

import os
from flask import Blueprint, current_app, jsonify, request, session
from services.advanced_analytics_service import (
    analyze_missing_values,
    detect_outliers,
    generate_correlation_matrix,
    generate_feature_importance,
    generate_statistical_summary,
)
from services.data_service import load_dataset
from services.performance_cache_service import get_cached_result, set_cached_result

advanced_analytics_bp = Blueprint("advanced_analytics", __name__)


def _user() -> str | None:
    user = session.get("user")
    if user is None:
        return None
    if isinstance(user, dict):
        return str(user.get("id") or user.get("email") or user.get("username") or user.get("name") or "").strip() or None
    return str(user).strip() or None


def _unauthorized():
    return jsonify({"success": False, "message": "Please log in again."}), 401


def _load(filename: str):
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        raise FileNotFoundError("Dataset file was not found.")
    return load_dataset(path)


def _cached(namespace: str, payload: dict, generator):
    result = get_cached_result(namespace, payload)
    if result is not None:
        result["cached"] = True
        return result
    result = generator()
    if result.get("success"):
        set_cached_result(namespace, payload, result)
    result["cached"] = False
    return result


@advanced_analytics_bp.route("/api/advanced-analytics/<filename>/correlation")
def correlation(filename: str):
    if _user() is None:
        return _unauthorized()
    try:
        return jsonify(_cached("correlation", {"filename": filename}, lambda: generate_correlation_matrix(_load(filename))))
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


@advanced_analytics_bp.route("/api/advanced-analytics/<filename>/outliers")
def outliers(filename: str):
    if _user() is None:
        return _unauthorized()
    column = request.args.get("column")
    try:
        return jsonify(_cached("outliers", {"filename": filename, "column": column}, lambda: detect_outliers(_load(filename), column)))
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


@advanced_analytics_bp.route("/api/advanced-analytics/<filename>/missing")
def missing(filename: str):
    if _user() is None:
        return _unauthorized()
    try:
        return jsonify(_cached("missing", {"filename": filename}, lambda: analyze_missing_values(_load(filename))))
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


@advanced_analytics_bp.route("/api/advanced-analytics/<filename>/feature-importance", methods=["POST"])
def feature_importance(filename: str):
    if _user() is None:
        return _unauthorized()
    payload = request.get_json(silent=True) or {}
    target = str(payload.get("target_column", ""))
    try:
        return jsonify(_cached("feature_importance", {"filename": filename, "target": target}, lambda: generate_feature_importance(_load(filename), target)))
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500


@advanced_analytics_bp.route("/api/advanced-analytics/<filename>/statistics")
def statistics(filename: str):
    if _user() is None:
        return _unauthorized()
    try:
        return jsonify(_cached("statistics", {"filename": filename}, lambda: generate_statistical_summary(_load(filename))))
    except Exception as error:
        return jsonify({"success": False, "message": str(error)}), 500
