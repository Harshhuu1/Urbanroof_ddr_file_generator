from __future__ import annotations

import hashlib
import io
import logging
import re
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from ddr_generator.models import AreaObservation, ImageAsset, ThermalFinding

logging.getLogger("pypdf").setLevel(logging.ERROR)

AREA_HINTS = [
    "master bedroom",
    "common bathroom",
    "kitchen",
    "bedroom",
    "hall",
    "bathroom",
    "parking area",
    "balcony",
    "external wall",
]


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_pdf_pages(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    return [_clean_text(page.extract_text() or "") for page in reader.pages]


def parse_inspection_metadata(inspection_pages: list[str]) -> dict[str, str]:
    text = "\n".join(inspection_pages)
    metadata = {
        "inspection_date": _extract_simple(text, r"Inspection Date and Time:\s*([^\n]+)"),
        "inspected_by": _extract_simple(text, r"Inspected By:\s*([^\n]+)"),
        "property_type": _extract_simple(text, r"Property Type:\s*([^\n]+)"),
        "floors": _extract_simple(text, r"Floors:\s*([0-9]+)"),
    }
    return {k: (v if v else "Not Available") for k, v in metadata.items()}


def _extract_simple(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return ""
    return _clean_text(match.group(1))


def parse_impacted_areas(inspection_pages: list[str]) -> list[AreaObservation]:
    text = "\n".join(inspection_pages)
    pattern = re.compile(
        r"(Impacted Area\s+\d+)(.*?)(?=Impacted Area\s+\d+|Site Details|$)",
        re.IGNORECASE | re.DOTALL,
    )
    areas: list[AreaObservation] = []
    for _, block in pattern.findall(text):
        neg = _extract_with_stop(
            block,
            r"Negative side Description\s*(.*?)(?=Negative side photographs|Positive side Description|$)",
        )
        pos = _extract_with_stop(
            block,
            r"Positive side Description\s*(.*?)(?=Positive side photographs|Negative side Description|$)",
        )
        area_name = _infer_area_name(neg, pos)
        areas.append(
            AreaObservation(
                area=area_name,
                negative_observation=neg or "Not Available",
                positive_observation=pos or "Not Available",
            )
        )
    return areas


def _extract_with_stop(block: str, regex: str) -> str:
    match = re.search(regex, block, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return _clean_text(match.group(1))


def _infer_area_name(negative: str, positive: str) -> str:
    negative_text = negative.lower()
    positive_text = positive.lower()
    for hint in AREA_HINTS:
        if hint in negative_text:
            return hint.title()
    for hint in AREA_HINTS:
        if hint in positive_text:
            return hint.title()
    text = f"{negative_text} {positive_text}"
    for hint in AREA_HINTS:
        if hint in text:
            return hint.title()
    return "Unspecified Area"


def extract_images(pdf_path: Path, output_dir: Path, prefix: str) -> list[ImageAsset]:
    reader = PdfReader(str(pdf_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    seen_hashes: set[str] = set()
    extracted: list[ImageAsset] = []

    for page_index, page in enumerate(reader.pages, start=1):
        images_for_page: list[tuple[int, bytes, str]] = []
        per_page_limit = 1 if prefix.lower().startswith("thermal") else 3
        for image in page.images:
            data = image.data
            try:
                w, h = Image.open(io.BytesIO(data)).size
            except Exception:
                continue
            if w < 280 or h < 280:
                continue
            digest = hashlib.sha1(data).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            images_for_page.append((len(data), data, image.name))
            if prefix.lower().startswith("thermal") and len(images_for_page) >= per_page_limit:
                break

        images_for_page.sort(key=lambda x: x[0], reverse=True)
        for rank, (_, data, image_name) in enumerate(images_for_page[:per_page_limit], start=1):
            extension = _guess_extension(image_name)
            file_name = f"{prefix}_p{page_index:03d}_{rank}{extension}"
            file_path = output_dir / file_name
            file_path.write_bytes(data)
            extracted.append(
                ImageAsset(
                    file_name=file_name,
                    relative_path=file_path.as_posix(),
                    source=prefix,
                    page_number=page_index,
                    caption=f"{prefix.title()} image from page {page_index}",
                )
            )
    return extracted


def _guess_extension(image_name: str) -> str:
    suffix = Path(image_name).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        return suffix
    return ".jpg"


def parse_thermal_findings(thermal_pages: list[str]) -> list[ThermalFinding]:
    findings: list[ThermalFinding] = []
    for page_index, text in enumerate(thermal_pages, start=1):
        compact = re.sub(r"\s+", "", text)
        hotspot = re.search(r"Hotspot:([0-9]+(?:\.[0-9]+)?)(?:Â°|°)?C", compact, re.IGNORECASE)
        coldspot = re.search(r"Coldspot:([0-9]+(?:\.[0-9]+)?)(?:Â°|°)?C", compact, re.IGNORECASE)
        image_name = re.search(r"Thermalimage:([A-Za-z0-9_.-]+?)(?:Device|Serial|$)", compact, re.IGNORECASE)
        if not hotspot and not coldspot and not image_name:
            continue
        hot_val = _safe_float(hotspot.group(1) if hotspot else None)
        cold_val = _safe_float(coldspot.group(1) if coldspot else None)
        delta = hot_val - cold_val if hot_val is not None and cold_val is not None else None
        observation = (
            f"Thermal difference observed ({delta:.1f} C)." if delta is not None else "Thermal variation observed."
        )
        findings.append(
            ThermalFinding(
                page_number=page_index,
                hotspot_c=hotspot.group(1) if hotspot else "Not Available",
                coldspot_c=coldspot.group(1) if coldspot else "Not Available",
                image_name=image_name.group(1) if image_name else "Not Available",
                observation=observation,
            )
        )
    return findings
