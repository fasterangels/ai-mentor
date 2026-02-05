"""
Offline cache repository: upsert and read latest IngestedMatchData by match_id.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.cache_models import IngestedMatchCache
from ingestion.schema import IngestedMatchData, MatchIdentity


def _payload_to_data(payload_json: str) -> IngestedMatchData:
    """Deserialize payload JSON to IngestedMatchData (with datetime parsing)."""
    raw = json.loads(payload_json)
    return IngestedMatchData.model_validate(raw)


class IngestionCacheRepository:
    """Repository for ingested match cache (no base class; custom API)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        match_id: str,
        connector_name: str,
        collected_at_utc: datetime,
        payload_json: str,
        payload_checksum: str,
    ) -> None:
        """Insert or replace cache row for match_id (one row per match, latest wins)."""
        existing = await self.session.get(IngestedMatchCache, match_id)
        if existing:
            existing.connector_name = connector_name
            existing.collected_at_utc = collected_at_utc
            existing.payload_json = payload_json
            existing.payload_checksum = payload_checksum
            self.session.add(existing)
        else:
            row = IngestedMatchCache(
                match_id=match_id,
                connector_name=connector_name,
                collected_at_utc=collected_at_utc,
                payload_json=payload_json,
                payload_checksum=payload_checksum,
            )
            self.session.add(row)

    async def get_latest(self, match_id: str) -> Optional[IngestedMatchData]:
        """Return latest cached payload for match_id or None."""
        row = await self.session.get(IngestedMatchCache, match_id)
        if row is None:
            return None
        return _payload_to_data(row.payload_json)

    async def list_latest_matches(
        self, connector_name: str
    ) -> List[MatchIdentity]:
        """Return MatchIdentity list from cached payloads for this connector."""
        stmt = select(IngestedMatchCache).where(
            IngestedMatchCache.connector_name == connector_name
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        identities: List[MatchIdentity] = []
        for row in rows:
            data = _payload_to_data(row.payload_json)
            identities.append(data.identity)
        return identities
