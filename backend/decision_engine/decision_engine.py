"""
Minimal GO/NO-GO decision engine skeleton.

This module is intentionally self-contained and metrics-only:
it does not integrate with the existing analyzer or policy
runtime yet. It provides a deterministic scoring and decision
function that can be wired into a GO/NO-GO pipeline later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.calibration.confidence_calibration import (
    ConfidenceCalibrator,
    apply as apply_calibrator,
)
from evaluation.reason_metrics import select_reliability


@dataclass
class DecisionInput:
    """
    Structured input to the decision engine for a single market.

    Attributes:
        market: Market identifier (e.g. "one_x_two").
        conf_raw: Raw model confidence (0..1, but not yet calibrated).
        reasons: List of active reason codes supporting the decision.
        reason_conflicts: Whether there is a known conflict among the reasons.
        meta: Optional opaque metadata, not interpreted by this module.
    """

    market: str
    conf_raw: float
    reasons: List[str]
    reason_conflicts: bool = False
    meta: Optional[Dict[str, Any]] = None


@dataclass
class DecisionArtifacts:
    """
    Static artifacts used by the decision engine.

    Attributes:
        reliability_table: Nested dict[market][reason] -> reliability (0..1).
        thresholds: Dict[market] -> decision threshold for score (0..1).
        min_reasons: Minimum number of active reasons required.
        min_confidence: Minimum calibrated confidence required.
        low_reliability_cutoff: Any reason below this is considered low reliability.
        window: Descriptive time window for the artifacts (e.g. "90d").
        version: Logical version identifier for the artifacts.
    """

    reliability_table: Dict[str, Dict[str, float]] = field(default_factory=dict)
    thresholds: Dict[str, float] = field(default_factory=dict)
    min_reasons: int = 2
    min_confidence: float = 0.50
    low_reliability_cutoff: float = 0.35
    window: str = "90d"
    version: str = "v0"


@dataclass
class DecisionOutput:
    """
    Output of the decision engine for a single market.

    Attributes:
        decision: "GO" or "NO_GO".
        score: Final decision score.
        conf_cal: Calibrated confidence used in scoring.
        flags: List of diagnostic flags (e.g. "low_confidence").
        top_reasons: Up to three lowest-reliability reasons, each as
            {"reason": str, "reliability": float}.
        artifacts_version: Version identifier of the artifacts used.
    """

    decision: str
    score: float
    conf_cal: float
    flags: List[str] = field(default_factory=list)
    top_reasons: List[Dict[str, Any]] = field(default_factory=list)
    artifacts_version: str = ""


def calibrate_confidence(
    conf_raw: float,
    calibrator: Optional[ConfidenceCalibrator] = None,
) -> float:
    """
    Calibrate raw confidence into a calibrated value in [0.0, 1.0].

    By default this is identity with clamping; when a calibrator is
    provided, its binning curve is applied instead.
    """
    if calibrator is None:
        if conf_raw < 0.0:
            return 0.0
        if conf_raw > 1.0:
            return 1.0
        return conf_raw

    return apply_calibrator(calibrator, conf_raw)


def lookup_reliabilities(
    market: str,
    reasons: List[str],
    artifacts: DecisionArtifacts,
) -> List[Tuple[str, float]]:
    """
    Look up reliability for each active reason in a given market.

    Missing reasons (or missing markets) get a default reliability of 0.50.
    The returned list preserves the input reason order.
    """
    market_table = artifacts.reliability_table.get(market, {})
    out: List[Tuple[str, float]] = []

    # Build a lightweight reason_reliability structure from the table to
    # enable window-aware selection while remaining backwards compatible.
    # We only expose an all_time window here; select_reliability will
    # fallback appropriately when other windows are not present.
    global_rr: Dict[str, float] = {}
    per_market_rr: Dict[str, Dict[str, float]] = {}
    for mkt, reason_map in artifacts.reliability_table.items():
        if not isinstance(reason_map, dict):
            continue
        per_market_rr[mkt] = {}
        for r, v in reason_map.items():
            try:
                val = float(v)
            except (TypeError, ValueError):
                continue
            per_market_rr[mkt][r] = val
            # First occurrence wins for global map
            if r not in global_rr:
                global_rr[r] = val

    reason_reliability = {
        "global": {"all_time": global_rr},
        "per_market": {m: {"all_time": rm} for m, rm in per_market_rr.items()},
    }

    for reason in reasons:
        if not reason:
            continue
        rel = select_reliability(
            reason=reason,
            market=market,
            reason_reliability=reason_reliability,
            window=artifacts.window,
        )
        out.append((reason, rel))
    return out


def reason_weight(reliability: float) -> float:
    """
    Deterministic weight function for v1.

    reliability in [0,1]; emphasize reliable reasons, downweight weak ones.
    Example mapping:
        w = max(0.0, (reliability - 0.3) / 0.7)
    """
    r = max(0.0, min(1.0, float(reliability)))
    w = (r - 0.3) / 0.7
    return max(0.0, min(1.0, w))


def weighted_reason_strength(reliabilities: List[Tuple[str, float]]) -> float:
    """
    Compute weighted mean of reliabilities using reason_weight.

    If all weights are zero, fallback to simple mean of reliabilities.
    """
    if not reliabilities:
        return 0.0
    ws: List[float] = []
    rs: List[float] = []
    for _, r in reliabilities:
        w = reason_weight(r)
        ws.append(w)
        rs.append(float(r))
    denom = sum(ws)
    if denom > 0.0:
        return sum(w * r for w, r in zip(ws, rs)) / denom
    return sum(rs) / float(len(rs))


def compute_score(
    conf_cal: float,
    reliabilities: List[Tuple[str, float]],
    reason_conflicts: bool,
    min_reasons: int,
) -> Tuple[float, List[str]]:
    """
    Compute a decision score and associated flags.

    Scoring rule:
      - reason_strength = average of reliabilities (or 0 when no reasons)
      - penalties:
          +0.20 if reason_conflicts is True  -> flag "conflict"
          +0.20 if len(reliabilities) < min_reasons -> flag "insufficient_reasons"
      - score = 0.6 * conf_cal + 0.4 * reason_strength - penalties
    """
    flags: List[str] = []

    reason_strength = weighted_reason_strength(reliabilities)

    penalties = 0.0
    if reason_conflicts:
        penalties += 0.20
        flags.append("conflict")
    if len(reliabilities) < min_reasons:
        penalties += 0.20
        flags.append("insufficient_reasons")

    score = 0.6 * conf_cal + 0.4 * reason_strength - penalties
    return score, flags


def decide(
    input: DecisionInput,
    artifacts: DecisionArtifacts,
    calibrator: Optional[ConfidenceCalibrator] = None,
) -> DecisionOutput:
    """
    Compute a GO/NO-GO decision for a single market.

    Decision rule:
      - Calibrate confidence.
      - Compute score with reason-based penalties.
      - Flags:
          * "low_confidence" if conf_cal < min_confidence
          * "low_reliability_reason_active" if any reliability < low_reliability_cutoff
          * "conflict" / "insufficient_reasons" may already be present from scoring
      - decision == "GO" iff:
          * score >= threshold_for_market
          * and no "low_confidence"
          * and no "low_reliability_reason_active"
          * and no "insufficient_reasons"
        Otherwise decision == "NO_GO".

    Threshold default for unknown markets is 0.55.
    """
    conf_cal = calibrate_confidence(input.conf_raw, calibrator=calibrator)

    reliabilities = lookup_reliabilities(input.market, input.reasons, artifacts)
    score, flags = compute_score(
        conf_cal=conf_cal,
        reliabilities=reliabilities,
        reason_conflicts=input.reason_conflicts,
        min_reasons=artifacts.min_reasons,
    )

    # Confidence-based flag
    if conf_cal < artifacts.min_confidence:
        flags.append("low_confidence")

    # Low-reliability reasons flag
    low_rel_reasons = [
        (reason, rel) for reason, rel in reliabilities if rel < artifacts.low_reliability_cutoff
    ]
    if low_rel_reasons:
        flags.append("low_reliability_reason_active")

    # Threshold lookup with default
    threshold = artifacts.thresholds.get(input.market, 0.55)

    has_low_conf = "low_confidence" in flags
    has_low_rel = "low_reliability_reason_active" in flags
    has_insufficient = "insufficient_reasons" in flags

    go_allowed = (
        score >= threshold
        and not has_low_conf
        and not has_low_rel
        and not has_insufficient
    )
    decision = "GO" if go_allowed else "NO_GO"

    # Top 3 reasons by lowest reliability (risk-surfacing)
    sorted_by_risk = sorted(
        reliabilities,
        key=lambda item: (item[1], item[0]),  # reliability asc, reason name as tiebreaker
    )
    top_reasons = [
        {"reason": reason, "reliability": rel}
        for reason, rel in sorted_by_risk[:3]
    ]

    return DecisionOutput(
        decision=decision,
        score=score,
        conf_cal=conf_cal,
        flags=flags,
        top_reasons=top_reasons,
        artifacts_version=artifacts.version,
    )

