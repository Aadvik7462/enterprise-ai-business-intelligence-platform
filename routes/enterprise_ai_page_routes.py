
from __future__ import annotations

import os

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    session,
    url_for
)

from services.data_service import load_dataset
from services.enterprise_ai_database import (
    list_goals,
    list_schedules,
    list_scenarios
)
from services.enterprise_ai_service import (
    calculate_business_health,
    generate_executive_report,
    get_numeric_columns
)


enterprise_ai_page_bp = Blueprint(
    "enterprise_ai_page",
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


@enterprise_ai_page_bp.route(
    "/enterprise-ai/<filename>"
)
def enterprise_ai_page(filename: str):
    user_id = current_user_id()

    if user_id is None:
        return redirect(
            url_for("auth.login")
        )

    filepath = os.path.join(
        current_app.config[
            "UPLOAD_FOLDER"
        ],
        filename
    )

    if not os.path.exists(filepath):
        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    df = load_dataset(filepath)

    return render_template(
        "enterprise_ai.html",
        active_page="enterprise_ai",
        filename=filename,
        numeric_columns=get_numeric_columns(
            df
        ),
        health=calculate_business_health(
            df
        ),
        report=generate_executive_report(
            df,
            filename
        ),
        goals=list_goals(
            user_id,
            filename
        ),
        scenarios=list_scenarios(
            user_id,
            filename
        ),
        schedules=list_schedules(
            user_id
        )
    )
