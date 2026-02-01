from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.competition import Competition
from .base import BaseRepository


class CompetitionRepository(BaseRepository[Competition]):
    """Repository for Competition entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, id: str) -> Optional[Competition]:
        """Get competition by ID."""
        return await super().get_by_id(Competition, id)

    async def get_by_name(self, name: str) -> Optional[Competition]:
        """Get competition by name."""
        stmt = select(Competition).where(Competition.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> List[Competition]:
        """List all active competitions."""
        stmt = select(Competition).where(Competition.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
