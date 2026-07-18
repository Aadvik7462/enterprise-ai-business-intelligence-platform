import os

from flask import (
    Blueprint,
    request,
    jsonify,
    session,
    current_app
)

from services.ai_chart_service import (
    generate_chart_from_question
)

from services.data_service import (
    load_dataset,
    get_dataset_stats
)

from services.enterprise_copilot_service import (
    answer_copilot_question
)


ai_bp = Blueprint(
    "ai",
    __name__
)


@ai_bp.route(
    "/api/copilot/<filename>",
    methods=["POST"]
)
def copilot_query(filename):
    if "user" not in session:
        return jsonify({
            "success": False,
            "response_type": "text",
            "answer": (
                "Your session has expired. "
                "Please log in again."
            )
        }), 401

    filepath = os.path.join(
        current_app.config[
            "UPLOAD_FOLDER"
        ],
        filename
    )

    if not os.path.exists(filepath):
        return jsonify({
            "success": False,
            "response_type": "text",
            "answer": (
                "The selected dataset "
                "could not be found."
            )
        }), 404

    request_data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    question = str(
        request_data.get(
            "question",
            ""
        )
    ).strip()

    if not question:
        return jsonify({
            "success": False,
            "response_type": "text",
            "answer": (
                "Please enter a question."
            )
        }), 400

    try:
        df = load_dataset(
            filepath
        )

        stats = get_dataset_stats(
            df,
            filepath
        )

        normalized_question = (
            question.lower()
        )

        chart_keywords = [
            "show",
            "chart",
            "plot",
            "graph",
            "visualize",
            "display",
            "bar chart",
            "line chart",
            "pie chart",
            "donut chart",
            "scatter"
        ]

        is_chart_request = any(
            keyword in normalized_question
            for keyword in chart_keywords
        )

        if is_chart_request:
            chart_response = (
                generate_chart_from_question(
                    question=question,
                    df=df
                )
            )

            if chart_response.get(
                "success"
            ):
                return jsonify({
                    "success": True,
                    "response_type": "chart",
                    "answer": (
                        chart_response.get(
                            "message",
                            "Chart generated successfully."
                        )
                    ),
                    "chart": (
                        chart_response.get(
                            "chart"
                        )
                    )
                })

        copilot_response = (
            answer_copilot_question(
                df=df,
                question=question
            )
        )

        return jsonify(
            copilot_response
        )

    except Exception as error:
        current_app.logger.exception(
            "BI Copilot analysis failed."
        )

        return jsonify({
            "success": False,
            "response_type": "text",
            "answer": (
                "Unable to analyze the dataset: "
                f"{str(error)}"
            )
        }), 500