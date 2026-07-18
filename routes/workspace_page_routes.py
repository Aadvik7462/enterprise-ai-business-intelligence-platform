from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    session,
    url_for
)

from services.workspace_service import (
    ensure_personal_workspace,
    get_workspace,
    list_saved_dashboards,
    list_workspaces
)


workspace_page_bp = Blueprint(
    "workspace_page",
    __name__
)


def get_current_user_id() -> str | None:
    """
    Return the current authenticated user identifier.

    Supports:
    - session["user"] as a string
    - session["user"] as a dictionary
    """

    user = session.get("user")

    if user is None:
        return None

    if isinstance(user, dict):
        user_id = (
            user.get("id")
            or user.get("email")
            or user.get("username")
            or user.get("name")
        )

        if user_id is None:
            return None

        return str(user_id).strip() or None

    return str(user).strip() or None


def login_redirect():
    """
    Redirect unauthenticated users to the login page.
    """

    return redirect(
        url_for("auth.login")
    )


@workspace_page_bp.route("/workspaces")
def workspace_page():
    """
    Render the main Workspace Management page.
    """

    owner_id = get_current_user_id()

    if owner_id is None:
        return login_redirect()

    ensure_personal_workspace(
        owner_id
    )

    workspaces = list_workspaces(
        owner_id
    )

    dashboards = list_saved_dashboards(
        owner_id
    )

    total_workspaces = len(
        workspaces
    )

    total_dashboards = len(
        dashboards
    )

    favorite_count = sum(
        1
        for dashboard in dashboards
        if dashboard.get(
            "is_favorite"
        )
    )

    default_workspace = next(
        (
            workspace
            for workspace in workspaces
            if workspace.get(
                "is_default"
            )
        ),
        None
    )

    return render_template(
        "workspaces.html",
        workspaces=workspaces,
        dashboards=dashboards,
        total_workspaces=total_workspaces,
        total_dashboards=total_dashboards,
        favorite_count=favorite_count,
        default_workspace=default_workspace
    )


@workspace_page_bp.route(
    "/workspaces/<int:workspace_id>"
)
def workspace_detail_page(
    workspace_id: int
):
    """
    Render one workspace and all dashboards saved inside it.
    """

    owner_id = get_current_user_id()

    if owner_id is None:
        return login_redirect()

    workspace = get_workspace(
        workspace_id=workspace_id,
        owner_id=owner_id
    )

    if workspace is None:
        abort(
            404,
            description="Workspace not found."
        )

    dashboards = list_saved_dashboards(
        owner_id=owner_id,
        workspace_id=workspace_id
    )

    total_dashboards = len(
        dashboards
    )

    favorite_count = sum(
        1
        for dashboard in dashboards
        if dashboard.get(
            "is_favorite"
        )
    )

    dashboard_type_counts = {
        "executive": 0,
        "analytics": 0,
        "forecast": 0,
        "preview": 0
    }

    for dashboard in dashboards:
        dashboard_type = str(
            dashboard.get(
                "dashboard_type",
                "executive"
            )
        ).strip().lower()

        if dashboard_type not in dashboard_type_counts:
            dashboard_type_counts[
                dashboard_type
            ] = 0

        dashboard_type_counts[
            dashboard_type
        ] += 1

    recent_dashboard = (
        dashboards[0]
        if dashboards
        else None
    )

    return render_template(
        "workspace_detail.html",
        workspace=workspace,
        dashboards=dashboards,
        total_dashboards=total_dashboards,
        favorite_count=favorite_count,
        dashboard_type_counts=dashboard_type_counts,
        recent_dashboard=recent_dashboard,
        active_page="workspaces"
    )