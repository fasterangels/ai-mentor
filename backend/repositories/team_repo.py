from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.team import Team
from models.team_alias import TeamAlias
from .base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Repository for Team entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, id: str) -> Optional[Team]:
        """Get team by ID."""
        return await super().get_by_id(Team, id)

    async def get_by_name(self, name: str) -> Optional[Team]:
        """Get team by exact name."""
        stmt = select(Team).where(Team.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> List[Team]:
        """List all active teams."""
        stmt = select(Team).where(Team.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_alias(
        self, alias_norm: str
    ) -> Optional[Team]:
        """Find team by normalized alias (uses index on alias_norm)."""
        stmt = (
            select(Team)
            .join(TeamAlias, Team.id == TeamAlias.team_id)
            .where(TeamAlias.alias_norm == alias_norm)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
