
from __future__ import annotations

import os

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    request,
    session
)

from services.data_service import load_dataset
from services.enterprise_ai_database import (
    create_goal,
    create_schedule,
    delete_goal,
    delete_schedule,
    list_goals,
    list_scenarios,
    list_schedules,
    save_scenario
)
from services.enterprise_ai_service import (
    build_scenario_comparison,
    calculate_business_health,
    evaluate_goal_progress,
    generate_executive_report,
    generate_kpi_narration,
    get_numeric_columns,
    render_executive_report_html,
    run_what_if_analysis
)


enterprise_ai_bp = Blueprint(
    "enterprise_ai",
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
        "message": "Please log in again."
    }), 401


def get_dataframe(filename: str):
    filepath = os.path.join(
        current_app.config[
            "UPLOAD_FOLDER"
        ],
        filename
    )

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            "Dataset file was not found."
        )

    return load_dataset(filepath)


@enterprise_ai_bp.route(
    "/api/enterprise-ai/<filename>/health",
    methods=["GET"]
)
def business_health(filename: str):
    if current_user_id() is None:
        return unauthorized()

    try:
        return jsonify(
            calculate_business_health(
                get_dataframe(filename)
            )
        )
    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@enterprise_ai_bp.route(
    "/api/enterprise-ai/<filename>/narration",
    methods=["POST"]
)
def kpi_narration(filename: str):
    if current_user_id() is None:
        return unauthorized()

    payload = request.get_json(
        silent=True
    ) or {}

    try:
        result = generate_kpi_narration(
            get_dataframe(filename),
            str(
                payload.get(
                    "metric_column",
                    ""
                )
            )
        )

        return jsonify(result)

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@enterprise_ai_bp.route(
    "/api/enterprise-ai/<filename>/what-if",
    methods=["POST"]
)
def what_if(filename: str):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    payload = request.get_json(
        silent=True
    ) or {}

    try:
        result = run_what_if_analysis(
            get_dataframe(filename),
            str(
                payload.get(
                    "metric_column",
                    ""
                )
            ),
            float(
                payload.get(
                    "change_percent",
                    0
                )
            )
        )

        return jsonify(result)

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@enterprise_ai_bp.route(
    "/api/enterprise-ai/<filename>/scenarios",
    methods=["GET", "POST"]
)
def scenarios(filename: str):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    if request.method == "GET":
        return jsonify({
            "success": True,
            "scenarios": list_scenarios(
                user_id,
                filename
            )
        })

    payload = request.get_json(
        silent=True
    ) or {}

    try:
        metric_column = str(
            payload.get(
                "metric_column",
                ""
            )
        )

        result = build_scenario_comparison(
            get_dataframe(filename),
            metric_column,
            float(
                payload.get(
                    "optimistic_percent",
                    10
                )
            ),
            float(
                payload.get(
                    "expected_percent",
                    0
                )
            ),
            float(
                payload.get(
                    "pessimistic_percent",
                    -10
                )
            )
        )

        if result.get("success"):
            for scenario in result[
                "scenarios"
            ]:
                save_scenario(
                    owner_id=user_id,
                    filename=filename,
                    scenario_name=scenario[
                        "name"
                    ],
                    metric_column=metric_column,
                    change_percent=scenario[
                        "change_percent"
                    ],
                    base_value=result[
                        "base_total"
                    ],
                    projected_value=scenario[
                        "projected_total"
                    ]
                )

        return jsonify(result)

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@enterprise_ai_bp.route(
    "/api/enterprise-ai/<filename>/goals",
    methods=["GET", "POST"]
)
def goals(filename: str):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    if request.method == "GET":
        goals_list = list_goals(
            user_id,
            filename
        )

        for goal in goals_list:
            goal["progress"] = (
                evaluate_goal_progress(
                    goal["current_value"],
                    goal["target_value"]
                )
            )

        return jsonify({
            "success": True,
            "goals": goals_list
        })

    payload = request.get_json(
        silent=True
    ) or {}

    try:
        goal = create_goal(
            owner_id=user_id,
            filename=filename,
            metric_column=str(
                payload.get(
                    "metric_column",
                    ""
                )
            ),
            goal_name=str(
                payload.get(
                    "goal_name",
                    ""
                )
            ).strip(),
            target_value=float(
                payload.get(
                    "target_value",
                    0
                )
            ),
            current_value=float(
                payload.get(
                    "current_value",
                    0
                )
            ),
            due_date=str(
                payload.get(
                    "due_date",
                    ""
                )
            )
        )

        goal["progress"] = (
            evaluate_goal_progress(
                goal["current_value"],
                goal["target_value"]
            )
        )

        return jsonify({
            "success": True,
            "goal": goal
        }), 201

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400


@enterprise_ai_bp.route(
    "/api/enterprise-ai/goals/<int:goal_id>",
    methods=["DELETE"]
)
def remove_goal(goal_id: int):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    deleted = delete_goal(
        goal_id,
        user_id
    )

    return jsonify({
        "success": deleted,
        "message": (
            "Goal deleted."
            if deleted
            else "Goal not found."
        )
    }), (
        200
        if deleted
        else 404
    )


@enterprise_ai_bp.route(
    "/api/enterprise-ai/schedules",
    methods=["GET", "POST"]
)
def schedules():
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    if request.method == "GET":
        return jsonify({
            "success": True,
            "schedules": list_schedules(
                user_id
            )
        })

    payload = request.get_json(
        silent=True
    ) or {}

    try:
        schedule = create_schedule(
            owner_id=user_id,
            filename=str(
                payload.get(
                    "filename",
                    ""
                )
            ),
            report_name=str(
                payload.get(
                    "report_name",
                    ""
                )
            ).strip(),
            frequency=str(
                payload.get(
                    "frequency",
                    "weekly"
                )
            ),
            delivery_email=str(
                payload.get(
                    "delivery_email",
                    ""
                )
            ),
            export_format=str(
                payload.get(
                    "export_format",
                    "html"
                )
            )
        )

        return jsonify({
            "success": True,
            "schedule": schedule,
            "message": (
                "Report schedule saved. "
                "Delivery execution can be connected "
                "to a production task runner later."
            )
        }), 201

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400


@enterprise_ai_bp.route(
    "/api/enterprise-ai/schedules/<int:schedule_id>",
    methods=["DELETE"]
)
def remove_schedule(schedule_id: int):
    user_id = current_user_id()

    if user_id is None:
        return unauthorized()

    deleted = delete_schedule(
        schedule_id,
        user_id
    )

    return jsonify({
        "success": deleted,
        "message": (
            "Schedule deleted."
            if deleted
            else "Schedule not found."
        )
    }), (
        200
        if deleted
        else 404
    )


@enterprise_ai_bp.route(
    "/api/enterprise-ai/<filename>/report",
    methods=["GET"]
)
def executive_report(filename: str):
    if current_user_id() is None:
        return unauthorized()

    metric_column = request.args.get(
        "metric_column"
    )

    try:
        report = generate_executive_report(
            get_dataframe(filename),
            filename,
            metric_column
        )

        html = render_executive_report_html(
            report
        )

        response = make_response(html)

        response.headers[
            "Content-Type"
        ] = "text/html; charset=utf-8"

        response.headers[
            "Content-Disposition"
        ] = (
            f'attachment; filename="'
            f'{filename}_executive_ai_report.html"'
        )

        return response

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500
