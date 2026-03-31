from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from ddr_generator.extractors import (
    extract_images,
    parse_impacted_areas,
    parse_inspection_metadata,
    parse_thermal_findings,
    read_pdf_pages,
)
from ddr_generator.report_renderer import render_html, render_markdown
from ddr_generator.synthesizer import build_ddr_report


def generate_report_bundle(
    inspection_pdf: Path,
    thermal_pdf: Path,
    output_dir: Path,
    report_title: str,
    template_dir: Path,
    static_dir: Path,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_static_dir = output_dir / "static"
    output_static_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(static_dir / "report.css", output_static_dir / "report.css")

    inspection_pages = read_pdf_pages(inspection_pdf)
    thermal_pages = read_pdf_pages(thermal_pdf)
    inspection_metadata = parse_inspection_metadata(inspection_pages)

    areas = parse_impacted_areas(inspection_pages)
    thermal_findings = parse_thermal_findings(thermal_pages)
    inspection_images = extract_images(inspection_pdf, assets_dir, "inspection")
    thermal_images = extract_images(thermal_pdf, assets_dir, "thermal")
    _to_relative_assets(inspection_images, output_dir)
    _to_relative_assets(thermal_images, output_dir)

    report = build_ddr_report(
        areas=areas,
        thermal_findings=thermal_findings,
        inspection_images=inspection_images,
        thermal_images=thermal_images,
        inspection_metadata=inspection_metadata,
    )

    markdown_file = output_dir / "main_ddr.md"
    html_file = output_dir / "main_ddr.html"
    json_file = output_dir / "main_ddr.json"

    render_markdown(report, markdown_file)
    render_html(report, template_dir, html_file, report_title)
    json_file.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    return {
        "report": report,
        "markdown_file": markdown_file,
        "html_file": html_file,
        "json_file": json_file,
        "assets_dir": assets_dir,
    }


def _to_relative_assets(asset_list, output_dir: Path) -> None:
    for asset in asset_list:
        asset.relative_path = Path(asset.relative_path).relative_to(output_dir).as_posix()
