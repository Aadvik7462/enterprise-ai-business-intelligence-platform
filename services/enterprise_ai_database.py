
from __future__ import annotations

from datetime import datetime
from typing import Any

from services.workspace_service import get_connection


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def init_enterprise_ai_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS business_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                metric_column TEXT NOT NULL,
                goal_name TEXT NOT NULL,
                target_value REAL NOT NULL,
                current_value REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                due_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS report_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                report_name TEXT NOT NULL,
                frequency TEXT NOT NULL DEFAULT 'weekly',
                delivery_email TEXT DEFAULT '',
                export_format TEXT NOT NULL DEFAULT 'html',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scenario_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                scenario_name TEXT NOT NULL,
                metric_column TEXT NOT NULL,
                change_percent REAL NOT NULL,
                base_value REAL NOT NULL,
                projected_value REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_business_goals_owner
            ON business_goals(owner_id);

            CREATE INDEX IF NOT EXISTS idx_report_schedules_owner
            ON report_schedules(owner_id);

            CREATE INDEX IF NOT EXISTS idx_scenario_history_owner
            ON scenario_history(owner_id);
            """
        )
        connection.commit()


def create_goal(
    owner_id: str,
    filename: str,
    metric_column: str,
    goal_name: str,
    target_value: float,
    current_value: float = 0,
    due_date: str = ""
) -> dict[str, Any]:
    timestamp = _now()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO business_goals (
                owner_id,
                filename,
                metric_column,
                goal_name,
                target_value,
                current_value,
                status,
                due_date,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (
                owner_id,
                filename,
                metric_column,
                goal_name,
                float(target_value),
                float(current_value),
                due_date,
                timestamp,
                timestamp
            )
        )
        connection.commit()

        row = connection.execute(
            "SELECT * FROM business_goals WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


def list_goals(
    owner_id: str,
    filename: str | None = None
) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM business_goals
        WHERE owner_id = ?
    """
    params: list[Any] = [owner_id]

    if filename:
        query += " AND filename = ?"
        params.append(filename)

    query += " ORDER BY updated_at DESC"

    with get_connection() as connection:
        rows = connection.execute(
            query,
            params
        ).fetchall()

    return [dict(row) for row in rows]


def delete_goal(
    goal_id: int,
    owner_id: str
) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM business_goals
            WHERE id = ?
              AND owner_id = ?
            """,
            (goal_id, owner_id)
        )
        connection.commit()

    return cursor.rowcount > 0


def create_schedule(
    owner_id: str,
    filename: str,
    report_name: str,
    frequency: str,
    delivery_email: str = "",
    export_format: str = "html"
) -> dict[str, Any]:
    allowed_frequency = {
        "daily",
        "weekly",
        "monthly"
    }

    allowed_format = {
        "html",
        "pdf",
        "pptx"
    }

    clean_frequency = (
        frequency
        if frequency in allowed_frequency
        else "weekly"
    )

    clean_format = (
        export_format
        if export_format in allowed_format
        else "html"
    )

    timestamp = _now()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO report_schedules (
                owner_id,
                filename,
                report_name,
                frequency,
                delivery_email,
                export_format,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                owner_id,
                filename,
                report_name,
                clean_frequency,
                delivery_email,
                clean_format,
                timestamp,
                timestamp
            )
        )
        connection.commit()

        row = connection.execute(
            "SELECT * FROM report_schedules WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


def list_schedules(
    owner_id: str
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM report_schedules
            WHERE owner_id = ?
            ORDER BY updated_at DESC
            """,
            (owner_id,)
        ).fetchall()

    return [dict(row) for row in rows]


def delete_schedule(
    schedule_id: int,
    owner_id: str
) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM report_schedules
            WHERE id = ?
              AND owner_id = ?
            """,
            (schedule_id, owner_id)
        )
        connection.commit()

    return cursor.rowcount > 0


def save_scenario(
    owner_id: str,
    filename: str,
    scenario_name: str,
    metric_column: str,
    change_percent: float,
    base_value: float,
    projected_value: float
) -> dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scenario_history (
                owner_id,
                filename,
                scenario_name,
                metric_column,
                change_percent,
                base_value,
                projected_value,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                filename,
                scenario_name,
                metric_column,
                float(change_percent),
                float(base_value),
                float(projected_value),
                _now()
            )
        )
        connection.commit()

        row = connection.execute(
            "SELECT * FROM scenario_history WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


def list_scenarios(
    owner_id: str,
    filename: str | None = None
) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM scenario_history
        WHERE owner_id = ?
    """
    params: list[Any] = [owner_id]

    if filename:
        query += " AND filename = ?"
        params.append(filename)

    query += " ORDER BY created_at DESC"

    with get_connection() as connection:
        rows = connection.execute(
            query,
            params
        ).fetchall()

    return [dict(row) for row in rows]
