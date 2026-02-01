"""GET /api/v1/evaluation/kpis and GET /api/v1/evaluation/history."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from evaluation.metrics import get_kpis
from services.history_service import get_history

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/kpis")
async def get_evaluation_kpis(
    period: str = Query(..., description="DAY | WEEK | MONTH"),
    reference_date_utc: str = Query(..., description="ISO datetime UTC"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return KPIReport as JSON."""
    try:
        dt = datetime.fromisoformat(reference_date_utc.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        dt = datetime.now(timezone.utc)
    period_upper = period.upper() if period else "DAY"
    if period_upper not in ("DAY", "WEEK", "MONTH"):
        period_upper = "DAY"
    report = await get_kpis(session, period_upper, dt)
    return {
        "period": report.period,
        "reference_date_utc": report.reference_date_utc.isoformat() if hasattr(report.reference_date_utc, "isoformat") else str(report.reference_date_utc),
        "total_predictions": report.total_predictions,
        "hits": report.hits,
        "misses": report.misses,
        "hit_rate": report.hit_rate,
        "miss_rate": report.miss_rate,
    }


@router.get("/history")
async def get_evaluation_history(
    from_utc: str | None = Query(None, alias="from"),
    to_utc: str | None = Query(None, alias="to"),
    result_filter: str | None = Query("all", description="all | hits | misses"),
    filter: str | None = Query(None, include_in_schema=False),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return rows: created_at_utc, match_label, market, decision, final_score, outcome."""
    rf = (filter or result_filter or "all").lower()
    if rf not in ("all", "hits", "misses"):
        rf = "all"
    params = {
        "from_utc": from_utc,
        "to_utc": to_utc,
        "result_filter": rf,
        "limit": limit,
    }
    return await get_history(session, params)
