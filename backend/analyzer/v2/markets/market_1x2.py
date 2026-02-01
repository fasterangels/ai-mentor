"""Analyzer v2 — 1X2 market scoring (deterministic, rule-based)."""

from __future__ import annotations

from typing import Any, Dict, List

from ..contracts import (
    DecisionKind,
    MARKET_1X2,
    MAX_DECISION_REASONS,
    POLICY_VERSION_V2,
    Selection1X2,
)
from ..gates import should_downgrade_to_no_bet

HOME_ADVANTAGE = 0.15
MIN_SEP_1X2 = 0.10


def score_1x2(
    features: Dict[str, Any],
    gate_results: list,
    consensus_quality: float,
    min_confidence: float,
) -> Dict[str, Any]:
    """
    Compute 1X2 decision from features. Returns v2 decision dict.
    Gates already run; if hard gate blocked, caller uses NO_PREDICTION.
    """
    reasons: List[str] = []
    flags: List[str] = []
    evidence_refs: List[str] = []

    if not features.get("has_stats"):
        return _decision(
            market=MARKET_1X2,
            kind=DecisionKind.NO_PREDICTION,
            selection=None,
            confidence=None,
            reasons=["Missing stats for 1X2"],
            flags=flags,
            evidence_refs=evidence_refs,
        )

    team_strength = features.get("team_strength") or {}
    home_s = team_strength.get("home") or {}
    away_s = team_strength.get("away") or {}
    home_attack = _f(home_s.get("goals_scored"))
    home_def = _f(home_s.get("goals_conceded"))
    away_attack = _f(away_s.get("goals_scored"))
    away_def = _f(away_s.get("goals_conceded"))

    home_net = home_attack - away_def
    away_net = away_attack - home_def
    h2h = features.get("h2h") or {}
    if h2h.get("matches_played", 0) > 0:
        total = h2h["matches_played"]
        home_h2h = (h2h.get("home_wins", 0) * 1.0 + h2h.get("draws", 0) * 0.5) / total
        away_h2h = (h2h.get("away_wins", 0) * 1.0 + h2h.get("draws", 0) * 0.5) / total
        home_net += (home_h2h - 0.5) * 0.1
        away_net += (away_h2h - 0.5) * 0.1
        reasons.append("H2H used")
        evidence_refs.append("stats.head_to_head")

    scores = {
        Selection1X2.HOME: home_net + HOME_ADVANTAGE,
        Selection1X2.DRAW: 0.0,
        Selection1X2.AWAY: away_net - HOME_ADVANTAGE,
    }
    # Normalize to pseudo-probs (bounded 0..1 via softmax-like)
    exp_sum = sum(2 ** v for v in scores.values())
    probs = {k: (2 ** v) / exp_sum for k, v in scores.items()}
    sorted_items = sorted(probs.items(), key=lambda x: -x[1])
    top_sel = sorted_items[0][0]
    top_prob = sorted_items[0][1]
    second_prob = sorted_items[1][1] if len(sorted_items) > 1 else 0.0
    separation = top_prob - second_prob

    confidence = min(1.0, max(0.0, 0.5 + separation * 2.0))
    reasons.append(f"top={top_sel} sep={separation:.2f}")

    if separation < MIN_SEP_1X2:
        return _decision(
            market=MARKET_1X2,
            kind=DecisionKind.NO_BET,
            selection=None,
            confidence=confidence,
            reasons=reasons[:MAX_DECISION_REASONS],
            flags=flags,
            evidence_refs=evidence_refs,
        )

    downgrade, soft_gates = should_downgrade_to_no_bet(
        confidence, len(flags), consensus_quality, min_confidence
    )
    gate_results.extend(soft_gates)
    if downgrade:
        return _decision(
            market=MARKET_1X2,
            kind=DecisionKind.NO_BET,
            selection=None,
            confidence=confidence,
            reasons=reasons[:MAX_DECISION_REASONS],
            flags=flags,
            evidence_refs=evidence_refs,
        )

    return _decision(
        market=MARKET_1X2,
        kind=DecisionKind.PLAY,
        selection=top_sel.value if hasattr(top_sel, "value") else top_sel,
        confidence=confidence,
        reasons=reasons[:MAX_DECISION_REASONS],
        flags=flags,
        evidence_refs=evidence_refs,
    )


def _f(x: Any) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _decision(
    market: str,
    kind: str,
    selection: Any,
    confidence: Any,
    reasons: List[str],
    flags: List[str],
    evidence_refs: List[str],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "market": market,
        "decision": kind,
        "reasons": reasons[:MAX_DECISION_REASONS],
        "flags": list(flags),
        "evidence_refs": list(evidence_refs),
        "policy_version": POLICY_VERSION_V2,
        "meta": {},
    }
    if selection is not None:
        out["selection"] = selection
    if confidence is not None:
        out["confidence"] = round(confidence, 4)
    return out
