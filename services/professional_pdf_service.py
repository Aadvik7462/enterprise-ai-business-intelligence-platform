from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle
)


def _safe_number(value: Any) -> str:
    try:
        numeric_value = float(value)

        return f"{numeric_value:,.2f}"

    except (
        TypeError,
        ValueError
    ):
        return str(value)


def _build_dataset_metrics(
    df: pd.DataFrame
) -> dict[str, Any]:
    total_rows = int(
        len(df)
    )

    total_columns = int(
        len(df.columns)
    )

    missing_values = int(
        df.isna()
        .sum()
        .sum()
    )

    duplicate_rows = int(
        df.duplicated()
        .sum()
    )

    total_cells = max(
        1,
        total_rows
        * total_columns
    )

    quality_score = round(
        (
            1
            - missing_values
            / total_cells
        )
        * 100,
        2
    )

    numeric_columns = [
        str(column)
        for column in df.select_dtypes(
            include="number"
        ).columns
    ]

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
        "quality_score": quality_score,
        "numeric_columns": numeric_columns
    }


def _build_numeric_summary(
    df: pd.DataFrame,
    numeric_columns: list[str]
) -> list[list[str]]:
    rows = [
        [
            "Column",
            "Total",
            "Average",
            "Minimum",
            "Maximum"
        ]
    ]

    for column in numeric_columns[:12]:
        series = pd.to_numeric(
            df[column],
            errors="coerce"
        ).dropna()

        if series.empty:
            continue

        rows.append([
            column,
            _safe_number(
                series.sum()
            ),
            _safe_number(
                series.mean()
            ),
            _safe_number(
                series.min()
            ),
            _safe_number(
                series.max()
            )
        ])

    return rows


def _add_page_number(
    canvas,
    document
) -> None:
    canvas.saveState()

    page_number = canvas.getPageNumber()

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.setFillColor(
        colors.HexColor(
            "#64748B"
        )
    )

    canvas.drawRightString(
        document.pagesize[0]
        - 15 * mm,
        10 * mm,
        f"Page {page_number}"
    )

    canvas.drawString(
        15 * mm,
        10 * mm,
        "AI Business Intelligence Platform"
    )

    canvas.restoreState()


def generate_professional_pdf(
    df: pd.DataFrame,
    filename: str,
    output_path: str,
    insights: list[str] | None = None,
    recommendations: list[str] | None = None
) -> str:
    os.makedirs(
        os.path.dirname(
            output_path
        ),
        exist_ok=True
    )

    metrics = _build_dataset_metrics(
        df
    )

    document = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=17 * mm,
        bottomMargin=18 * mm,
        title=(
            f"Executive BI Report - "
            f"{filename}"
        ),
        author=(
            "AI Business Intelligence "
            "Platform"
        )
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=29,
        textColor=colors.HexColor(
            "#0F172A"
        ),
        alignment=TA_CENTER,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor(
            "#64748B"
        ),
        alignment=TA_CENTER,
        spaceAfter=20
    )

    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor(
            "#1D4ED8"
        ),
        spaceBefore=10,
        spaceAfter=10
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor(
            "#334155"
        )
    )

    story = []

    story.append(
        Paragraph(
            "Executive Business Intelligence Report",
            title_style
        )
    )

    story.append(
        Paragraph(
            (
                f"Dataset: {filename}<br/>"
                f"Generated: "
                f"{datetime.now().strftime('%d %B %Y, %I:%M %p')}"
            ),
            subtitle_style
        )
    )

    story.append(
        Paragraph(
            "Dataset Overview",
            section_style
        )
    )

    overview_data = [
        [
            "Total Rows",
            "Total Columns",
            "Missing Values",
            "Duplicate Rows",
            "Quality Score"
        ],
        [
            f"{metrics['total_rows']:,}",
            f"{metrics['total_columns']:,}",
            f"{metrics['missing_values']:,}",
            f"{metrics['duplicate_rows']:,}",
            f"{metrics['quality_score']}%"
        ]
    ]

    overview_table = Table(
        overview_data,
        colWidths=[
            48 * mm,
            48 * mm,
            48 * mm,
            48 * mm,
            48 * mm
        ]
    )

    overview_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#0F172A"
                )
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "BACKGROUND",
                (0, 1),
                (-1, 1),
                colors.HexColor(
                    "#EFF6FF"
                )
            ),
            (
                "TEXTCOLOR",
                (0, 1),
                (-1, 1),
                colors.HexColor(
                    "#1D4ED8"
                )
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, -1),
                "Helvetica-Bold"
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                10
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#CBD5E1"
                )
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                11
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                11
            )
        ])
    )

    story.append(
        overview_table
    )

    story.append(
        Spacer(
            1,
            14
        )
    )

    story.append(
        Paragraph(
            "Numeric KPI Summary",
            section_style
        )
    )

    numeric_summary = (
        _build_numeric_summary(
            df,
            metrics[
                "numeric_columns"
            ]
        )
    )

    if len(numeric_summary) > 1:
        numeric_table = Table(
            numeric_summary,
            repeatRows=1,
            colWidths=[
                65 * mm,
                43 * mm,
                43 * mm,
                43 * mm,
                43 * mm
            ]
        )

        numeric_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#2563EB"
                    )
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    "Helvetica"
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "RIGHT"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#CBD5E1"
                    )
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor(
                            "#F8FAFC"
                        )
                    ]
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                )
            ])
        )

        story.append(
            numeric_table
        )

    else:
        story.append(
            Paragraph(
                (
                    "No numeric columns were "
                    "available for KPI analysis."
                ),
                body_style
            )
        )

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "AI Insights",
            section_style
        )
    )

    insight_items = (
        insights
        or [
            (
                "The report was generated "
                "successfully from the uploaded "
                "dataset."
            )
        ]
    )

    for index, insight in enumerate(
        insight_items,
        start=1
    ):
        story.append(
            Paragraph(
                (
                    f"<b>{index}.</b> "
                    f"{insight}"
                ),
                body_style
            )
        )

        story.append(
            Spacer(
                1,
                7
            )
        )

    story.append(
        Spacer(
            1,
            10
        )
    )

    story.append(
        Paragraph(
            "Business Recommendations",
            section_style
        )
    )

    recommendation_items = (
        recommendations
        or [
            (
                "Monitor the most important KPIs "
                "regularly and investigate major "
                "variations."
            ),
            (
                "Resolve missing values before "
                "using the dataset for critical "
                "business decisions."
            ),
            (
                "Use forecasting and scenario "
                "analysis for forward-looking "
                "planning."
            )
        ]
    )

    for index, recommendation in enumerate(
        recommendation_items,
        start=1
    ):
        story.append(
            Paragraph(
                (
                    f"<b>{index}.</b> "
                    f"{recommendation}"
                ),
                body_style
            )
        )

        story.append(
            Spacer(
                1,
                7
            )
        )

    document.build(
        story,
        onFirstPage=_add_page_number,
        onLaterPages=_add_page_number
    )

    return output_path