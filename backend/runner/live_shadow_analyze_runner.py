"""
LIVE_SHADOW_ANALYZE run mode: full pipeline with decisions (analyzer ON), hard block persistence.
Compare live vs recorded analysis: picks, confidence, reasons, coverage.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.shadow_pipeline import run_shadow_pipeline
from reports.live_shadow_analyze_guardrails import (
    DEFAULT_POLICY,
    compare_analysis,
    evaluate,
)
from reports.index_store import append_live_shadow_analyze_run, load_index, save_index
from runner.live_shadow_compare_runner import _connector_supports_live_and_recorded


MODE_LIVE_SHADOW_ANALYZE = "LIVE_SHADOW_ANALYZE"
REPORTS_SUBDIR = "live_shadow_analyze"
INDEX_PATH = "reports/index.json"


def _run_id() -> str:
    """Deterministic run id for report file and index."""
    return f"live_shadow_analyze_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _live_writes_allowed() -> bool:
    return os.environ.get("LIVE_WRITES_ALLOWED", "").strip().lower() in ("1", "true", "yes")


async def run_live_shadow_analyze(
    session: AsyncSession,
    connector_name: str,
    match_ids: Optional[List[str]] = None,
    recorded_connector_name: Optional[str] = None,
    *,
    now_utc: Optional[datetime] = None,
    final_scores: Optional[Dict[str, Dict[str, int]]] = None,
    policy: Optional[Dict[str, Any]] = None,
    reports_dir: str | Path = "reports",
    index_path: str | Path = INDEX_PATH,
) -> Dict[str, Any]:
    """
    Run LIVE_SHADOW_ANALYZE: full pipeline with analyzer (decisions ON), hard block persistence.
    - Runs live path via connector_name (requires LIVE_IO_ALLOWED and for real_provider REAL_PROVIDER_LIVE).
    - Runs recorded path for same match_ids (via recorded_connector_name if provided, else connector_name with recorded env).
    - Compares analysis results: picks, confidence, reasons, coverage.
    - Hard blocks: no DB writes, no cache writes, no policy activation (tuner outputs ignored).
    - Analyzer invoked exactly once per snapshot (live and recorded).
    - Audit generated but read-only.
    """
    from ingestion.live_io import get_connector_safe
    from runner.live_shadow_compare_runner import _recorded_env

    policy = policy or DEFAULT_POLICY
    now = now_utc or datetime.now(timezone.utc)
    final_scores = final_scores or {}

    # Get match_ids from live connector if not provided
    if match_ids is None:
        live_adapter = get_connector_safe(connector_name)
        if not live_adapter:
            return {"error": "CONNECTOR_NOT_AVAILABLE", "detail": "Live connector not available (check LIVE_IO_ALLOWED and connector env)."}
        match_ids = sorted(m.match_id for m in live_adapter.fetch_matches())
    else:
        match_ids = sorted(match_ids)

    if not match_ids:
        return {"error": "NO_MATCHES", "detail": "No matches found or provided."}

    # Run live analysis (hard block persistence: dry_run=True)
    live_reports: Dict[str, Dict[str, Any]] = {}
    for match_id in match_ids:
        score = final_scores.get(match_id) or {"home": 0, "away": 0}
        try:
            report = await run_shadow_pipeline(
                session,
                connector_name=connector_name,
                match_id=match_id,
                final_score=score,
                status="FINAL",
                now_utc=now,
                dry_run=True,
                hard_block_persistence=True,  # Hard block ALL persistence
            )
            if report.get("error"):
                continue
            live_reports[match_id] = report
        except Exception as e:  # noqa: BLE001
            continue

    # Run recorded analysis (same match_ids, recorded connector)
    recorded_reports: Dict[str, Dict[str, Any]] = {}
    recorded_conn = recorded_connector_name or connector_name
    if recorded_connector_name:
        # Use different connector for recorded (e.g. sample_platform for stub_live_platform)
        recorded_adapter = get_connector_safe(recorded_conn)
        if recorded_adapter:
            for match_id in match_ids:
                score = final_scores.get(match_id) or {"home": 0, "away": 0}
                try:
                    report = await run_shadow_pipeline(
                        session,
                        connector_name=recorded_conn,
                        match_id=match_id,
                        final_score=score,
                        status="FINAL",
                        now_utc=now,
                        dry_run=True,
                        hard_block_persistence=True,
                    )
                    if report.get("error"):
                        continue
                    recorded_reports[match_id] = report
                except Exception as e:  # noqa: BLE001
                    continue
    elif _connector_supports_live_and_recorded(connector_name):
        # Use connector with env toggling (e.g. real_provider)
        with _recorded_env(connector_name):
            recorded_adapter = get_connector_safe(connector_name)
            if recorded_adapter:
                for match_id in match_ids:
                    score = final_scores.get(match_id) or {"home": 0, "away": 0}
                    try:
                        report = await run_shadow_pipeline(
                            session,
                            connector_name=connector_name,
                            match_id=match_id,
                            final_score=score,
                            status="FINAL",
                            now_utc=now,
                            dry_run=True,
                            hard_block_persistence=True,  # Hard block ALL persistence
                        )
                        if report.get("error"):
                            continue
                        recorded_reports[match_id] = report
                    except Exception as e:  # noqa: BLE001
                        continue

    # Compare per-match and aggregate
    per_match_compare: List[Dict[str, Any]] = []
    all_alerts: List[Dict[str, Any]] = []
    for match_id in match_ids:
        live_analysis = live_reports.get(match_id, {}).get("analysis") or {}
        recorded_analysis = recorded_reports.get(match_id, {}).get("analysis") or {}
        if not live_analysis or not recorded_analysis:
            continue
        compare_result = compare_analysis(
            {"analysis": live_analysis},
            {"analysis": recorded_analysis},
        )
        match_alerts = evaluate(
            {"analysis": live_analysis},
            {"analysis": recorded_analysis},
            policy=policy,
        )
        per_match_compare.append({
            "match_id": match_id,
            "compare": compare_result,
            "alerts": match_alerts,
        })
        all_alerts.extend(match_alerts)

    # Aggregate summary
    total_matches = len(per_match_compare)
    pick_changes = sum(1 for m in per_match_compare for p in (m.get("compare", {}).get("pick_parity") or {}).values() if not p.get("parity", True))
    coverage_drops = sum(len(m.get("compare", {}).get("coverage_diff", {}).get("missing_in_live", [])) for m in per_match_compare)

    run_id = _run_id()
    created_at = now.isoformat()
    report_payload = {
        "run_id": run_id,
        "created_at_utc": created_at,
        "mode": MODE_LIVE_SHADOW_ANALYZE,
        "connector_name": connector_name,
        "match_ids": match_ids,
        "live_analysis_reports": live_reports,
        "recorded_analysis_reports": recorded_reports,
        "per_match_compare": per_match_compare,
        "summary": {
            "total_matches": total_matches,
            "pick_changes": pick_changes,
            "coverage_drops": coverage_drops,
            "alerts_count": len(all_alerts),
        },
        "alerts": all_alerts,
    }

    if _live_writes_allowed():
        reports_path = Path(reports_dir) / REPORTS_SUBDIR
        reports_path.mkdir(parents=True, exist_ok=True)
        report_file = reports_path / f"{run_id}.json"
        import json
        report_file.write_text(json.dumps(report_payload, sort_keys=True, indent=2, default=str), encoding="utf-8")
        index = load_index(index_path)
        append_live_shadow_analyze_run(index, {
            "run_id": run_id,
            "created_at_utc": created_at,
            "connector_name": connector_name,
            "matches_count": total_matches,
            "summary": report_payload["summary"],
            "alerts_count": len(all_alerts),
        })
        save_index(index, index_path)
        report_payload["_report_path"] = str(report_file)

    return report_payload


