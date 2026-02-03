"""POST /api/v1/results/attach — attach final result to a snapshot and resolve outcomes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from services.results_attach_service import attach_result

router = APIRouter(prefix="/results", tags=["results"])


class AttachResultBody(BaseModel):
    """
    Body for POST /results/attach.

    snapshot_id is exactly the analysis_run_id (integer as string). There is no separate
    snapshot entity: one snapshot = one analysis run.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "snapshot_id": "1",
                "home_goals": 2,
                "away_goals": 1,
                "status": "FINAL",
            }
        }
    )

    snapshot_id: str = Field(
        ...,
        description="Same as analysis_run_id: the analysis run id as string (e.g. '1'). One snapshot = one analysis run.",
    )
    home_goals: int = Field(..., ge=0, description="Home team goals")
    away_goals: int = Field(..., ge=0, description="Away team goals")
    status: str = Field(
        default="FINAL",
        description="Match status: FINAL | ABANDONED | POSTPONED | UNKNOWN",
    )


@router.post(
    "/attach",
    summary="Attach final result and resolve outcomes",
    description="Load snapshot by id (snapshot_id = analysis_run_id), write final result, compute market outcomes (SUCCESS/FAILURE/NEUTRAL), persist and return.",
)
async def post_results_attach(
    body: AttachResultBody,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Attach final match result to a snapshot and resolve per-market outcomes.

    - **snapshot_id**: Exactly the analysis_run_id as string (e.g. "1"). One snapshot = one analysis run.
    - **home_goals**, **away_goals**: must be >= 0.
    - **status**: FINAL (default) | ABANDONED | POSTPONED | UNKNOWN.

    Returns snapshot_id, market_outcomes (one_x_two, over_under_25, gg_ng), final_result.
    """
    if body.status not in ("FINAL", "ABANDONED", "POSTPONED", "UNKNOWN"):
        raise HTTPException(
            status_code=400,
            detail="status must be one of: FINAL, ABANDONED, POSTPONED, UNKNOWN",
        )
    try:
        return await attach_result(
            session,
            snapshot_id=body.snapshot_id,
            home_goals=body.home_goals,
            away_goals=body.away_goals,
            status=body.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
