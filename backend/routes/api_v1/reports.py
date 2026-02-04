"""GET /api/v1/reports/live-shadow/latest, POST /api/v1/reports/live-shadow/run, GET /api/v1/reports/live-shadow-analyze/latest, POST /api/v1/reports/live-shadow-analyze/run."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from reports.index_store import load_index
from runner.live_shadow_compare_runner import run_live_shadow_compare
from runner.live_shadow_analyze_runner import run_live_shadow_analyze

router = APIRouter(prefix="/reports", tags=["reports"])
INDEX_PATH = "reports/index.json"


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
