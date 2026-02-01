from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prediction_outcome import PredictionOutcome
from .base import BaseRepository


class PredictionOutcomeRepository(BaseRepository[PredictionOutcome]):
    """Repository for PredictionOutcome entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, outcome: PredictionOutcome) -> PredictionOutcome:
        """Create a new prediction outcome."""
        await self.add(outcome)
        return outcome

    async def get_by_prediction(
        self, prediction_id: int
    ) -> Optional[PredictionOutcome]:
        """Get outcome for a specific prediction."""
        stmt = select(PredictionOutcome).where(
            PredictionOutcome.prediction_id == prediction_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
