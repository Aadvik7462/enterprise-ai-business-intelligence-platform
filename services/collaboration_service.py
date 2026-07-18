from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any

from services.workspace_service import (
    _load_database,
    get_connection,
)


# =====================================================
# GENERAL HELPERS
# =====================================================

def _now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _clean_email(value: str) -> str:
    """Normalize an email address."""
    return str(value or "").strip().lower()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a SQLite row to a dictionary."""
    if row is None:
        return None

    return dict(row)


def _workspace_by_id(
    workspace_id: int,
) -> dict[str, Any] | None:
    """
    Find a workspace from the JSON workspace database.

    Workspaces are stored by workspace_service.py inside:
    exports/workspace/workspace_database.json
    """
    database = _load_database()

    for workspace in database.get("workspaces", []):
        if int(workspace.get("id", 0)) == int(workspace_id):
            return dict(workspace)

    return None


def _dashboard_by_id(
    dashboard_id: int,
) -> dict[str, Any] | None:
    """
    Find a dashboard from the JSON workspace database.
    """
    database = _load_database()

    for dashboard in database.get("dashboards", []):
        if int(dashboard.get("id", 0)) == int(dashboard_id):
            return dict(dashboard)

    for dashboard in database.get("enterprise_dashboards", []):
        if int(dashboard.get("id", 0)) == int(dashboard_id):
            return dict(dashboard)

    return None


def _workspace_name(workspace_id: int) -> str:
    """Return a workspace name without using an SQL JOIN."""
    workspace = _workspace_by_id(workspace_id)

    if workspace is None:
        return f"Workspace #{workspace_id}"

    return str(
        workspace.get("name")
        or f"Workspace #{workspace_id}"
    )


def _dashboard_name(dashboard_id: int) -> str:
    """Return a dashboard name from the JSON database."""
    dashboard = _dashboard_by_id(dashboard_id)

    if dashboard is None:
        return f"Dashboard #{dashboard_id}"

    return str(
        dashboard.get("name")
        or f"Dashboard #{dashboard_id}"
    )


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

def init_collaboration_database() -> None:
    """
    Initialize collaboration tables.

    Important:
    Workspaces and dashboards are stored in JSON by workspace_service.py.
    Therefore, these SQLite tables intentionally do not use foreign keys
    referencing workspaces or saved_dashboards.
    """
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
                UNIQUE(workspace_id, user_id)
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
                responded_at TEXT
            );

            CREATE TABLE IF NOT EXISTS dashboard_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dashboard_id INTEGER NOT NULL,
                shared_by TEXT NOT NULL,
                shared_with TEXT NOT NULL,
                permission TEXT NOT NULL DEFAULT 'viewer',
                created_at TEXT NOT NULL,
                UNIQUE(dashboard_id, shared_with)
            );

            CREATE TABLE IF NOT EXISTS dashboard_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dashboard_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                comment TEXT NOT NULL,
                parent_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
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
                idx_workspace_members_user
            ON workspace_members(user_id);

            CREATE INDEX IF NOT EXISTS
                idx_workspace_invitations_email
            ON workspace_invitations(invited_email);

            CREATE INDEX IF NOT EXISTS
                idx_workspace_invitations_workspace
            ON workspace_invitations(workspace_id);

            CREATE INDEX IF NOT EXISTS
                idx_dashboard_shares_dashboard
            ON dashboard_shares(dashboard_id);

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

        connection.commit()


def _ensure_database() -> None:
    """Ensure collaboration tables exist before every operation."""
    init_collaboration_database()


# =====================================================
# AUDIT LOGS
# =====================================================

def log_activity(
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: str = "",
) -> None:
    _ensure_database()

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
                str(user_id),
                str(action),
                str(entity_type),
                entity_id,
                str(details or ""),
                _now(),
            ),
        )

        connection.commit()


def list_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    _ensure_database()

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

    params.append(max(1, min(int(limit), 500)))

    with get_connection() as connection:
        rows = connection.execute(
            query,
            params,
        ).fetchall()

    return [dict(row) for row in rows]


# =====================================================
# NOTIFICATIONS
# =====================================================

def create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> dict[str, Any]:
    _ensure_database()

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
                str(user_id),
                str(notification_type),
                str(title),
                str(message),
                related_type,
                related_id,
                _now(),
            ),
        )

        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM notifications
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return dict(row)


def list_notifications(
    user_id: str,
    unread_only: bool = False,
) -> list[dict[str, Any]]:
    _ensure_database()

    query = """
        SELECT *
        FROM notifications
        WHERE user_id = ?
    """

    params: list[Any] = [str(user_id)]

    if unread_only:
        query += " AND is_read = 0"

    query += " ORDER BY created_at DESC"

    with get_connection() as connection:
        rows = connection.execute(
            query,
            params,
        ).fetchall()

    return [dict(row) for row in rows]


def mark_notification_read(
    notification_id: int,
    user_id: str,
) -> bool:
    _ensure_database()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
              AND user_id = ?
            """,
            (
                int(notification_id),
                str(user_id),
            ),
        )

        connection.commit()

    return cursor.rowcount > 0


# =====================================================
# WORKSPACE MEMBERS
# =====================================================

def add_workspace_member(
    workspace_id: int,
    user_id: str,
    role: str = "viewer",
) -> dict[str, Any]:
    _ensure_database()

    workspace = _workspace_by_id(workspace_id)

    if workspace is None:
        raise ValueError("Workspace not found.")

    allowed_roles = {
        "owner",
        "admin",
        "editor",
        "viewer",
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
                int(workspace_id),
                str(user_id),
                clean_role,
                timestamp,
                timestamp,
            ),
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
                int(workspace_id),
                str(user_id),
            ),
        ).fetchone()

    result = dict(row)
    result["workspace_name"] = _workspace_name(workspace_id)

    return result


def list_workspace_members(
    workspace_id: int,
) -> list[dict[str, Any]]:
    _ensure_database()

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
            (int(workspace_id),),
        ).fetchall()

    workspace_name = _workspace_name(workspace_id)

    members = []

    for row in rows:
        member = dict(row)
        member["workspace_name"] = workspace_name
        members.append(member)

    return members


def remove_workspace_member(
    workspace_id: int,
    user_id: str,
) -> bool:
    _ensure_database()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM workspace_members
            WHERE workspace_id = ?
              AND user_id = ?
              AND role != 'owner'
            """,
            (
                int(workspace_id),
                str(user_id),
            ),
        )

        connection.commit()

    return cursor.rowcount > 0


# =====================================================
# WORKSPACE INVITATIONS
# =====================================================

def create_invitation(
    workspace_id: int,
    invited_by: str,
    invited_email: str,
    role: str,
    token: str | None = None,
) -> dict[str, Any]:
    _ensure_database()

    workspace = _workspace_by_id(workspace_id)

    if workspace is None:
        raise ValueError("Workspace not found.")

    allowed_roles = {
        "admin",
        "editor",
        "viewer",
    }

    clean_role = (
        role
        if role in allowed_roles
        else "viewer"
    )

    email = _clean_email(invited_email)

    if not email:
        raise ValueError("Invited email is required.")

    invitation_token = (
        str(token).strip()
        if token
        else secrets.token_urlsafe(32)
    )

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT *
            FROM workspace_invitations
            WHERE workspace_id = ?
              AND invited_email = ?
              AND status = 'pending'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (
                int(workspace_id),
                email,
            ),
        ).fetchone()

        if existing is not None:
            result = dict(existing)
            result["workspace_name"] = _workspace_name(workspace_id)
            return result

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
                int(workspace_id),
                str(invited_by),
                email,
                clean_role,
                invitation_token,
                _now(),
            ),
        )

        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM workspace_invitations
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    result = dict(row)
    result["workspace_name"] = _workspace_name(workspace_id)

    return result


def list_invitations(
    invited_email: str,
) -> list[dict[str, Any]]:
    """
    List invitations without joining an SQL workspaces table.

    Workspace names are loaded from workspace_database.json.
    """
    _ensure_database()

    email = _clean_email(invited_email)

    if not email:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM workspace_invitations
            WHERE invited_email = ?
              AND status = 'pending'
            ORDER BY created_at DESC
            """,
            (email,),
        ).fetchall()

    invitations = []

    for row in rows:
        invitation = dict(row)

        invitation["workspace_name"] = _workspace_name(
            invitation["workspace_id"]
        )

        invitations.append(invitation)

    return invitations


def respond_to_invitation(
    invitation_id: int,
    invited_email: str,
    accept: bool,
) -> dict[str, Any] | None:
    _ensure_database()

    email = _clean_email(invited_email)

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
                int(invitation_id),
                email,
            ),
        ).fetchone()

        if invitation is None:
            return None

        workspace_id = int(invitation["workspace_id"])

        if _workspace_by_id(workspace_id) is None:
            raise ValueError(
                "The workspace linked to this invitation no longer exists."
            )

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
                int(invitation_id),
            ),
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
                    workspace_id,
                    email,
                    invitation["role"],
                    timestamp,
                    timestamp,
                ),
            )

        connection.commit()

        updated = connection.execute(
            """
            SELECT *
            FROM workspace_invitations
            WHERE id = ?
            """,
            (int(invitation_id),),
        ).fetchone()

    result = dict(updated)
    result["workspace_name"] = _workspace_name(workspace_id)

    return result


# =====================================================
# DASHBOARD SHARING
# =====================================================

def share_dashboard(
    dashboard_id: int,
    shared_by: str,
    shared_with: str,
    permission: str = "viewer",
) -> dict[str, Any]:
    _ensure_database()

    dashboard = _dashboard_by_id(dashboard_id)

    if dashboard is None:
        raise ValueError("Dashboard not found.")

    allowed_permissions = {
        "editor",
        "viewer",
    }

    clean_permission = (
        permission
        if permission in allowed_permissions
        else "viewer"
    )

    shared_email = _clean_email(shared_with)

    if not shared_email:
        raise ValueError("Shared user email is required.")

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
                shared_by = excluded.shared_by,
                permission = excluded.permission
            """,
            (
                int(dashboard_id),
                str(shared_by),
                shared_email,
                clean_permission,
                _now(),
            ),
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
                int(dashboard_id),
                shared_email,
            ),
        ).fetchone()

    result = dict(row)
    result["dashboard_name"] = _dashboard_name(dashboard_id)

    return result


def list_dashboard_shares(
    dashboard_id: int,
) -> list[dict[str, Any]]:
    _ensure_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM dashboard_shares
            WHERE dashboard_id = ?
            ORDER BY created_at DESC
            """,
            (int(dashboard_id),),
        ).fetchall()

    dashboard_name = _dashboard_name(dashboard_id)

    shares = []

    for row in rows:
        share = dict(row)
        share["dashboard_name"] = dashboard_name
        shares.append(share)

    return shares


# =====================================================
# DASHBOARD COMMENTS
# =====================================================

def add_comment(
    dashboard_id: int,
    user_id: str,
    comment: str,
    parent_id: int | None = None,
) -> dict[str, Any]:
    _ensure_database()

    if _dashboard_by_id(dashboard_id) is None:
        raise ValueError("Dashboard not found.")

    clean_comment = str(comment or "").strip()

    if not clean_comment:
        raise ValueError("Comment cannot be empty.")

    timestamp = _now()

    with get_connection() as connection:
        if parent_id is not None:
            parent = connection.execute(
                """
                SELECT id
                FROM dashboard_comments
                WHERE id = ?
                  AND dashboard_id = ?
                """,
                (
                    int(parent_id),
                    int(dashboard_id),
                ),
            ).fetchone()

            if parent is None:
                raise ValueError("Parent comment not found.")

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
                int(dashboard_id),
                str(user_id),
                clean_comment,
                parent_id,
                timestamp,
                timestamp,
            ),
        )

        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM dashboard_comments
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    result = dict(row)
    result["dashboard_name"] = _dashboard_name(dashboard_id)

    return result


def list_comments(
    dashboard_id: int,
) -> list[dict[str, Any]]:
    _ensure_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM dashboard_comments
            WHERE dashboard_id = ?
            ORDER BY created_at ASC
            """,
            (int(dashboard_id),),
        ).fetchall()

    dashboard_name = _dashboard_name(dashboard_id)

    comments = []

    for row in rows:
        comment = dict(row)
        comment["dashboard_name"] = dashboard_name
        comments.append(comment)

    return comments


def delete_comment(
    comment_id: int,
    user_id: str,
) -> bool:
    _ensure_database()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM dashboard_comments
            WHERE id = ?
              AND user_id = ?
            """,
            (
                int(comment_id),
                str(user_id),
            ),
        )

        connection.commit()

    return cursor.rowcount > 0