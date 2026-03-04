from __future__ import annotations

from typing import Any, Dict

from backend.calibration.confidence_calibration import load_calibrator
from backend.decision_engine.decision_engine import (
    DecisionArtifacts,
    DecisionInput,
    decide,
)
from backend.policies.decision_engine_policy import load_policy


def run_decision_engine_runtime(prediction: Dict[str, Any], reason_reliability: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """
    Runtime entrypoint for GO/NO-GO decision evaluation.

    prediction: dict with at least:
      - market: str
      - confidence: float
      - reason_codes: list[str]
      - reason_conflicts: bool

    reason_reliability: reliability_table shaped as:
      {market: {reason_code: reliability_float}}
    """
    policy = load_policy("backend/policies/decision_engine_policy.json")
    calibrator = load_calibrator("backend/calibration/confidence_calibrator.json")

    market = prediction.get("market", "default")
    confidence = prediction.get("confidence", 0.0)
    reasons = prediction.get("reason_codes") or []
    if not isinstance(reasons, list):
        reasons = list(reasons)
    conflicts = bool(prediction.get("reason_conflicts", False))

    inp = DecisionInput(
        market=str(market),
        conf_raw=float(confidence),
        reasons=[str(r) for r in reasons],
        reason_conflicts=conflicts,
    )

    artifacts = DecisionArtifacts(
        reliability_table=reason_reliability,
        thresholds=policy.thresholds,
        window="90d",
        version=policy.version,
    )

    result = decide(inp, artifacts, calibrator=calibrator)

    return {
        "decision": result.decision,
        "score": result.score,
        "confidence_calibrated": result.conf_cal,
        "flags": list(result.flags),
    }


def apply_runtime_decision(prediction: Dict[str, Any], reason_reliability: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """
    Apply the runtime decision engine to a single prediction.

    If decision == "GO": return prediction unchanged.
    If decision == "NO_GO": annotate prediction with refusal metadata.
    """
    result = run_decision_engine_runtime(prediction, reason_reliability)

    if result["decision"] == "NO_GO":
        prediction = dict(prediction)  # avoid mutating caller inadvertently
        prediction["refused"] = True
        prediction["refusal_reason"] = result["flags"]

    return prediction

