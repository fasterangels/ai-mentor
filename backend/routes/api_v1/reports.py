"""GET /api/v1/reports/live-shadow/latest, POST ...; GET /api/v1/reports/index, GET /api/v1/reports/item/{run_id}, GET /api/v1/reports/file (read-only viewer)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Header, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from reports.index_store import load_index
from reports.viewer_guard import (
    check_reports_token,
    get_reports_root,
    safe_path_under_reports,
)
from runner.live_shadow_compare_runner import run_live_shadow_compare
from runner.live_shadow_analyze_runner import run_live_shadow_analyze

router = APIRouter(prefix="/reports", tags=["reports"])
INDEX_PATH = "reports/index.json"


def _require_reports_token(x_reports_token: str | None = Header(None, alias="X-Reports-Token")) -> None:
    """Dependency: if REPORTS_READ_TOKEN is set, require X-Reports-Token header to match; else allow."""
    if not check_reports_token(x_reports_token):
        raise HTTPException(status_code=401, detail="Reports access requires valid X-Reports-Token")


@router.post(
    "/live-shadow/run",
    summary="Run LIVE_SHADOW_COMPARE",
    response_description="Diff report (no analyzer, no writes unless LIVE_WRITES_ALLOWED).",
)
def live_shadow_run(body: dict) -> dict:
    """
    Run live shadow compare: pull live + recorded ingestion snapshots, diff, optionally persist.
    Body: connector_name (e.g. real_provider). Requires LIVE_IO_ALLOWED and for real_provider REAL_PROVIDER_LIVE.
    No decisions; no cache/DB writes unless LIVE_WRITES_ALLOWED=true.
    """
    connector_name = (body.get("connector_name") or "").strip() or None
    if not connector_name:
        return {"error": "INVALID_ARGS", "detail": "connector_name required (e.g. real_provider)."}
    return run_live_shadow_compare(connector_name=connector_name)


@router.get(
    "/live-shadow/latest",
    summary="Latest live shadow compare report summary",
    response_description="Summary of latest run from reports/index.json (read-only, no DB).",
)
def live_shadow_latest(index_path: str | None = None) -> dict:
    """
    Return the latest live shadow compare run summary from reports/index.json.
    Does not require database; reads only the index file.
    """
    path = Path(index_path or INDEX_PATH)
    index = load_index(path)
    latest_id = index.get("latest_live_shadow_run_id")
    runs = index.get("live_shadow_runs") or []
    if not latest_id or not runs:
        return {"latest_run_id": None, "summary": None, "runs_count": len(runs)}
    entry = next((r for r in reversed(runs) if r.get("run_id") == latest_id), None)
    if not entry:
        return {"latest_run_id": latest_id, "summary": None, "runs_count": len(runs)}
    return {
        "latest_run_id": latest_id,
        "created_at_utc": entry.get("created_at_utc"),
        "connector_name": entry.get("connector_name"),
        "matches_count": entry.get("matches_count"),
        "summary": entry.get("summary"),
        "alerts_count": entry.get("alerts_count"),
        "runs_count": len(runs),
    }


@router.post(
    "/live-shadow-analyze/run",
    summary="Run LIVE_SHADOW_ANALYZE",
    response_description="Analysis report with decisions, compare vs recorded (no writes unless LIVE_WRITES_ALLOWED).",
)
async def live_shadow_analyze_run(
    body: dict,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Run live shadow analyze: full pipeline with analyzer (decisions ON), compare vs recorded.
    Body: connector_name (e.g. real_provider), match_ids (optional list).
    Requires LIVE_IO_ALLOWED and for real_provider REAL_PROVIDER_LIVE.
    Hard blocks: no DB writes, no cache writes, no policy activation.
    """
    connector_name = (body.get("connector_name") or "").strip() or None
    if not connector_name:
        return {"error": "INVALID_ARGS", "detail": "connector_name required (e.g. real_provider)."}
    match_ids = body.get("match_ids")
    if match_ids is not None and not isinstance(match_ids, list):
        match_ids = [str(m) for m in match_ids] if match_ids else None
    elif match_ids is not None:
        match_ids = [str(m).strip() for m in match_ids if str(m).strip()]
    report = await run_live_shadow_analyze(
        session,
        connector_name=connector_name,
        match_ids=match_ids,
    )
    await session.commit()
    return report


@router.get(
    "/live-shadow-analyze/latest",
    summary="Latest live shadow analyze report summary",
    response_description="Summary of latest run from reports/index.json (read-only, no DB).",
)
def live_shadow_analyze_latest(index_path: str | None = None) -> dict:
    """
    Return the latest live shadow analyze run summary from reports/index.json.
    Does not require database; reads only the index file.
    """
    path = Path(index_path or INDEX_PATH)
    index = load_index(path)
    latest_id = index.get("latest_live_shadow_analyze_run_id")
    runs = index.get("live_shadow_analyze_runs") or []
    if not latest_id or not runs:
        return {"latest_run_id": None, "summary": None, "runs_count": len(runs)}
    entry = next((r for r in reversed(runs) if r.get("run_id") == latest_id), None)
    if not entry:
        return {"latest_run_id": latest_id, "summary": None, "runs_count": len(runs)}
    return {
        "latest_run_id": latest_id,
        "created_at_utc": entry.get("created_at_utc"),
        "connector_name": entry.get("connector_name"),
        "matches_count": entry.get("matches_count"),
        "summary": entry.get("summary"),
        "alerts_count": entry.get("alerts_count"),
        "runs_count": len(runs),
    }


@router.get(
    "/activation/latest",
    summary="Latest activation run summary",
    response_description="Summary of latest activation run from reports/index.json (read-only, no DB).",
)
def activation_latest(index_path: str | None = None) -> dict:
    """
    Return the latest activation run summary from reports/index.json.
    Does not require database; reads only the index file.
    """
    path = Path(index_path or INDEX_PATH)
    index = load_index(path)
    latest_id = index.get("latest_activation_run_id")
    runs = index.get("activation_runs") or []
    if not latest_id or not runs:
        return {"latest_run_id": None, "summary": None, "runs_count": len(runs)}
    entry = next((r for r in reversed(runs) if r.get("run_id") == latest_id), None)
    if not entry:
        return {"latest_run_id": latest_id, "summary": None, "runs_count": len(runs)}
    return {
        "latest_run_id": latest_id,
        "created_at_utc": entry.get("created_at_utc"),
        "connector_name": entry.get("connector_name"),
        "matches_count": entry.get("matches_count"),
        "activated": entry.get("activated", False),
        "reason": entry.get("reason"),
        "activation_summary": entry.get("activation_summary", {}),
        "runs_count": len(runs),
    }


# ---- Read-only reports viewer (path-safe, optional token) ----

RUN_LIST_KEYS = (
    "runs",
    "live_shadow_runs",
    "live_shadow_analyze_runs",
    "activation_runs",
    "burn_in_runs",
    "burn_in_ops_runs",
    "provider_parity_runs",
    "quality_audit_runs",
    "tuning_plan_runs",
)

BUNDLE_PATHS: Dict[str, List[str]] = {
    "burn_in_ops_runs": ["burn_in/{run_id}/summary.json", "burn_in/{run_id}/live_compare.json", "burn_in/{run_id}/live_analyze.json"],
    "tuning_plan_runs": ["tuning_plan/{run_id}.json"],
    "provider_parity_runs": ["provider_parity/{run_id}.json"],
    "live_shadow_runs": ["live_shadow_compare/{run_id}.json"],
    "live_shadow_analyze_runs": ["live_shadow_analyze/{run_id}.json"],
}


@router.get(
    "/index",
    summary="Get reports index",
    response_description="Full reports/index.json (read-only).",
    dependencies=[Depends(_require_reports_token)],
)
def reports_index() -> dict:
    """Return reports/index.json from the configured reports directory."""
    root = get_reports_root()
    index_path = root / "index.json"
    return load_index(index_path)


@router.get(
    "/item/{run_id}",
    summary="Get report item by run_id",
    response_description="Consolidated bundle paths and key summaries for the run.",
    dependencies=[Depends(_require_reports_token)],
)
def reports_item(run_id: str) -> dict:
    """Return which index lists contain this run_id, their entry, and relative paths to report files."""
    root = get_reports_root()
    index = load_index(root / "index.json")
    found: List[Dict[str, Any]] = []
    for key in RUN_LIST_KEYS:
        runs = index.get(key) or []
        if not isinstance(runs, list):
            continue
        entry = next((r for r in runs if r.get("run_id") == run_id), None)
        if not entry:
            continue
        paths: List[str] = []
        if key in BUNDLE_PATHS:
            paths = [p.format(run_id=run_id) for p in BUNDLE_PATHS[key]]
        found.append({"source": key, "entry": entry, "paths": paths})
    if not found:
        return {"run_id": run_id, "found": False, "sources": []}
    return {"run_id": run_id, "found": True, "sources": found}


@router.get(
    "/file",
    summary="Serve a report JSON file (sandboxed under reports/)",
    response_description="JSON file contents or 404.",
    dependencies=[Depends(_require_reports_token)],
)
def reports_file(path: str) -> dict:
    """Serve a report file by relative path under reports/. Path traversal is blocked."""
    root = get_reports_root()
    safe = safe_path_under_reports(root, path)
    if safe is None:
        raise HTTPException(status_code=400, detail="Invalid or disallowed path")
    if not safe.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        text = safe.read_text(encoding="utf-8")
        return json.loads(text)
    except (OSError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=500, detail=f"Read error: {e!s}")
