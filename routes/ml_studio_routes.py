
from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, send_file, session

from services.data_service import load_dataset
from services.ml_studio_service import train_ml_model


ml_studio_bp = Blueprint(
    "ml_studio",
    __name__,
    url_prefix="/ml-studio",
)


def model_directory() -> Path:
    folder = Path(current_app.root_path) / "exports" / "models"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@ml_studio_bp.get("/<filename>")
def ml_studio_page(filename):
    safe_filename = os.path.basename(filename)
    dataframe = load_dataset(safe_filename)
    session["uploaded_file"] = safe_filename

    columns = [
        {
            "name": str(column),
            "dtype": str(dataframe[column].dtype),
            "unique": int(dataframe[column].nunique(dropna=True)),
        }
        for column in dataframe.columns
    ]

    return render_template(
        "ml_studio.html",
        filename=safe_filename,
        columns=columns,
        row_count=len(dataframe),
    )


@ml_studio_bp.post("/train")
def ml_studio_train():
    payload = request.get_json(silent=True) or {}

    filename = (
        str(payload.get("filename", "")).strip()
        or session.get("uploaded_file")
    )

    if not filename:
        return jsonify({
            "success": False,
            "message": "No active dataset was found.",
        }), 400

    try:
        dataframe = load_dataset(os.path.basename(filename))

        result = train_ml_model(
            dataframe,
            requested_task=str(payload.get("task_type", "auto")),
            target_column=str(payload.get("target_column", "")).strip() or None,
            model_name=str(payload.get("model_name", "random_forest")),
            test_size=float(payload.get("test_size", 0.2)),
            cluster_count=int(payload.get("cluster_count", 4)),
        )

        if not result.success:
            return jsonify(result.to_dict()), 400

        model_filename = (
            Path(os.path.basename(filename)).stem
            + "_"
            + result.task_type
            + "_model.joblib"
        )

        model_path = model_directory() / model_filename
        model_path.write_bytes(result.model_bytes or b"")

        session["latest_ml_model"] = str(model_path)

        response = result.to_dict()
        response["download_url"] = "/ml-studio/download-model"

        return jsonify(response)

    except Exception as error:
        current_app.logger.exception("ML Studio training failed")

        return jsonify({
            "success": False,
            "message": str(error) if current_app.debug else "Model training failed.",
        }), 500


@ml_studio_bp.get("/download-model")
def ml_studio_download_model():
    path_value = session.get("latest_ml_model")

    if not path_value:
        return jsonify({
            "success": False,
            "message": "No trained model is available.",
        }), 404

    model_path = Path(path_value)

    if not model_path.exists():
        return jsonify({
            "success": False,
            "message": "The trained model file was not found.",
        }), 404

    return send_file(
        model_path,
        as_attachment=True,
        download_name=model_path.name,
    )
