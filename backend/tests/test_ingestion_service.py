"""Ingestion service: ingest_all('dummy') writes cache and returns correct counts."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import ingestion.cache_models  # noqa: F401
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from ingestion.cache_repo import IngestionCacheRepository
from ingestion.ingestion_service import ingest_all


@pytest.fixture
def test_db():
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
async def test_ingest_all_dummy_writes_cache_and_returns_counts(test_db):
    """ingest_all('dummy') fetches 2 matches, writes both, returns fetched_matches=2, cached_writes=2."""
    async with get_database_manager().session() as session:
        summary = await ingest_all(session, "dummy")
    assert summary["fetched_matches"] == 2
    assert summary["cached_writes"] == 2
    assert summary["failures"] == []

    async with get_database_manager().session() as session:
        repo = IngestionCacheRepository(session)
        data1 = await repo.get_latest("dummy-match-1")
        data2 = await repo.get_latest("dummy-match-2")
    assert data1 is not None
    assert data2 is not None
    assert data1.identity.match_id == "dummy-match-1"
    assert data2.identity.match_id == "dummy-match-2"
    assert data1.source == "dummy"
    assert data1.checksum is not None
