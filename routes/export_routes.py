import os

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    send_file,
    send_from_directory,
    session,
    url_for
)

from services.data_service import (
    get_dataset_stats,
    load_dataset
)

from services.export_history_service import (
    get_export_history,
    record_export
)

from services.export_service import (
    generate_export_package,
    generate_pdf_report,
    generate_ppt_report
)

from services.insight_service import (
    generate_insights
)

from services.professional_excel_service import (
    generate_professional_excel
)

from services.professional_pdf_service import (
    generate_professional_pdf
)

from services.professional_ppt_service import (
    generate_professional_ppt
)

from services.recommendation_service import (
    generate_recommendations
)


# ==========================================================
# Export Blueprint
# ==========================================================

export_bp = Blueprint(
    "export",
    __name__
)


# ==========================================================
# Helper Functions
# ==========================================================

def _get_dataset_filepath(filename: str) -> str:
    """
    Return the full path of an uploaded dataset.
    """

    upload_folder = current_app.config[
        "UPLOAD_FOLDER"
    ]

    return os.path.join(
        upload_folder,
        filename
    )


def _get_export_folder() -> str:
    """
    Return the export folder and create it when necessary.
    """

    export_folder = os.path.join(
        current_app.root_path,
        "exports"
    )

    os.makedirs(
        export_folder,
        exist_ok=True
    )

    return export_folder


def _prepare_export_data(filepath: str):
    """
    Load the dataset and prepare data shared by export routes.
    """

    df = load_dataset(
        filepath
    )

    stats = get_dataset_stats(
        df,
        filepath
    )

    insights = generate_insights(
        df,
        stats
    )

    recommendations = generate_recommendations(
        stats
    )

    return (
        df,
        stats,
        insights,
        recommendations
    )


def _normalize_export_items(
    items,
    preferred_keys
) -> list[str]:
    """
    Convert insights or recommendations into plain strings.
    """

    normalized_items: list[str] = []

    if items is None:
        return normalized_items

    if isinstance(items, str):
        return [items]

    if isinstance(items, dict):
        items = [items]

    if not isinstance(
        items,
        (
            list,
            tuple,
            set
        )
    ):
        items = [items]

    for item in items:
        if item is None:
            continue

        if isinstance(item, dict):
            value = None

            for key in preferred_keys:
                possible_value = item.get(
                    key
                )

                if possible_value:
                    value = possible_value
                    break

            if value is None:
                value = " | ".join(
                    f"{key}: {item_value}"
                    for key, item_value in item.items()
                    if item_value is not None
                )

            normalized_items.append(
                str(value)
            )

        else:
            normalized_items.append(
                str(item)
            )

    return normalized_items


# ==========================================================
# Export Center Page
# ==========================================================

@export_bp.route(
    "/export-center/<filename>"
)
def export_center(filename):
    """
    Display the professional Export Center.
    """

    if "user" not in session:
        return redirect(
            url_for(
                "auth.login"
            )
        )

    filepath = _get_dataset_filepath(
        filename
    )

    if not os.path.exists(filepath):
        flash(
            "Dataset file not found.",
            "error"
        )

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    try:
        df = load_dataset(
            filepath
        )

        stats = get_dataset_stats(
            df,
            filepath
        )

        history = get_export_history()

        return render_template(
            "export_center.html",
            filename=filename,
            stats=stats,
            export_history=history
        )

    except Exception as error:
        flash(
            (
                "Unable to open Export Center: "
                f"{str(error)}"
            ),
            "error"
        )

        return redirect(
            url_for(
                "executive.executive_dashboard",
                filename=filename
            )
        )


# ==========================================================
# Standard PDF Export
# ==========================================================

@export_bp.route(
    "/export/pdf/<filename>"
)
def export_pdf(filename):
    """
    Generate and download the standard PDF report.
    """

    if "user" not in session:
        return redirect(
            url_for(
                "auth.login"
            )
        )

    filepath = _get_dataset_filepath(
        filename
    )

    if not os.path.exists(filepath):
        flash(
            "File not found.",
            "error"
        )

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    try:
        (
            df,
            stats,
            insights,
            recommendations
        ) = _prepare_export_data(
            filepath
        )

        export_folder = _get_export_folder()

        report_name = generate_pdf_report(
            filename,
            stats,
            insights,
            recommendations,
            export_folder
        )

        return send_from_directory(
            export_folder,
            report_name,
            as_attachment=True
        )

    except Exception as error:
        flash(
            (
                "PDF export failed: "
                f"{str(error)}"
            ),
            "error"
        )

        return redirect(
            url_for(
                "data.preview_dataset",
                filename=filename
            )
        )


# ==========================================================
# Professional PDF Export
# ==========================================================

@export_bp.route(
    "/export/professional-pdf/<filename>"
)
def export_professional_pdf(filename):
    """
    Generate and download the professional PDF report.
    """

    if "user" not in session:
        return redirect(
            url_for(
                "auth.login"
            )
        )

    filepath = _get_dataset_filepath(
        filename
    )

    if not os.path.exists(filepath):
        flash(
            "Dataset file was not found.",
            "error"
        )

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    try:
        (
            df,
            stats,
            insights,
            recommendations
        ) = _prepare_export_data(
            filepath
        )

        export_folder = _get_export_folder()

        safe_name = os.path.splitext(
            filename
        )[0]

        output_filename = (
            f"{safe_name}_"
            "professional_report.pdf"
        )

        output_path = os.path.join(
            export_folder,
            output_filename
        )

        normalized_insights = _normalize_export_items(
            insights,
            preferred_keys=(
                "message",
                "text",
                "insight",
                "description",
                "content"
            )
        )

        normalized_recommendations = _normalize_export_items(
            recommendations,
            preferred_keys=(
                "message",
                "text",
                "recommendation",
                "description",
                "content"
            )
        )

        generate_professional_pdf(
            df=df,
            filename=filename,
            output_path=output_path,
            insights=normalized_insights,
            recommendations=normalized_recommendations
        )

        record_export(
            dataset_name=filename,
            export_format="PDF",
            output_filename=output_filename
        )

        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename
        )

    except Exception as error:
        flash(
            (
                "Professional PDF export failed: "
                f"{str(error)}"
            ),
            "error"
        )

        return redirect(
            url_for(
                "data.preview_dataset",
                filename=filename
            )
        )


# ==========================================================
# Standard PowerPoint Export
# ==========================================================

@export_bp.route(
    "/export/ppt/<filename>"
)
def export_ppt(filename):
    """
    Generate and download the standard PowerPoint report.
    """

    if "user" not in session:
        return redirect(
            url_for(
                "auth.login"
            )
        )

    filepath = _get_dataset_filepath(
        filename
    )

    if not os.path.exists(filepath):
        flash(
            "File not found.",
            "error"
        )

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    try:
        (
            df,
            stats,
            insights,
            recommendations
        ) = _prepare_export_data(
            filepath
        )

        export_folder = _get_export_folder()

        ppt_name = generate_ppt_report(
            filename,
            stats,
            insights,
            recommendations,
            export_folder
        )

        return send_from_directory(
            export_folder,
            ppt_name,
            as_attachment=True
        )

    except Exception as error:
        flash(
            (
                "PPT export failed: "
                f"{str(error)}"
            ),
            "error"
        )

        return redirect(
            url_for(
                "data.preview_dataset",
                filename=filename
            )
        )


# ==========================================================
# Professional PowerPoint Export
# ==========================================================

@export_bp.route(
    "/export/professional-ppt/<filename>"
)
def export_professional_ppt(filename):
    """
    Generate and download the professional PowerPoint report.
    """

    if "user" not in session:
        return redirect(
            url_for(
                "auth.login"
            )
        )

    filepath = _get_dataset_filepath(
        filename
    )

    if not os.path.exists(filepath):
        flash(
            "Dataset file not found.",
            "error"
        )

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    try:
        (
            df,
            stats,
            insights,
            recommendations
        ) = _prepare_export_data(
            filepath
        )

        export_folder = _get_export_folder()

        safe_name = os.path.splitext(
            filename
        )[0]

        output_filename = (
            f"{safe_name}_"
            "professional_report.pptx"
        )

        output_path = os.path.join(
            export_folder,
            output_filename
        )

        generate_professional_ppt(
            df=df,
            filename=filename,
            stats=stats,
            insights=insights,
            recommendations=recommendations,
            output_path=output_path
        )

        record_export(
            dataset_name=filename,
            export_format="PPT",
            output_filename=output_filename
        )

        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename
        )

    except Exception as error:
        flash(
            (
                "Professional PPT export failed: "
                f"{str(error)}"
            ),
            "error"
        )

        return redirect(
            url_for(
                "executive.executive_dashboard",
                filename=filename
            )
        )


# ==========================================================
# Professional Excel Export
# ==========================================================

@export_bp.route(
    "/export/professional-excel/<filename>"
)
def export_professional_excel(filename):
    """
    Generate and download the professional Excel report.
    """

    if "user" not in session:
        return redirect(
            url_for(
                "auth.login"
            )
        )

    filepath = _get_dataset_filepath(
        filename
    )

    if not os.path.exists(filepath):
        flash(
            "Dataset file not found.",
            "error"
        )

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    try:
        (
            df,
            stats,
            insights,
            recommendations
        ) = _prepare_export_data(
            filepath
        )

        export_folder = _get_export_folder()

        safe_name = os.path.splitext(
            filename
        )[0]

        output_filename = (
            f"{safe_name}_"
            "professional_report.xlsx"
        )

        output_path = os.path.join(
            export_folder,
            output_filename
        )

        generated_file = generate_professional_excel(
            df=df,
            filename=filename,
            stats=stats,
            insights=insights,
            recommendations=recommendations,
            output_path=output_path
        )

        record_export(
            dataset_name=filename,
            export_format="EXCEL",
            output_filename=output_filename
        )

        return send_file(
            generated_file,
            as_attachment=True,
            download_name=output_filename
        )

    except Exception as error:
        flash(
            (
                "Professional Excel export failed: "
                f"{str(error)}"
            ),
            "error"
        )

        return redirect(
            url_for(
                "executive.executive_dashboard",
                filename=filename
            )
        )


# ==========================================================
# Complete ZIP Export Package
# ==========================================================

@export_bp.route(
    "/export/package/<filename>"
)
def export_package(filename):
    """
    Generate and download the complete ZIP export package.
    """

    if "user" not in session:
        return redirect(
            url_for(
                "auth.login"
            )
        )

    filepath = _get_dataset_filepath(
        filename
    )

    if not os.path.exists(filepath):
        flash(
            "File not found.",
            "error"
        )

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    try:
        (
            df,
            stats,
            insights,
            recommendations
        ) = _prepare_export_data(
            filepath
        )

        export_folder = _get_export_folder()

        zip_name = generate_export_package(
            filename=filename,
            source_filepath=filepath,
            stats=stats,
            insights=insights,
            recommendations=recommendations,
            export_folder=export_folder
        )

        record_export(
            dataset_name=filename,
            export_format="ZIP",
            output_filename=zip_name
        )

        return send_from_directory(
            export_folder,
            zip_name,
            as_attachment=True
        )

    except Exception as error:
        flash(
            (
                "Export package failed: "
                f"{str(error)}"
            ),
            "error"
        )

        return redirect(
            url_for(
                "executive.executive_dashboard",
                filename=filename
            )
        )