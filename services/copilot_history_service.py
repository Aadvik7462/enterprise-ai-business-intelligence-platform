from __future__ import annotations

from datetime import datetime
from typing import Any
from services.workspace_service import get_connection


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def init_copilot_history_database() -> None:
    with get_connection() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS copilot_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS copilot_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            response_type TEXT NOT NULL DEFAULT 'text',
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES copilot_conversations(id) ON DELETE CASCADE
        );
        """)
        connection.commit()


def create_conversation(owner_id: str, filename: str, title: str) -> dict[str, Any]:
    now = _now()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO copilot_conversations (owner_id, filename, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (owner_id, filename, title, now, now),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM copilot_conversations WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_conversations(owner_id: str, filename: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM copilot_conversations WHERE owner_id = ? AND filename = ? ORDER BY updated_at DESC",
            (owner_id, filename),
        ).fetchall()
    return [dict(row) for row in rows]


def add_message(conversation_id: int, role: str, content: str, response_type: str = "text") -> dict[str, Any]:
    now = _now()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO copilot_messages (conversation_id, role, content, response_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, role, content, response_type, now),
        )
        connection.execute("UPDATE copilot_conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
        connection.commit()
        row = connection.execute("SELECT * FROM copilot_messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_messages(conversation_id: int, owner_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT m.* FROM copilot_messages AS m
            JOIN copilot_conversations AS c ON c.id = m.conversation_id
            WHERE m.conversation_id = ? AND c.owner_id = ?
            ORDER BY m.created_at ASC
            """,
            (conversation_id, owner_id),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_conversation(conversation_id: int, owner_id: str) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM copilot_conversations WHERE id = ? AND owner_id = ?", (conversation_id, owner_id))
        connection.commit()
    return cursor.rowcount > 0
