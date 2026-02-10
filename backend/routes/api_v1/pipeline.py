"""POST /api/v1/pipeline/shadow/run — run shadow pipeline (read-only; no policy apply)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from pipeline.report_schema import CANONICAL_FLOW_SHADOW_RUN, REPORT_SCHEMA_VERSION
from pipeline.shadow_pipeline import run_shadow_pipeline
from version import get_version as get_app_version

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post(
    "/shadow/run",
    summary="Run shadow pipeline",
    response_description="PipelineReport (ingestion, analysis, resolution, evaluation checksum, proposal, audit). Does NOT apply policy.",
)
async def shadow_run(
    body: dict,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Run end-to-end shadow pipeline: ingestion -> analysis -> result attach -> evaluation -> tune -> audit.
    Body: connector_name (default dummy), match_id, final_home_goals, final_away_goals, status (default FINAL).
    Returns PipelineReport. Does NOT apply any policy automatically.
    """
    connector_name = (body.get("connector_name") or "dummy").strip()
    match_id = (body.get("match_id") or "").strip()
    if not match_id:
        from datetime import datetime, timezone
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "canonical_flow": CANONICAL_FLOW_SHADOW_RUN,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "app_version": get_app_version(),
            "error": "MISSING_MATCH_ID",
            "detail": "match_id is required",
            "ingestion": {},
            "analysis": {},
            "resolution": {},
            "evaluation_report_checksum": None,
            "proposal": {},
            "audit": {},
        }
    final_home_goals = int(body.get("final_home_goals", 0))
    final_away_goals = int(body.get("final_away_goals", 0))
    status = (body.get("status") or "FINAL").strip()
    report = await run_shadow_pipeline(
        session,
        connector_name=connector_name,
        match_id=match_id,
        final_score={"home": final_home_goals, "away": final_away_goals},
        status=status,
    )
    await session.commit()
    return report
