"""History: query Prediction + PredictionOutcome for evaluation history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prediction import Prediction
from models.prediction_outcome import PredictionOutcome


async def get_history(session: AsyncSession, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple select: join PredictionOutcome with Prediction.
    result_filter: all | hits | misses.
    If no outcome row → outcome PENDING, final_score null.
    """
    from_utc = params.get("from_utc")
    to_utc = params.get("to_utc")
    result_filter = params.get("result_filter") or "all"
    limit = int(params.get("limit") or 100)

    stmt = (
        select(PredictionOutcome, Prediction)
        .join(Prediction, PredictionOutcome.prediction_id == Prediction.id)
        .order_by(PredictionOutcome.evaluated_at_utc.desc())
        .limit(limit)
    )
    if from_utc:
        try:
            dt = datetime.fromisoformat(from_utc.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            stmt = stmt.where(PredictionOutcome.evaluated_at_utc >= dt)
        except (ValueError, AttributeError):
            pass
    if to_utc:
        try:
            dt = datetime.fromisoformat(to_utc.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            stmt = stmt.where(PredictionOutcome.evaluated_at_utc <= dt)
        except (ValueError, AttributeError):
            pass
    if result_filter == "hits":
        stmt = stmt.where(PredictionOutcome.hit_bool == True)
    elif result_filter == "misses":
        stmt = stmt.where(PredictionOutcome.hit_bool == False)

    result = await session.execute(stmt)
    rows: List[Dict[str, Any]] = []
    for outcome, pred in result.all():
        evaluated_at = outcome.evaluated_at_utc
        if hasattr(evaluated_at, "isoformat"):
            created_at_utc = evaluated_at.isoformat()
        else:
            created_at_utc = str(evaluated_at)
        final_score = f"{outcome.final_home_score}-{outcome.final_away_score}"
        outcome_str = "HIT" if outcome.hit_bool else "MISS"
        match_label = f"Match {outcome.match_id}"
        rows.append({
            "created_at_utc": created_at_utc,
            "match_label": match_label,
            "market": pred.market,
            "decision": pred.decision,
            "final_score": final_score,
            "outcome": outcome_str,
        })
    return {"rows": rows}
