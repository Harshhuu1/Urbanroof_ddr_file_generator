from __future__ import annotations

import argparse
from pathlib import Path

from ddr_generator.pipeline import generate_report_bundle
from ddr_generator.pdf_renderer import render_pdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Main DDR from inspection + thermal PDF reports.")
    parser.add_argument("--inspection", required=True, type=Path, help="Path to inspection/sample report PDF.")
    parser.add_argument("--thermal", required=True, type=Path, help="Path to thermal report PDF.")
    parser.add_argument(
        "--output-dir",
        default=Path("output"),
        type=Path,
        help="Output folder for generated report and extracted images.",
    )
    parser.add_argument("--title", default="Main DDR (Detailed Diagnostic Report)", help="Report title.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = generate_report_bundle(
        inspection_pdf=args.inspection,
        thermal_pdf=args.thermal,
        output_dir=output_dir,
        report_title=args.title,
        template_dir=Path("templates"),
        static_dir=Path("static"),
    )
    pdf_file = output_dir / "main_ddr.pdf"
    try:
        render_pdf(bundle["report"], pdf_file, output_dir)
        pdf_line = f"\n- {pdf_file}"
    except RuntimeError:
        pdf_line = "\n- PDF skipped (install reportlab to enable PDF output)"

    print(
        f"Generated:\n- {bundle['markdown_file']}\n- {bundle['html_file']}\n- {bundle['json_file']}\n- {bundle['assets_dir']}{pdf_line}"
    )


if __name__ == "__main__":
    main()
