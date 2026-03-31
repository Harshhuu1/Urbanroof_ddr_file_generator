# UrbanRoof DDR File Generator

Generate a professional **Main DDR (Detailed Diagnostic Report)** from:
- Inspection report PDF
- Thermal report PDF

The system extracts text + images, synthesizes area-wise diagnostic insights, and exports:
- `main_ddr.pdf`
- `main_ddr.html`
- `main_ddr.md`
- `main_ddr.json`
- image assets under `assets/`

## 1. Features

- Upload workflow via dashboard (inspection + thermal PDFs).
- Structured DDR output with cover, table of contents, and engineering sections.
- Area-wise image linking with labels (`IMAGE 1`, `IMAGE 2`, ...).
- Thermal reading tables (hotspot/coldspot/image ID).
- Severity and distribution charts.
- Priority model:
  - `Critical (Immediate)`
  - `Moderate`
  - `Monitor`
- Estimated impact model:
  - `Low repair effort`
  - `Medium intervention`
  - `Structural risk / high intervention`
- Explicit handling of missing/unclear/conflicting data.

## 2. Project Structure

```text
ddr-generator/
  app.py
  Procfile
  render.yaml
  requirements.txt
  ddr_generator/
    __init__.py
    cli.py
    extractors.py
    models.py
    pipeline.py
    synthesizer.py
    report_renderer.py
    pdf_renderer.py
  templates/
    dashboard.html
    report.html.j2
  static/
    dashboard.css
    report.css
```

## 3. Installation

```bash
pip install -r requirements.txt
```

## 4. Quick Start

### 4.1 Dashboard (Recommended)

```bash
python app.py
```

Open in browser:

`http://127.0.0.1:5000`

Flow:
1. Upload Inspection PDF
2. Upload Thermal PDF
3. Click **Generate Report**
4. Download PDF/HTML/MD/JSON

### 4.2 CLI

```bash
python -m ddr_generator.cli ^
  --inspection "C:\Users\ASUS\Desktop\gdsc\Sample Report.pdf" ^
  --thermal "C:\Users\ASUS\Desktop\gdsc\Thermal Images.pdf" ^
  --output-dir output_pro_plus_v2
```

## 5. Outputs

In selected output directory:
- `main_ddr.pdf` (final professional deliverable)
- `main_ddr.html` (browser preview)
- `main_ddr.md` (plain documentation)
- `main_ddr.json` (machine-readable report data)
- `assets/` (extracted images used in report)

Dashboard runs are stored in:
- `runs/<run_id>/inputs`
- `runs/<run_id>/output`

## 6. Processing Pipeline

1. **Parse source PDFs** (`extractors.py`)
2. **Extract impacted areas and thermal findings**
3. **Extract and deduplicate relevant images**
4. **Synthesize engineering insights** (`synthesizer.py`)
   - root cause
   - severity reasoning
   - priority
   - estimated impact
   - action recommendations
   - image insights
5. **Render report artifacts**
   - HTML/MD/JSON (`report_renderer.py`)
   - Professional PDF (`pdf_renderer.py`)

## 7. Deployment (Render)

This repo already includes `render.yaml` and `Procfile`.

Manual settings (if needed):
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --timeout 300 --workers 1`

Steps:
1. Push repo to GitHub.
2. Create Render Web Service from this repo.
3. Deploy and open generated URL.

## 8. Limitations

- Thermal-to-area mapping is still heuristic when source thermal pages do not contain explicit room labels.
- Engineering diagnosis is rule-based from extracted text; it supports decision-making but is not a replacement for on-site structural audit.
- Very large PDFs may increase processing time and memory use on free hosting tiers.

## 9. Future Enhancements

- Stronger semantic matching between thermal pages and exact room sections.
- Optional cost-band estimation per action.
- Better chart theming and pagination for long reports.
- Persistent storage/database for multi-user dashboard sessions.

## 10. Troubleshooting

- If PDF generation fails, ensure `reportlab` is installed:
  - `pip install reportlab`
- If local server does not open:
  - check `http://127.0.0.1:5000`
  - ensure no port conflict on `5000`
- If cloud deploy fails:
  - verify `requirements.txt` and start command in Render logs.

## 11. Detailed Technical Notes

For deeper architecture notes, see:
- `docs/TECHNICAL_DOCUMENTATION.md`
