from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.match import Match
from .base import BaseRepository


class MatchRepository(BaseRepository[Match]):
    """Repository for Match entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, id: str) -> Optional[Match]:
        """Get match by ID."""
        return await super().get_by_id(Match, id)

    async def find_by_competition_and_kickoff(
        self,
        competition_id: str,
        kickoff_from: datetime,
        kickoff_to: datetime,
    ) -> List[Match]:
        """Find matches by competition and kickoff range (uses index)."""
        stmt = (
            select(Match)
            .where(Match.competition_id == competition_id)
            .where(Match.kickoff_utc >= kickoff_from)
            .where(Match.kickoff_utc <= kickoff_to)
            .order_by(Match.kickoff_utc)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_teams_and_kickoff(
        self,
        home_team_id: str,
        away_team_id: str,
        kickoff_from: datetime,
        kickoff_to: datetime,
    ) -> List[Match]:
        """Find matches by teams and kickoff range (uses index)."""
        stmt = (
            select(Match)
            .where(Match.home_team_id == home_team_id)
            .where(Match.away_team_id == away_team_id)
            .where(Match.kickoff_utc >= kickoff_from)
            .where(Match.kickoff_utc <= kickoff_to)
            .order_by(Match.kickoff_utc)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
