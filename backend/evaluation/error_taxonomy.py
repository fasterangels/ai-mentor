"""
Error taxonomy engine v1 (metrics-only; no analyzer/decision behavior changes).

Classifies incorrect decisions (outcome != SUCCESS) into a stable set of tags.
One decision can have multiple tags (multi-label).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from evaluation.reason_metrics import (  # reuse polarity map
    POLARITY_NEUTRAL,
    POLARITY_OPPOSE,
    POLARITY_SUPPORT,
    REASON_POLARITY,
)

ERROR_TAXONOMY_VERSION = 1
DEFAULT_LOW_CONF_THRESHOLD = 0.55
DEFAULT_HIGH_CONF_THRESHOLD = 0.75


def _sorted_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy with sorted keys recursively for deterministic JSON."""
    out: Dict[str, Any] = {}
    for k in sorted(d.keys()):
        v = d[k]
        if isinstance(v, dict):
            out[k] = _sorted_dict(v)
        else:
            out[k] = v
    return out


def _polarity(code: str) -> str:
    return REASON_POLARITY.get(code, POLARITY_NEUTRAL)


DecisionRecord = Tuple[str, str, Optional[float], List[str]]
# (market, outcome, confidence, reason_codes)


def compute_error_taxonomy(
    decisions: List[DecisionRecord],
    low_conf_threshold: float = DEFAULT_LOW_CONF_THRESHOLD,
    high_conf_threshold: float = DEFAULT_HIGH_CONF_THRESHOLD,
) -> Dict[str, Any]:
    """
    Compute error taxonomy aggregates from evaluated decisions.

    decisions: list of (market, outcome, confidence, reason_codes).
    outcome: "SUCCESS" | "FAILURE" | "NEUTRAL" | "UNRESOLVED".
    Only outcome == "FAILURE" is treated as an incorrect decision.

    Tags (multi-label):
      - outcome_mismatch: outcome == "FAILURE"
      - low_confidence_error: FAILURE and confidence < low_conf_threshold
      - high_confidence_error: FAILURE and confidence >= high_conf_threshold
      - reason_conflict_error: FAILURE and both support+oppose reasons active
      - sparse_evidence_error: FAILURE and len(reason_codes) <= 1
      - unknown_bucket: FAILURE and none of the above tags except outcome_mismatch

    Returns dict with:
      {
        "global": {tag -> count},
        "per_market": {market -> {tag -> count}},
        "per_reason": {
          reason_code -> {
            "global": {"incorrect_decisions": count},
            "per_market": {market -> {"incorrect_decisions": count}},
          }
        },
        "thresholds": {
          "low_conf_threshold": float,
          "high_conf_threshold": float,
        },
      }
    """
    global_counts: Dict[str, int] = {}
    per_market_counts: Dict[str, Dict[str, int]] = {}
    per_reason_counts: Dict[str, Dict[str, Any]] = {}

    for market, outcome, confidence, reason_codes in decisions:
        if outcome != "FAILURE":
            continue

        tags: List[str] = []

        # A) outcome_mismatch
        tags.append("outcome_mismatch")

        # B/C) confidence-based errors (if confidence is known)
        if confidence is not None:
            if confidence < low_conf_threshold:
                tags.append("low_confidence_error")
            if confidence >= high_conf_threshold:
                tags.append("high_confidence_error")

        # D) reason_conflict_error
        pols = {_polarity(code) for code in reason_codes if code}
        if POLARITY_SUPPORT in pols and POLARITY_OPPOSE in pols:
            tags.append("reason_conflict_error")

        # E) sparse_evidence_error
        if len([c for c in reason_codes if c]) <= 1:
            tags.append("sparse_evidence_error")

        # F) unknown_bucket if none of B–E matched
        non_base_tags = {t for t in tags if t != "outcome_mismatch"}
        if not non_base_tags:
            tags.append("unknown_bucket")

        # Aggregate tag counts
        if not tags:
            continue
        if market not in per_market_counts:
            per_market_counts[market] = {}
        for tag in tags:
            global_counts[tag] = global_counts.get(tag, 0) + 1
            per_market_counts[market][tag] = per_market_counts[market].get(tag, 0) + 1

        # Per-reason involvement (incorrect decisions only)
        for code in {c for c in reason_codes if c}:
            entry = per_reason_counts.setdefault(
                code,
                {
                    "global": {"incorrect_decisions": 0},
                    "per_market": {},
                },
            )
            entry["global"]["incorrect_decisions"] += 1
            mstats = entry["per_market"].setdefault(
                market,
                {"incorrect_decisions": 0},
            )
            mstats["incorrect_decisions"] += 1

    global_sorted = {tag: global_counts[tag] for tag in sorted(global_counts.keys())}
    per_market_sorted: Dict[str, Dict[str, int]] = {
        m: {tag: per_market_counts[m][tag] for tag in sorted(per_market_counts[m].keys())}
        for m in sorted(per_market_counts.keys())
    }

    per_reason_sorted: Dict[str, Any] = {}
    for code in sorted(per_reason_counts.keys()):
        entry = per_reason_counts[code]
        per_market = entry["per_market"]
        per_reason_sorted[code] = {
            "global": entry["global"],
            "per_market": {
                m: per_market[m]
                for m in sorted(per_market.keys())
            },
        }

    return {
        "global": global_sorted,
        "per_market": per_market_sorted,
        "per_reason": per_reason_sorted,
        "thresholds": {
            "low_conf_threshold": low_conf_threshold,
            "high_conf_threshold": high_conf_threshold,
        },
    }


def error_taxonomy_for_report(
    decisions: List[DecisionRecord],
    low_conf_threshold: float = DEFAULT_LOW_CONF_THRESHOLD,
    high_conf_threshold: float = DEFAULT_HIGH_CONF_THRESHOLD,
) -> Dict[str, Any]:
    """
    Wrap compute_error_taxonomy with versioned meta for evaluation reports.
    """
    metrics = compute_error_taxonomy(
        decisions,
        low_conf_threshold=low_conf_threshold,
        high_conf_threshold=high_conf_threshold,
    )
    return {
        "error_taxonomy": _sorted_dict(metrics),
        "meta": {"error_taxonomy_version": ERROR_TAXONOMY_VERSION},
    }

