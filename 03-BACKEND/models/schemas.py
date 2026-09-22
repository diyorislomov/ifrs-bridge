"""Core data models for IFRS Bridge gap detection."""

from dataclasses import dataclass, field


@dataclass
class Gap:
    gap_id: str
    mhms_id: str
    title: str
    risk: str
    nas_treatment: str
    mhms_treatment: str
    lex_uz_ref: str
    ifrs_ref: str
    detection_keywords: list[str] = field(default_factory=list)
    adjustment_hint: str = ""


@dataclass
class NASStatement:
    company_name: str
    period_end: str
    total_assets: float
    line_items: dict[str, float] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    gaps_detected: list[Gap] = field(default_factory=list)
    explanations: dict[str, str] = field(default_factory=dict)
    report_data: dict = field(default_factory=dict)
