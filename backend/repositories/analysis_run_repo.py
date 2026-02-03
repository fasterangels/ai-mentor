from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.analysis_run import AnalysisRun
from .base import BaseRepository


class AnalysisRunRepository(BaseRepository[AnalysisRun]):
    """Repository for AnalysisRun entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, run: AnalysisRun) -> AnalysisRun:
        """Create a new analysis run."""
        await self.add(run)
        return run

    async def get_by_id(self, id: int) -> Optional[AnalysisRun]:
        """Get analysis run by ID."""
        return await super().get_by_id(AnalysisRun, id)

    async def list_recent(self, limit: int = 20) -> List[AnalysisRun]:
        """List recent analysis runs (ordered by creation time, descending)."""
        stmt = (
            select(AnalysisRun)
            .order_by(desc(AnalysisRun.created_at_utc))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_created_between(
        self,
        from_utc: Optional[datetime] = None,
        to_utc: Optional[datetime] = None,
        limit: int = 5000,
    ) -> List[AnalysisRun]:
        """List analysis runs with created_at_utc in [from_utc, to_utc] (inclusive)."""
        stmt = select(AnalysisRun).order_by(desc(AnalysisRun.created_at_utc)).limit(limit)
        if from_utc is not None:
            stmt = stmt.where(AnalysisRun.created_at_utc >= from_utc)
        if to_utc is not None:
            stmt = stmt.where(AnalysisRun.created_at_utc <= to_utc)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
