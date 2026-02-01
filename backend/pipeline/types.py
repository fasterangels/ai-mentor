from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PipelineInput:
    """Input for the data pipeline."""

    match_id: str
    domains: List[str]  # e.g., ["fixtures", "stats"]
    window_hours: int = 72
    force_refresh: bool = False


@dataclass
class QualityReport:
    """Quality gate assessment result."""

    passed: bool
    score: float  # 0.0-1.0
    flags: List[str] = field(default_factory=list)


@dataclass
class DomainData:
    """Data for a single domain with quality and source metadata."""

    data: Dict[str, Any]
    quality: QualityReport
    sources: List[str] = field(default_factory=list)  # Source names that contributed


@dataclass
class EvidencePack:
    """Structured evidence pack ready for analysis."""

    match_id: str
    domains: Dict[str, DomainData] = field(default_factory=dict)
    captured_at_utc: datetime = field(default_factory=lambda: datetime.now())
    flags: List[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result from pipeline execution."""

    status: str  # "OK" | "NO_DATA" | "PARTIAL"
    evidence_pack: Optional[EvidencePack] = None
    notes: List[str] = field(default_factory=list)
