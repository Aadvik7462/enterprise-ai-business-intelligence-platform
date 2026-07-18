
from __future__ import annotations

import os
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
    session,
)

from services.automl_service import run_automl
from services.data_service import load_dataset


automl_bp = Blueprint(
    "automl",
    __name__,
    url_prefix="/automl",
)


def automl_export_directory() -> Path:
    folder = (
        Path(
            current_app.root_path
        )
        / "exports"
        / "automl"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    return folder


@automl_bp.get("/<filename>")
def automl_page(filename):
    safe_filename = os.path.basename(
        filename
    )

    dataframe = load_dataset(
        safe_filename
    )

    session["uploaded_file"] = safe_filename

    columns = [
        {
            "name": str(column),
            "dtype": str(
                dataframe[column].dtype
            ),
            "unique": int(
                dataframe[column].nunique(
                    dropna=True
                )
            ),
            "missing": int(
                dataframe[column].isna().sum()
            ),
        }
        for column in dataframe.columns
    ]

    return render_template(
        "automl_studio.html",
        filename=safe_filename,
        columns=columns,
        row_count=int(
            len(
                dataframe
            )
        ),
    )


@automl_bp.post("/train")
def automl_train():
    payload = request.get_json(
        silent=True
    ) or {}

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

    target_column = str(
        payload.get(
            "target_column",
            "",
        )
    ).strip()

    if not filename:
        return jsonify(
            {
                "success": False,
                "message": "No active dataset was found.",
            }
        ), 400

    if not target_column:
        return jsonify(
            {
                "success": False,
                "message": "Select a target column.",
            }
        ), 400

    try:
        safe_filename = os.path.basename(
            filename
        )

        dataframe = load_dataset(
            safe_filename
        )

        result = run_automl(
            dataframe,
            target_column=target_column,
            test_size=float(
                payload.get(
                    "test_size",
                    0.2,
                )
            ),
        )

        if not result.success:
            return jsonify(
                result.to_dict()
            ), 400

        stem = Path(
            safe_filename
        ).stem

        export_directory = (
            automl_export_directory()
        )

        model_path = (
            export_directory
            / f"{stem}_best_automl_model.joblib"
        )

        predictions_path = (
            export_directory
            / f"{stem}_automl_predictions.csv"
        )

        leaderboard_path = (
            export_directory
            / f"{stem}_automl_leaderboard.csv"
        )

        model_path.write_bytes(
            result.model_bytes or b""
        )

        predictions_path.write_bytes(
            result.predictions_csv or b""
        )

        leaderboard_path.write_bytes(
            result.leaderboard_csv or b""
        )

        session["automl_model_path"] = str(
            model_path
        )

        session["automl_predictions_path"] = str(
            predictions_path
        )

        session["automl_leaderboard_path"] = str(
            leaderboard_path
        )

        response = result.to_dict()

        response["downloads"] = {
            "model": "/automl/download/model",
            "predictions": "/automl/download/predictions",
            "leaderboard": "/automl/download/leaderboard",
        }

        return jsonify(
            response
        )

    except Exception as error:
        current_app.logger.exception(
            "AutoML training failed"
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    str(error)
                    if current_app.debug
                    else "AutoML training failed."
                ),
            }
        ), 500


def send_session_file(
    session_key: str,
    download_name: str,
):
    path_value = session.get(
        session_key
    )

    if not path_value:
        return jsonify(
            {
                "success": False,
                "message": "The requested export is unavailable.",
            }
        ), 404

    path = Path(
        path_value
    )

    if not path.exists():
        return jsonify(
            {
                "success": False,
                "message": "The requested file was not found.",
            }
        ), 404

    return send_file(
        path,
        as_attachment=True,
        download_name=download_name,
    )


@automl_bp.get("/download/model")
def automl_download_model():
    return send_session_file(
        "automl_model_path",
        "best_automl_model.joblib",
    )


@automl_bp.get("/download/predictions")
def automl_download_predictions():
    return send_session_file(
        "automl_predictions_path",
        "automl_predictions.csv",
    )


@automl_bp.get("/download/leaderboard")
def automl_download_leaderboard():
    return send_session_file(
        "automl_leaderboard_path",
        "automl_leaderboard.csv",
    )
