"""
Confidence penalty computation (H2 Part A). READ-ONLY: no effect applied yet.
Uses H1 decay params + age band; outputs PenaltyResult for reporting/analysis only.
"""

from __future__ import annotations

from dataclasses import dataclass

from modeling.reason_decay.model import DecayModelParams


@dataclass
class PenaltyResult:
    """
    Result of confidence penalty computation (read-only).
    penalized_confidence is computed but NOT used anywhere; no analyzer change.
    """
    market: str
    reason_code: str
    age_band: str
    original_confidence: float
    penalty_factor: float  # in [0, 1]
    penalized_confidence: float  # original_confidence * penalty_factor, clamped [0, 1]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_penalty(
    market: str,
    reason_code: str,
    age_band: str,
    original_confidence: float,
    decay_params: DecayModelParams | None,
) -> PenaltyResult:
    """
    Compute theoretical confidence penalty from staleness (age_band) and H1 decay params.
    Deterministic. No effect applied yet — output is for reporting/analysis only.

    Safety rules:
    - penalty_factor clamped to [0, 1]. Penalty only, no boosts.
    - If decay_params is None or has no/low support (bands_with_support == 0),
      penalty_factor = 1.0 (no penalty).
    - penalized_confidence = original_confidence * penalty_factor, clamped to [0, 1].
    """
    if decay_params is None:
        penalty_factor = 1.0
    elif decay_params.fit_quality is not None and decay_params.fit_quality.bands_with_support == 0:
        penalty_factor = 1.0
    else:
        penalty_factor = decay_params.penalty_for(age_band)
        penalty_factor = _clamp(penalty_factor, 0.0, 1.0)

    penalized = original_confidence * penalty_factor
    penalized = _clamp(penalized, 0.0, 1.0)

    return PenaltyResult(
        market=market,
        reason_code=reason_code,
        age_band=age_band,
        original_confidence=original_confidence,
        penalty_factor=penalty_factor,
        penalized_confidence=penalized,
    )
