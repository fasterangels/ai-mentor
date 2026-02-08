"""Data models and constants for refusal threshold grid search (shadow-only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

# Fixed constant for safety_score objective: safety_score = accuracy_on_non_refused - ALPHA * refusal_rate
ALPHA = 0.10

# Stale bands in order from least stale to most stale (index used for "age_band >= threshold")
STALE_BANDS: tuple[str, ...] = ("6-24h", "1-3d", "3-7d", "7d+")

# effective_confidence_threshold grid: 0.05 steps from 0.10 to 0.90
def effective_confidence_grid() -> List[float]:
    """Deterministic grid of effective confidence thresholds."""
    return [round(0.10 + i * 0.05, 2) for i in range(17)]  # 0.10 .. 0.90


@dataclass
class ShadowDecision:
    """One decision with uncertainty-shadow inputs and evaluation outcome (for grid search)."""

    effective_confidence: float  # 0..1, hypothetical from shadow
    age_band: str  # one of STALE_BANDS
    outcome: str  # SUCCESS | FAILURE | NEUTRAL | UNRESOLVED
    market: Optional[str] = None  # for per-market optimization
    fixture_id: Optional[str] = None


@dataclass
class BestThresholds:
    """Best thresholds and metrics for one market or overall."""

    effective_confidence_threshold: float
    stale_band_threshold: str
    refusal_rate: float
    accuracy_on_non_refused: float  # excludes neutrals in denominator
    safety_score: float
    support_total: int
    support_refused: int
    support_non_refused: int
    success_non_refused: int
    failure_non_refused: int
