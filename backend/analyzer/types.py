from __future__ import annotations

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pipeline.types import EvidencePack


@dataclass
class AnalyzerPolicy:
    """Policy configuration for analyzer decisions."""

    min_sep_1x2: float = 0.10
    min_sep_ou: float = 0.08
    min_sep_gg: float = 0.08
    min_confidence: float = 0.62
    risk_caps: Dict[str, float] = field(default_factory=lambda: {"default": 0.35})


@dataclass
class AnalyzerInput:
    """Input for the analyzer engine."""

    analysis_run_id: str
    match_id: str
    mode: str  # "PREGAME" | "LIVE"
    markets: List[str]  # e.g., ["1X2", "OU25", "GGNG"]
    policy: AnalyzerPolicy = field(default_factory=AnalyzerPolicy)
    evidence_pack: Optional[EvidencePack] = None


@dataclass
class MarketDecision:
    """Decision for a single market."""

    market: str  # "1X2" | "OU25" | "GGNG"
    decision: str  # "HOME" | "DRAW" | "AWAY" | "OVER" | "UNDER" | "GG" | "NG" | "NO_BET"
    probabilities: Dict[str, float] = field(default_factory=dict)
    separation: float = 0.0
    confidence: float = 0.0
    risk: float = 0.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class AnalysisRunMetadata:
    """Metadata about the analysis run."""

    logic_version: str = "analyzer_v1"
    flags: List[str] = field(default_factory=list)


@dataclass
class AnalyzerResult:
    """Result from analyzer execution."""

    status: str  # "OK" | "NO_PREDICTION"
    analysis_run: AnalysisRunMetadata
    decisions: List[MarketDecision] = field(default_factory=list)
