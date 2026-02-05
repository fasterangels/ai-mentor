"""Analyzer v2 — OU_2.5 market scoring (deterministic, rule-based)."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from ..contracts import (
    DecisionKind,
    MAX_DECISION_REASONS,
    MARKET_OU_25,
    POLICY_VERSION_V2,
    SelectionOU25,
)
from ..gates import should_downgrade_to_no_bet
from ..reason_codes import codes_for_reasons, EXPECTED_GOALS_ABOVE, EXPECTED_GOALS_BELOW, GOALS_TREND, MISSING_STATS, XG_PROXY

EXPECTED_GOALS_THRESHOLD = 2.5
MIN_SEP_OU = 0.08


def score_ou_25(
    features: Dict[str, Any],
    gate_results: list,
    consensus_quality: float,
    min_confidence: float,
) -> Dict[str, Any]:
    """
    Compute Over/Under 2.5 decision from features. Returns v2 decision dict.
    """
    reasons: List[str] = []
    reason_codes_ou: List[str] = []
    flags: List[str] = []
    evidence_refs: List[str] = []

    if not features.get("has_stats"):
        return _decision(
            market=MARKET_OU_25,
            kind=DecisionKind.NO_PREDICTION,
            selection=None,
            confidence=None,
            reasons=["Missing stats for OU_2.5"],
            reason_codes=[MISSING_STATS],
            flags=flags,
            evidence_refs=evidence_refs,
        )

    goals = features.get("goals_trend") or {}
    home_avg = _f(goals.get("home_avg"))
    away_avg = _f(goals.get("away_avg"))
    home_conceded = _f(goals.get("home_conceded_avg"))
    away_conceded = _f(goals.get("away_conceded_avg"))

    expected_goals = (home_avg + away_conceded) / 2.0 + (away_avg + home_conceded) / 2.0
    reasons.append(f"xG proxy={expected_goals:.2f}")
    reason_codes_ou.append(XG_PROXY)
    reason_codes_ou.append(GOALS_TREND)
    evidence_refs.append("stats.goals_trend")

    diff = expected_goals - EXPECTED_GOALS_THRESHOLD
    p_over = 0.5 + 0.5 * math.tanh(diff * 0.5)
    p_under = 1.0 - p_over
    separation = abs(p_over - p_under)

    confidence = min(1.0, max(0.0, 0.5 + separation * 2.0))

    if separation < MIN_SEP_OU:
        return _decision(
            market=MARKET_OU_25,
            kind=DecisionKind.NO_BET,
            selection=None,
            confidence=confidence,
            reasons=reasons[:MAX_DECISION_REASONS],
            reason_codes=reason_codes_ou[:MAX_DECISION_REASONS],
            flags=flags,
            evidence_refs=evidence_refs,
        )

    downgrade, soft_gates = should_downgrade_to_no_bet(
        confidence, len(flags), consensus_quality, min_confidence
    )
    gate_results.extend(soft_gates)
    if downgrade:
        return _decision(
            market=MARKET_OU_25,
            kind=DecisionKind.NO_BET,
            selection=None,
            confidence=confidence,
            reasons=reasons[:MAX_DECISION_REASONS],
            reason_codes=reason_codes_ou[:MAX_DECISION_REASONS],
            flags=flags,
            evidence_refs=evidence_refs,
        )

    if p_over >= p_under:
        selection = SelectionOU25.OVER
        reasons.append("expected goals above threshold")
        reason_codes_ou.append(EXPECTED_GOALS_ABOVE)
    else:
        selection = SelectionOU25.UNDER
        reasons.append("expected goals below threshold")
        reason_codes_ou.append(EXPECTED_GOALS_BELOW)

    return _decision(
        market=MARKET_OU_25,
        kind=DecisionKind.PLAY,
        selection=selection.value,
        confidence=confidence,
        reasons=reasons[:MAX_DECISION_REASONS],
        reason_codes=reason_codes_ou[:MAX_DECISION_REASONS],
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
    reason_codes: Optional[List[str]] = None,
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
    out["reason_codes"] = (reason_codes or codes_for_reasons(reasons))[:MAX_DECISION_REASONS]
    if selection is not None:
        out["selection"] = selection
    if confidence is not None:
        out["confidence"] = round(confidence, 4)
    return out
