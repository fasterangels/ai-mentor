from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.source_mapping import SourceEntityMap
from .base import BaseRepository


class SourceMappingRepository(BaseRepository[SourceEntityMap]):
    """Repository for SourceEntityMap entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_mapping(
        self,
        source_name: str,
        entity_type: str,
        source_entity_id: str,
    ) -> Optional[SourceEntityMap]:
        """Get mapping by source name, entity type, and source entity ID."""
        stmt = (
            select(SourceEntityMap)
            .where(SourceEntityMap.source_name == source_name)
            .where(SourceEntityMap.entity_type == entity_type)
            .where(SourceEntityMap.source_entity_id == source_entity_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_mapping(
        self,
        source_name: str,
        entity_type: str,
        source_entity_id: str,
        canonical_entity_id: str,
        mapping_confidence: float = 1.0,
    ) -> SourceEntityMap:
        """Upsert a mapping (SELECT + UPDATE/INSERT, no DB-specific UPSERT)."""
        existing = await self.get_mapping(
            source_name, entity_type, source_entity_id
        )
        if existing:
            existing.canonical_entity_id = canonical_entity_id
            existing.mapping_confidence = mapping_confidence
            existing.updated_at_utc = datetime.now(timezone.utc)
            return existing
        else:
            new_mapping = SourceEntityMap(
                source_name=source_name,
                entity_type=entity_type,
                source_entity_id=source_entity_id,
                canonical_entity_id=canonical_entity_id,
                mapping_confidence=mapping_confidence,
                updated_at_utc=datetime.now(timezone.utc),
            )
            await self.add(new_mapping)
            return new_mapping
