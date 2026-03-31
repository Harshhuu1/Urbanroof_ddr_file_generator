from __future__ import annotations

from math import ceil

from ddr_generator.models import AreaObservation, DDRReport, ImageAsset, ThermalFinding


def build_ddr_report(
    areas: list[AreaObservation],
    thermal_findings: list[ThermalFinding],
    inspection_images: list[ImageAsset],
    thermal_images: list[ImageAsset],
    inspection_metadata: dict[str, str] | None = None,
) -> DDRReport:
    _assign_inspection_images(areas, inspection_images)
    _assign_thermal_data(areas, thermal_findings, thermal_images)

    conflicts: list[str] = []
    global_missing: list[str] = []
    for area in areas:
        _enrich_area_fields(area)
        conflicts.extend(area.conflicts)
        global_missing.extend(area.missing_or_unclear)

    if not areas:
        global_missing.append("Impacted areas could not be extracted from the inspection report.")

    summary = _build_property_summary(areas)
    root_section = _build_root_cause_section(areas)
    severity_section = _build_severity_section(areas)
    actions_section = _build_actions_section(areas)
    header = {
        "inspection_date": (inspection_metadata or {}).get("inspection_date", "Not Available"),
        "inspected_by": (inspection_metadata or {}).get("inspected_by", "Not Available"),
        "property_type": (inspection_metadata or {}).get("property_type", "Not Available"),
        "floors": (inspection_metadata or {}).get("floors", "Not Available"),
    }
    notes = [
        "Data and Information Disclaimer: This is a non-invasive diagnostic summary from visible/available data in source PDFs.",
        "No hidden condition testing was performed by this automation. Physical validation by engineer is recommended.",
    ]
    if thermal_findings:
        notes.append(
            "Thermal pages do not explicitly label room/area names in source; mapping to area sections is indicative and should be field-verified."
        )

    return DDRReport(
        report_header=header,
        property_issue_summary=summary,
        area_observations=areas,
        probable_root_cause_section=root_section,
        severity_assessment_section=severity_section,
        recommended_actions_section=actions_section,
        additional_notes=notes,
        missing_or_unclear_information=_deduplicate(global_missing),
        conflicts=_deduplicate(conflicts),
    )


def _assign_inspection_images(areas: list[AreaObservation], images: list[ImageAsset]) -> None:
    if not areas:
        return
    per_area = max(1, ceil(len(images) / len(areas)))
    for index, area in enumerate(areas):
        start = index * per_area
        end = start + per_area
        area.inspection_images = images[start:end][:3]
        if not area.inspection_images:
            area.missing_or_unclear.append(f"{area.area}: Image Not Available (inspection).")


def _assign_thermal_data(
    areas: list[AreaObservation],
    findings: list[ThermalFinding],
    thermal_images: list[ImageAsset],
) -> None:
    if not areas:
        return
    for finding in findings:
        image_match = next((img for img in thermal_images if img.page_number == finding.page_number), None)
        finding.image = image_match
    per_area = max(1, ceil(len(findings) / len(areas)))
    for index, area in enumerate(areas):
        start = index * per_area
        end = start + per_area
        area.thermal_findings = findings[start:end]
        if not area.thermal_findings:
            area.missing_or_unclear.append(f"{area.area}: Thermal details Not Available.")


def _enrich_area_fields(area: AreaObservation) -> None:
    text = f"{area.negative_observation} {area.positive_observation}".lower()
    area.probable_root_cause = _detect_root_cause(text)
    area.severity, area.severity_reasoning, score = _severity_from_text(text, area.thermal_findings)
    area.priority_level = _priority_from_score(score, text)
    area.estimated_impact = _impact_from_priority(area.priority_level, text)
    area.recommended_actions = _recommended_actions(text, area.priority_level)
    area.image_insights = _build_image_insights(area, text)

    if area.negative_observation == "Not Available" and area.positive_observation == "Not Available":
        area.missing_or_unclear.append(f"{area.area}: Observation text Not Available.")
    for finding in area.thermal_findings:
        if finding.hotspot_c == "Not Available" or finding.coldspot_c == "Not Available":
            area.missing_or_unclear.append(f"{area.area}: Incomplete thermal reading on page {finding.page_number}.")
    if "damp" in text and "hollow" in text:
        area.conflicts.append(
            f"{area.area}: Dampness and tile hollowness both present; priority order is unclear from source-only data."
        )
    if not area.recommended_actions:
        area.recommended_actions = ["Detailed site investigation required. (Not Available)"]


def _detect_root_cause(text: str) -> str:
    causes: list[str] = []
    if ("damp" in text or "seep" in text) and ("skirting" in text or "wall" in text):
        causes.append("Probable capillary rise/moisture wicking at wall-floor junction")
    if "bathroom" in text or "wc" in text or "plumbing" in text or "tile joint" in text:
        causes.append("Possible plumbing line seepage or wet-area waterproofing failure")
    if "external wall" in text or "crack" in text or "duct" in text:
        causes.append("External envelope crack/duct pathway may allow lateral rainwater ingress")
    if "ceiling" in text and "damp" in text:
        causes.append("Overhead slab waterproofing deterioration cannot be ruled out")
    if "hollow" in text or "tile" in text:
        causes.append("Tile debonding likely due to moisture-influenced substrate distress")
    if not causes:
        return "Not Available"
    return "; ".join(_deduplicate(causes)) + "."


def _severity_from_text(text: str, findings: list[ThermalFinding]) -> tuple[str, str, int]:
    score = 0
    max_delta = 0.0
    if "damp" in text or "seep" in text:
        score += 2
    if "crack" in text:
        score += 2
    if "hollow" in text:
        score += 1
    if "ceiling" in text and "damp" in text:
        score += 1
    for finding in findings:
        try:
            delta = float(finding.hotspot_c) - float(finding.coldspot_c)
        except ValueError:
            continue
        max_delta = max(max_delta, delta)
        if delta >= 6:
            score += 2
        elif delta >= 4:
            score += 1
    if score >= 6:
        return "High", f"Multiple risk indicators with thermal delta up to {max_delta:.1f} C.", score
    if score >= 3:
        return "Medium", f"Active symptoms observed; thermal delta up to {max_delta:.1f} C supports intervention.", score
    return "Low", "Limited extracted indicators in available source pages.", score


def _priority_from_score(score: int, text: str) -> str:
    if score >= 6 or ("crack" in text and ("damp" in text or "seep" in text)):
        return "Critical (Immediate)"
    if score >= 3:
        return "Moderate"
    return "Monitor"


def _impact_from_priority(priority: str, text: str) -> str:
    if priority.startswith("Critical"):
        if "crack" in text or "external wall" in text:
            return "Structural risk / high intervention"
        return "Medium-to-high intervention"
    if priority == "Moderate":
        return "Medium intervention"
    return "Low repair effort"


def _recommended_actions(text: str, priority: str) -> list[str]:
    actions: list[str] = [f"Priority Plan: {priority}."]
    if "damp" in text or "seep" in text:
        actions.append("Trace seepage path and rectify waterproofing/plaster with moisture barriers.")
    if "hollow" in text or "tile" in text:
        actions.append("Remove hollow tile pockets and relay with treated substrate and fresh grouting.")
    if "crack" in text:
        actions.append("Carry out crack mapping and seal structural ingress paths under engineer supervision.")
    if "plumbing" in text or "bathroom" in text or "wc" in text:
        actions.append("Pressure-test nearby plumbing lines and repair leakage points before surface finishing.")
    actions.append("Perform post-repair thermal verification and update closure record.")
    return _deduplicate(actions)


def _build_image_insights(area: AreaObservation, text: str) -> list[str]:
    insights: list[str] = []
    if "damp" in text or "seep" in text:
        insights.append("Visible discoloration/patched damp zones indicate prolonged moisture retention.")
    if "hollow" in text or "tile" in text:
        insights.append("Surface/tile distress suggests possible grout and bond degradation.")
    if "crack" in text:
        insights.append("Crack trace in wall envelope may serve as water ingress pathway.")
    deltas: list[float] = []
    for finding in area.thermal_findings[:3]:
        try:
            deltas.append(float(finding.hotspot_c) - float(finding.coldspot_c))
        except ValueError:
            continue
    if deltas:
        insights.append(f"Thermal anomaly observed with delta range {min(deltas):.1f} to {max(deltas):.1f} C.")
    if not insights:
        insights.append("Image context not conclusive from available source visuals.")
    return _deduplicate(insights)


def _build_property_summary(areas: list[AreaObservation]) -> list[str]:
    if not areas:
        return ["Not Available"]
    total = len(areas)
    critical = sum(1 for a in areas if a.priority_level.startswith("Critical"))
    moderate = sum(1 for a in areas if a.priority_level == "Moderate")
    monitor = sum(1 for a in areas if a.priority_level == "Monitor")
    damp = sum(1 for a in areas if "damp" in a.negative_observation.lower() or "damp" in a.positive_observation.lower())
    return [
        f"{total} impacted areas identified from inspection report.",
        f"Priority split: {critical} Critical, {moderate} Moderate, {monitor} Monitor.",
        f"Moisture-linked indicators present in {damp} area(s).",
    ]


def _build_root_cause_section(areas: list[AreaObservation]) -> list[str]:
    return _deduplicate([f"{a.area}: {a.probable_root_cause}" for a in areas]) or ["Not Available"]


def _build_severity_section(areas: list[AreaObservation]) -> list[str]:
    return _deduplicate(
        [f"{a.area}: {a.severity} ({a.severity_reasoning}) | Priority {a.priority_level} | Impact {a.estimated_impact}" for a in areas]
    ) or ["Not Available"]


def _build_actions_section(areas: list[AreaObservation]) -> list[str]:
    actions: list[str] = []
    for area in areas:
        actions.extend([f"{area.area}: {a}" for a in area.recommended_actions])
    return _deduplicate(actions) or ["Not Available"]


def _deduplicate(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        clean = item.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        output.append(clean)
    return output
