from __future__ import annotations

from flask import (
    Blueprint,
    jsonify,
    request,
    session
)

from services.workspace_service import (
    create_workspace,
    delete_saved_dashboard,
    delete_workspace,
    ensure_personal_workspace,
    get_saved_dashboard,
    get_workspace,
    list_saved_dashboards,
    list_workspaces,
    save_dashboard,
    set_default_workspace,
    toggle_dashboard_favorite,
    update_saved_dashboard,
    update_workspace
)


workspace_bp = Blueprint(
    "workspace",
    __name__
)


def get_current_user_id() -> str | None:
    """
    Return the current authenticated user identifier.

    Your project currently stores the logged-in user in session["user"].
    This helper supports both a plain string and a dictionary.
    """

    user = session.get("user")

    if user is None:
        return None

    if isinstance(user, dict):
        return str(
            user.get("id")
            or user.get("email")
            or user.get("username")
            or ""
        ).strip() or None

    return str(user).strip() or None


def unauthorized_response():
    return jsonify({
        "success": False,
        "message": (
            "Your session has expired. "
            "Please log in again."
        )
    }), 401


def parse_integer(
    value,
    field_name: str
) -> int:
    try:
        return int(value)

    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be a valid number."
        )


# =====================================================
# WORKSPACE ROUTES
# =====================================================

@workspace_bp.route(
    "/api/workspaces",
    methods=["GET"]
)
def get_workspaces():
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    ensure_personal_workspace(
        owner_id
    )

    workspaces = list_workspaces(
        owner_id
    )

    return jsonify({
        "success": True,
        "workspaces": workspaces
    })


@workspace_bp.route(
    "/api/workspaces",
    methods=["POST"]
)
def create_workspace_route():
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    request_data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    try:
        workspace = create_workspace(
            owner_id=owner_id,
            name=request_data.get(
                "name",
                ""
            ),
            description=request_data.get(
                "description",
                ""
            ),
            workspace_type=request_data.get(
                "workspace_type",
                "personal"
            ),
            is_default=bool(
                request_data.get(
                    "is_default",
                    False
                )
            )
        )

        return jsonify({
            "success": True,
            "message": (
                "Workspace created successfully."
            ),
            "workspace": workspace
        }), 201

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "message": (
                "Workspace creation failed: "
                f"{str(error)}"
            )
        }), 500


@workspace_bp.route(
    "/api/workspaces/<int:workspace_id>",
    methods=["GET"]
)
def get_workspace_route(
    workspace_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    workspace = get_workspace(
        workspace_id=workspace_id,
        owner_id=owner_id
    )

    if workspace is None:
        return jsonify({
            "success": False,
            "message": "Workspace not found."
        }), 404

    dashboards = list_saved_dashboards(
        owner_id=owner_id,
        workspace_id=workspace_id
    )

    return jsonify({
        "success": True,
        "workspace": workspace,
        "dashboards": dashboards
    })


@workspace_bp.route(
    "/api/workspaces/<int:workspace_id>",
    methods=["PUT"]
)
def update_workspace_route(
    workspace_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    request_data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    try:
        workspace = update_workspace(
            workspace_id=workspace_id,
            owner_id=owner_id,
            name=request_data.get(
                "name",
                ""
            ),
            description=request_data.get(
                "description",
                ""
            ),
            workspace_type=request_data.get(
                "workspace_type",
                "personal"
            )
        )

        return jsonify({
            "success": True,
            "message": (
                "Workspace updated successfully."
            ),
            "workspace": workspace
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "message": (
                "Workspace update failed: "
                f"{str(error)}"
            )
        }), 500


@workspace_bp.route(
    "/api/workspaces/<int:workspace_id>",
    methods=["DELETE"]
)
def delete_workspace_route(
    workspace_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    try:
        deleted = delete_workspace(
            workspace_id=workspace_id,
            owner_id=owner_id
        )

        if not deleted:
            return jsonify({
                "success": False,
                "message": "Workspace not found."
            }), 404

        return jsonify({
            "success": True,
            "message": (
                "Workspace deleted successfully."
            )
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "message": (
                "Workspace deletion failed: "
                f"{str(error)}"
            )
        }), 500


@workspace_bp.route(
    "/api/workspaces/<int:workspace_id>/default",
    methods=["POST"]
)
def set_default_workspace_route(
    workspace_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    try:
        workspace = set_default_workspace(
            workspace_id=workspace_id,
            owner_id=owner_id
        )

        return jsonify({
            "success": True,
            "message": (
                "Default workspace updated."
            ),
            "workspace": workspace
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "message": (
                "Unable to update the default workspace: "
                f"{str(error)}"
            )
        }), 500


# =====================================================
# SAVED DASHBOARD ROUTES
# =====================================================

@workspace_bp.route(
    "/api/workspaces/<int:workspace_id>/dashboards",
    methods=["GET"]
)
def get_workspace_dashboards(
    workspace_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    workspace = get_workspace(
        workspace_id=workspace_id,
        owner_id=owner_id
    )

    if workspace is None:
        return jsonify({
            "success": False,
            "message": "Workspace not found."
        }), 404

    favorites_only = (
        request.args.get(
            "favorites",
            ""
        ).lower()
        in {
            "1",
            "true",
            "yes"
        }
    )

    dashboards = list_saved_dashboards(
        owner_id=owner_id,
        workspace_id=workspace_id,
        favorites_only=favorites_only
    )

    return jsonify({
        "success": True,
        "workspace": workspace,
        "dashboards": dashboards
    })


@workspace_bp.route(
    "/api/workspaces/<int:workspace_id>/dashboards",
    methods=["POST"]
)
def save_dashboard_route(
    workspace_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    request_data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    try:
        dashboard = save_dashboard(
            workspace_id=workspace_id,
            owner_id=owner_id,
            name=request_data.get(
                "name",
                ""
            ),
            filename=request_data.get(
                "filename",
                ""
            ),
            dashboard_type=request_data.get(
                "dashboard_type",
                "executive"
            ),
            description=request_data.get(
                "description",
                ""
            ),
            dashboard_state=request_data.get(
                "dashboard_state",
                {}
            ),
            thumbnail=request_data.get(
                "thumbnail",
                ""
            )
        )

        return jsonify({
            "success": True,
            "message": (
                "Dashboard saved successfully."
            ),
            "dashboard": dashboard
        }), 201

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "message": (
                "Dashboard save failed: "
                f"{str(error)}"
            )
        }), 500


@workspace_bp.route(
    "/api/dashboards",
    methods=["GET"]
)
def get_all_saved_dashboards():
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    workspace_id = request.args.get(
        "workspace_id"
    )

    parsed_workspace_id = None

    if workspace_id:
        try:
            parsed_workspace_id = parse_integer(
                workspace_id,
                "workspace_id"
            )

        except ValueError as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 400

    favorites_only = (
        request.args.get(
            "favorites",
            ""
        ).lower()
        in {
            "1",
            "true",
            "yes"
        }
    )

    dashboards = list_saved_dashboards(
        owner_id=owner_id,
        workspace_id=parsed_workspace_id,
        favorites_only=favorites_only
    )

    return jsonify({
        "success": True,
        "dashboards": dashboards
    })


@workspace_bp.route(
    "/api/dashboards/<int:dashboard_id>",
    methods=["GET"]
)
def get_saved_dashboard_route(
    dashboard_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    dashboard = get_saved_dashboard(
        dashboard_id=dashboard_id,
        owner_id=owner_id
    )

    if dashboard is None:
        return jsonify({
            "success": False,
            "message": (
                "Saved dashboard not found."
            )
        }), 404

    return jsonify({
        "success": True,
        "dashboard": dashboard
    })


@workspace_bp.route(
    "/api/dashboards/<int:dashboard_id>",
    methods=["PUT"]
)
def update_saved_dashboard_route(
    dashboard_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    request_data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    try:
        dashboard = update_saved_dashboard(
            dashboard_id=dashboard_id,
            owner_id=owner_id,
            name=request_data.get(
                "name",
                ""
            ),
            description=request_data.get(
                "description",
                ""
            )
        )

        return jsonify({
            "success": True,
            "message": (
                "Dashboard updated successfully."
            ),
            "dashboard": dashboard
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "message": (
                "Dashboard update failed: "
                f"{str(error)}"
            )
        }), 500


@workspace_bp.route(
    "/api/dashboards/<int:dashboard_id>",
    methods=["DELETE"]
)
def delete_saved_dashboard_route(
    dashboard_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    try:
        deleted = delete_saved_dashboard(
            dashboard_id=dashboard_id,
            owner_id=owner_id
        )

        if not deleted:
            return jsonify({
                "success": False,
                "message": (
                    "Saved dashboard not found."
                )
            }), 404

        return jsonify({
            "success": True,
            "message": (
                "Dashboard deleted successfully."
            )
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": (
                "Dashboard deletion failed: "
                f"{str(error)}"
            )
        }), 500


@workspace_bp.route(
    "/api/dashboards/<int:dashboard_id>/favorite",
    methods=["POST"]
)
def toggle_dashboard_favorite_route(
    dashboard_id: int
):
    owner_id = get_current_user_id()

    if owner_id is None:
        return unauthorized_response()

    try:
        dashboard = toggle_dashboard_favorite(
            dashboard_id=dashboard_id,
            owner_id=owner_id
        )

        return jsonify({
            "success": True,
            "message": (
                "Favorite status updated."
            ),
            "dashboard": dashboard
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "message": (
                "Favorite update failed: "
                f"{str(error)}"
            )
        }), 500