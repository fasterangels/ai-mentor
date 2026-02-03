"""Ingestion API: connectors list, run dummy, cache endpoints."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import ingestion.cache_models  # noqa: F401
import pytest
from httpx import ASGITransport, AsyncClient

from core.dependencies import get_db_session
from core.database import init_database, dispose_database, get_database_manager
from main import app
from models.base import Base


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
async def test_get_connectors_includes_dummy(test_db):
    """GET /api/v1/ingestion/connectors returns list including 'dummy'."""
    async def override_session():
        async with get_database_manager().session() as s:
            yield s

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.get("/api/v1/ingestion/connectors")
    app.dependency_overrides.pop(get_db_session, None)
    assert r.status_code == 200
    data = r.json()
    assert "connectors" in data
    assert "dummy" in data["connectors"]


@pytest.mark.asyncio
async def test_post_run_dummy_returns_summary(test_db):
    """POST /api/v1/ingestion/run/dummy runs ingestion and returns summary."""
    async def override_session():
        async with get_database_manager().session() as s:
            yield s

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.post("/api/v1/ingestion/run/dummy")
    app.dependency_overrides.pop(get_db_session, None)
    assert r.status_code == 200
    data = r.json()
    assert data["fetched_matches"] == 2
    assert data["cached_writes"] == 2
    assert data["failures"] == []


@pytest.mark.asyncio
async def test_get_cache_matches_after_run(test_db):
    """GET /api/v1/ingestion/cache/matches/dummy returns cached identities after run."""
    async def override_session():
        async with get_database_manager().session() as s:
            yield s

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.post("/api/v1/ingestion/run/dummy")
        r = await client.get("/api/v1/ingestion/cache/matches/dummy")
    app.dependency_overrides.pop(get_db_session, None)
    assert r.status_code == 200
    data = r.json()
    assert "identities" in data
    assert len(data["identities"]) == 2
    ids = {i["match_id"] for i in data["identities"]}
    assert ids == {"dummy-match-1", "dummy-match-2"}


@pytest.mark.asyncio
async def test_get_cache_match_returns_payload_or_404(test_db):
    """GET /api/v1/ingestion/cache/match/{match_id} returns payload or 404."""
    async def override_session():
        async with get_database_manager().session() as s:
            yield s

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.post("/api/v1/ingestion/run/dummy")
        r = await client.get("/api/v1/ingestion/cache/match/dummy-match-1")
        r404 = await client.get("/api/v1/ingestion/cache/match/nonexistent")
    app.dependency_overrides.pop(get_db_session, None)
    assert r.status_code == 200
    data = r.json()
    assert data["identity"]["match_id"] == "dummy-match-1"
    assert data["source"] == "dummy"
    assert data["checksum"] is not None
    assert r404.status_code == 404
