"""
LIVE_SHADOW_COMPARE run mode: compare live vs recorded ingestion only (no analyzer, no decisions).
Hard block cache/persistence unless LIVE_WRITES_ALLOWED=true.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ingestion.connectors.platform_base import DataConnector, IngestedMatchData
from reports.live_shadow_compare import (
    DEFAULT_POLICY,
    build_snapshot_list,
    compare,
    ingested_to_dict,
)
from reports.index_store import append_live_shadow_run, load_index, save_index


MODE_LIVE_SHADOW_COMPARE = "LIVE_SHADOW_COMPARE"
REPORTS_SUBDIR = "live_shadow_compare"
INDEX_PATH = "reports/index.json"


def _run_id() -> str:
    """Deterministic run id for report file and index."""
    return f"live_shadow_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _live_writes_allowed() -> bool:
    return os.environ.get("LIVE_WRITES_ALLOWED", "").strip().lower() in ("1", "true", "yes")


def run_live_shadow_compare(
    connector_name: Optional[str] = None,
    match_ids: Optional[List[str]] = None,
    live_adapter: Optional[DataConnector] = None,
    recorded_adapter: Optional[DataConnector] = None,
    live_snapshots: Optional[List[Dict[str, Any]]] = None,
    recorded_snapshots: Optional[List[Dict[str, Any]]] = None,
    policy: Optional[Dict[str, Any]] = None,
    reports_dir: str | Path = "reports",
    index_path: str | Path = INDEX_PATH,
) -> Dict[str, Any]:
    """
    Run LIVE_SHADOW_COMPARE: build live and recorded ingestion snapshots, diff them, optionally persist.
    - No analyzer is invoked (normalization only).
    - No cache or DB writes unless LIVE_WRITES_ALLOWED=true.
    Either pass (live_adapter, recorded_adapter) for tests, or connector_name and rely on env for live/recorded.
    Snapshots can be pre-built as live_snapshots / recorded_snapshots (each list of {"match_id": str, "data": dict|None}).
    """
    policy = policy or DEFAULT_POLICY

    if live_snapshots is not None and recorded_snapshots is not None:
        # Pre-built snapshots (e.g. from tests)
        live_list = live_snapshots
        recorded_list = recorded_snapshots
        match_ids_used = sorted(set(s["match_id"] for s in live_list) | set(s["match_id"] for s in recorded_list))
        connector_used = connector_name or "stub"
    elif live_adapter is not None and recorded_adapter is not None:
        # Use adapters to build snapshots
        if match_ids is None:
            match_ids_used = sorted(m.match_id for m in live_adapter.fetch_matches())
        else:
            match_ids_used = sorted(match_ids)
        live_list = [{"match_id": mid, "data": ingested_to_dict(d) if d else None} for mid in match_ids_used for d in [live_adapter.fetch_match_data(mid)]]
        recorded_list = [{"match_id": mid, "data": ingested_to_dict(d) if d else None} for mid in match_ids_used for d in [recorded_adapter.fetch_match_data(mid)]]
        live_list.sort(key=lambda x: x["match_id"])
        recorded_list.sort(key=lambda x: x["match_id"])
        connector_used = live_adapter.name
    elif connector_name and _connector_supports_live_and_recorded(connector_name):
        # Use connector with env toggling (e.g. real_provider): live first, then recorded
        from ingestion.live_io import get_connector_safe
        live_adapter = get_connector_safe(connector_name)
        if not live_adapter:
            return {"error": "CONNECTOR_NOT_AVAILABLE", "detail": "Live connector not available (set REAL_PROVIDER_LIVE and LIVE_IO_ALLOWED for real_provider)."}
        with _recorded_env(connector_name):
            rec_adapter = get_connector_safe(connector_name)
        if not rec_adapter:
            return {"error": "CONNECTOR_NOT_AVAILABLE", "detail": "Recorded connector not available (recorded path requires connector in recorded mode)."}
        match_ids_used = sorted(m.match_id for m in live_adapter.fetch_matches())
        live_list = [{"match_id": mid, "data": ingested_to_dict(d) if d else None} for mid in match_ids_used for d in [live_adapter.fetch_match_data(mid)]]
        recorded_list = [{"match_id": mid, "data": ingested_to_dict(d) if d else None} for mid in match_ids_used for d in [rec_adapter.fetch_match_data(mid)]]
        connector_used = connector_name
    else:
        return {"error": "INVALID_ARGS", "detail": "Provide (live_adapter + recorded_adapter) or (live_snapshots + recorded_snapshots) or connector_name that supports live+recorded."}

    # Deterministic ordering
    live_list.sort(key=lambda x: x["match_id"])
    recorded_list.sort(key=lambda x: x["match_id"])

    diff_report = compare(live_list, recorded_list, policy=policy)
    summary = diff_report.get("summary") or {}
    alerts = diff_report.get("alerts") or []

    run_id = _run_id()
    created_at = datetime.now(timezone.utc).isoformat()
    report_payload = {
        "run_id": run_id,
        "created_at_utc": created_at,
        "mode": MODE_LIVE_SHADOW_COMPARE,
        "connector_name": connector_used,
        "match_ids": match_ids_used,
        "live_ingestion_snapshot": live_list,
        "recorded_ingestion_snapshot": recorded_list,
        "diff_report": diff_report,
    }

    if _live_writes_allowed():
        reports_path = Path(reports_dir) / REPORTS_SUBDIR
        reports_path.mkdir(parents=True, exist_ok=True)
        report_file = reports_path / f"{run_id}.json"
        import json
        report_file.write_text(json.dumps(report_payload, sort_keys=True, indent=2, default=str), encoding="utf-8")
        index = load_index(index_path)
        append_live_shadow_run(index, {
            "run_id": run_id,
            "created_at_utc": created_at,
            "connector_name": connector_used,
            "matches_count": len(match_ids_used),
            "summary": summary,
            "alerts_count": len(alerts),
        })
        save_index(index, index_path)
        report_payload["_report_path"] = str(report_file)

    return report_payload


def _connector_supports_live_and_recorded(name: str) -> bool:
    """True if connector can be used in both live and recorded mode via env (e.g. real_provider)."""
    return name == "real_provider"


class _recorded_env:
    """Context manager to set env for recorded path (e.g. REAL_PROVIDER_LIVE=0)."""

    def __init__(self, connector_name: str) -> None:
        self.connector_name = connector_name
        self._saved: Dict[str, str] = {}

    def __enter__(self) -> None:
        if self.connector_name == "real_provider":
            self._saved["REAL_PROVIDER_LIVE"] = os.environ.get("REAL_PROVIDER_LIVE", "")
            os.environ["REAL_PROVIDER_LIVE"] = "0"

    def __exit__(self, *args: Any) -> None:
        if self.connector_name == "real_provider" and "REAL_PROVIDER_LIVE" in self._saved:
            os.environ["REAL_PROVIDER_LIVE"] = self._saved["REAL_PROVIDER_LIVE"]
