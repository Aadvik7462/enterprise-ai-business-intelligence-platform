from __future__ import annotations

from flask import (
    Blueprint,
    redirect,
    render_template,
    session,
    url_for
)

from services.collaboration_service import (
    list_audit_logs,
    list_invitations,
    list_notifications
)


collaboration_page_bp = Blueprint(
    "collaboration_page",
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


@collaboration_page_bp.route(
    "/collaboration"
)
def collaboration_center():
    user_id = current_user_id()

    if user_id is None:
        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "collaboration.html",
        active_page="collaboration",
        invitations=list_invitations(
            user_id
        ),
        notifications=list_notifications(
            user_id
        ),
        audit_logs=list_audit_logs(
            limit=50
        )
    )
