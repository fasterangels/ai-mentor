from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.raw_payload import RawPayload
from .base import BaseRepository


class RawPayloadRepository(BaseRepository[RawPayload]):
    """Repository for RawPayload entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_distinct_match_ids(self, source_name: str = "pipeline_cache") -> List[str]:
        """Return distinct related_match_id for the given source (ingestion cache)."""
        stmt = (
            select(distinct(RawPayload.related_match_id))
            .where(RawPayload.source_name == source_name)
            .where(RawPayload.related_match_id.isnot(None))
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return sorted([r for r in rows if r])

    async def add_payload(
        self,
        source_name: str,
        domain: str,
        payload_hash: str,
        payload_json: str,
        related_match_id: Optional[str] = None,
    ) -> RawPayload:
        payload = RawPayload(
            source_name=source_name,
            domain=domain,
            fetched_at_utc=datetime.now(timezone.utc),
            payload_hash=payload_hash,
            payload_json=payload_json,
            related_match_id=related_match_id,
        )
        await self.add(payload)
        return payload

    async def exists_by_hash(self, payload_hash: str) -> bool:
        stmt = select(RawPayload).where(RawPayload.payload_hash == payload_hash)
        result = await self.session.execute(stmt)
        return result.first() is not None