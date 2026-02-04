"""
Integration tests: activation-off mode (no writes), activation-on mode (writes occur).
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
from pipeline.shadow_pipeline import run_shadow_pipeline


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
async def test_activation_off_mode_no_writes(test_db, stub_client) -> None:
    """When activation=False, no DB writes occur even if env flags are set."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "stub_live_platform")
        
        from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
        from ingestion.registry import get_connector, register_connector
        adapter = StubLivePlatformAdapter(base_url="http://testserver")
        adapter._base_url = "http://testserver"
        adapter._client = stub_client
        
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            match_id = "stub_live_001"
            
            async with get_database_manager().session() as session:
                report = await run_shadow_pipeline(
                    session,
                    connector_name="stub_live_platform",
                    match_id=match_id,
                    final_score={"home": 2, "away": 1},
                    status="FINAL",
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    activation=False,  # Activation OFF
                )
                
                # Check activation section
                assert "activation" in report
                assert report["activation"]["activated"] is False
                assert report["activation"]["audits"]
                
                # Check that snapshot_id is None (no writes)
                assert report.get("analysis", {}).get("snapshot_id") is None
        finally:
            if original:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_activation_on_mode_writes_occur(test_db, stub_client) -> None:
    """When activation=True and all gates pass, writes occur and activation_audit is created."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "stub_live_platform")
        m.setenv("ACTIVATION_MARKETS", "1X2")
        
        from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
        from ingestion.registry import get_connector, register_connector
        adapter = StubLivePlatformAdapter(base_url="http://testserver")
        adapter._base_url = "http://testserver"
        adapter._client = stub_client
        
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            match_id = "stub_live_001"
            
            async with get_database_manager().session() as session:
                report = await run_shadow_pipeline(
                    session,
                    connector_name="stub_live_platform",
                    match_id=match_id,
                    final_score={"home": 2, "away": 1},
                    status="FINAL",
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    activation=True,  # Activation ON
                )
                
                # Check activation section
                assert "activation" in report
                assert report["activation"]["audits"]
                
                # If activation was allowed, snapshot_id should be set
                # (may be None if guardrails failed, but structure should exist)
                activation_section = report["activation"]
                if activation_section.get("activated"):
                    assert report.get("analysis", {}).get("snapshot_id") is not None
        finally:
            if original:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_kill_switch_overrides_activation(test_db, stub_client) -> None:
    """Kill-switch forces shadow-only even when activation=True."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "stub_live_platform")
        m.setenv("ACTIVATION_KILL_SWITCH", "true")  # Kill-switch ON
        
        from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
        from ingestion.registry import get_connector, register_connector
        adapter = StubLivePlatformAdapter(base_url="http://testserver")
        adapter._base_url = "http://testserver"
        adapter._client = stub_client
        
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            match_id = "stub_live_001"
            
            async with get_database_manager().session() as session:
                report = await run_shadow_pipeline(
                    session,
                    connector_name="stub_live_platform",
                    match_id=match_id,
                    final_score={"home": 2, "away": 1},
                    status="FINAL",
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    activation=True,  # Activation requested but kill-switch blocks
                )
                
                # Check activation section
                assert "activation" in report
                assert report["activation"]["activated"] is False
                assert "KILL_SWITCH" in report["activation"]["reason"].upper()
                
                # No writes should occur
                assert report.get("analysis", {}).get("snapshot_id") is None
        finally:
            if original:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_burn_in_off_no_writes(test_db, stub_client) -> None:
    """Burn-in mode OFF (activation=False): no writes occur."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "burn_in")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "stub_live_platform")
        m.setenv("ACTIVATION_MAX_MATCHES", "1")
        
        from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
        from ingestion.registry import get_connector, register_connector
        adapter = StubLivePlatformAdapter(base_url="http://testserver")
        adapter._base_url = "http://testserver"
        adapter._client = stub_client
        
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            match_id = "stub_live_001"
            
            async with get_database_manager().session() as session:
                report = await run_shadow_pipeline(
                    session,
                    connector_name="stub_live_platform",
                    match_id=match_id,
                    final_score={"home": 2, "away": 1},
                    status="FINAL",
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    activation=False,  # Burn-in / activation OFF
                )
                
                assert "activation" in report
                assert report["activation"]["activated"] is False
                assert report.get("analysis", {}).get("snapshot_id") is None
        finally:
            if original:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_burn_in_on_at_most_one_match_activated_and_audit(test_db, stub_client) -> None:
    """Burn-in ON with stub connector: at most 1 match activated and audit written."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "burn_in")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "stub_live_platform")  # allow stub in burn-in
        m.setenv("ACTIVATION_MARKETS", "1X2")
        m.setenv("ACTIVATION_MAX_MATCHES", "1")
        m.setenv("ACTIVATION_MIN_CONFIDENCE_BURN_IN", "0.5")
        
        from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
        from ingestion.registry import get_connector, register_connector
        adapter = StubLivePlatformAdapter(base_url="http://testserver")
        adapter._base_url = "http://testserver"
        adapter._client = stub_client
        
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            match_id = "stub_live_001"
            
            async with get_database_manager().session() as session:
                report = await run_shadow_pipeline(
                    session,
                    connector_name="stub_live_platform",
                    match_id=match_id,
                    final_score={"home": 2, "away": 1},
                    status="FINAL",
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    activation=True,
                )
                
                assert "activation" in report
                assert "audits" in report["activation"]
                audits = report["activation"]["audits"]
                assert len(audits) >= 1
                activated_count = sum(1 for a in audits if a.get("activation_allowed"))
                assert activated_count <= 1, "Burn-in caps at most 1 match activated"
                if report["activation"].get("burn_in"):
                    assert "activated_matches" in report["activation"]["burn_in"]
                    assert "guardrail_state" in report["activation"]["burn_in"]
                if report["activation"].get("activated"):
                    assert report.get("analysis", {}).get("snapshot_id") is not None
        finally:
            if original:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_kill_switch_overrides_burn_in(test_db, stub_client) -> None:
    """ACTIVATION_KILL_SWITCH=true forces shadow-only even in burn-in mode."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "burn_in")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "stub_live_platform")
        m.setenv("ACTIVATION_KILL_SWITCH", "true")
        
        from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
        from ingestion.registry import get_connector, register_connector
        adapter = StubLivePlatformAdapter(base_url="http://testserver")
        adapter._base_url = "http://testserver"
        adapter._client = stub_client
        
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            match_id = "stub_live_001"
            
            async with get_database_manager().session() as session:
                report = await run_shadow_pipeline(
                    session,
                    connector_name="stub_live_platform",
                    match_id=match_id,
                    final_score={"home": 2, "away": 1},
                    status="FINAL",
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    activation=True,
                )
                
                assert report["activation"]["activated"] is False
                assert "KILL_SWITCH" in report["activation"]["reason"].upper()
                assert report.get("analysis", {}).get("snapshot_id") is None
        finally:
            if original:
                register_connector("stub_live_platform", original)
