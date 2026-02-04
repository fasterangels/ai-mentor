"""
MULTI_PROVIDER_PARITY run mode: ingest same match set from provider A and B (recorded by default),
produce parity report under reports/provider_parity/<run_id>.json, append summary to index.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ingestion.connectors.platform_base import DataConnector
from ingestion.live_io import get_connector_safe
from ingestion.parity.provider_parity import compare
from reports.index_store import append_provider_parity_run, load_index, save_index
from reports.live_shadow_compare import ingested_to_dict

MODE_MULTI_PROVIDER_PARITY = "MULTI_PROVIDER_PARITY"
REPORTS_SUBDIR = "provider_parity"
INDEX_PATH = "reports/index.json"


def _run_id() -> str:
    return f"parity_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def run_provider_parity(
    provider_a_name: str,
    provider_b_name: str,
    match_ids: Optional[List[str]] = None,
    policy: Optional[Dict[str, Any]] = None,
    reports_dir: str | Path = "reports",
    index_path: str | Path = INDEX_PATH,
) -> Dict[str, Any]:
    """
    Run MULTI_PROVIDER_PARITY: ingest same match set from A and B (recorded fixtures by default),
    compare via provider_parity.compare, write report to reports/provider_parity/<run_id>.json,
    append summary to index. No live calls in tests (connectors via get_connector_safe = recorded-first).
    """
    adapter_a = get_connector_safe(provider_a_name)
    adapter_b = get_connector_safe(provider_b_name)
    if not adapter_a:
        return {"error": "CONNECTOR_NOT_AVAILABLE", "detail": f"Provider A {provider_a_name!r} not available (use recorded-first connector)."}
    if not adapter_b:
        return {"error": "CONNECTOR_NOT_AVAILABLE", "detail": f"Provider B {provider_b_name!r} not available (use recorded-first connector)."}

    if match_ids is None:
        ids_a = {m.match_id for m in adapter_a.fetch_matches()}
        ids_b = {m.match_id for m in adapter_b.fetch_matches()}
        match_ids = sorted(ids_a | ids_b)
    else:
        match_ids = sorted(set(match_ids))

    list_a: List[Dict[str, Any]] = []
    list_b: List[Dict[str, Any]] = []
    for mid in match_ids:
        d_a = adapter_a.fetch_match_data(mid) if isinstance(adapter_a, DataConnector) else None
        d_b = adapter_b.fetch_match_data(mid) if isinstance(adapter_b, DataConnector) else None
        list_a.append({"match_id": mid, "data": ingested_to_dict(d_a) if d_a else None})
        list_b.append({"match_id": mid, "data": ingested_to_dict(d_b) if d_b else None})

    parity_report = compare(list_a, list_b, policy=policy)
    summary = parity_report.get("summary") or {}
    alerts = parity_report.get("alerts") or []

    run_id = _run_id()
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"

    report_payload: Dict[str, Any] = {
        "run_id": run_id,
        "created_at_utc": created_at,
        "provider_a": provider_a_name,
        "provider_b": provider_b_name,
        "match_ids": match_ids,
        "matches_count": len(match_ids),
        "parity": parity_report,
        "summary": summary,
        "alerts": alerts,
        "alerts_count": len(alerts),
    }

    reports_path = Path(reports_dir)
    out_dir = reports_path / REPORTS_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / f"{run_id}.json"
    report_file.write_text(json.dumps(report_payload, sort_keys=True, separators=(",", ":"), default=str), encoding="utf-8")

    index = load_index(index_path)
    append_provider_parity_run(index, {
        "run_id": run_id,
        "created_at_utc": created_at,
        "provider_a": provider_a_name,
        "provider_b": provider_b_name,
        "matches_count": len(match_ids),
        "summary": summary,
        "alerts_count": len(alerts),
    })
    save_index(index, index_path)
    report_payload["_report_path"] = str(report_file)
    return report_payload
