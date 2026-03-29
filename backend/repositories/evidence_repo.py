"""
Repository for evidence items v1 (injuries, news, etc.).
Upsert: do not overwrite existing except to fill missing optional fields; audit when update occurs.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.evidence.types import (
    EvidenceItem,
    EvidenceType,
    ReliabilityTier,
    SourceClass,
)
from models.evidence_item import EvidenceItemV1

from .base import BaseRepository


def _tags_to_json(tags: Optional[List[str]]) -> Optional[str]:
    if not tags:
        return None
    return json.dumps(tags)


def _json_to_tags(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _row_to_item(row: EvidenceItemV1) -> EvidenceItem:
    """Map DB row to domain EvidenceItem."""
    return EvidenceItem(
        evidence_id=row.evidence_id,
        fixture_id=row.fixture_id,
        team_id=row.team_id,
        player_id=row.player_id,
        evidence_type=EvidenceType(row.evidence_type),
        title=row.title,
        description=row.description,
        source_class=SourceClass(row.source_class),
        source_name=row.source_name,
        source_ref=row.source_ref,
        reliability_tier=ReliabilityTier(row.reliability_tier),
        observed_at=row.observed_at,
        effective_from=row.effective_from,
        expected_valid_until=row.expected_valid_until,
        created_at=row.created_at,
        checksum=row.checksum,
        conflict_group_id=row.conflict_group_id,
        tags=_json_to_tags(row.tags),
    )


def _item_to_row(item: EvidenceItem) -> EvidenceItemV1:
    """Map domain EvidenceItem to DB row (new)."""
    return EvidenceItemV1(
        evidence_id=item.evidence_id,
        fixture_id=item.fixture_id,
        team_id=item.team_id,
        player_id=item.player_id,
        evidence_type=item.evidence_type.value,
        title=item.title[:256] if item.title else "",
        description=item.description[:2000] if item.description else None,
        source_class=item.source_class.value,
        source_name=item.source_name,
        source_ref=item.source_ref,
        reliability_tier=item.reliability_tier.value,
        observed_at=item.observed_at,
        effective_from=item.effective_from,
        expected_valid_until=item.expected_valid_until,
        created_at=item.created_at,
        checksum=item.checksum,
        conflict_group_id=item.conflict_group_id,
        tags=_tags_to_json(item.tags),
    )


class EvidenceRepository(BaseRepository[EvidenceItemV1]):
    """Repository for evidence_items_v1. Upsert is additive (fill missing only)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def find_by_checksum(self, checksum: str) -> Optional[EvidenceItem]:
        """Return one evidence item by checksum, or None."""
        stmt = select(EvidenceItemV1).where(EvidenceItemV1.checksum == checksum)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _row_to_item(row)

    async def get_by_evidence_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        """Return one evidence item by evidence_id, or None."""
        row = await self.session.get(EvidenceItemV1, evidence_id)
        if row is None:
            return None
        return _row_to_item(row)

    async def list_evidence_for_fixture(
        self,
        fixture_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        types: Optional[List[EvidenceType]] = None,
    ) -> List[EvidenceItem]:
        """List evidence for a fixture with optional time and type filters."""
        stmt = select(EvidenceItemV1).where(EvidenceItemV1.fixture_id == fixture_id)
        if since is not None:
            stmt = stmt.where(EvidenceItemV1.observed_at >= since)
        if until is not None:
            stmt = stmt.where(EvidenceItemV1.observed_at <= until)
        if types:
            type_values = [t.value for t in types]
            stmt = stmt.where(EvidenceItemV1.evidence_type.in_(type_values))
        stmt = stmt.order_by(EvidenceItemV1.observed_at)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [_row_to_item(r) for r in rows]

    async def upsert_evidence_item(
        self,
        item: EvidenceItem,
        on_update: Optional[Callable[[EvidenceItemV1, EvidenceItem], None]] = None,
    ) -> tuple[str, str]:
        """
        Insert or update (fill missing optional fields only).
        Returns (evidence_id, outcome): "inserted" | "deduped" | "updated".
        """
        existing_by_checksum = await self.find_by_checksum(item.checksum)
        if existing_by_checksum is not None:
            return existing_by_checksum.evidence_id, "deduped"

        existing_row = await self.session.get(EvidenceItemV1, item.evidence_id)
        if existing_row is not None:
            updated = False
            if existing_row.description is None and item.description is not None:
                existing_row.description = item.description[:2000]
                updated = True
            if existing_row.source_ref is None and item.source_ref is not None:
                existing_row.source_ref = item.source_ref
                updated = True
            if existing_row.effective_from is None and item.effective_from is not None:
                existing_row.effective_from = item.effective_from
                updated = True
            if existing_row.expected_valid_until is None and item.expected_valid_until is not None:
                existing_row.expected_valid_until = item.expected_valid_until
                updated = True
            if existing_row.conflict_group_id is None and item.conflict_group_id is not None:
                existing_row.conflict_group_id = item.conflict_group_id
                updated = True
            if existing_row.tags is None and item.tags is not None:
                existing_row.tags = _tags_to_json(item.tags)
                updated = True
            if updated and on_update:
                on_update(existing_row, item)
            self.session.add(existing_row)
            return item.evidence_id, "updated"

        row = _item_to_row(item)
        await self.add(row)
        return item.evidence_id, "inserted"
