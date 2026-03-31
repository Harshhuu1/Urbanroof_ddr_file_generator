from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from ddr_generator.models import DDRReport

try:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Image as RLImage,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:  # pragma: no cover
    A4 = None


def render_pdf(report: DDRReport, output_file: Path, base_dir: Path) -> None:
    if A4 is None:
        raise RuntimeError("PDF export requires reportlab. Install dependencies from requirements.txt.")

    styles = getSampleStyleSheet()
    cover_title = ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        alignment=1,
        fontSize=26,
        leading=30,
        textColor=colors.HexColor("#0f172a"),
    )
    cover_subtitle = ParagraphStyle(
        name="CoverSubtitle",
        parent=styles["Normal"],
        alignment=1,
        fontSize=12,
        textColor=colors.HexColor("#334155"),
        leading=16,
    )
    h1 = ParagraphStyle(
        name="H1",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#0b3b3a"),
        spaceBefore=8,
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        name="H2",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=6,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        name="Body",
        parent=styles["Normal"],
        fontSize=9.6,
        leading=13,
        textColor=colors.HexColor("#111827"),
    )
    bullet = ParagraphStyle(
        name="Bullet",
        parent=body,
        leftIndent=14,
        bulletIndent=6,
        spaceBefore=1,
        spaceAfter=1,
    )
    caption = ParagraphStyle(
        name="Caption",
        parent=styles["Italic"],
        fontSize=8.5,
        textColor=colors.HexColor("#334155"),
        leading=11,
    )

    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="Main DDR",
        author="DDR Generator",
    )

    story = []
    _build_cover(story, report, cover_title, cover_subtitle, body)
    story.append(PageBreak())

    _build_toc(story, h1, body)
    story.append(PageBreak())

    _build_about_and_disclaimer(story, report, h1, body, bullet)
    story.append(PageBreak())

    _build_summary_and_charts(story, report, h1, h2, body, bullet)
    story.append(PageBreak())

    image_counter = 1
    story.append(Paragraph("2. Area-wise Observations", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#94a3b8")))
    story.append(Spacer(1, 0.2 * cm))
    for idx, area in enumerate(report.area_observations, start=1):
        story.append(Paragraph(f"2.{idx} {area.area}", h2))
        grid_data = [
            ["Negative Side Observation", area.negative_observation],
            ["Positive Side Observation", area.positive_observation],
            ["Probable Root Cause", area.probable_root_cause],
            ["Severity", f"{area.severity} - {area.severity_reasoning}"],
            ["Priority Level", area.priority_level],
            ["Estimated Impact", area.estimated_impact],
        ]
        table = Table(grid_data, colWidths=[5.2 * cm, 11.2 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.12 * cm))

        story.append(Paragraph("Recommended Actions:", body))
        for action in area.recommended_actions:
            story.append(Paragraph(f"- {action}", bullet))

        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph("Inspection & Thermal Image Evidence:", body))
        images = area.inspection_images[:2] + [f.image for f in area.thermal_findings[:2] if f.image]
        if not images:
            story.append(Paragraph("- Image Not Available", bullet))
        for image_asset in images:
            if image_asset is None:
                continue
            image_path = base_dir / image_asset.relative_path
            if not image_path.exists():
                story.append(Paragraph(f"- IMAGE {image_counter}: Image Not Available", bullet))
                image_counter += 1
                continue
            _append_image(story, image_path, width_cm=7.8)
            story.append(
                Paragraph(
                    f"IMAGE {image_counter}: {image_asset.caption} | Linked Section: {area.area}",
                    caption,
                )
            )
            image_counter += 1
        if area.image_insights:
            story.append(Spacer(1, 0.06 * cm))
            story.append(Paragraph("Image Insight:", body))
            for insight in area.image_insights:
                story.append(Paragraph(f"- {insight}", bullet))

        thermal_rows = []
        for finding in area.thermal_findings[:4]:
            thermal_rows.append(
                [
                    f"Page {finding.page_number}",
                    f"Hotspot {finding.hotspot_c} C",
                    f"Coldspot {finding.coldspot_c} C",
                    finding.image_name,
                ]
            )
        if thermal_rows:
            story.append(Spacer(1, 0.08 * cm))
            story.append(Paragraph("Thermal Reading Table", body))
            thermal_table = Table(
                [["Page", "Hotspot", "Coldspot", "Thermal Image ID"]] + thermal_rows,
                colWidths=[2.2 * cm, 3.8 * cm, 3.8 * cm, 6.6 * cm],
            )
            thermal_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#cbd5e1")),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#94a3b8")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(thermal_table)

        story.append(Spacer(1, 0.28 * cm))

    story.append(PageBreak())
    _build_final_sections(story, report, h1, h2, body, bullet)
    story.append(PageBreak())
    _build_action_matrix(story, report, h1, body)

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)


def _build_cover(story: list, report: DDRReport, title_style: ParagraphStyle, sub_style: ParagraphStyle, body: ParagraphStyle) -> None:
    story.append(Spacer(1, 2.8 * cm))
    story.append(Paragraph("UrbanRoof Diagnostic Services", sub_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("MAIN DDR", title_style))
    story.append(Paragraph("Detailed Diagnostic Report", title_style))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph("Property Condition Assessment Report", sub_style))
    story.append(Spacer(1, 1.3 * cm))

    details = [
        ["Inspection Date", report.report_header.get("inspection_date", "Not Available")],
        ["Inspected By", report.report_header.get("inspected_by", "Not Available")],
        ["Property Type", report.report_header.get("property_type", "Not Available")],
        ["Floors", report.report_header.get("floors", "Not Available")],
        ["Report Generated On", datetime.now().strftime("%d %b %Y")],
    ]
    table = Table(details, colWidths=[5.2 * cm, 8.8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#0f766e")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.6 * cm))
    story.append(
        Paragraph(
            "Prepared for diagnostic decision support. This report is generated from uploaded inspection and thermal documents.",
            body,
        )
    )


def _build_toc(story: list, h1: ParagraphStyle, body: ParagraphStyle) -> None:
    story.append(Paragraph("Table of Contents", h1))
    rows = [
        ["1.", "Property Issue Summary", "4"],
        ["2.", "Area-wise Observations", "5 onwards"],
        ["3.", "Probable Root Cause", "final section"],
        ["4.", "Severity Assessment (with reasoning)", "final section"],
        ["5.", "Recommended Actions", "final section"],
        ["6.", "Additional Notes", "final section"],
        ["7.", "Missing or Unclear Information", "final section"],
        ["8.", "Conflicts", "final section"],
        ["9.", "Priority Action Matrix", "final section"],
    ]
    table = Table([["No.", "Section", "Page"]] + rows, colWidths=[1.2 * cm, 12 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#cbd5e1")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Page references are approximate and may vary based on image count.", body))


def _build_about_and_disclaimer(
    story: list,
    report: DDRReport,
    h1: ParagraphStyle,
    body: ParagraphStyle,
    bullet: ParagraphStyle,
) -> None:
    story.append(Paragraph("About This Report", h1))
    story.append(
        Paragraph(
            "This DDR consolidates textual observations from the inspection document and thermal patterns from the thermal report. "
            "Findings are organized area-wise to support engineering follow-up and repair planning.",
            body,
        )
    )
    story.append(Spacer(1, 0.18 * cm))
    story.append(Paragraph("Data & Information Disclaimer", h1))
    for note in report.additional_notes:
        story.append(Paragraph(f"- {note}", bullet))
    story.append(Paragraph("- Hidden structural members and concealed service lines were not directly inspected in this automated process.", bullet))
    story.append(Paragraph("- Any structural intervention must be validated by site engineer before execution.", bullet))


def _build_summary_and_charts(
    story: list,
    report: DDRReport,
    h1: ParagraphStyle,
    h2: ParagraphStyle,
    body: ParagraphStyle,
    bullet: ParagraphStyle,
) -> None:
    story.append(Paragraph("1. Property Issue Summary", h1))
    for point in report.property_issue_summary:
        story.append(Paragraph(f"- {point}", bullet))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Severity Distribution Chart", h2))
    severity_counts = Counter(a.severity for a in report.area_observations)
    if not severity_counts:
        story.append(Paragraph("Not Available", body))
        return

    pie_drawing = Drawing(15.5 * cm, 7.2 * cm)
    pie = Pie()
    pie.x = 0.3 * cm
    pie.y = 0.8 * cm
    pie.width = 4.9 * cm
    pie.height = 4.9 * cm
    data = [severity_counts.get("High", 0), severity_counts.get("Medium", 0), severity_counts.get("Low", 0)]
    total = max(1, sum(data))
    pie.data = data
    pie.labels = ["High", "Medium", "Low"]
    pie.sideLabels = True
    pie.simpleLabels = 0
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = colors.HexColor("#dc2626")
    pie.slices[1].fillColor = colors.HexColor("#f59e0b")
    pie.slices[2].fillColor = colors.HexColor("#16a34a")
    pie_drawing.add(pie)
    pie_drawing.add(String(0.3 * cm, 6.4 * cm, "Severity Mix", fontSize=10))

    bar = VerticalBarChart()
    bar.x = 7.3 * cm
    bar.y = 1.0 * cm
    bar.height = 4.9 * cm
    bar.width = 7.8 * cm
    bar.data = [
        data
    ]
    bar.categoryAxis.categoryNames = ["High", "Medium", "Low"]
    bar.valueAxis.valueMin = 0
    bar.valueAxis.valueMax = max(1, max(bar.data[0]) + 1)
    bar.barLabels.nudge = 8
    bar.barLabels.fontSize = 8
    bar.barLabelFormat = "%d"
    bar.barLabels.boxAnchor = "ne"
    bar.bars[0].fillColor = colors.HexColor("#0f766e")
    pie_drawing.add(bar)
    story.append(pie_drawing)
    distribution_table = Table(
        [
            ["Band", "Count", "Share"],
            ["High", str(data[0]), f"{(data[0] / total) * 100:.1f}%"],
            ["Medium", str(data[1]), f"{(data[1] / total) * 100:.1f}%"],
            ["Low", str(data[2]), f"{(data[2] / total) * 100:.1f}%"],
        ],
        colWidths=[4 * cm, 3 * cm, 3 * cm],
    )
    distribution_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#cbd5e1")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#94a3b8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(distribution_table)


def _build_final_sections(
    story: list,
    report: DDRReport,
    h1: ParagraphStyle,
    h2: ParagraphStyle,
    body: ParagraphStyle,
    bullet: ParagraphStyle,
) -> None:
    story.append(Paragraph("3. Probable Root Cause", h1))
    for row in report.probable_root_cause_section:
        story.append(Paragraph(f"- {row}", bullet))

    story.append(Spacer(1, 0.12 * cm))
    story.append(Paragraph("4. Severity Assessment (with reasoning)", h1))
    for row in report.severity_assessment_section:
        story.append(Paragraph(f"- {row}", bullet))

    story.append(Spacer(1, 0.12 * cm))
    story.append(Paragraph("5. Recommended Actions", h1))
    for row in report.recommended_actions_section:
        story.append(Paragraph(f"- {row}", bullet))

    story.append(Spacer(1, 0.12 * cm))
    story.append(Paragraph("6. Additional Notes", h1))
    for note in report.additional_notes:
        story.append(Paragraph(f"- {note}", bullet))

    story.append(Spacer(1, 0.12 * cm))
    story.append(Paragraph("7. Missing or Unclear Information", h1))
    missing = report.missing_or_unclear_information or ["Not Available"]
    for line in missing:
        story.append(Paragraph(f"- {line}", bullet))

    story.append(Spacer(1, 0.12 * cm))
    story.append(Paragraph("8. Conflicts", h1))
    conflicts = report.conflicts or ["Not Available"]
    for line in conflicts:
        story.append(Paragraph(f"- {line}", bullet))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("End of Report", h2))
    story.append(Paragraph("Prepared by automated DDR engine for review and engineering validation.", body))


def _build_action_matrix(story: list, report: DDRReport, h1: ParagraphStyle, body: ParagraphStyle) -> None:
    story.append(Paragraph("9. Priority Action Matrix", h1))
    rows = [["Area", "Priority", "Estimated Impact", "Primary Root Cause", "Immediate Action"]]
    for area in report.area_observations:
        primary_action = area.recommended_actions[0] if area.recommended_actions else "Not Available"
        rows.append(
            [
                area.area,
                area.priority_level,
                area.estimated_impact,
                area.probable_root_cause,
                primary_action,
            ]
        )
    cell = ParagraphStyle(
        name="MatrixCell",
        parent=body,
        fontSize=7.6,
        leading=9.1,
    )
    rows_wrapped = [rows[0]]
    for area in report.area_observations:
        primary_action = next((x for x in area.recommended_actions if not x.startswith("Priority Plan:")), "Not Available")
        rows_wrapped.append(
            [
                Paragraph(area.area, cell),
                Paragraph(area.priority_level, cell),
                Paragraph(area.estimated_impact, cell),
                Paragraph(area.probable_root_cause, cell),
                Paragraph(primary_action, cell),
            ]
        )

    table = Table(rows_wrapped, colWidths=[2.4 * cm, 2.8 * cm, 2.8 * cm, 4.8 * cm, 4.8 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#94a3b8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Use this matrix as execution order input for contractor planning.", body))


def _append_image(story: list, image_path: Path, width_cm: float) -> None:
    img = RLImage(str(image_path))
    target_width = width_cm * cm
    scale = target_width / img.imageWidth
    img.drawWidth = target_width
    img.drawHeight = img.imageHeight * scale
    story.append(img)
    story.append(Spacer(1, 0.12 * cm))


def _draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawString(doc.leftMargin, 0.65 * cm, "UrbanRoof DDR | Confidential")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.65 * cm, f"Page {doc.page}")
    canvas.restoreState()
