from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from ddr_generator.pdf_renderer import render_pdf
from ddr_generator.pipeline import generate_report_bundle

BASE_DIR = Path(__file__).parent.resolve()
RUNS_DIR = BASE_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = "ddr-local-secret"
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024

ALLOWED_SUFFIX = {".pdf"}
RUNS: dict[str, dict[str, str]] = {}


@app.get("/")
def index():
    latest_run = None
    if RUNS:
        latest_id = next(reversed(RUNS))
        latest_run = {"id": latest_id, **RUNS[latest_id]}
    return render_template("dashboard.html", latest_run=latest_run)


@app.route("/generate", methods=["GET", "POST"])
def generate():
    if request.method == "GET":
        flash("Use the upload form on the home page to generate a report.", "error")
        return redirect(url_for("index"))

    inspection_file = request.files.get("inspection_pdf")
    thermal_file = request.files.get("thermal_pdf")
    title = (request.form.get("report_title") or "Main DDR (Detailed Diagnostic Report)").strip()

    if not inspection_file or not thermal_file:
        flash("Please upload both Inspection and Thermal PDFs.", "error")
        return redirect(url_for("index"))

    inspection_name = secure_filename(inspection_file.filename or "")
    thermal_name = secure_filename(thermal_file.filename or "")
    if Path(inspection_name).suffix.lower() not in ALLOWED_SUFFIX or Path(thermal_name).suffix.lower() not in ALLOWED_SUFFIX:
        flash("Only .pdf files are supported.", "error")
        return redirect(url_for("index"))

    run_id = uuid.uuid4().hex[:12]
    run_dir = RUNS_DIR / run_id
    input_dir = run_dir / "inputs"
    output_dir = run_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)

    inspection_path = input_dir / inspection_name
    thermal_path = input_dir / thermal_name
    inspection_file.save(inspection_path)
    thermal_file.save(thermal_path)

    bundle = generate_report_bundle(
        inspection_pdf=inspection_path,
        thermal_pdf=thermal_path,
        output_dir=output_dir,
        report_title=title,
        template_dir=BASE_DIR / "templates",
        static_dir=BASE_DIR / "static",
    )

    pdf_status = "ready"
    pdf_file = output_dir / "main_ddr.pdf"
    try:
        render_pdf(bundle["report"], pdf_file, output_dir)
    except RuntimeError:
        pdf_status = "unavailable"

    RUNS[run_id] = {
        "html": "main_ddr.html",
        "markdown": "main_ddr.md",
        "json": "main_ddr.json",
        "pdf": "main_ddr.pdf",
        "pdf_status": pdf_status,
    }
    return redirect(url_for("result", run_id=run_id))


@app.get("/result/<run_id>")
def result(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        abort(404)
    return render_template("dashboard.html", latest_run={"id": run_id, **run})


@app.get("/download/<run_id>/<artifact>")
def download(run_id: str, artifact: str):
    run = RUNS.get(run_id)
    if not run:
        abort(404)
    if artifact not in {"html", "markdown", "json", "pdf"}:
        abort(404)
    if artifact == "pdf" and run.get("pdf_status") != "ready":
        flash("PDF renderer is unavailable. Install dependencies and regenerate.", "error")
        return redirect(url_for("result", run_id=run_id))

    file_name = run[artifact]
    file_path = RUNS_DIR / run_id / "output" / file_name
    if not file_path.exists():
        abort(404)
    return send_file(file_path, as_attachment=True, download_name=file_name)


@app.get("/runs/<run_id>/<path:subpath>")
def serve_run_file(run_id: str, subpath: str):
    file_path = RUNS_DIR / run_id / "output" / subpath
    if not file_path.exists():
        abort(404)
    return send_file(file_path)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
