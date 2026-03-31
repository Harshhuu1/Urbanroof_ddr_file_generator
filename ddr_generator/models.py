from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ImageAsset:
    file_name: str
    relative_path: str
    source: str
    page_number: int
    caption: str


@dataclass
class ThermalFinding:
    page_number: int
    hotspot_c: str
    coldspot_c: str
    image_name: str
    observation: str
    image: ImageAsset | None = None


@dataclass
class AreaObservation:
    area: str
    negative_observation: str
    positive_observation: str
    thermal_findings: list[ThermalFinding] = field(default_factory=list)
    inspection_images: list[ImageAsset] = field(default_factory=list)
    probable_root_cause: str = "Not Available"
    severity: str = "Medium"
    severity_reasoning: str = "Not Available"
    priority_level: str = "Moderate"
    estimated_impact: str = "Medium intervention"
    recommended_actions: list[str] = field(default_factory=list)
    image_insights: list[str] = field(default_factory=list)
    additional_notes: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    missing_or_unclear: list[str] = field(default_factory=list)


@dataclass
class DDRReport:
    report_header: dict[str, str]
    property_issue_summary: list[str]
    area_observations: list[AreaObservation]
    probable_root_cause_section: list[str]
    severity_assessment_section: list[str]
    recommended_actions_section: list[str]
    additional_notes: list[str]
    missing_or_unclear_information: list[str]
    conflicts: list[str]
