"""Football decision engine: convert model signals into GO / NO_GO decision."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class DecisionResult:
    decision: str
    confidence: float
    reasons: List[str]


def build_decision(payload: Dict[str, Any]) -> DecisionResult:
    meta = payload.get("meta", {})

    prediction = meta.get("calibrated_prediction") or meta.get("model_prediction", {})

    value = meta.get("value_signal", {})

    fatigue = meta.get("schedule_fatigue", {})

    injuries = meta.get("injury_impact", {})

    confidence = max(
        prediction.get("home_prob", 0.0),
        prediction.get("draw_prob", 0.0),
        prediction.get("away_prob", 0.0),
    )

    reasons: List[str] = []

    if value.get("is_value"):
        reasons.append("value_edge")

    if fatigue:
        home_fatigue = fatigue.get("home", {}) or {}
        away_fatigue = fatigue.get("away", {}) or {}
        if home_fatigue.get("fatigue_score", 0) > 0.7 or away_fatigue.get("fatigue_score", 0) > 0.7:
            reasons.append("fatigue_risk")

    if injuries:
        home_inj = injuries.get("home", {}) or {}
        away_inj = injuries.get("away", {}) or {}
        if home_inj.get("injury_impact_score", 0) > 0.3 or away_inj.get("injury_impact_score", 0) > 0.3:
            reasons.append("injury_risk")

    if confidence < 0.45:
        return DecisionResult("NO_GO", confidence, reasons)

    if value.get("is_value") and confidence >= 0.5:
        return DecisionResult("GO", confidence, reasons)

    return DecisionResult("LOW_CONFIDENCE", confidence, reasons)
