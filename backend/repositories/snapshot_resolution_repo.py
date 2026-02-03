from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.snapshot_resolution import SnapshotResolution
from .base import BaseRepository


class SnapshotResolutionRepository(BaseRepository[SnapshotResolution]):
    """Repository for SnapshotResolution entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, resolution: SnapshotResolution) -> SnapshotResolution:
        """Create a new snapshot resolution."""
        await self.add(resolution)
        return resolution

    async def get_by_analysis_run_id(
        self, analysis_run_id: int
    ) -> Optional[SnapshotResolution]:
        """Get resolution for an analysis run, if any."""
        stmt = select(SnapshotResolution).where(
            SnapshotResolution.analysis_run_id == analysis_run_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
