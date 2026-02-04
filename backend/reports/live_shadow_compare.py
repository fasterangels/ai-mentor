"""
Live shadow compare: diff engine for live vs recorded ingestion snapshots.
Deterministic comparison: identity parity, odds presence, odds value drift, schema drift.
Policy thresholds and guardrail alerts.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from ingestion.connectors.platform_base import IngestedMatchData

# Default policy for drift thresholds
DEFAULT_POLICY: Dict[str, Any] = {
    "max_missing_markets_pct": 10.0,
    "max_schema_drift_count": 5,
    "max_odds_outlier_count": 10,
    "max_identity_mismatch_count": 0,
}

ODDS_KEYS = ("home", "draw", "away")
IDENTITY_KEYS = ("match_id", "home_team", "away_team", "kickoff_utc")
SCHEMA_KEYS = ("match_id", "home_team", "away_team", "competition", "kickoff_utc", "odds_1x2", "status")


def ingested_to_dict(d: IngestedMatchData) -> Dict[str, Any]:
    """Convert IngestedMatchData to stable dict for snapshot/diff."""
    return asdict(d)


def _snapshot_item(match_id: str, data: IngestedMatchData | None) -> Dict[str, Any]:
    """One entry in a snapshot list: match_id + data (dict or None)."""
    return {
        "match_id": match_id,
        "data": ingested_to_dict(data) if data is not None else None,
    }


def build_snapshot_list(items: List[tuple[str, IngestedMatchData | None]]) -> List[Dict[str, Any]]:
    """Build deterministic snapshot list (sorted by match_id)."""
    return [_snapshot_item(mid, data) for mid, data in sorted(items, key=lambda x: x[0])]


def compare(
    live_snapshots: List[Dict[str, Any]],
    recorded_snapshots: List[Dict[str, Any]],
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compare live vs recorded snapshots. Both lists must be sorted by match_id (deterministic).
    Each snapshot entry: {"match_id": str, "data": dict | None}.
    Returns diff report with identity_parity, odds_presence_parity, odds_value_drift, schema_drift, alerts.
    """
    policy = policy or DEFAULT_POLICY
    live_by_id = {s["match_id"]: s.get("data") for s in live_snapshots}
    rec_by_id = {s["match_id"]: s.get("data") for s in recorded_snapshots}
    all_match_ids = sorted(set(live_by_id) | set(rec_by_id))

    identity_parity: Dict[str, Dict[str, Any]] = {}
    odds_presence_parity: Dict[str, Dict[str, Any]] = {}
    odds_value_drift: Dict[str, Dict[str, Any]] = {}
    schema_drift: Dict[str, Dict[str, Any]] = {}
    identity_mismatch_count = 0
    schema_drift_count = 0
    odds_outlier_count = 0
    missing_markets_total = 0
    markets_denom = 0

    for match_id in all_match_ids:
        live_data = live_by_id.get(match_id)
        rec_data = rec_by_id.get(match_id)

        # Identity parity (match_id, teams, kickoff UTC)
        live_id = _identity_dict(live_data)
        rec_id = _identity_dict(rec_data)
        id_match = live_id == rec_id
        identity_parity[match_id] = {"parity": id_match, "live": live_id, "recorded": rec_id}
        if not id_match and (live_data is not None or rec_data is not None):
            identity_mismatch_count += 1

        # Odds presence (markets available, missing/extra)
        live_odds = (live_data or {}).get("odds_1x2") if isinstance(live_data, dict) else None
        rec_odds = (rec_data or {}).get("odds_1x2") if isinstance(rec_data, dict) else None
        live_keys = set(live_odds.keys()) if isinstance(live_odds, dict) else set()
        rec_keys = set(rec_odds.keys()) if isinstance(rec_odds, dict) else set()
        missing_in_live = rec_keys - live_keys
        missing_in_rec = live_keys - rec_keys
        odds_presence_parity[match_id] = {
            "live_keys": sorted(live_keys),
            "recorded_keys": sorted(rec_keys),
            "missing_in_live": sorted(missing_in_live),
            "missing_in_recorded": sorted(missing_in_rec),
        }
        for _ in ODDS_KEYS:
            markets_denom += 1
        if rec_odds:
            for k in ODDS_KEYS:
                if k in rec_odds and k not in (live_odds or {}):
                    missing_markets_total += 1

        # Odds value drift (abs/percent deltas, outliers)
        deltas: Dict[str, Dict[str, float]] = {}
        if isinstance(live_odds, dict) and isinstance(rec_odds, dict):
            for k in ODDS_KEYS:
                if k in live_odds and k in rec_odds:
                    lv = float(live_odds[k])
                    rv = float(rec_odds[k])
                    abs_delta = abs(lv - rv)
                    pct_delta = (abs_delta / rv * 100.0) if rv else 0.0
                    deltas[k] = {"abs_delta": round(abs_delta, 4), "pct_delta": round(pct_delta, 2)}
                    if pct_delta > 5.0 or abs_delta > 0.1:
                        odds_outlier_count += 1
        odds_value_drift[match_id] = {"deltas": deltas}

        # Schema drift (missing fields, type mismatches)
        live_ok = isinstance(live_data, dict)
        rec_ok = isinstance(rec_data, dict)
        missing_fields_live = [] if not live_ok else [k for k in SCHEMA_KEYS if k not in live_data]
        missing_fields_rec = [] if not rec_ok else [k for k in SCHEMA_KEYS if k not in rec_data]
        type_mismatches = []
        if live_ok and rec_ok:
            for k in SCHEMA_KEYS:
                if k in live_data and k in rec_data:
                    if type(live_data[k]) != type(rec_data[k]):
                        type_mismatches.append(k)
        schema_drift[match_id] = {
            "missing_in_live": missing_fields_live,
            "missing_in_recorded": missing_fields_rec,
            "type_mismatches": type_mismatches,
        }
        if missing_fields_live or missing_fields_rec or type_mismatches:
            schema_drift_count += 1

    missing_markets_pct = (missing_markets_total / markets_denom * 100.0) if markets_denom else 0.0

    # Guardrail alerts
    max_missing_pct = float(policy.get("max_missing_markets_pct", DEFAULT_POLICY["max_missing_markets_pct"]))
    max_schema = int(policy.get("max_schema_drift_count", DEFAULT_POLICY["max_schema_drift_count"]))
    max_outliers = int(policy.get("max_odds_outlier_count", DEFAULT_POLICY["max_odds_outlier_count"]))
    max_identity = int(policy.get("max_identity_mismatch_count", DEFAULT_POLICY["max_identity_mismatch_count"]))

    alerts: List[Dict[str, Any]] = []
    if missing_markets_pct > max_missing_pct:
        alerts.append({
            "code": "LIVE_SHADOW_MISSING_MARKETS_PCT",
            "severity": "WARN",
            "message": f"Missing markets pct {missing_markets_pct:.1f}% exceeds threshold {max_missing_pct}%.",
        })
    if schema_drift_count > max_schema:
        alerts.append({
            "code": "LIVE_SHADOW_SCHEMA_DRIFT",
            "severity": "WARN",
            "message": f"Schema drift count {schema_drift_count} exceeds threshold {max_schema}.",
        })
    if odds_outlier_count > max_outliers:
        alerts.append({
            "code": "LIVE_SHADOW_ODDS_OUTLIERS",
            "severity": "WARN",
            "message": f"Odds outlier count {odds_outlier_count} exceeds threshold {max_outliers}.",
        })
    if identity_mismatch_count > max_identity:
        alerts.append({
            "code": "LIVE_SHADOW_IDENTITY_MISMATCH",
            "severity": "WARN",
            "message": f"Identity mismatch count {identity_mismatch_count} exceeds threshold {max_identity}.",
        })

    return {
        "identity_parity": identity_parity,
        "odds_presence_parity": odds_presence_parity,
        "odds_value_drift": odds_value_drift,
        "schema_drift": schema_drift,
        "summary": {
            "match_count": len(all_match_ids),
            "identity_mismatch_count": identity_mismatch_count,
            "schema_drift_count": schema_drift_count,
            "odds_outlier_count": odds_outlier_count,
            "missing_markets_pct": round(missing_markets_pct, 2),
        },
        "alerts": alerts,
    }


def _identity_dict(data: Any) -> Dict[str, Any]:
    """Extract identity fields for comparison (match_id, home_team, away_team, kickoff_utc)."""
    if not isinstance(data, dict):
        return {}
    return {k: data.get(k) for k in IDENTITY_KEYS if data.get(k) is not None}
