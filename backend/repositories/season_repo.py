from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.season import Season
from .base import BaseRepository


class SeasonRepository(BaseRepository[Season]):
    """Repository for Season entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, id: str) -> Optional[Season]:
        """Get season by ID."""
        return await super().get_by_id(Season, id)

    async def list_by_competition(
        self, competition_id: str
    ) -> List[Season]:
        """List seasons for a specific competition."""
        stmt = (
            select(Season)
            .where(Season.competition_id == competition_id)
            .order_by(Season.year_start.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
