"""Analyzer v2 — Entry point. Deterministic, gates-first, v2 contract."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pipeline.types import EvidencePack

from .contracts import (
    ANALYZER_VERSION_V2,
    POLICY_VERSION_V2,
    SUPPORTED_MARKETS_V2,
    DecisionKind,
)
from .features import extract_features, consensus_quality_from_features, evidence_quality_score
from .gates import run_hard_gates
from .markets import score_market


def analyze_v2(
    resolver_status: str,
    evidence_pack: Optional[EvidencePack],
    markets: List[str],
    min_confidence: float = 0.62,
) -> Dict[str, Any]:
    """
    Run analyzer v2. Deterministic; gates-first; emits v2 decision contract.
    Returns analyzer dict: status, version, policy_version, analysis_run, decisions.
    """
    all_gate_results: List[Dict[str, Any]] = []
    global_flags: List[str] = []
    decisions: List[Dict[str, Any]] = []

    # Resolver not RESOLVED => global NO_PREDICTION, no market decisions
    if resolver_status != "RESOLVED":
        all_gate_results.append({
            "gate_id": "resolver",
            "pass": False,
            "notes": f"resolver status {resolver_status}",
        })
        flag = "AMBIGUOUS" if resolver_status == "AMBIGUOUS" else "NOT_FOUND"
        global_flags.append(flag)
        return _build_result(
            status="NO_PREDICTION",
            decisions=[],
            gate_results=all_gate_results,
            global_flags=global_flags,
            conflict_summary=None,
        )

    features = extract_features(evidence_pack)
    eq_score = evidence_quality_score(features)
    cq = consensus_quality_from_features(features)
    conflict_summary = {
        "evidence_quality": round(eq_score, 4),
        "consensus_quality": round(cq, 4),
    }

    for market in markets:
        blocked, gate_results, flags = run_hard_gates(resolver_status, market, features)
        all_gate_results.extend(gate_results)

        if blocked:
            decisions.append(_no_prediction_decision(market, flags))
            global_flags.extend(flags)
            continue

        decision = score_market(market, features, gate_results, cq, min_confidence)
        decisions.append(decision)
        for f in decision.get("flags") or []:
            if f not in global_flags:
                global_flags.append(f)

    # Counts
    counts = {"PLAY": 0, "NO_BET": 0, "NO_PREDICTION": 0}
    for d in decisions:
        kind = d.get("decision", "NO_PREDICTION")
        if kind in counts:
            counts[kind] += 1

    # Overall status: OK if any PLAY; NO_PREDICTION if all blocked
    any_play = counts["PLAY"] > 0
    status = "OK" if any_play else "NO_PREDICTION"

    return _build_result(
        status=status,
        decisions=decisions,
        gate_results=all_gate_results,
        global_flags=global_flags,
        conflict_summary=conflict_summary,
        counts=counts,
    )


def _no_prediction_decision(market: str, flags: List[str]) -> Dict[str, Any]:
    from .contracts import MAX_DECISION_REASONS, POLICY_VERSION_V2
    return {
        "market": market,
        "decision": DecisionKind.NO_PREDICTION,
        "selection": None,
        "confidence": None,
        "reasons": [f"Gate blocked: {', '.join(flags)}"][:MAX_DECISION_REASONS],
        "flags": list(flags),
        "evidence_refs": [],
        "policy_version": POLICY_VERSION_V2,
        "meta": {},
    }


def _build_result(
    status: str,
    decisions: List[Dict[str, Any]],
    gate_results: List[Dict[str, Any]],
    global_flags: List[str],
    conflict_summary: Optional[Dict[str, Any]] = None,
    counts: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "version": ANALYZER_VERSION_V2,
        "policy_version": POLICY_VERSION_V2,
        "analysis_run": {
            "flags": list(global_flags),
            "gate_results": gate_results,
            "conflict_summary": conflict_summary or {},
            "counts": counts or {"PLAY": 0, "NO_BET": 0, "NO_PREDICTION": 0},
        },
        "decisions": decisions,
    }
