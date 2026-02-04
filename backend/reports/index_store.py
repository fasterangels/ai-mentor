"""
Reports index: load/save index.json with stable JSON (sorted keys).
Index structure: runs (list of run entries), latest_run_id.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _stable_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def load_index(path: str | Path = "reports/index.json") -> Dict[str, Any]:
    """
    Load index from path. Returns dict with keys: runs (list), latest_run_id (str or None),
    live_shadow_runs (list), latest_live_shadow_run_id (str or None),
    live_shadow_analyze_runs (list), latest_live_shadow_analyze_run_id (str or None).
    If file does not exist or is invalid JSON, returns empty index (no crash).
    """
    path = Path(path)
    if not path.exists():
        return {
            "runs": [],
            "latest_run_id": None,
            "live_shadow_runs": [],
            "latest_live_shadow_run_id": None,
            "live_shadow_analyze_runs": [],
            "latest_live_shadow_analyze_run_id": None,
            "activation_runs": [],
            "latest_activation_run_id": None,
            "burn_in_runs": [],
            "latest_burn_in_run_id": None,
            "provider_parity_runs": [],
            "latest_provider_parity_run_id": None,
            "quality_audit_runs": [],
            "latest_quality_audit_run_id": None,
        }
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (json.JSONDecodeError, OSError):
        return {
            "runs": [],
            "latest_run_id": None,
            "live_shadow_runs": [],
            "latest_live_shadow_run_id": None,
            "live_shadow_analyze_runs": [],
            "latest_live_shadow_analyze_run_id": None,
            "activation_runs": [],
            "latest_activation_run_id": None,
            "burn_in_runs": [],
            "latest_burn_in_run_id": None,
            "provider_parity_runs": [],
            "latest_provider_parity_run_id": None,
            "quality_audit_runs": [],
            "latest_quality_audit_run_id": None,
        }
    runs = data.get("runs")
    if not isinstance(runs, list):
        runs = []
    live_shadow_runs = data.get("live_shadow_runs")
    if not isinstance(live_shadow_runs, list):
        live_shadow_runs = []
    live_shadow_analyze_runs = data.get("live_shadow_analyze_runs")
    if not isinstance(live_shadow_analyze_runs, list):
        live_shadow_analyze_runs = []
    activation_runs = data.get("activation_runs")
    if not isinstance(activation_runs, list):
        activation_runs = []
    burn_in_runs = data.get("burn_in_runs")
    if not isinstance(burn_in_runs, list):
        burn_in_runs = []
    provider_parity_runs = data.get("provider_parity_runs")
    if not isinstance(provider_parity_runs, list):
        provider_parity_runs = []
    quality_audit_runs = data.get("quality_audit_runs")
    if not isinstance(quality_audit_runs, list):
        quality_audit_runs = []
    return {
        "runs": runs,
        "latest_run_id": data.get("latest_run_id"),
        "live_shadow_runs": live_shadow_runs,
        "latest_live_shadow_run_id": data.get("latest_live_shadow_run_id"),
        "live_shadow_analyze_runs": live_shadow_analyze_runs,
        "latest_live_shadow_analyze_run_id": data.get("latest_live_shadow_analyze_run_id"),
        "activation_runs": activation_runs,
        "latest_activation_run_id": data.get("latest_activation_run_id"),
        "burn_in_runs": burn_in_runs,
        "latest_burn_in_run_id": data.get("latest_burn_in_run_id"),
        "provider_parity_runs": provider_parity_runs,
        "latest_provider_parity_run_id": data.get("latest_provider_parity_run_id"),
        "quality_audit_runs": quality_audit_runs,
        "latest_quality_audit_run_id": data.get("latest_quality_audit_run_id"),
    }


def append_run(index: Dict[str, Any], run_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a run entry to the index and set latest_run_id.
    run_meta must include: run_id, created_at_utc, connector_name, matches_count,
    batch_output_checksum, alerts_count. May include live_io_alerts_count.
    Returns updated index (mutates and returns the same dict).
    """
    runs: List[Dict[str, Any]] = index.get("runs") or []
    entry = {
        "run_id": run_meta.get("run_id"),
        "created_at_utc": run_meta.get("created_at_utc"),
        "connector_name": run_meta.get("connector_name"),
        "matches_count": run_meta.get("matches_count"),
        "batch_output_checksum": run_meta.get("batch_output_checksum"),
        "alerts_count": run_meta.get("alerts_count"),
    }
    if run_meta.get("live_io_alerts_count") is not None:
        entry["live_io_alerts_count"] = run_meta["live_io_alerts_count"]
    runs.append(entry)
    index["runs"] = runs
    index["latest_run_id"] = run_meta.get("run_id")
    return index


def append_live_shadow_run(index: Dict[str, Any], run_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a live shadow compare run entry. run_meta: run_id, created_at_utc, connector_name,
    matches_count, summary (dict), alerts_count.
    Sets latest_live_shadow_run_id. Returns updated index.
    """
    runs: List[Dict[str, Any]] = index.get("live_shadow_runs") or []
    entry = {
        "run_id": run_meta.get("run_id"),
        "created_at_utc": run_meta.get("created_at_utc"),
        "connector_name": run_meta.get("connector_name"),
        "matches_count": run_meta.get("matches_count"),
        "summary": run_meta.get("summary"),
        "alerts_count": run_meta.get("alerts_count"),
    }
    runs.append(entry)
    index["live_shadow_runs"] = runs
    index["latest_live_shadow_run_id"] = run_meta.get("run_id")
    return index


def append_live_shadow_analyze_run(index: Dict[str, Any], run_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a live shadow analyze run entry. run_meta: run_id, created_at_utc, connector_name,
    matches_count, summary (dict), alerts_count.
    Sets latest_live_shadow_analyze_run_id. Returns updated index.
    """
    runs: List[Dict[str, Any]] = index.get("live_shadow_analyze_runs") or []
    entry = {
        "run_id": run_meta.get("run_id"),
        "created_at_utc": run_meta.get("created_at_utc"),
        "connector_name": run_meta.get("connector_name"),
        "matches_count": run_meta.get("matches_count"),
        "summary": run_meta.get("summary"),
        "alerts_count": run_meta.get("alerts_count"),
    }
    runs.append(entry)
    index["live_shadow_analyze_runs"] = runs
    index["latest_live_shadow_analyze_run_id"] = run_meta.get("run_id")
    return index


def append_activation_run(index: Dict[str, Any], run_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append an activation run entry. run_meta: run_id, created_at_utc, connector_name,
    matches_count, activated (bool), reason (str or None), activation_summary (dict).
    Sets latest_activation_run_id. Returns updated index.
    """
    runs: List[Dict[str, Any]] = index.get("activation_runs") or []
    entry = {
        "run_id": run_meta.get("run_id"),
        "created_at_utc": run_meta.get("created_at_utc"),
        "connector_name": run_meta.get("connector_name"),
        "matches_count": run_meta.get("matches_count"),
        "activated": run_meta.get("activated", False),
        "reason": run_meta.get("reason"),
        "activation_summary": run_meta.get("activation_summary", {}),
    }
    runs.append(entry)
    index["activation_runs"] = runs
    index["latest_activation_run_id"] = run_meta.get("run_id")
    return index


def append_burn_in_run(index: Dict[str, Any], run_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a burn-in run summary. run_meta: run_id, created_at_utc, connector_name,
    matches_count, burn_in_summary (dict with activated_matches, rejected_matches,
    rejected_reasons, burn_in_confidence_gate, guardrail_state).
    Sets latest_burn_in_run_id. Returns updated index.
    """
    runs: List[Dict[str, Any]] = index.get("burn_in_runs") or []
    entry = {
        "run_id": run_meta.get("run_id"),
        "created_at_utc": run_meta.get("created_at_utc"),
        "connector_name": run_meta.get("connector_name"),
        "matches_count": run_meta.get("matches_count"),
        "burn_in_summary": run_meta.get("burn_in_summary", {}),
    }
    runs.append(entry)
    index["burn_in_runs"] = runs
    index["latest_burn_in_run_id"] = run_meta.get("run_id")
    return index


def append_provider_parity_run(index: Dict[str, Any], run_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a provider parity run. run_meta: run_id, created_at_utc, provider_a, provider_b,
    matches_count, summary (dict), alerts_count.
    Sets latest_provider_parity_run_id. Returns updated index.
    """
    runs: List[Dict[str, Any]] = index.get("provider_parity_runs") or []
    entry = {
        "run_id": run_meta.get("run_id"),
        "created_at_utc": run_meta.get("created_at_utc"),
        "provider_a": run_meta.get("provider_a"),
        "provider_b": run_meta.get("provider_b"),
        "matches_count": run_meta.get("matches_count"),
        "summary": run_meta.get("summary"),
        "alerts_count": run_meta.get("alerts_count"),
    }
    runs.append(entry)
    index["provider_parity_runs"] = runs
    index["latest_provider_parity_run_id"] = run_meta.get("run_id")
    return index


def append_quality_audit_run(index: Dict[str, Any], run_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a quality audit run. run_meta: run_id, created_at_utc, run_count, summary (dict).
    Sets latest_quality_audit_run_id. Returns updated index.
    """
    runs: List[Dict[str, Any]] = index.get("quality_audit_runs") or []
    entry = {
        "run_id": run_meta.get("run_id"),
        "created_at_utc": run_meta.get("created_at_utc"),
        "run_count": run_meta.get("run_count"),
        "summary": run_meta.get("summary"),
    }
    runs.append(entry)
    index["quality_audit_runs"] = runs
    index["latest_quality_audit_run_id"] = run_meta.get("run_id")
    return index


def save_index(index: Dict[str, Any], path: str | Path) -> None:
    """Persist index to path with stable JSON (sorted keys)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_stable_dumps(index), encoding="utf-8")
