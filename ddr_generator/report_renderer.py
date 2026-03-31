from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ddr_generator.models import DDRReport


def render_markdown(report: DDRReport, output_file: Path) -> None:
    lines: list[str] = ["# Main DDR (Detailed Diagnostic Report)", ""]
    lines.append("## Report Header")
    lines.append(f"- Inspection Date: {report.report_header.get('inspection_date', 'Not Available')}")
    lines.append(f"- Inspected By: {report.report_header.get('inspected_by', 'Not Available')}")
    lines.append(f"- Property Type: {report.report_header.get('property_type', 'Not Available')}")
    lines.append(f"- Floors: {report.report_header.get('floors', 'Not Available')}")
    lines.append("")

    lines.append("## 1. Property Issue Summary")
    for item in report.property_issue_summary:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 2. Area-wise Observations")
    if not report.area_observations:
        lines.append("- Not Available")
    for index, area in enumerate(report.area_observations, start=1):
        lines.append(f"### 2.{index} {area.area}")
        lines.append(f"- Negative Side Observation: {area.negative_observation}")
        lines.append(f"- Positive Side Observation: {area.positive_observation}")
        lines.append(f"- Evidence Note: Derived from extracted inspection text and linked thermal pages.")
        lines.append("- Inspection Images:")
        if area.inspection_images:
            for image in area.inspection_images:
                lines.append(f"  - ![{image.caption}]({image.relative_path})")
        else:
            lines.append("  - Image Not Available")
        lines.append("- Thermal Findings:")
        if area.thermal_findings:
            for finding in area.thermal_findings:
                lines.append(
                    f"  - Page {finding.page_number}: hotspot {finding.hotspot_c} C, coldspot {finding.coldspot_c} C, "
                    f"image {finding.image_name}, observation: {finding.observation}"
                )
                if finding.image:
                    lines.append(f"    - ![{finding.image.caption}]({finding.image.relative_path})")
                else:
                    lines.append("    - Image Not Available")
        else:
            lines.append("  - Not Available")
        lines.append("")

    lines.append("## 3. Probable Root Cause")
    for row in report.probable_root_cause_section:
        lines.append(f"- {row}")
    lines.append("")

    lines.append("## 4. Severity Assessment (with reasoning)")
    for row in report.severity_assessment_section:
        lines.append(f"- {row}")
    lines.append("")

    lines.append("## 5. Recommended Actions")
    for row in report.recommended_actions_section:
        lines.append(f"- {row}")
    lines.append("")

    lines.append("## 6. Additional Notes")
    for note in report.additional_notes:
        lines.append(f"- {note}")
    lines.append("")

    lines.append("## 7. Missing or Unclear Information")
    if report.missing_or_unclear_information:
        for item in report.missing_or_unclear_information:
            lines.append(f"- {item}")
    else:
        lines.append("- Not Available")
    lines.append("")

    lines.append("## Conflicts")
    if report.conflicts:
        for item in report.conflicts:
            lines.append(f"- {item}")
    else:
        lines.append("- Not Available")
    lines.append("")

    output_file.write_text("\n".join(lines), encoding="utf-8")


def render_html(report: DDRReport, template_dir: Path, output_file: Path, report_title: str) -> None:
    environment = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template("report.html.j2")
    html = template.render(report=report, report_title=report_title)
    output_file.write_text(html, encoding="utf-8")
