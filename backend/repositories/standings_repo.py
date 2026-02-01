from __future__ import annotations

from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.standings import StandingsRow, StandingsSnapshot
from .base import BaseRepository


class StandingsRepository(BaseRepository[StandingsSnapshot]):
    """Repository for StandingsSnapshot and StandingsRow entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_latest_snapshot(
        self, competition_id: str, season_id: Optional[str] = None
    ) -> Optional[StandingsSnapshot]:
        """Get the most recent standings snapshot for a competition/season."""
        stmt = (
            select(StandingsSnapshot)
            .where(StandingsSnapshot.competition_id == competition_id)
            .order_by(desc(StandingsSnapshot.captured_at_utc))
            .limit(1)
        )
        if season_id is not None:
            stmt = stmt.where(StandingsSnapshot.season_id == season_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_rows(
        self, snapshot_id: int
    ) -> List[StandingsRow]:
        """List all rows for a standings snapshot (ordered by position)."""
        stmt = (
            select(StandingsRow)
            .where(StandingsRow.snapshot_id == snapshot_id)
            .order_by(StandingsRow.position)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
