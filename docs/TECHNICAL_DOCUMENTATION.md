# Technical Documentation

## A. Objective

The project converts two raw source documents:
- inspection report PDF
- thermal report PDF

into a structured DDR package suitable for client-facing review and engineering planning.

## B. Core Design Principles

- Deterministic and reproducible processing (no mandatory external LLM dependency).
- Explicit handling of uncertainty (`Not Available` and conflict logs).
- Traceable evidence through image mapping and thermal page references.
- Modular architecture for easy extension.

## C. Module Responsibilities

### `app.py`
- Flask dashboard entrypoint.
- Handles uploads and run lifecycle.
- Exposes download endpoints for generated artifacts.

### `ddr_generator/pipeline.py`
- Orchestrates full report generation.
- Coordinates extraction, synthesis, and rendering.

### `ddr_generator/extractors.py`
- Reads PDF text by page.
- Parses:
  - inspection metadata
  - impacted area observations
  - thermal findings (hotspot/coldspot/image ID)
- Extracts image binaries with basic filtering and deduplication.

### `ddr_generator/synthesizer.py`
- Computes per-area diagnostics:
  - probable root cause
  - severity with reasoning
  - priority level
  - estimated impact
  - recommended actions
  - image insights
- Aggregates report-level sections and summaries.

### `ddr_generator/report_renderer.py`
- Renders markdown and HTML report outputs.

### `ddr_generator/pdf_renderer.py`
- Produces professional PDF with:
  - cover page
  - table of contents
  - disclaimer/about page
  - chart section
  - area-wise diagnostic sections
  - image labels
  - thermal tables
  - final action matrix

## D. Data Model

Key dataclasses in `models.py`:
- `ImageAsset`
- `ThermalFinding`
- `AreaObservation`
- `DDRReport`

The final `DDRReport` object acts as a single source of truth for all renderers.

## E. Inference & Scoring Strategy

The synthesis layer uses rule-based logic:
- keyword patterns (`damp`, `seep`, `crack`, `tile`, `plumbing`, etc.)
- thermal delta ranges (`hotspot - coldspot`)

Outputs:
- severity (`High`, `Medium`, `Low`)
- priority (`Critical`, `Moderate`, `Monitor`)
- impact category (`Low`, `Medium`, `Structural risk`)

This keeps behavior explainable and audit-friendly.

## F. Web Endpoints

- `GET /` dashboard
- `POST /generate` upload + run
- `GET /result/<run_id>` run view
- `GET /download/<run_id>/<artifact>` artifact download
- `GET /runs/<run_id>/<path:subpath>` serve generated files

## G. Generated Artifact Contract

For each run:
- `main_ddr.pdf`
- `main_ddr.html`
- `main_ddr.md`
- `main_ddr.json`
- `assets/*`

## H. Deployment Notes

- Production startup: `gunicorn app:app --timeout 300 --workers 1`
- Render configuration is included via `render.yaml`.
- Free-tier instances may sleep and cold-start.

## I. Known Constraints

- Thermal room mapping is not fully semantic when room labels are absent in source thermal pages.
- Highly non-standard PDF templates may require regex/parser updates.
- Current storage is filesystem-based; horizontal scaling would need shared object storage.

## J. Extension Guide

Recommended next additions:
- semantic area-matching for thermal pages
- configurable repair cost estimation
- persistent report history with DB
- unit tests for extraction and scoring rules
