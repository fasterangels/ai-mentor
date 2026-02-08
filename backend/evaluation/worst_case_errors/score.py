"""
Deterministic worst-case score per evaluated decision.
Fixed formula: no dynamic tuning.
"""

from __future__ import annotations

from .model import EvaluatedDecision, UncertaintyShadow

# Fixed weights (do not tune)
UNCERTAINTY_PENALTY = 0.25


def worst_case_score(decision: EvaluatedDecision) -> float:
    """
    Compute worst-case score for one evaluated decision.

    - base = 1 if incorrect else 0
    - weight_confidence = original_confidence (clamped 0..1)
    - optional_penalty = 0.25 if uncertainty_shadow.would_refuse else 0
    - WorstCaseScore = base * (1 + weight_confidence + optional_penalty)
    """
    incorrect = decision.outcome == "FAILURE"
    base = 1.0 if incorrect else 0.0

    confidence = decision.original_confidence
    if confidence is None:
        confidence = 0.0
    weight_confidence = max(0.0, min(1.0, float(confidence)))

    optional_penalty = 0.0
    if decision.uncertainty_shadow is not None and decision.uncertainty_shadow.would_refuse:
        optional_penalty = UNCERTAINTY_PENALTY

    return base * (1.0 + weight_confidence + optional_penalty)
