from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from services.workspace_service import get_connection


def init_workspace_version_database() -> None:
    with get_connection() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS dashboard_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dashboard_id INTEGER NOT NULL,
            owner_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            dashboard_state TEXT NOT NULL,
            change_summary TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(dashboard_id, version_number),
            FOREIGN KEY(dashboard_id) REFERENCES saved_dashboards(id) ON DELETE CASCADE
        );
        """)
        connection.commit()


def create_dashboard_version(dashboard_id: int, owner_id: str, dashboard_state: dict[str, Any], change_summary: str = "") -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COALESCE(MAX(version_number), 0) AS latest_version FROM dashboard_versions WHERE dashboard_id = ? AND owner_id = ?",
            (dashboard_id, owner_id),
        ).fetchone()
        number = int(row["latest_version"]) + 1
        cursor = connection.execute(
            "INSERT INTO dashboard_versions (dashboard_id, owner_id, version_number, dashboard_state, change_summary, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (dashboard_id, owner_id, number, json.dumps(dashboard_state, default=str), change_summary, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
        )
        connection.commit()
        version = connection.execute("SELECT * FROM dashboard_versions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    result = dict(version)
    result["dashboard_state"] = json.loads(result["dashboard_state"])
    return result


def list_dashboard_versions(dashboard_id: int, owner_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM dashboard_versions WHERE dashboard_id = ? AND owner_id = ? ORDER BY version_number DESC",
            (dashboard_id, owner_id),
        ).fetchall()
    output = []
    for row in rows:
        item = dict(row)
        item["dashboard_state"] = json.loads(item["dashboard_state"])
        output.append(item)
    return output


def get_dashboard_version(version_id: int, owner_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM dashboard_versions WHERE id = ? AND owner_id = ?", (version_id, owner_id)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["dashboard_state"] = json.loads(result["dashboard_state"])
    return result
