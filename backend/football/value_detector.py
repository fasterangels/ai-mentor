"""Value/edge detector: compare model probabilities vs bookmaker implied probabilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ValueSignal:
    edge_home: float
    edge_draw: float
    edge_away: float
    best_outcome: str
    best_edge: float
    is_value: bool


def compute_edges(
    model_probs: Dict[str, float],
    implied_probs: Dict[str, float],
) -> ValueSignal:
    # edge = model - implied
    eh = model_probs.get("home_prob", 0.0) - implied_probs.get("home", 0.0)
    ed = model_probs.get("draw_prob", 0.0) - implied_probs.get("draw", 0.0)
    ea = model_probs.get("away_prob", 0.0) - implied_probs.get("away", 0.0)

    best_outcome, best_edge = max(
        [("home", eh), ("draw", ed), ("away", ea)],
        key=lambda x: x[1],
    )

    is_value = best_edge >= 0.05  # v0 threshold

    return ValueSignal(
        edge_home=eh,
        edge_draw=ed,
        edge_away=ea,
        best_outcome=best_outcome,
        best_edge=best_edge,
        is_value=is_value,
    )


def to_reason_codes(v: ValueSignal) -> List[str]:
    codes: List[str] = []
    if v.is_value:
        codes.append("V1_VALUE_EDGE_PRESENT")
    if v.best_edge >= 0.10:
        codes.append("V2_STRONG_VALUE_EDGE")
    return codes
