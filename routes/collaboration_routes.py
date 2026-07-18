from __future__ import annotations

import secrets

from flask import (
    Blueprint,
    jsonify,
    request,
    session
)

from services.collaboration_service import (
    add_comment,
    create_invitation,
    create_notification,
    delete_comment,
    list_audit_logs,
    list_comments,
    list_dashboard_shares,
    list_invitations,
    list_notifications,
    list_workspace_members,
    log_activity,
    mark_notification_read,
    remove_workspace_member,
    respond_to_invitation,
    share_dashboard
)

from services.workspace_service import (
    get_saved_dashboard,
    get_workspace
)


collaboration_bp = Blueprint(
    "collaboration",
    __name__
)


def current_user_id() -> str | None:
    user = session.get("user")

    if user is None:
        return None

    if isinstance(user, dict):
        return str(
            user.get("id")
            or user.get("email")
            or user.get("username")
            or user.get("name")
            or ""
        ).strip() or None

    return str(user).strip() or None


def unauthorized():
    return jsonify({
        "success": False,
        "message": (
            "Your session has expired. "
            "Please log in again."
        )
    }), 401


@collaboration_bp.route(
    "/api/workspaces/<int:workspace_id>/members",
    methods=["GET"]
)
def get_members(workspace_id: int):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    workspace = get_workspace(
        workspace_id=workspace_id,
        owner_id=user_id
    )

    if workspace is None:
        return jsonify({
            "success": False,
            "message": "Workspace not found."
        }), 404

    return jsonify({
        "success": True,
        "members": list_workspace_members(
            workspace_id
        )
    })


@collaboration_bp.route(
    "/api/workspaces/<int:workspace_id>/invite",
    methods=["POST"]
)
def invite_member(workspace_id: int):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    workspace = get_workspace(
        workspace_id=workspace_id,
        owner_id=user_id
    )

    if workspace is None:
        return jsonify({
            "success": False,
            "message": "Workspace not found."
        }), 404

    payload = (
        request.get_json(
            silent=True
        )
        or {}
    )

    email = str(
        payload.get(
            "email",
            ""
        )
    ).strip().lower()

    role = str(
        payload.get(
            "role",
            "viewer"
        )
    ).strip().lower()

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required."
        }), 400

    invitation = create_invitation(
        workspace_id=workspace_id,
        invited_by=user_id,
        invited_email=email,
        role=role,
        token=secrets.token_urlsafe(24)
    )

    create_notification(
        user_id=email,
        notification_type="workspace_invitation",
        title="Workspace invitation",
        message=(
            f"You were invited to "
            f"{workspace['name']} as {role}."
        ),
        related_type="workspace",
        related_id=workspace_id
    )

    log_activity(
        user_id=user_id,
        action="invite_member",
        entity_type="workspace",
        entity_id=workspace_id,
        details=f"Invited {email} as {role}"
    )

    return jsonify({
        "success": True,
        "message": (
            "Workspace invitation created."
        ),
        "invitation": invitation
    }), 201


@collaboration_bp.route(
    "/api/invitations",
    methods=["GET"]
)
def get_invitations():
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    return jsonify({
        "success": True,
        "invitations": list_invitations(
            user_id
        )
    })


@collaboration_bp.route(
    "/api/invitations/<int:invitation_id>/respond",
    methods=["POST"]
)
def respond_invitation(invitation_id: int):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    payload = (
        request.get_json(
            silent=True
        )
        or {}
    )

    accept = bool(
        payload.get(
            "accept",
            False
        )
    )

    invitation = respond_to_invitation(
        invitation_id=invitation_id,
        invited_email=user_id,
        accept=accept
    )

    if invitation is None:
        return jsonify({
            "success": False,
            "message": (
                "Invitation was not found."
            )
        }), 404

    log_activity(
        user_id=user_id,
        action=(
            "accept_invitation"
            if accept
            else "reject_invitation"
        ),
        entity_type="workspace",
        entity_id=invitation[
            "workspace_id"
        ]
    )

    return jsonify({
        "success": True,
        "message": (
            "Invitation accepted."
            if accept
            else "Invitation rejected."
        ),
        "invitation": invitation
    })


@collaboration_bp.route(
    "/api/workspaces/<int:workspace_id>/members/<path:member_id>",
    methods=["DELETE"]
)
def remove_member(
    workspace_id: int,
    member_id: str
):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    workspace = get_workspace(
        workspace_id=workspace_id,
        owner_id=user_id
    )

    if workspace is None:
        return jsonify({
            "success": False,
            "message": "Workspace not found."
        }), 404

    removed = remove_workspace_member(
        workspace_id,
        member_id
    )

    if not removed:
        return jsonify({
            "success": False,
            "message": (
                "Member not found or owner "
                "cannot be removed."
            )
        }), 400

    log_activity(
        user_id=user_id,
        action="remove_member",
        entity_type="workspace",
        entity_id=workspace_id,
        details=f"Removed {member_id}"
    )

    return jsonify({
        "success": True,
        "message": "Member removed."
    })


@collaboration_bp.route(
    "/api/dashboards/<int:dashboard_id>/shares",
    methods=["GET", "POST"]
)
def dashboard_shares(dashboard_id: int):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    dashboard = get_saved_dashboard(
        dashboard_id=dashboard_id,
        owner_id=user_id
    )

    if dashboard is None:
        return jsonify({
            "success": False,
            "message": "Dashboard not found."
        }), 404

    if request.method == "GET":
        return jsonify({
            "success": True,
            "shares": list_dashboard_shares(
                dashboard_id
            )
        })

    payload = (
        request.get_json(
            silent=True
        )
        or {}
    )

    email = str(
        payload.get(
            "email",
            ""
        )
    ).strip().lower()

    permission = str(
        payload.get(
            "permission",
            "viewer"
        )
    ).strip().lower()

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required."
        }), 400

    share = share_dashboard(
        dashboard_id=dashboard_id,
        shared_by=user_id,
        shared_with=email,
        permission=permission
    )

    create_notification(
        user_id=email,
        notification_type="dashboard_shared",
        title="Dashboard shared",
        message=(
            f"{dashboard['name']} was shared "
            f"with you as {permission}."
        ),
        related_type="dashboard",
        related_id=dashboard_id
    )

    log_activity(
        user_id=user_id,
        action="share_dashboard",
        entity_type="dashboard",
        entity_id=dashboard_id,
        details=f"Shared with {email}"
    )

    return jsonify({
        "success": True,
        "message": "Dashboard shared.",
        "share": share
    }), 201


@collaboration_bp.route(
    "/api/dashboards/<int:dashboard_id>/comments",
    methods=["GET", "POST"]
)
def dashboard_comments(dashboard_id: int):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    if request.method == "GET":
        return jsonify({
            "success": True,
            "comments": list_comments(
                dashboard_id
            )
        })

    payload = (
        request.get_json(
            silent=True
        )
        or {}
    )

    try:
        comment = add_comment(
            dashboard_id=dashboard_id,
            user_id=user_id,
            comment=str(
                payload.get(
                    "comment",
                    ""
                )
            ),
            parent_id=payload.get(
                "parent_id"
            )
        )

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    log_activity(
        user_id=user_id,
        action="add_comment",
        entity_type="dashboard",
        entity_id=dashboard_id
    )

    return jsonify({
        "success": True,
        "message": "Comment added.",
        "comment": comment
    }), 201


@collaboration_bp.route(
    "/api/comments/<int:comment_id>",
    methods=["DELETE"]
)
def remove_comment(comment_id: int):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    deleted = delete_comment(
        comment_id,
        user_id
    )

    if not deleted:
        return jsonify({
            "success": False,
            "message": "Comment not found."
        }), 404

    return jsonify({
        "success": True,
        "message": "Comment deleted."
    })


@collaboration_bp.route(
    "/api/notifications",
    methods=["GET"]
)
def notifications():
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    unread_only = (
        request.args.get(
            "unread",
            ""
        ).lower()
        in {
            "1",
            "true",
            "yes"
        }
    )

    return jsonify({
        "success": True,
        "notifications": list_notifications(
            user_id,
            unread_only=unread_only
        )
    })


@collaboration_bp.route(
    "/api/notifications/<int:notification_id>/read",
    methods=["POST"]
)
def read_notification(notification_id: int):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    updated = mark_notification_read(
        notification_id,
        user_id
    )

    if not updated:
        return jsonify({
            "success": False,
            "message": (
                "Notification not found."
            )
        }), 404

    return jsonify({
        "success": True,
        "message": (
            "Notification marked as read."
        )
    })


@collaboration_bp.route(
    "/api/audit-logs",
    methods=["GET"]
)
def audit_logs():
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    entity_type = request.args.get(
        "entity_type"
    )

    entity_id = request.args.get(
        "entity_id"
    )

    parsed_entity_id = None

    if entity_id:
        try:
            parsed_entity_id = int(
                entity_id
            )
        except ValueError:
            return jsonify({
                "success": False,
                "message": (
                    "entity_id must be numeric."
                )
            }), 400

    return jsonify({
        "success": True,
        "logs": list_audit_logs(
            entity_type=entity_type,
            entity_id=parsed_entity_id
        )
    })
