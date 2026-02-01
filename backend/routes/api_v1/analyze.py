"""POST /api/v1/analyze — resolver + pipeline + analyzer flow."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from services.analysis_service import run_analysis_flow

router = APIRouter()


@router.post("/analyze")
async def post_analyze(
    body: dict,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Accept JSON: home_text, away_text, kickoff_hint_utc?, window_hours?, competition_id?, mode?, markets?, policy?.
    Return 200 with status OK | NO_PREDICTION | AMBIGUOUS | NOT_FOUND, match_id, resolver, evidence_pack?, analyzer?.
    """
    if not isinstance(body, dict):
        body = {}
    result = await run_analysis_flow(session, body)
    return result
