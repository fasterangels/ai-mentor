from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.fetch_log import SourceFetchLog
from .base import BaseRepository


class FetchLogRepository(BaseRepository[SourceFetchLog]):
    """Repository for SourceFetchLog entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def add_log(
        self,
        source_name: str,
        domain: str,
        status: str,
        latency_ms: int,
        url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SourceFetchLog:
        """Add a fetch log entry."""
        log_entry = SourceFetchLog(
            source_name=source_name,
            domain=domain,
            fetched_at_utc=datetime.now(timezone.utc),
            status=status,
            latency_ms=latency_ms,
            url=url,
            notes=notes,
        )
        await self.add(log_entry)
        return log_entry
