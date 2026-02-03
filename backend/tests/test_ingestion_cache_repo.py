"""Cache repo: upsert + get_latest roundtrip; list_latest_matches."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import ingestion.cache_models  # noqa: F401 — register table with Base.metadata
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from ingestion.cache_repo import IngestionCacheRepository
from ingestion.schema import IngestedMatchData, MatchIdentity, MatchState, OddsSnapshot


@pytest.fixture
def test_db():
    """In-memory SQLite with all tables including ingested_match_cache."""
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


def _sample_data(match_id: str) -> IngestedMatchData:
    identity = MatchIdentity(
        match_id=match_id,
        home_team="H",
        away_team="A",
        competition="C",
        kickoff_utc=datetime(2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
    )
    return IngestedMatchData(
        identity=identity,
        odds=[],
        state=MatchState(minute=None, score_home=None, score_away=None, status="SCHEDULED"),
    )


@pytest.mark.asyncio
async def test_upsert_get_latest_roundtrip(test_db):
    """Upsert then get_latest returns the same payload."""
    async with get_database_manager().session() as session:
        repo = IngestionCacheRepository(session)
        data = _sample_data("match-1")
        data.source = "dummy"
        data.collected_at_utc = datetime.now(timezone.utc)
        data.checksum = "abc123"
        payload_json = data.model_dump_json()
        await repo.upsert(
            match_id="match-1",
            connector_name="dummy",
            collected_at_utc=data.collected_at_utc,
            payload_json=payload_json,
            payload_checksum="abc123",
        )
    async with get_database_manager().session() as session:
        repo = IngestionCacheRepository(session)
        out = await repo.get_latest("match-1")
        assert out is not None
        assert out.identity.match_id == "match-1"
        assert out.identity.home_team == "H"


@pytest.mark.asyncio
async def test_get_latest_missing_returns_none(test_db):
    """get_latest for unknown match_id returns None."""
    async with get_database_manager().session() as session:
        repo = IngestionCacheRepository(session)
        out = await repo.get_latest("nonexistent")
        assert out is None


@pytest.mark.asyncio
async def test_list_latest_matches_returns_identities(test_db):
    """list_latest_matches returns MatchIdentity list for connector."""
    async with get_database_manager().session() as session:
        repo = IngestionCacheRepository(session)
        for mid in ("m1", "m2"):
            data = _sample_data(mid)
            data.source = "dummy"
            data.collected_at_utc = datetime.now(timezone.utc)
            data.checksum = "x"
            await repo.upsert(
                match_id=mid,
                connector_name="dummy",
                collected_at_utc=data.collected_at_utc,
                payload_json=data.model_dump_json(),
                payload_checksum="x",
            )
    async with get_database_manager().session() as session:
        repo = IngestionCacheRepository(session)
        identities = await repo.list_latest_matches("dummy")
        assert len(identities) == 2
        ids = {i.match_id for i in identities}
        assert ids == {"m1", "m2"}
