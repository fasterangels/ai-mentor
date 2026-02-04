"""GET /api/v1/reports/live-shadow/latest and POST /api/v1/reports/live-shadow/run."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from reports.index_store import load_index
from runner.live_shadow_compare_runner import run_live_shadow_compare

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
