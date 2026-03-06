"""
Reason failure envelope metrics (metrics-only; no decision/analyzer changes).

A reason is "active" for a decision if it appears in the decision's reason codes list.
A reason is counted as a failure exposure when the decision outcome is incorrect
and the reason was active.

This module computes, for each reason code:
- global: activations, failures, failure_rate
- per_market: activations, failures, failure_rate
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

REASON_FAILURE_METRICS_VERSION = 1


def _sorted_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of dict with keys sorted recursively for deterministic JSON."""
    return {
        k: _sorted_dict(v) if isinstance(v, dict) else v
        for k, v in sorted(d.items())
    }


def compute_reason_failure_metrics(
    decisions: List[Tuple[str, str, List[str]]],
) -> Dict[str, Any]:
    """
    Compute failure envelope metrics from a list of (market, outcome, reason_codes).

    decisions: list of (market, outcome, list of reason codes) per evaluated decision.
    outcome is a string such as "SUCCESS", "FAILURE", "NEUTRAL", "UNRESOLVED".
    A reason is a failure exposure when outcome == "FAILURE" and the reason is active.

    Returns dict:
      reason_code -> {
        "global": {activations, failures, failure_rate},
        "per_market": {
          market -> {activations, failures, failure_rate}
        },
      }
    with reason codes and markets sorted deterministically.
    """
    if not decisions:
        return {}

    stats: Dict[str, Dict[str, Any]] = {}

    for market, outcome, codes in decisions:
        is_failure = outcome == "FAILURE"
        for code in codes:
            if not code:
                continue
            reason_entry = stats.setdefault(
                code,
                {
                    "global": {"activations": 0, "failures": 0},
                    "per_market": {},
                },
            )
            g = reason_entry["global"]
            g["activations"] += 1
            if is_failure:
                g["failures"] += 1

            per_m = reason_entry["per_market"].setdefault(
                market,
                {"activations": 0, "failures": 0},
            )
            per_m["activations"] += 1
            if is_failure:
                per_m["failures"] += 1

    # Compute failure_rate and sort keys
    result: Dict[str, Any] = {}
    for code in sorted(stats.keys()):
        entry = stats[code]
        g = entry["global"]
        ga = g["activations"]
        gf = g["failures"]
        g["failure_rate"] = round(gf / ga, 3) if ga > 0 else 0.0

        per_market_sorted: Dict[str, Any] = {}
        for market in sorted(entry["per_market"].keys()):
            m_stats = entry["per_market"][market]
            ma = m_stats["activations"]
            mf = m_stats["failures"]
            m_stats["failure_rate"] = round(mf / ma, 3) if ma > 0 else 0.0
            per_market_sorted[market] = m_stats

        result[code] = {
            "global": g,
            "per_market": per_market_sorted,
        }

    return result


def reason_failure_metrics_for_report(
    decisions: List[Tuple[str, str, List[str]]],
) -> Dict[str, Any]:
    """
    Wrap compute_reason_failure_metrics with version meta for inclusion in evaluation reports.
    """
    metrics = compute_reason_failure_metrics(decisions)
    return {
        "reason_failure_metrics": _sorted_dict(metrics),
        "meta": {"reason_failure_metrics_version": REASON_FAILURE_METRICS_VERSION},
    }

