from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prediction import Prediction
from .base import BaseRepository


class PredictionRepository(BaseRepository[Prediction]):
    """Repository for Prediction entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, prediction: Prediction) -> Prediction:
        """Create a new prediction."""
        await self.add(prediction)
        return prediction

    async def list_by_match(self, match_id: str) -> List[Prediction]:
        """List predictions for a specific match."""
        stmt = (
            select(Prediction)
            .where(Prediction.match_id == match_id)
            .order_by(Prediction.created_at_utc.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_analysis_run(
        self, analysis_run_id: int
    ) -> List[Prediction]:
        """List predictions for a specific analysis run."""
        stmt = (
            select(Prediction)
            .where(Prediction.analysis_run_id == analysis_run_id)
            .order_by(Prediction.created_at_utc)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
