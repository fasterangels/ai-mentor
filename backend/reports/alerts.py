"""
Guardrail alerts: deterministic evaluation from a BatchReport.
"""

from __future__ import annotations

from typing import Any, Dict, List


def evaluate_alerts(batch_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluate guardrail rules on batch_report. Returns list of Alert dicts:
    { "code": str, "severity": "INFO"|"WARN"|"CRITICAL", "message": str }.
    Rules (deterministic):
    - total_matches == 0 -> INFO NO_MATCHES
    - total_changed_decisions > 0.3 * total_matches -> WARN CHANGES_SPIKE
    - any per_market_changed_counts market > 0.4 * total_matches -> WARN MARKET_CHANGES_SPIKE
    - failures list non-empty -> WARN PARTIAL_FAILURES
    """
    alerts: List[Dict[str, Any]] = []
    aggregates = batch_report.get("aggregates") or {}
    total_matches = int(aggregates.get("total_matches", 0))
    total_changed_decisions = int(aggregates.get("total_changed_decisions", 0))
    per_market = aggregates.get("per_market_changed_counts") or {}
    failures = batch_report.get("failures") or []

    if total_matches == 0:
        alerts.append({
            "code": "NO_MATCHES",
            "severity": "INFO",
            "message": "No matches processed in this run.",
        })

    if total_matches > 0 and total_changed_decisions > 0.3 * total_matches:
        alerts.append({
            "code": "CHANGES_SPIKE",
            "severity": "WARN",
            "message": f"Total changed decisions ({total_changed_decisions}) exceeds 30% of matches ({total_matches}).",
        })

    if total_matches > 0:
        threshold = 0.4 * total_matches
        for market, count in per_market.items():
            if count > threshold:
                alerts.append({
                    "code": "MARKET_CHANGES_SPIKE",
                    "severity": "WARN",
                    "message": f"Market '{market}' changed count ({count}) exceeds 40% of matches ({total_matches}).",
                })

    if failures:
        alerts.append({
            "code": "PARTIAL_FAILURES",
            "severity": "WARN",
            "message": f"Run had {len(failures)} failure(s).",
        })

    return alerts
