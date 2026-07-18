from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from flask import current_app


_FILE_LOCK = Lock()


# =====================================================
# STORAGE HELPERS
# =====================================================


def get_connection() -> sqlite3.Connection:
    """
    Return a SQLite connection used by workspace versioning and related
    workspace modules.

    Database location:
        exports/workspace/workspace.db
    """
    database_path = (
        Path(current_app.root_path)
        / "exports"
        / "workspace"
        / "workspace.db"
    )

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        database_path
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection



def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _database_path() -> Path:
    """
    Store workspace data inside:
        exports/workspace/workspace_database.json
    """
    path = (
        Path(current_app.root_path)
        / "exports"
        / "workspace"
        / "workspace_database.json"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path


def _empty_database() -> dict[str, Any]:
    return {
        "next_workspace_id": 1,
        "next_dashboard_id": 1,
        "workspaces": [],
        "dashboards": [],
        "enterprise_dashboards": [],
        "activity": [],
    }


def _load_database() -> dict[str, Any]:
    path = _database_path()

    with _FILE_LOCK:
        if not path.exists():
            database = _empty_database()
            path.write_text(
                json.dumps(database, indent=2),
                encoding="utf-8",
            )
            return database

        try:
            database = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            database = _empty_database()

        defaults = _empty_database()

        for key, value in defaults.items():
            database.setdefault(key, deepcopy(value))

        return database


def _save_database(database: dict[str, Any]) -> None:
    path = _database_path()

    with _FILE_LOCK:
        temporary_path = path.with_suffix(".tmp")

        temporary_path.write_text(
            json.dumps(
                database,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(path)


def _clean_text(
    value: Any,
    field_name: str,
    *,
    required: bool = False,
    maximum_length: int = 200,
) -> str:
    text = str(value or "").strip()

    if required and not text:
        raise ValueError(f"{field_name} is required.")

    if len(text) > maximum_length:
        raise ValueError(
            f"{field_name} must not exceed "
            f"{maximum_length} characters."
        )

    return text


def _workspace_for_owner(
    database: dict[str, Any],
    workspace_id: int,
    owner_id: str,
) -> dict[str, Any] | None:
    for workspace in database["workspaces"]:
        if (
            int(workspace["id"]) == int(workspace_id)
            and str(workspace["owner_id"]) == str(owner_id)
        ):
            return workspace

    return None


def _dashboard_for_owner(
    database: dict[str, Any],
    dashboard_id: int,
    owner_id: str,
) -> dict[str, Any] | None:
    for dashboard in database["dashboards"]:
        if (
            int(dashboard["id"]) == int(dashboard_id)
            and str(dashboard["owner_id"]) == str(owner_id)
        ):
            return dashboard

    return None


# =====================================================
# WORKSPACE FUNCTIONS EXPECTED BY workspace_routes.py
# =====================================================

def ensure_personal_workspace(
    owner_id: str,
) -> dict[str, Any]:
    owner_id = _clean_text(
        owner_id,
        "owner_id",
        required=True,
    )

    database = _load_database()

    owned_workspaces = [
        workspace
        for workspace in database["workspaces"]
        if workspace["owner_id"] == owner_id
    ]

    if owned_workspaces:
        default_workspace = next(
            (
                workspace
                for workspace in owned_workspaces
                if workspace.get("is_default")
            ),
            None,
        )

        if default_workspace:
            return deepcopy(default_workspace)

        owned_workspaces[0]["is_default"] = True
        owned_workspaces[0]["updated_at"] = _utc_now()
        _save_database(database)

        return deepcopy(owned_workspaces[0])

    workspace = {
        "id": database["next_workspace_id"],
        "owner_id": owner_id,
        "name": "Personal Workspace",
        "description": "Default personal workspace",
        "workspace_type": "personal",
        "is_default": True,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }

    database["next_workspace_id"] += 1
    database["workspaces"].append(workspace)
    _save_database(database)

    return deepcopy(workspace)


def create_workspace(
    owner_id: str,
    name: str,
    description: str = "",
    workspace_type: str = "personal",
    is_default: bool = False,
) -> dict[str, Any]:
    owner_id = _clean_text(
        owner_id,
        "owner_id",
        required=True,
    )

    name = _clean_text(
        name,
        "Workspace name",
        required=True,
        maximum_length=100,
    )

    description = _clean_text(
        description,
        "Description",
        maximum_length=500,
    )

    workspace_type = _clean_text(
        workspace_type,
        "Workspace type",
        required=True,
        maximum_length=50,
    ).lower()

    allowed_types = {
        "personal",
        "team",
        "enterprise",
    }

    if workspace_type not in allowed_types:
        raise ValueError(
            "Workspace type must be personal, team, or enterprise."
        )

    database = _load_database()

    duplicate = any(
        workspace["owner_id"] == owner_id
        and workspace["name"].lower() == name.lower()
        for workspace in database["workspaces"]
    )

    if duplicate:
        raise ValueError(
            "A workspace with this name already exists."
        )

    if is_default:
        for workspace in database["workspaces"]:
            if workspace["owner_id"] == owner_id:
                workspace["is_default"] = False

    workspace = {
        "id": database["next_workspace_id"],
        "owner_id": owner_id,
        "name": name,
        "description": description,
        "workspace_type": workspace_type,
        "is_default": bool(is_default),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }

    database["next_workspace_id"] += 1
    database["workspaces"].append(workspace)

    owned_count = sum(
        1
        for item in database["workspaces"]
        if item["owner_id"] == owner_id
    )

    if owned_count == 1:
        workspace["is_default"] = True

    _save_database(database)

    return deepcopy(workspace)


def list_workspaces(
    owner_id: str,
) -> list[dict[str, Any]]:
    owner_id = _clean_text(
        owner_id,
        "owner_id",
        required=True,
    )

    ensure_personal_workspace(owner_id)

    database = _load_database()

    workspaces = [
        deepcopy(workspace)
        for workspace in database["workspaces"]
        if workspace["owner_id"] == owner_id
    ]

    workspaces.sort(
        key=lambda item: (
            not bool(item.get("is_default")),
            item.get("name", "").lower(),
        )
    )

    for workspace in workspaces:
        workspace["dashboard_count"] = sum(
            1
            for dashboard in database["dashboards"]
            if dashboard["workspace_id"] == workspace["id"]
        )

    return workspaces


def get_workspace(
    workspace_id: int,
    owner_id: str,
) -> dict[str, Any] | None:
    database = _load_database()

    workspace = _workspace_for_owner(
        database,
        workspace_id,
        owner_id,
    )

    if workspace is None:
        return None

    result = deepcopy(workspace)

    result["dashboard_count"] = sum(
        1
        for dashboard in database["dashboards"]
        if dashboard["workspace_id"] == workspace["id"]
    )

    return result


def update_workspace(
    workspace_id: int,
    owner_id: str,
    name: str,
    description: str = "",
    workspace_type: str = "personal",
) -> dict[str, Any]:
    name = _clean_text(
        name,
        "Workspace name",
        required=True,
        maximum_length=100,
    )

    description = _clean_text(
        description,
        "Description",
        maximum_length=500,
    )

    workspace_type = _clean_text(
        workspace_type,
        "Workspace type",
        required=True,
        maximum_length=50,
    ).lower()

    if workspace_type not in {
        "personal",
        "team",
        "enterprise",
    }:
        raise ValueError(
            "Workspace type must be personal, team, or enterprise."
        )

    database = _load_database()

    workspace = _workspace_for_owner(
        database,
        workspace_id,
        owner_id,
    )

    if workspace is None:
        raise ValueError("Workspace not found.")

    duplicate = any(
        item["owner_id"] == owner_id
        and int(item["id"]) != int(workspace_id)
        and item["name"].lower() == name.lower()
        for item in database["workspaces"]
    )

    if duplicate:
        raise ValueError(
            "A workspace with this name already exists."
        )

    workspace.update(
        {
            "name": name,
            "description": description,
            "workspace_type": workspace_type,
            "updated_at": _utc_now(),
        }
    )

    _save_database(database)

    return deepcopy(workspace)


def delete_workspace(
    workspace_id: int,
    owner_id: str,
) -> bool:
    database = _load_database()

    workspace = _workspace_for_owner(
        database,
        workspace_id,
        owner_id,
    )

    if workspace is None:
        return False

    owned_workspaces = [
        item
        for item in database["workspaces"]
        if item["owner_id"] == owner_id
    ]

    if len(owned_workspaces) <= 1:
        raise ValueError(
            "You cannot delete your only workspace."
        )

    was_default = bool(
        workspace.get("is_default")
    )

    database["workspaces"] = [
        item
        for item in database["workspaces"]
        if not (
            int(item["id"]) == int(workspace_id)
            and item["owner_id"] == owner_id
        )
    ]

    database["dashboards"] = [
        dashboard
        for dashboard in database["dashboards"]
        if not (
            int(dashboard["workspace_id"]) == int(workspace_id)
            and dashboard["owner_id"] == owner_id
        )
    ]

    if was_default:
        for item in database["workspaces"]:
            if item["owner_id"] == owner_id:
                item["is_default"] = True
                item["updated_at"] = _utc_now()
                break

    _save_database(database)

    return True


def set_default_workspace(
    workspace_id: int,
    owner_id: str,
) -> dict[str, Any]:
    database = _load_database()

    workspace = _workspace_for_owner(
        database,
        workspace_id,
        owner_id,
    )

    if workspace is None:
        raise ValueError("Workspace not found.")

    for item in database["workspaces"]:
        if item["owner_id"] == owner_id:
            item["is_default"] = (
                int(item["id"]) == int(workspace_id)
            )
            item["updated_at"] = _utc_now()

    _save_database(database)

    return deepcopy(workspace)


# =====================================================
# SAVED DASHBOARD FUNCTIONS
# =====================================================

def save_dashboard(
    workspace_id: int,
    owner_id: str,
    name: str,
    filename: str,
    dashboard_type: str = "executive",
    description: str = "",
    dashboard_state: dict[str, Any] | None = None,
    thumbnail: str = "",
) -> dict[str, Any]:
    database = _load_database()

    workspace = _workspace_for_owner(
        database,
        workspace_id,
        owner_id,
    )

    if workspace is None:
        raise ValueError("Workspace not found.")

    name = _clean_text(
        name,
        "Dashboard name",
        required=True,
        maximum_length=120,
    )

    filename = _clean_text(
        filename,
        "Filename",
        required=True,
        maximum_length=255,
    )

    dashboard_type = _clean_text(
        dashboard_type,
        "Dashboard type",
        required=True,
        maximum_length=50,
    )

    description = _clean_text(
        description,
        "Description",
        maximum_length=500,
    )

    if dashboard_state is None:
        dashboard_state = {}

    if not isinstance(dashboard_state, dict):
        raise ValueError(
            "dashboard_state must be a JSON object."
        )

    dashboard = {
        "id": database["next_dashboard_id"],
        "workspace_id": int(workspace_id),
        "owner_id": str(owner_id),
        "name": name,
        "filename": filename,
        "dashboard_type": dashboard_type,
        "description": description,
        "dashboard_state": dashboard_state,
        "thumbnail": str(thumbnail or ""),
        "is_favorite": False,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }

    database["next_dashboard_id"] += 1
    database["dashboards"].append(dashboard)

    _save_database(database)

    return deepcopy(dashboard)


def list_saved_dashboards(
    owner_id: str,
    workspace_id: int | None = None,
    favorites_only: bool = False,
) -> list[dict[str, Any]]:
    database = _load_database()

    dashboards = [
        dashboard
        for dashboard in database["dashboards"]
        if dashboard["owner_id"] == str(owner_id)
    ]

    if workspace_id is not None:
        dashboards = [
            dashboard
            for dashboard in dashboards
            if int(dashboard["workspace_id"]) == int(workspace_id)
        ]

    if favorites_only:
        dashboards = [
            dashboard
            for dashboard in dashboards
            if bool(dashboard.get("is_favorite"))
        ]

    dashboards.sort(
        key=lambda item: item.get(
            "updated_at",
            "",
        ),
        reverse=True,
    )

    return deepcopy(dashboards)


def get_saved_dashboard(
    dashboard_id: int,
    owner_id: str,
) -> dict[str, Any] | None:
    database = _load_database()

    dashboard = _dashboard_for_owner(
        database,
        dashboard_id,
        owner_id,
    )

    return (
        deepcopy(dashboard)
        if dashboard is not None
        else None
    )


def update_saved_dashboard(
    dashboard_id: int,
    owner_id: str,
    name: str,
    description: str = "",
) -> dict[str, Any]:
    database = _load_database()

    dashboard = _dashboard_for_owner(
        database,
        dashboard_id,
        owner_id,
    )

    if dashboard is None:
        raise ValueError(
            "Saved dashboard not found."
        )

    dashboard["name"] = _clean_text(
        name,
        "Dashboard name",
        required=True,
        maximum_length=120,
    )

    dashboard["description"] = _clean_text(
        description,
        "Description",
        maximum_length=500,
    )

    dashboard["updated_at"] = _utc_now()

    _save_database(database)

    return deepcopy(dashboard)


def delete_saved_dashboard(
    dashboard_id: int,
    owner_id: str,
) -> bool:
    database = _load_database()

    dashboard = _dashboard_for_owner(
        database,
        dashboard_id,
        owner_id,
    )

    if dashboard is None:
        return False

    database["dashboards"] = [
        item
        for item in database["dashboards"]
        if not (
            int(item["id"]) == int(dashboard_id)
            and item["owner_id"] == str(owner_id)
        )
    ]

    _save_database(database)

    return True


def toggle_dashboard_favorite(
    dashboard_id: int,
    owner_id: str,
) -> dict[str, Any]:
    database = _load_database()

    dashboard = _dashboard_for_owner(
        database,
        dashboard_id,
        owner_id,
    )

    if dashboard is None:
        raise ValueError(
            "Saved dashboard not found."
        )

    dashboard["is_favorite"] = not bool(
        dashboard.get("is_favorite")
    )

    dashboard["updated_at"] = _utc_now()

    _save_database(database)

    return deepcopy(dashboard)


# =====================================================
# PHASE 4 ENTERPRISE WORKSPACE COMPATIBILITY
# =====================================================

def load_workspace() -> dict[str, Any]:
    """
    Compatibility function used by Phase 4 enterprise workspace.
    """
    database = _load_database()

    return {
        "dashboards": deepcopy(
            database.get(
                "enterprise_dashboards",
                [],
            )
        ),
        "members": [
            {
                "name": "Owner",
                "role": "Admin",
            }
        ],
        "activity": deepcopy(
            database.get(
                "activity",
                [],
            )
        ),
    }


def save_workspace(
    workspace: dict[str, Any],
) -> None:
    """
    Compatibility function for the Phase 4 service API.
    """
    if not isinstance(workspace, dict):
        raise ValueError(
            "Workspace data must be a dictionary."
        )

    database = _load_database()

    database["enterprise_dashboards"] = deepcopy(
        workspace.get(
            "dashboards",
            [],
        )
    )

    database["activity"] = deepcopy(
        workspace.get(
            "activity",
            [],
        )
    )

    _save_database(database)


def add_dashboard(
    name: str,
    filename: str,
) -> dict[str, Any]:
    """
    Publish a lightweight dashboard entry for Phase 4.
    """
    database = _load_database()

    dashboards = database.setdefault(
        "enterprise_dashboards",
        [],
    )

    next_id = max(
        [
            int(item.get("id", 0))
            for item in dashboards
        ],
        default=0,
    ) + 1

    dashboard = {
        "id": next_id,
        "name": _clean_text(
            name,
            "Dashboard name",
            required=True,
            maximum_length=120,
        ),
        "filename": _clean_text(
            filename,
            "Filename",
            required=True,
            maximum_length=255,
        ),
        "status": "Published",
        "created_at": _utc_now(),
    }

    dashboards.append(dashboard)

    database.setdefault(
        "activity",
        [],
    ).insert(
        0,
        {
            "message": (
                f"Published dashboard: "
                f"{dashboard['name']}"
            ),
            "created_at": _utc_now(),
        },
    )

    _save_database(database)

    return deepcopy(dashboard)


# =====================================================
# DATABASE INITIALIZATION (compatibility)
# =====================================================

def init_workspace_database() -> None:
    """
    Compatibility initializer expected by app.py.
    Ensures both the JSON store and SQLite database exist.
    """
    _load_database()
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workspace_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER,
                dashboard_id INTEGER,
                version_name TEXT,
                version_data TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()