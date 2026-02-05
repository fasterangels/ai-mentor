"""
Integration tests: activation rollout (deterministic subset) and daily cap.
Phase 25 / RFC-001. No external network; uses stub_live_platform and temp index.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

import models  # noqa: F401
from core.database import dispose_database, get_database_manager, init_database
from dev.stub_server import create_stub_app
from models.base import Base
from reports.index_store import save_index
from runner.shadow_runner import run_shadow_batch


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


@pytest.fixture
def stub_client():
    """Local stub server (no external IO)."""
    return TestClient(create_stub_app())


@pytest.mark.asyncio
async def test_expanded_tier_rollout_pct_activates_only_deterministic_subset(test_db, stub_client, tmp_path) -> None:
    """Expanded tier with rollout_pct=50 activates only the first 50% of match_ids (stable sort)."""
    from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
    from ingestion.registry import get_connector, register_connector

    index_path = tmp_path / "index.json"
    save_index({"activation_runs": [], "burn_in_ops_runs": []}, index_path)

    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "expanded")
        m.setenv("ACTIVATION_TIER", "expanded")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "stub_live_platform")
        m.setenv("ACTIVATION_MARKETS", "1X2")
        m.setenv("ACTIVATION_MAX_MATCHES", "10")
        m.setenv("ACTIVATION_ROLLOUT_PCT", "50")
        m.setenv("ACTIVATION_DAILY_MAX_ACTIVATIONS", "0")  # 0 = no cap (unlimited for this test)
        m.setenv("ACTIVATION_MIN_CONFIDENCE", "0.5")

        adapter = StubLivePlatformAdapter(base_url="http://testserver")
        adapter._base_url = "http://testserver"
        adapter._client = stub_client

        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            # 4 match_ids; sorted: a1, b2, c3, d4. 50% -> first 2 (a1, b2) in rollout set
            match_ids = ["d4", "a1", "c3", "b2"]
            now = datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
            final_scores = {mid: {"home": 1, "away": 0} for mid in match_ids}

            async with get_database_manager().session() as session:
                report = await run_shadow_batch(
                    session,
                    connector_name="stub_live_platform",
                    match_ids=match_ids,
                    now_utc=now,
                    final_scores=final_scores,
                    activation=True,
                    index_path=str(index_path),
                )

            assert report.get("error") is None
            act = report.get("activation") or {}
            assert act.get("tier") == "expanded"
            assert act.get("rollout_pct") == 50.0
            # Deterministic: only first 50% (2 of 4) can be in rollout set
            assert act.get("eligible_count") == 4
            activated_matches = act.get("activated_matches") or []
            sorted_ids = sorted(match_ids)
            expected_rollout_set = set(sorted_ids[:2])  # first 2
            assert set(activated_matches) <= expected_rollout_set, (
                f"activated_matches {activated_matches} must be subset of rollout set {expected_rollout_set}"
            )
            assert act.get("activated_count") <= 2
        finally:
            if original:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_daily_cap_prevents_activation_when_exceeded(test_db, stub_client, tmp_path) -> None:
    """When daily activations already at cap, batch activates 0 and reason mentions daily cap."""
    from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
    from ingestion.registry import get_connector, register_connector

    today = datetime.now(timezone.utc).date().isoformat()
    index = {
        "activation_runs": [
            {
                "run_id": "prev-run",
                "created_at_utc": f"{today}T10:00:00Z",
                "connector_name": "stub_live_platform",
                "matches_count": 2,
                "activated": True,
                "activated_count": 2,
            },
        ],
        "burn_in_ops_runs": [],
    }
    index_path = tmp_path / "index.json"
    save_index(index, index_path)

    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "expanded")
        m.setenv("ACTIVATION_TIER", "expanded")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "stub_live_platform")
        m.setenv("ACTIVATION_MARKETS", "1X2")
        m.setenv("ACTIVATION_MAX_MATCHES", "10")
        m.setenv("ACTIVATION_ROLLOUT_PCT", "100")
        m.setenv("ACTIVATION_DAILY_MAX_ACTIVATIONS", "2")  # cap 2, already 2 used today
        m.setenv("ACTIVATION_MIN_CONFIDENCE", "0.5")

        adapter = StubLivePlatformAdapter(base_url="http://testserver")
        adapter._base_url = "http://testserver"
        adapter._client = stub_client

        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            match_ids = ["m1", "m2"]
            now = datetime(2025, 10, 1, 14, 0, 0, tzinfo=timezone.utc)
            final_scores = {mid: {"home": 1, "away": 0} for mid in match_ids}

            async with get_database_manager().session() as session:
                report = await run_shadow_batch(
                    session,
                    connector_name="stub_live_platform",
                    match_ids=match_ids,
                    now_utc=now,
                    final_scores=final_scores,
                    activation=True,
                    index_path=str(index_path),
                )

            assert report.get("error") is None
            act = report.get("activation") or {}
            assert act.get("daily_cap_remaining_before_run") == 0
            assert act.get("activated_count") == 0
            reason = (act.get("reason") or "").lower()
            assert "daily" in reason or "cap" in reason
        finally:
            if original:
                register_connector("stub_live_platform", original)
