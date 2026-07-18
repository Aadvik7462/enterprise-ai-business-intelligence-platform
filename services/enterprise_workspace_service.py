
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import current_app


def workspace_path() -> Path:
    path = (
        Path(
            current_app.root_path
        )
        / "exports"
        / "workspace"
        / "workspace_state.json"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path


def load_workspace() -> dict[str, Any]:
    path = workspace_path()

    if not path.exists():
        return {
            "dashboards": [],
            "members": [
                {
                    "name": "Owner",
                    "role": "Admin",
                }
            ],
            "activity": [],
        }

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (json.JSONDecodeError, OSError):
        return {
            "dashboards": [],
            "members": [],
            "activity": [],
        }


def save_workspace(
    workspace: dict[str, Any],
) -> None:
    workspace_path().write_text(
        json.dumps(
            workspace,
            indent=2,
        ),
        encoding="utf-8",
    )


def add_dashboard(
    name: str,
    filename: str,
) -> dict[str, Any]:
    workspace = load_workspace()

    dashboard = {
        "id": len(
            workspace["dashboards"]
        ) + 1,
        "name": name,
        "filename": filename,
        "status": "Published",
    }

    workspace["dashboards"].append(
        dashboard
    )

    workspace["activity"].insert(
        0,
        {
            "message": f"Published dashboard: {name}",
        },
    )

    save_workspace(
        workspace
    )

    return dashboard
