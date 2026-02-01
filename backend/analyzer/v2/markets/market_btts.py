"""Analyzer v2 — BTTS market scoring (deterministic, rule-based)."""

from __future__ import annotations

from typing import Any, Dict, List

from ..contracts import (
    DecisionKind,
    MAX_DECISION_REASONS,
    MARKET_BTTS,
    POLICY_VERSION_V2,
    SelectionBTTS,
)
from ..gates import should_downgrade_to_no_bet

MIN_SEP_BTTS = 0.08


def score_btts(
    features: Dict[str, Any],
    gate_results: list,
    consensus_quality: float,
    min_confidence: float,
) -> Dict[str, Any]:
    """
    Compute Both Teams To Score (YES/NO) decision from features. Returns v2 decision dict.
    """
    reasons: List[str] = []
    flags: List[str] = []
    evidence_refs: List[str] = []

    if not features.get("has_stats"):
        return _decision(
            market=MARKET_BTTS,
            kind=DecisionKind.NO_PREDICTION,
            selection=None,
            confidence=None,
            reasons=["Missing stats for BTTS"],
            flags=flags,
            evidence_refs=evidence_refs,
        )

    goals = features.get("goals_trend") or {}
    home_avg = _f(goals.get("home_avg"))
    away_avg = _f(goals.get("away_avg"))
    home_conceded = _f(goals.get("home_conceded_avg"))
    away_conceded = _f(goals.get("away_conceded_avg"))

    home_scoring = min(1.0, max(0.0, home_avg / 3.0))
    away_scoring = min(1.0, max(0.0, away_avg / 3.0))
    home_conceding = min(1.0, max(0.0, home_conceded / 3.0))
    away_conceding = min(1.0, max(0.0, away_conceded / 3.0))
    p_home_scores = home_scoring * away_conceding
    p_away_scores = away_scoring * home_conceding
    p_yes = p_home_scores * p_away_scores
    p_no = 1.0 - p_yes
    separation = abs(p_yes - p_no)
    reasons.append(f"P(GG) proxy={p_yes:.2f}")
    evidence_refs.append("stats.goals_trend")

    confidence = min(1.0, max(0.0, 0.5 + separation * 2.0))

    if separation < MIN_SEP_BTTS:
        return _decision(
            market=MARKET_BTTS,
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
            market=MARKET_BTTS,
            kind=DecisionKind.NO_BET,
            selection=None,
            confidence=confidence,
            reasons=reasons[:MAX_DECISION_REASONS],
            flags=flags,
            evidence_refs=evidence_refs,
        )

    if p_yes >= p_no:
        selection = SelectionBTTS.YES
        reasons.append("both teams scoring trend")
    else:
        selection = SelectionBTTS.NO
        reasons.append("defensive strength present")

    return _decision(
        market=MARKET_BTTS,
        kind=DecisionKind.PLAY,
        selection=selection.value,
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
