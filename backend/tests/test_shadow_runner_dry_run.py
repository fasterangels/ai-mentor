"""
Tests for shadow runner dry-run: produces reports without persisting SnapshotResolution or cache.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from runner.shadow_runner import run_shadow_batch
from repositories.snapshot_resolution_repo import SnapshotResolutionRepository
from repositories.raw_payload_repo import RawPayloadRepository


@pytest.fixture
def test_db():
    """In-memory SQLite with all tables."""
    async def _setup():
        await init_database("sqlite+aiosqlite:///:memory:")
        engine = get_database_manager().engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _teardown():
        await dispose_database()

    asyncio.run(_setup())
    yield
    asyncio.run(_teardown())


@pytest.mark.asyncio
async def test_dry_run_produces_report_with_checksums(test_db) -> None:
    """Dry-run produces BatchReport with run_meta, per_match, checksums, and dry_run=True."""
    async with get_database_manager().session() as session:
        report = await run_shadow_batch(
            session,
            connector_name="dummy",
            match_ids=["dry-m1"],
            dry_run=True,
            final_scores={"dry-m1": {"home": 1, "away": 0}},
        )
    assert report.get("dry_run") is True
    assert report.get("run_meta") is not None
    assert report.get("per_match") is not None
    assert report.get("checksums") is not None
    assert report["checksums"].get("batch_output_checksum") is not None


@pytest.mark.asyncio
async def test_dry_run_does_not_persist_snapshot_resolution(test_db) -> None:
    """Dry-run does not create SnapshotResolution records."""
    async with get_database_manager().session() as session:
        await run_shadow_batch(
            session,
            connector_name="dummy",
            match_ids=["dry-m2"],
            dry_run=True,
            final_scores={"dry-m2": {"home": 0, "away": 0}},
        )
        resolution_repo = SnapshotResolutionRepository(session)
        # List all would require a method; we can count by querying analysis_run_id from resolutions
        from sqlalchemy import select, func
        from models.snapshot_resolution import SnapshotResolution
        result = await session.execute(select(func.count()).select_from(SnapshotResolution))
        count = result.scalar() or 0
    assert count == 0


@pytest.mark.asyncio
async def test_dry_run_does_not_write_cache(test_db) -> None:
    """Dry-run does not add to raw_payloads (cache) for the run."""
    async with get_database_manager().session() as session:
        match_ids = ["dry-cache-1"]
        await run_shadow_batch(
            session,
            connector_name="dummy",
            match_ids=match_ids,
            dry_run=True,
            final_scores={"dry-cache-1": {"home": 0, "away": 0}},
        )
        repo = RawPayloadRepository(session)
        cached_before = await repo.list_distinct_match_ids(source_name="pipeline_cache")
    # The match we ran in dry_run should not appear in cache (we did not write cache)
    assert "dry-cache-1" not in cached_before
