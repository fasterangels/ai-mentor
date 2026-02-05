"""
Cross-provider parity: compare same match set from provider A vs provider B.
Deterministic report: identity mismatches, market availability, odds drift, schema drift.
Guardrails emit alerts only (no blocking).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Default guardrail thresholds (alerts only)
DEFAULT_POLICY: Dict[str, Any] = {
    "max_identity_mismatch_count": 5,
    "max_missing_markets_pct": 15.0,
    "max_odds_outlier_count": 20,
}

ODDS_KEYS = ("home", "draw", "away")
IDENTITY_KEYS = ("match_id", "home_team", "away_team", "kickoff_utc")
SCHEMA_KEYS = ("match_id", "home_team", "away_team", "competition", "kickoff_utc", "odds_1x2", "status")

# Odds outlier: pct_delta > this or abs_delta > 0.15
ODDS_OUTLIER_PCT = 5.0
ODDS_OUTLIER_ABS = 0.15


def _identity_dict(data: Any) -> Dict[str, Any]:
    """Extract identity fields for comparison."""
    if not isinstance(data, dict):
        return {}
    return {k: data.get(k) for k in IDENTITY_KEYS if data.get(k) is not None}


def compare(
    provider_a_data: List[Dict[str, Any]],
    provider_b_data: List[Dict[str, Any]],
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compare provider A vs B snapshots. Both lists: [{"match_id": str, "data": dict|None}, ...].
    Deterministic: match_ids sorted; same input order yields same output.
    Returns report with identity_mismatches, market_availability_mismatches, odds_drift (outliers + distribution),
    schema_drift_counts, summary, alerts.
    """
    policy = policy or DEFAULT_POLICY
    a_by_id = {s["match_id"]: s.get("data") for s in provider_a_data}
    b_by_id = {s["match_id"]: s.get("data") for s in provider_b_data}
    all_match_ids = sorted(set(a_by_id) | set(b_by_id))

    identity_mismatches: Dict[str, Dict[str, Any]] = {}
    market_availability_mismatches: Dict[str, Dict[str, Any]] = {}
    odds_drift: Dict[str, Dict[str, Any]] = {}
    schema_drift: Dict[str, Dict[str, Any]] = {}

    identity_mismatch_count = 0
    schema_drift_count = 0
    odds_outlier_count = 0
    missing_markets_total = 0
    markets_denom = 0
    pct_deltas: List[float] = []
    abs_deltas: List[float] = []

    for match_id in all_match_ids:
        a_data = a_by_id.get(match_id)
        b_data = b_by_id.get(match_id)

        # Identity
        a_id = _identity_dict(a_data)
        b_id = _identity_dict(b_data)
        id_match = a_id == b_id
        if not id_match and (a_data is not None or b_data is not None):
            identity_mismatch_count += 1
            identity_mismatches[match_id] = {"parity": False, "provider_a": a_id, "provider_b": b_id}

        # Market availability (1X2 keys)
        a_odds = (a_data or {}).get("odds_1x2") if isinstance(a_data, dict) else None
        b_odds = (b_data or {}).get("odds_1x2") if isinstance(b_data, dict) else None
        a_keys = set(a_odds.keys()) if isinstance(a_odds, dict) else set()
        b_keys = set(b_odds.keys()) if isinstance(b_odds, dict) else set()
        missing_in_a = b_keys - a_keys
        missing_in_b = a_keys - b_keys
        market_availability_mismatches[match_id] = {
            "provider_a_keys": sorted(a_keys),
            "provider_b_keys": sorted(b_keys),
            "missing_in_a": sorted(missing_in_a),
            "missing_in_b": sorted(missing_in_b),
        }
        for _ in ODDS_KEYS:
            markets_denom += 1
        if b_odds:
            for k in ODDS_KEYS:
                if k in b_odds and k not in (a_odds or {}):
                    missing_markets_total += 1

        # Odds drift (outliers + collect for distribution)
        deltas: Dict[str, Dict[str, float]] = {}
        if isinstance(a_odds, dict) and isinstance(b_odds, dict):
            for k in ODDS_KEYS:
                if k in a_odds and k in b_odds:
                    av = float(a_odds[k])
                    bv = float(b_odds[k])
                    abs_delta = abs(av - bv)
                    pct_delta = (abs_delta / bv * 100.0) if bv else 0.0
                    deltas[k] = {"abs_delta": round(abs_delta, 4), "pct_delta": round(pct_delta, 2)}
                    pct_deltas.append(pct_delta)
                    abs_deltas.append(abs_delta)
                    if pct_delta > ODDS_OUTLIER_PCT or abs_delta > ODDS_OUTLIER_ABS:
                        odds_outlier_count += 1
        odds_drift[match_id] = {"deltas": deltas}

        # Schema drift
        a_ok = isinstance(a_data, dict)
        b_ok = isinstance(b_data, dict)
        missing_a = [] if not a_ok else [k for k in SCHEMA_KEYS if k not in (a_data or {})]
        missing_b = [] if not b_ok else [k for k in SCHEMA_KEYS if k not in (b_data or {})]
        type_mismatches = []
        if a_ok and b_ok and a_data and b_data:
            for k in SCHEMA_KEYS:
                if k in a_data and k in b_data:
                    if type(a_data[k]) != type(b_data[k]):
                        type_mismatches.append(k)
        schema_drift[match_id] = {
            "missing_in_a": missing_a,
            "missing_in_b": missing_b,
            "type_mismatches": type_mismatches,
        }
        if missing_a or missing_b or type_mismatches:
            schema_drift_count += 1

    missing_markets_pct = (missing_markets_total / markets_denom * 100.0) if markets_denom else 0.0
    pct_deltas_sorted = sorted(pct_deltas) if pct_deltas else []
    abs_deltas_sorted = sorted(abs_deltas) if abs_deltas else []

    def _p(values: List[float], p: float) -> float:
        if not values:
            return 0.0
        k = (len(values) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(values) - 1)
        return round(values[f] + (k - f) * (values[c] - values[f]), 4)

    distribution = {
        "pct_delta": {"count": len(pct_deltas_sorted), "p50": _p(pct_deltas_sorted, 50), "p95": _p(pct_deltas_sorted, 95)},
        "abs_delta": {"count": len(abs_deltas_sorted), "p50": _p(abs_deltas_sorted, 50), "p95": _p(abs_deltas_sorted, 95)},
    }

    # Alerts (no blocking)
    alerts: List[Dict[str, Any]] = []
    max_identity = int(policy.get("max_identity_mismatch_count", DEFAULT_POLICY["max_identity_mismatch_count"]))
    max_missing_pct = float(policy.get("max_missing_markets_pct", DEFAULT_POLICY["max_missing_markets_pct"]))
    max_outliers = int(policy.get("max_odds_outlier_count", DEFAULT_POLICY["max_odds_outlier_count"]))
    if identity_mismatch_count > max_identity:
        alerts.append({
            "code": "PARITY_IDENTITY_MISMATCH",
            "severity": "WARN",
            "message": f"Identity mismatch count {identity_mismatch_count} exceeds threshold {max_identity}.",
        })
    if missing_markets_pct > max_missing_pct:
        alerts.append({
            "code": "PARITY_MISSING_MARKETS_PCT",
            "severity": "WARN",
            "message": f"Missing markets pct {missing_markets_pct:.1f}% exceeds threshold {max_missing_pct}%.",
        })
    if odds_outlier_count > max_outliers:
        alerts.append({
            "code": "PARITY_ODDS_OUTLIERS",
            "severity": "WARN",
            "message": f"Odds outlier count {odds_outlier_count} exceeds threshold {max_outliers}.",
        })

    return {
        "identity_mismatches": identity_mismatches,
        "market_availability_mismatches": market_availability_mismatches,
        "odds_drift": {"per_match": odds_drift, "outlier_count": odds_outlier_count, "distribution": distribution},
        "schema_drift_counts": {mid: 1 if (schema_drift[mid]["missing_in_a"] or schema_drift[mid]["missing_in_b"] or schema_drift[mid]["type_mismatches"]) else 0 for mid in all_match_ids},
        "schema_drift": schema_drift,
        "summary": {
            "match_count": len(all_match_ids),
            "identity_mismatch_count": identity_mismatch_count,
            "missing_markets_pct": round(missing_markets_pct, 2),
            "odds_outlier_count": odds_outlier_count,
            "schema_drift_count": schema_drift_count,
        },
        "alerts": alerts,
    }
