"""
Burn-in ops: single pipeline ingestion -> live shadow compare -> live shadow analyze -> (optional) burn-in activation.
Writes one consolidated report bundle under reports/burn_in/<run_id>/ and updates index.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.live_io import get_connector_safe
from reports.index_store import append_burn_in_ops_run, append_activation_run, load_index, save_index
from limits.limits import prune_burn_in_ops_bundles

BURN_IN_OPS_SUBDIR = "burn_in"
INDEX_PATH = "reports/index.json"


def _run_id() -> str:
    return f"burn_in_ops_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


async def run_burn_in_ops(
    session: AsyncSession,
    connector_name: str,
    match_ids: Optional[List[str]] = None,
    *,
    enable_activation: bool = False,
    dry_run: bool = False,
    reports_dir: str | Path = "reports",
    index_path: str | Path = INDEX_PATH,
    live_adapter: Any = None,
    recorded_adapter: Any = None,
    max_bundles_retained: int = 30,
) -> Dict[str, Any]:
    """
    Run: ingestion (match list) -> live shadow compare -> live shadow analyze -> (optional) burn-in activation.
    Writes bundle to reports/burn_in/<run_id>/ and appends one entry to index.
    When dry_run=True, still builds result but may skip writing to disk (caller can check).
    """
    run_id = _run_id()
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"
    reports_path = Path(reports_dir)
    bundle_dir = reports_path / BURN_IN_OPS_SUBDIR / run_id

    adapter = live_adapter or get_connector_safe(connector_name)
    if not adapter:
        return {
            "run_id": run_id,
            "error": "CONNECTOR_NOT_AVAILABLE",
            "detail": f"Connector {connector_name!r} not available (check LIVE_IO_ALLOWED and connector env).",
            "status": "error",
        }
    if match_ids is None:
        match_ids = sorted(m.match_id for m in adapter.fetch_matches())
    else:
        match_ids = sorted(match_ids)

    if not match_ids:
        return {
            "run_id": run_id,
            "error": "NO_MATCHES",
            "detail": "No matches from connector or provided list.",
            "status": "error",
        }

    # 1) Live shadow compare
    from runner.live_shadow_compare_runner import run_live_shadow_compare, _connector_supports_live_and_recorded

    compare_report: Dict[str, Any] = {}
    if _connector_supports_live_and_recorded(connector_name):
        compare_report = run_live_shadow_compare(
            connector_name=connector_name,
            match_ids=match_ids,
            reports_dir=str(reports_path),
            index_path=str(index_path),
        )
    elif live_adapter is not None and recorded_adapter is not None:
        compare_report = run_live_shadow_compare(
            live_adapter=live_adapter,
            recorded_adapter=recorded_adapter,
            match_ids=match_ids,
            reports_dir=str(reports_path),
            index_path=str(index_path),
        )
    else:
        compare_report = run_live_shadow_compare(
            live_adapter=adapter,
            recorded_adapter=adapter,
            match_ids=match_ids,
            reports_dir=str(reports_path),
            index_path=str(index_path),
        )
    if compare_report.get("error"):
        compare_report["status"] = "error"

    # 2) Live shadow analyze
    from runner.live_shadow_analyze_runner import run_live_shadow_analyze

    analyze_report: Dict[str, Any] = {}
    try:
        analyze_report = await run_live_shadow_analyze(
            session,
            connector_name=connector_name,
            match_ids=match_ids,
            reports_dir=reports_path,
            index_path=index_path,
        )
    except Exception as e:
        analyze_report = {"error": "LIVE_SHADOW_ANALYZE_FAILED", "detail": str(e), "status": "error"}
    if analyze_report.get("error"):
        analyze_report["status"] = "error"

    # 3) Optional burn-in activation (shadow batch with activation=True)
    batch_report: Dict[str, Any] = {}
    activated = False
    activated_count = 0
    if enable_activation and not dry_run:
        from runner.shadow_runner import run_shadow_batch
        batch_report = await run_shadow_batch(
            session,
            connector_name=connector_name,
            match_ids=match_ids,
            activation=True,
            index_path=index_path,
        )
        if not batch_report.get("error"):
            act = batch_report.get("activation") or {}
            activated = act.get("activated", False)
            activated_count = int(act.get("activated_count", 0))

    alerts_count = 0
    for r in (compare_report, analyze_report):
        alerts_count += len(r.get("alerts") or [])
    status = "ok"
    if compare_report.get("error") or analyze_report.get("error"):
        status = "error"

    bundle = {
        "run_id": run_id,
        "created_at_utc": created_at,
        "connector_name": connector_name,
        "matches_count": len(match_ids),
        "status": status,
        "alerts_count": alerts_count,
        "activated": activated,
        "live_compare": compare_report,
        "live_analyze": analyze_report,
        "shadow_batch": batch_report if batch_report else None,
    }

    if not dry_run:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (bundle_dir / "summary.json").write_text(_stable_json({
            "run_id": run_id,
            "created_at_utc": created_at,
            "connector_name": connector_name,
            "matches_count": len(match_ids),
            "status": status,
            "alerts_count": alerts_count,
            "activated": activated,
        }), encoding="utf-8")
        (bundle_dir / "live_compare.json").write_text(_stable_json(compare_report), encoding="utf-8")
        (bundle_dir / "live_analyze.json").write_text(_stable_json(analyze_report), encoding="utf-8")
        if batch_report:
            (bundle_dir / "shadow_batch.json").write_text(_stable_json(batch_report), encoding="utf-8")

        index = load_index(index_path)
        append_burn_in_ops_run(index, {
            "run_id": run_id,
            "created_at_utc": created_at,
            "status": status,
            "alerts_count": alerts_count,
            "activated": activated,
            "activated_count": activated_count,
            "matches_count": len(match_ids),
            "connector_name": connector_name,
        })
        if activated and activated_count > 0:
            append_activation_run(index, {
                "run_id": run_id,
                "created_at_utc": created_at,
                "connector_name": connector_name,
                "matches_count": len(match_ids),
                "activated": True,
                "activated_count": activated_count,
                "reason": None,
                "activation_summary": (batch_report.get("activation") or {}),
            })
        prune_burn_in_ops_bundles(reports_path / BURN_IN_OPS_SUBDIR, index, max_retained=max_bundles_retained)
        save_index(index, index_path)

    bundle["_bundle_dir"] = str(bundle_dir)
    return bundle
