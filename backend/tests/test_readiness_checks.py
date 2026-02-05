"""
Tests for readiness checks: PASS in normal setup.
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
from readiness.checks import run_readiness_checks


@pytest.fixture
def repo_with_workflows(tmp_path: Path) -> Path:
    """Create a minimal .github/workflows dir with one yml."""
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("name: CI\n")
    return tmp_path


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
async def test_readiness_returns_pass_for_ci_workflow(repo_with_workflows: Path) -> None:
    """CI workflow check PASS when .github/workflows has yml."""
    results = await run_readiness_checks(repo_root=repo_with_workflows)
    codes = {r["code"]: r for r in results}
    assert "CI_WORKFLOW" in codes
    assert codes["CI_WORKFLOW"]["status"] == "PASS"


@pytest.mark.asyncio
async def test_readiness_policy_loads() -> None:
    """Policy check PASS when default policy loads."""
    results = await run_readiness_checks()
    codes = {r["code"]: r for r in results}
    assert "POLICY" in codes
    assert codes["POLICY"]["status"] == "PASS"


@pytest.mark.asyncio
async def test_readiness_ingestion_cache_with_session(test_db) -> None:
    """Ingestion cache check PASS when session provided and table exists."""
    async with get_database_manager().session() as session:
        results = await run_readiness_checks(session=session)
    codes = {r["code"]: r for r in results}
    assert "INGESTION_CACHE" in codes
    assert codes["INGESTION_CACHE"]["status"] == "PASS"


@pytest.mark.asyncio
async def test_readiness_shadow_endpoint_with_app(test_db) -> None:
    """Shadow endpoint check PASS when app provided and endpoint responds."""
    from main import app
    results = await run_readiness_checks(app=app)
    codes = {r["code"]: r for r in results}
    assert "SHADOW_ENDPOINT" in codes
    assert codes["SHADOW_ENDPOINT"]["status"] == "PASS"


@pytest.mark.asyncio
async def test_readiness_no_fail_in_normal_setup(test_db, repo_with_workflows) -> None:
    """In normal setup (workflows + session + app), no check is FAIL."""
    from main import app
    async with get_database_manager().session() as session:
        results = await run_readiness_checks(
            repo_root=repo_with_workflows,
            session=session,
            app=app,
        )
    for r in results:
        assert r["status"] != "FAIL", f"Check {r['code']} should not FAIL: {r['message']}"
