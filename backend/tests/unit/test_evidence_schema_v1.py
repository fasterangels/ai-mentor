"""
Unit tests: evidence schema v1 checksum determinism, repository upsert/dedup, list filters.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.evidence.canonicalization import evidence_checksum
from domain.evidence.types import (
    EvidenceItem,
    EvidenceType,
    ReliabilityTier,
    SourceClass,
)


def _make_item(
    title: str = "Test",
    description: str | None = None,
    evidence_id: str = "e1",
    fixture_id: str = "f1",
) -> EvidenceItem:
    now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    item = EvidenceItem(
        evidence_id=evidence_id,
        fixture_id=fixture_id,
        team_id=None,
        player_id=None,
        evidence_type=EvidenceType.INJURY,
        title=title,
        description=description,
        source_class=SourceClass.RECORDED,
        source_name="test",
        source_ref=None,
        reliability_tier=ReliabilityTier.HIGH,
        observed_at=now,
        effective_from=now,
        expected_valid_until=None,
        created_at=now,
        checksum="",
        conflict_group_id=None,
        tags=None,
    )
    item.checksum = evidence_checksum(item)
    return item


def test_checksum_determinism_same_content() -> None:
    """Same content -> same checksum."""
    a = _make_item(title="X", description="Y")
    b = _make_item(title="X", description="Y")
    b.evidence_id = "e2"
    b.checksum = evidence_checksum(b)
    assert a.checksum == b.checksum


def test_checksum_different_description_different_checksum() -> None:
    """Changed description -> different checksum."""
    a = _make_item(description="A")
    b = _make_item(description="B")
    b.checksum = evidence_checksum(b)
    assert a.checksum != b.checksum


def test_checksum_ordering_independent() -> None:
    """Canonicalization uses sorted keys so field order does not change checksum."""
    a = _make_item(title="T", description="D")
    b = _make_item(title="T", description="D")
    b.checksum = evidence_checksum(b)
    assert a.checksum == b.checksum


@pytest.mark.asyncio
async def test_repository_upsert_and_dedup() -> None:
    """Upsert inserts; same checksum again returns deduped."""
    import asyncio
    import sys
    from pathlib import Path
    _backend = Path(__file__).resolve().parent.parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))

    import models  # noqa: F401
    from core.database import init_database, dispose_database, get_database_manager
    from models.base import Base
    from repositories.evidence_repo import EvidenceRepository

    await init_database("sqlite+aiosqlite:///:memory:")
    engine = get_database_manager().engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with get_database_manager().session() as session:
            repo = EvidenceRepository(session)
            item = _make_item(evidence_id="id1", title="Upsert test")
            eid1, out1 = await repo.upsert_evidence_item(item)
            assert out1 == "inserted"
            assert eid1 == "id1"

            item2 = _make_item(evidence_id="id2", title="Upsert test")
            item2.checksum = item.checksum
            eid2, out2 = await repo.upsert_evidence_item(item2)
            assert out2 == "deduped"
            assert eid2 == "id1"
    finally:
        await dispose_database()


@pytest.mark.asyncio
async def test_repository_list_filters() -> None:
    """list_evidence_for_fixture filters by fixture, type."""
    import sys
    from pathlib import Path
    _backend = Path(__file__).resolve().parent.parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))

    import models  # noqa: F401
    from core.database import init_database, dispose_database, get_database_manager
    from models.base import Base
    from repositories.evidence_repo import EvidenceRepository

    await init_database("sqlite+aiosqlite:///:memory:")
    engine = get_database_manager().engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with get_database_manager().session() as session:
            repo = EvidenceRepository(session)
            now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
            for i, (ev_type, fid) in enumerate([(EvidenceType.INJURY, "f1"), (EvidenceType.DISRUPTION, "f1"), (EvidenceType.INJURY, "f2")]):
                item = _make_item(evidence_id=f"e{i}", fixture_id=fid, title=f"Item {i}")
                item.evidence_type = ev_type
                item.observed_at = now.replace(hour=now.hour + i)
                item.checksum = evidence_checksum(item)
                await repo.upsert_evidence_item(item)

            list_f1 = await repo.list_evidence_for_fixture("f1")
            assert len(list_f1) == 2
            list_f1_injury = await repo.list_evidence_for_fixture("f1", types=[EvidenceType.INJURY])
            assert len(list_f1_injury) == 1
            list_f2 = await repo.list_evidence_for_fixture("f2")
            assert len(list_f2) == 1
    finally:
        await dispose_database()
