"""Snapshot resolution repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.snapshot_resolution import SnapshotResolution
from .base import BaseRepository


class SnapshotResolutionRepository(BaseRepository[SnapshotResolution]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, resolution: SnapshotResolution) -> SnapshotResolution:
        await self.add(resolution)
        return resolution

    async def get_by_id(self, id: int) -> Optional[SnapshotResolution]:
        return await super().get_by_id(SnapshotResolution, id)

    async def get_by_analysis_run_id(self, analysis_run_id: int) -> Optional[SnapshotResolution]:
        stmt = select(SnapshotResolution).where(
            SnapshotResolution.analysis_run_id == analysis_run_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_created_between(
        self,
        from_utc: Optional[datetime] = None,
        to_utc: Optional[datetime] = None,
        limit: int = 5000,
    ) -> List[SnapshotResolution]:
        stmt = select(SnapshotResolution).order_by(SnapshotResolution.created_at_utc.desc()).limit(limit)
        if from_utc is not None:
            stmt = stmt.where(SnapshotResolution.created_at_utc >= from_utc)
        if to_utc is not None:
            stmt = stmt.where(SnapshotResolution.created_at_utc <= to_utc)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
