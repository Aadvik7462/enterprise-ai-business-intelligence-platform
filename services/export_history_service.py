from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


HISTORY_FILE = os.path.join(
    "exports",
    "export_history.json"
)


def _ensure_history_file() -> None:
    """
    Create the export directory and history file when missing.
    """

    os.makedirs(
        os.path.dirname(HISTORY_FILE),
        exist_ok=True
    )

    if not os.path.exists(HISTORY_FILE):
        with open(
            HISTORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                [],
                file,
                indent=4
            )


def get_export_history(
    limit: int = 10
) -> list[dict[str, Any]]:
    """
    Return the most recent export records.
    """

    _ensure_history_file()

    try:
        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            history = json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ):
        history = []

    history = sorted(
        history,
        key=lambda item: item.get(
            "created_at",
            ""
        ),
        reverse=True
    )

    return history[:limit]


def record_export(
    dataset_name: str,
    export_format: str,
    output_filename: str
) -> dict[str, Any]:
    """
    Save one export record.
    """

    _ensure_history_file()

    history = get_export_history(
        limit=100
    )

    created_at = datetime.now()

    record = {
        "dataset_name": dataset_name,
        "export_format": export_format.upper(),
        "output_filename": output_filename,
        "created_at": created_at.isoformat(),
        "display_time": created_at.strftime(
            "%d %b %Y, %I:%M %p"
        )
    }

    history.insert(
        0,
        record
    )

    history = history[:100]

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            history,
            file,
            indent=4
        )

    return record