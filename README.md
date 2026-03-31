# DDR Generator

Generate a structured **Main DDR (Detailed Diagnostic Report)** from:
- Inspection Report PDF (sample/site inspection details)
- Thermal Report PDF (thermal readings/images)

The tool extracts text and images from source PDFs, merges observations, handles missing/conflicting data, and outputs:
- `main_ddr.md`
- `main_ddr.html`
- `main_ddr.json`
- `main_ddr.pdf`
- extracted assets (`output/assets/`)

## Project Structure

```text
ddr-generator/
  ddr_generator/
    cli.py
    extractors.py
    models.py
    report_renderer.py
    synthesizer.py
  templates/
    report.html.j2
  static/
    report.css
  requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m ddr_generator.cli ^
  --inspection "C:\Users\ASUS\Desktop\gdsc\Sample Report.pdf" ^
  --thermal "C:\Users\ASUS\Desktop\gdsc\Thermal Images.pdf" ^
  --output-dir output
```

## Web Dashboard (Upload + PDF Download)

```bash
python app.py
```

Then open:

`http://127.0.0.1:5000`

From the dashboard:
- Upload inspection PDF
- Upload thermal PDF
- Click **Generate Report**
- Download generated PDF/HTML/JSON/Markdown

## Go Live (Render)

1. Push this repo to GitHub.
2. Open Render and create a new **Web Service** from your GitHub repo.
3. Render will auto-detect `render.yaml`, or use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --timeout 300 --workers 1`
4. Deploy and open the generated Render URL.

## What It Handles

- Extracts impacted-area observations from the inspection report.
- Extracts thermal hotspot/coldspot values and thermal image IDs.
- Extracts image assets from both reports and places them in DDR sections.
- Explicitly marks unavailable details as `Not Available`.
- Flags data conflicts where mixed indicators are present.

## Notes

- This is a deterministic pipeline (no external LLM required), so it is reproducible and easy to explain in interviews.
- You can adapt parsing rules in `extractors.py` for new report formats.
