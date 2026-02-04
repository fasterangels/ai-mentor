"""
Guardrails for live shadow analyze: compare live vs recorded analysis results.
Alerts only (never block run - shadow-only mode).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Default policy thresholds
DEFAULT_POLICY: Dict[str, Any] = {
    "max_pick_change_rate": 0.3,
    "max_confidence_delta_p95": 0.15,
    "max_coverage_drop_pct": 20.0,
    "max_reason_churn_rate": 0.4,
}


def _extract_decisions(analysis_report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract decisions by market from analysis report. Returns {market: {pick, confidence, reasons}}."""
    decisions: Dict[str, Dict[str, Any]] = {}
    analysis = analysis_report.get("analysis") or {}
    picks = analysis.get("markets_picks_confidences") or {}
    decisions_list = analysis.get("decisions") or []
    
    # First populate from markets_picks_confidences
    for market, pick_conf in picks.items():
        decisions[market] = {
            "pick": pick_conf.get("pick"),
            "confidence": float(pick_conf.get("confidence") or 0.0),
            "reasons": [],
        }
    
    # Then populate reasons from decisions array
    for dec in decisions_list:
        market = dec.get("market")
        if market:
            if market not in decisions:
                decisions[market] = {
                    "pick": dec.get("selection") or dec.get("decision"),
                    "confidence": float(dec.get("confidence") or 0.0),
                    "reasons": [],
                }
            decisions[market]["reasons"] = dec.get("reasons") or []
    
    return decisions


def _calculate_pick_change_rate(
    live_decisions: Dict[str, Dict[str, Any]],
    recorded_decisions: Dict[str, Dict[str, Any]],
) -> float:
    """Calculate rate of pick changes (0.0 to 1.0)."""
    all_markets = set(live_decisions.keys()) | set(recorded_decisions.keys())
    if not all_markets:
        return 0.0
    changes = 0
    for market in all_markets:
        live_pick = live_decisions.get(market, {}).get("pick")
        rec_pick = recorded_decisions.get(market, {}).get("pick")
        if live_pick != rec_pick:
            changes += 1
    return changes / len(all_markets) if all_markets else 0.0


def _calculate_confidence_deltas(
    live_decisions: Dict[str, Dict[str, Any]],
    recorded_decisions: Dict[str, Dict[str, Any]],
) -> List[float]:
    """Calculate absolute confidence deltas for all markets. Returns list of deltas."""
    deltas: List[float] = []
    all_markets = set(live_decisions.keys()) | set(recorded_decisions.keys())
    for market in all_markets:
        live_conf = float(live_decisions.get(market, {}).get("confidence") or 0.0)
        rec_conf = float(recorded_decisions.get(market, {}).get("confidence") or 0.0)
        deltas.append(abs(live_conf - rec_conf))
    return deltas


def _calculate_coverage_drop(
    live_decisions: Dict[str, Dict[str, Any]],
    recorded_decisions: Dict[str, Dict[str, Any]],
) -> float:
    """Calculate coverage drop percentage (markets with decisions in recorded but not in live)."""
    rec_markets = set(recorded_decisions.keys())
    live_markets = set(live_decisions.keys())
    if not rec_markets:
        return 0.0
    missing = rec_markets - live_markets
    return (len(missing) / len(rec_markets) * 100.0) if rec_markets else 0.0


def _calculate_reason_churn_rate(
    live_decisions: Dict[str, Dict[str, Any]],
    recorded_decisions: Dict[str, Dict[str, Any]],
) -> float:
    """Calculate reason churn rate (markets where reasons changed)."""
    common_markets = set(live_decisions.keys()) & set(recorded_decisions.keys())
    if not common_markets:
        return 0.0
    churned = 0
    for market in common_markets:
        live_reasons = set(live_decisions[market].get("reasons") or [])
        rec_reasons = set(recorded_decisions[market].get("reasons") or [])
        if live_reasons != rec_reasons:
            churned += 1
    return churned / len(common_markets) if common_markets else 0.0


def evaluate(
    live_analysis: Dict[str, Any],
    recorded_analysis: Dict[str, Any],
    policy: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate guardrails comparing live vs recorded analysis.
    Returns alerts (never blocks - shadow-only mode).
    """
    policy = policy or DEFAULT_POLICY
    live_decisions = _extract_decisions(live_analysis)
    recorded_decisions = _extract_decisions(recorded_analysis)

    pick_change_rate = _calculate_pick_change_rate(live_decisions, recorded_decisions)
    confidence_deltas = _calculate_confidence_deltas(live_decisions, recorded_decisions)
    confidence_delta_p95 = sorted(confidence_deltas)[int(len(confidence_deltas) * 0.95)] if confidence_deltas else 0.0
    coverage_drop_pct = _calculate_coverage_drop(live_decisions, recorded_decisions)
    reason_churn_rate = _calculate_reason_churn_rate(live_decisions, recorded_decisions)

    alerts: List[Dict[str, Any]] = []
    max_pick_change = float(policy.get("max_pick_change_rate", DEFAULT_POLICY["max_pick_change_rate"]))
    max_conf_delta = float(policy.get("max_confidence_delta_p95", DEFAULT_POLICY["max_confidence_delta_p95"]))
    max_coverage_drop = float(policy.get("max_coverage_drop_pct", DEFAULT_POLICY["max_coverage_drop_pct"]))
    max_reason_churn = float(policy.get("max_reason_churn_rate", DEFAULT_POLICY["max_reason_churn_rate"]))

    if pick_change_rate > max_pick_change:
        alerts.append({
            "code": "LIVE_SHADOW_PICK_CHANGE_RATE",
            "severity": "WARN",
            "message": f"Pick change rate {pick_change_rate:.1%} exceeds threshold {max_pick_change:.1%}.",
        })
    if confidence_delta_p95 > max_conf_delta:
        alerts.append({
            "code": "LIVE_SHADOW_CONFIDENCE_DELTA",
            "severity": "WARN",
            "message": f"Confidence delta p95 {confidence_delta_p95:.3f} exceeds threshold {max_conf_delta:.3f}.",
        })
    if coverage_drop_pct > max_coverage_drop:
        alerts.append({
            "code": "LIVE_SHADOW_COVERAGE_DROP",
            "severity": "WARN",
            "message": f"Coverage drop {coverage_drop_pct:.1f}% exceeds threshold {max_coverage_drop:.1f}%.",
        })
    if reason_churn_rate > max_reason_churn:
        alerts.append({
            "code": "LIVE_SHADOW_REASON_CHURN",
            "severity": "WARN",
            "message": f"Reason churn rate {reason_churn_rate:.1%} exceeds threshold {max_reason_churn:.1%}.",
        })

    return alerts


def compare_analysis(
    live_analysis: Dict[str, Any],
    recorded_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Side-by-side compare live vs recorded analysis.
    Returns: pick_parity, confidence_deltas, reasons_diff, coverage_diff.
    """
    live_decisions = _extract_decisions(live_analysis)
    recorded_decisions = _extract_decisions(recorded_analysis)
    all_markets = sorted(set(live_decisions.keys()) | set(recorded_decisions.keys()))

    pick_parity: Dict[str, Dict[str, Any]] = {}
    confidence_deltas: Dict[str, float] = {}
    reasons_diff: Dict[str, Dict[str, Any]] = {}
    coverage_diff: Dict[str, Any] = {
        "live_markets": sorted(live_decisions.keys()),
        "recorded_markets": sorted(recorded_decisions.keys()),
        "missing_in_live": sorted(set(recorded_decisions.keys()) - set(live_decisions.keys())),
        "missing_in_recorded": sorted(set(live_decisions.keys()) - set(recorded_decisions.keys())),
    }

    for market in all_markets:
        live_pick = live_decisions.get(market, {}).get("pick")
        rec_pick = recorded_decisions.get(market, {}).get("pick")
        live_conf = float(live_decisions.get(market, {}).get("confidence") or 0.0)
        rec_conf = float(recorded_decisions.get(market, {}).get("confidence") or 0.0)
        live_reasons = live_decisions.get(market, {}).get("reasons") or []
        rec_reasons = recorded_decisions.get(market, {}).get("reasons") or []

        pick_parity[market] = {
            "parity": live_pick == rec_pick,
            "live_pick": live_pick,
            "recorded_pick": rec_pick,
        }
        confidence_deltas[market] = round(live_conf - rec_conf, 4)
        reasons_diff[market] = {
            "live_reasons": live_reasons,
            "recorded_reasons": rec_reasons,
            "added": sorted(set(live_reasons) - set(rec_reasons)),
            "removed": sorted(set(rec_reasons) - set(live_reasons)),
        }

    return {
        "pick_parity": pick_parity,
        "confidence_deltas": confidence_deltas,
        "reasons_diff": reasons_diff,
        "coverage_diff": coverage_diff,
    }
