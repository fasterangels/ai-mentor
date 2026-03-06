"""POST /api/v1/pipeline/shadow/run — run shadow pipeline (read-only; no policy apply)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from pipeline.shadow_pipeline import run_shadow_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
logger = logging.getLogger(__name__)


def _json_error(status_code: int, message: str, error_code: str | None = None) -> JSONResponse:
    """Return a consistent JSON error response."""
    content: dict = {"status": "error", "message": message}
    if error_code:
        content["error"] = error_code
    return JSONResponse(status_code=status_code, content=content)


@router.post(
    "/shadow/run",
    summary="Run shadow pipeline",
    response_description="PipelineReport (ingestion, analysis, resolution, evaluation checksum, proposal, audit). Does NOT apply policy.",
)
async def shadow_run(
    body: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Run end-to-end shadow pipeline: ingestion -> analysis -> result attach -> evaluation -> tune -> audit.
    Body: connector_name (default dummy), match_id, final_home_goals, final_away_goals, status (default FINAL).
    Returns PipelineReport (always valid JSON). Does NOT apply any policy automatically.
    """
    try:
        connector_name = (body.get("connector_name") or "dummy").strip()
        match_id = (body.get("match_id") or "").strip()
        if not match_id:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "error",
                    "message": "match_id is required",
                    "error": "MISSING_MATCH_ID",
                    "detail": "match_id is required",
                    "ingestion": {},
                    "analysis": {},
                    "resolution": {},
                    "evaluation_report_checksum": None,
                    "proposal": {},
                    "audit": {},
                    "logs": [],
                },
            )
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
        return JSONResponse(status_code=200, content=report)
    except ValueError as e:
        logger.warning("Shadow run validation error: %s", e, exc_info=True)
        return _json_error(200, str(e), "VALIDATION_ERROR")
    except Exception as e:
        logger.exception("Shadow pipeline failed")
        return _json_error(500, str(e) or "Internal server error", "PIPELINE_ERROR")
