from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from services.workspace_service import (
    get_connection
)


def _now() -> str:
    return datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def init_collaboration_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS workspace_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(workspace_id, user_id),
                FOREIGN KEY(workspace_id)
                    REFERENCES workspaces(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS workspace_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                invited_by TEXT NOT NULL,
                invited_email TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                status TEXT NOT NULL DEFAULT 'pending',
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                responded_at TEXT,
                FOREIGN KEY(workspace_id)
                    REFERENCES workspaces(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS dashboard_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dashboard_id INTEGER NOT NULL,
                shared_by TEXT NOT NULL,
                shared_with TEXT NOT NULL,
                permission TEXT NOT NULL DEFAULT 'viewer',
                created_at TEXT NOT NULL,
                UNIQUE(dashboard_id, shared_with),
                FOREIGN KEY(dashboard_id)
                    REFERENCES saved_dashboards(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS dashboard_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dashboard_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                comment TEXT NOT NULL,
                parent_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(dashboard_id)
                    REFERENCES saved_dashboards(id)
                    ON DELETE CASCADE,
                FOREIGN KEY(parent_id)
                    REFERENCES dashboard_comments(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                related_type TEXT,
                related_id INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS
                idx_workspace_members_workspace
            ON workspace_members(workspace_id);

            CREATE INDEX IF NOT EXISTS
                idx_workspace_invitations_email
            ON workspace_invitations(invited_email);

            CREATE INDEX IF NOT EXISTS
                idx_dashboard_comments_dashboard
            ON dashboard_comments(dashboard_id);

            CREATE INDEX IF NOT EXISTS
                idx_notifications_user
            ON notifications(user_id, is_read);

            CREATE INDEX IF NOT EXISTS
                idx_audit_logs_entity
            ON audit_logs(entity_type, entity_id);
            """
        )


def log_activity(
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: str = ""
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_logs (
                user_id,
                action,
                entity_type,
                entity_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                action,
                entity_type,
                entity_id,
                details,
                _now()
            )
        )
        connection.commit()


def create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    related_type: str | None = None,
    related_id: int | None = None
) -> dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO notifications (
                user_id,
                notification_type,
                title,
                message,
                is_read,
                related_type,
                related_id,
                created_at
            )
            VALUES (?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                user_id,
                notification_type,
                title,
                message,
                related_type,
                related_id,
                _now()
            )
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM notifications
            WHERE id = ?
            """,
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


def list_notifications(
    user_id: str,
    unread_only: bool = False
) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM notifications
        WHERE user_id = ?
    """
    params: list[Any] = [user_id]

    if unread_only:
        query += " AND is_read = 0"

    query += " ORDER BY created_at DESC"

    with get_connection() as connection:
        rows = connection.execute(
            query,
            params
        ).fetchall()

    return [dict(row) for row in rows]


def mark_notification_read(
    notification_id: int,
    user_id: str
) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
              AND user_id = ?
            """,
            (
                notification_id,
                user_id
            )
        )
        connection.commit()

    return cursor.rowcount > 0


def add_workspace_member(
    workspace_id: int,
    user_id: str,
    role: str = "viewer"
) -> dict[str, Any]:
    allowed_roles = {
        "owner",
        "admin",
        "editor",
        "viewer"
    }

    clean_role = (
        role
        if role in allowed_roles
        else "viewer"
    )

    timestamp = _now()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO workspace_members (
                workspace_id,
                user_id,
                role,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 'active', ?, ?)
            ON CONFLICT(workspace_id, user_id)
            DO UPDATE SET
                role = excluded.role,
                status = 'active',
                updated_at = excluded.updated_at
            """,
            (
                workspace_id,
                user_id,
                clean_role,
                timestamp,
                timestamp
            )
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM workspace_members
            WHERE workspace_id = ?
              AND user_id = ?
            """,
            (
                workspace_id,
                user_id
            )
        ).fetchone()

    return dict(row)


def list_workspace_members(
    workspace_id: int
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM workspace_members
            WHERE workspace_id = ?
            ORDER BY
                CASE role
                    WHEN 'owner' THEN 1
                    WHEN 'admin' THEN 2
                    WHEN 'editor' THEN 3
                    ELSE 4
                END,
                created_at ASC
            """,
            (workspace_id,)
        ).fetchall()

    return [dict(row) for row in rows]


def remove_workspace_member(
    workspace_id: int,
    user_id: str
) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM workspace_members
            WHERE workspace_id = ?
              AND user_id = ?
              AND role != 'owner'
            """,
            (
                workspace_id,
                user_id
            )
        )
        connection.commit()

    return cursor.rowcount > 0


def create_invitation(
    workspace_id: int,
    invited_by: str,
    invited_email: str,
    role: str,
    token: str
) -> dict[str, Any]:
    allowed_roles = {
        "admin",
        "editor",
        "viewer"
    }

    clean_role = (
        role
        if role in allowed_roles
        else "viewer"
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO workspace_invitations (
                workspace_id,
                invited_by,
                invited_email,
                role,
                status,
                token,
                created_at
            )
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                workspace_id,
                invited_by,
                invited_email.lower().strip(),
                clean_role,
                token,
                _now()
            )
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM workspace_invitations
            WHERE id = ?
            """,
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


def list_invitations(
    invited_email: str
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                i.*,
                w.name AS workspace_name
            FROM workspace_invitations AS i
            JOIN workspaces AS w
                ON w.id = i.workspace_id
            WHERE i.invited_email = ?
              AND i.status = 'pending'
            ORDER BY i.created_at DESC
            """,
            (invited_email.lower().strip(),)
        ).fetchall()

    return [dict(row) for row in rows]


def respond_to_invitation(
    invitation_id: int,
    invited_email: str,
    accept: bool
) -> dict[str, Any] | None:
    with get_connection() as connection:
        invitation = connection.execute(
            """
            SELECT *
            FROM workspace_invitations
            WHERE id = ?
              AND invited_email = ?
              AND status = 'pending'
            """,
            (
                invitation_id,
                invited_email.lower().strip()
            )
        ).fetchone()

        if invitation is None:
            return None

        new_status = (
            "accepted"
            if accept
            else "rejected"
        )

        connection.execute(
            """
            UPDATE workspace_invitations
            SET
                status = ?,
                responded_at = ?
            WHERE id = ?
            """,
            (
                new_status,
                _now(),
                invitation_id
            )
        )

        if accept:
            timestamp = _now()

            connection.execute(
                """
                INSERT INTO workspace_members (
                    workspace_id,
                    user_id,
                    role,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'active', ?, ?)
                ON CONFLICT(workspace_id, user_id)
                DO UPDATE SET
                    role = excluded.role,
                    status = 'active',
                    updated_at = excluded.updated_at
                """,
                (
                    invitation["workspace_id"],
                    invited_email.lower().strip(),
                    invitation["role"],
                    timestamp,
                    timestamp
                )
            )

        connection.commit()

        updated = connection.execute(
            """
            SELECT *
            FROM workspace_invitations
            WHERE id = ?
            """,
            (invitation_id,)
        ).fetchone()

    return dict(updated)


def share_dashboard(
    dashboard_id: int,
    shared_by: str,
    shared_with: str,
    permission: str = "viewer"
) -> dict[str, Any]:
    allowed = {
        "editor",
        "viewer"
    }

    clean_permission = (
        permission
        if permission in allowed
        else "viewer"
    )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO dashboard_shares (
                dashboard_id,
                shared_by,
                shared_with,
                permission,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(dashboard_id, shared_with)
            DO UPDATE SET
                permission = excluded.permission
            """,
            (
                dashboard_id,
                shared_by,
                shared_with.lower().strip(),
                clean_permission,
                _now()
            )
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM dashboard_shares
            WHERE dashboard_id = ?
              AND shared_with = ?
            """,
            (
                dashboard_id,
                shared_with.lower().strip()
            )
        ).fetchone()

    return dict(row)


def list_dashboard_shares(
    dashboard_id: int
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM dashboard_shares
            WHERE dashboard_id = ?
            ORDER BY created_at DESC
            """,
            (dashboard_id,)
        ).fetchall()

    return [dict(row) for row in rows]


def add_comment(
    dashboard_id: int,
    user_id: str,
    comment: str,
    parent_id: int | None = None
) -> dict[str, Any]:
    clean_comment = comment.strip()

    if not clean_comment:
        raise ValueError(
            "Comment cannot be empty."
        )

    timestamp = _now()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO dashboard_comments (
                dashboard_id,
                user_id,
                comment,
                parent_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                dashboard_id,
                user_id,
                clean_comment,
                parent_id,
                timestamp,
                timestamp
            )
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM dashboard_comments
            WHERE id = ?
            """,
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


def list_comments(
    dashboard_id: int
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM dashboard_comments
            WHERE dashboard_id = ?
            ORDER BY created_at ASC
            """,
            (dashboard_id,)
        ).fetchall()

    return [dict(row) for row in rows]


def delete_comment(
    comment_id: int,
    user_id: str
) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM dashboard_comments
            WHERE id = ?
              AND user_id = ?
            """,
            (
                comment_id,
                user_id
            )
        )
        connection.commit()

    return cursor.rowcount > 0


def list_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 100
) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM audit_logs
        WHERE 1 = 1
    """

    params: list[Any] = []

    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)

    if entity_id is not None:
        query += " AND entity_id = ?"
        params.append(entity_id)

    query += """
        ORDER BY created_at DESC
        LIMIT ?
    """

    params.append(limit)

    with get_connection() as connection:
        rows = connection.execute(
            query,
            params
        ).fetchall()

    return [dict(row) for row in rows]
