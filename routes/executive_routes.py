import os
from services.ai_report_service import generate_executive_report
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    current_app
)

from services.data_service import (
    load_dataset,
    get_dataset_stats,
    get_column_summary,
    get_numeric_summary,
    get_chart_data
)

from services.insight_service import generate_insights
from services.recommendation_service import generate_recommendations
from services.chart_service import (
    generate_auto_charts,
    generate_plotly_charts
)


executive_bp = Blueprint("executive", __name__)


@executive_bp.route("/executive-dashboard/<filename>")
def executive_dashboard(filename):
    if "user" not in session:
        return redirect(url_for("auth.login"))

    filepath = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

    if not os.path.exists(filepath):
        flash("File not found", "error")
        return redirect(url_for("dashboard.dashboard"))

    try:
        df = load_dataset(filepath)

        stats = get_dataset_stats(df, filepath)
        column_summary = get_column_summary(df)
        numeric_summary = get_numeric_summary(df)
        chart_data = get_chart_data(df)
        insights = generate_insights(df, stats)
        recommendations = generate_recommendations(stats)
        executive_report = generate_executive_report(df, stats)
        charts = generate_auto_charts(df)
        plotly_charts = generate_plotly_charts(df)

        preview_data = df.head(10).to_html(
            classes="data-table",
            index=False,
            border=0
        )

        return render_template(
            "executive_dashboard.html",
            filename=filename,
            stats=stats,
            column_summary=column_summary,
            numeric_summary=numeric_summary,
            chart_data=chart_data,
            insights=insights,
            recommendations=recommendations,
            executive_report=executive_report,
            charts=charts,
            plotly_charts=plotly_charts,
            preview_data=preview_data,
            cleaning_report=session.get("cleaning_report"),
            active_page="executive"
        )

    except Exception as e:
        flash(f"Error loading executive dashboard: {str(e)}", "error")
        return redirect(url_for("dashboard.dashboard"))