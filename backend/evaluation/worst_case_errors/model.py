"""Data models for worst-case error tracking (measurement-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class UncertaintyShadow:
    """Optional shadow data: would the uncertainty layer have refused this decision?"""

    would_refuse: bool
    triggered_uncertainty_signals: Optional[List[str]] = None


@dataclass
class EvaluatedDecision:
    """One evaluated decision (one fixture+market): prediction, outcome, confidence, optional shadow."""

    fixture_id: str
    market: str
    prediction: str  # pick
    outcome: str  # SUCCESS | FAILURE | NEUTRAL | UNRESOLVED
    original_confidence: float  # 0..1
    uncertainty_shadow: Optional[UncertaintyShadow] = None
    snapshot_ids: Optional[List[str]] = None
    snapshot_type: Optional[str] = None  # "recorded" | "live_shadow" when known


@dataclass
class WorstCaseRow:
    """One row in the worst-case report: fixture, market, prediction, outcome, score, optional signals."""

    fixture_id: str
    market: str
    prediction: str
    outcome: str
    original_confidence: float
    worst_case_score: float
    triggered_uncertainty_signals: Optional[List[str]] = None
    snapshot_ids: Optional[List[str]] = None
    snapshot_type: Optional[str] = None  # "recorded" | "live_shadow" for LIVE_SHADOW focus


@dataclass
class WorstCaseReport:
    """Ranked worst-case rows (score desc, then fixture_id) plus computed_at_utc."""

    rows: List[WorstCaseRow]
    computed_at_utc: datetime
