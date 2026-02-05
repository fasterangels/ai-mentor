"""
Integration tests: shadow pipeline under deterministic stub failure modes (no external IO).
Uses in-process stub (TestClient) and STUB_LIVE_MODE; asserts live_io_metrics and live_io_alerts.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

import models  # noqa: F401
from core.database import get_database_manager, init_database, dispose_database
from dev.stub_server import create_stub_app
from models.base import Base
from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
from ingestion.live_io import circuit_breaker_reset, reset_metrics
from ingestion.registry import get_connector, register_connector
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


def _adapter_using_stub_client(adapter: StubLivePlatformAdapter, stub_client: TestClient) -> None:
    """Point adapter at test client so requests hit in-process stub (no real network)."""
    adapter._base_url = "http://testserver"
    adapter._client = stub_client


@pytest.mark.asyncio
async def test_drill_ok_mode_no_alerts(test_db, stub_client) -> None:
    """ok mode: normal responses; no alerts under normal thresholds."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        m.setenv("LIVE_IO_MAX_TIMEOUTS", "5")
        m.setenv("LIVE_IO_MAX_P95_MS", "5000")
        m.setenv("LIVE_IO_MAX_RATE_LIMITED", "3")
        reset_metrics()
        circuit_breaker_reset()
        adapter = StubLivePlatformAdapter()
        _adapter_using_stub_client(adapter, stub_client)
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            async with get_database_manager().session() as session:
                report = await run_shadow_batch(
                    session,
                    connector_name="stub_live_platform",
                    match_ids=["stub_live_001"],
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    dry_run=True,
                )
            assert "live_io_metrics" in report
            assert "live_io_alerts" in report
            assert report["live_io_metrics"]["counters"].get("requests_total", 0) >= 1
            assert report["live_io_metrics"]["counters"].get("failures_total", 0) == 0
            codes = [a.get("code") for a in report["live_io_alerts"]]
            assert "LIVE_IO_HIGH_FAILURE_RATE" not in codes
            assert "LIVE_IO_TIMEOUTS" not in codes
            assert "LIVE_IO_RATE_LIMITED" not in codes
        finally:
            adapter.close()
            if original is not None:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_drill_500_mode_increments_failures_and_alerts(test_db, stub_client) -> None:
    """500 mode: increments failures_total; guardrails alert on high failure rate when threshold exceeded."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "500")
        m.setenv("LIVE_IO_MAX_TIMEOUTS", "10")
        m.setenv("LIVE_IO_MAX_RATE_LIMITED", "10")
        m.setenv("LIVE_IO_MAX_P95_MS", "10000")
        reset_metrics()
        circuit_breaker_reset()
        adapter = StubLivePlatformAdapter()
        _adapter_using_stub_client(adapter, stub_client)
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            async with get_database_manager().session() as session:
                report = await run_shadow_batch(
                    session,
                    connector_name="stub_live_platform",
                    match_ids=["stub_live_001"],
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    dry_run=True,
                )
            assert "live_io_metrics" in report
            assert "live_io_alerts" in report
            counters = report["live_io_metrics"]["counters"]
            assert counters.get("requests_total", 0) >= 1
            assert counters.get("failures_total", 0) >= 1
            codes = [a.get("code") for a in report["live_io_alerts"]]
            assert "LIVE_IO_HIGH_FAILURE_RATE" in codes
        finally:
            adapter.close()
            if original is not None:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_drill_rate_limit_mode_increments_rate_limited_and_alerts(test_db, stub_client) -> None:
    """429 mode: increments rate_limited_total; guardrails alert when threshold exceeded."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "rate_limit")
        m.setenv("LIVE_IO_MAX_TIMEOUTS", "10")
        m.setenv("LIVE_IO_MAX_RATE_LIMITED", "0")
        m.setenv("LIVE_IO_MAX_P95_MS", "10000")
        reset_metrics()
        circuit_breaker_reset()
        adapter = StubLivePlatformAdapter()
        _adapter_using_stub_client(adapter, stub_client)
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            async with get_database_manager().session() as session:
                report = await run_shadow_batch(
                    session,
                    connector_name="stub_live_platform",
                    match_ids=["stub_live_001"],
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    dry_run=True,
                )
            assert "live_io_metrics" in report
            assert "live_io_alerts" in report
            counters = report["live_io_metrics"]["counters"]
            assert counters.get("rate_limited_total", 0) >= 1
            codes = [a.get("code") for a in report["live_io_alerts"]]
            assert "LIVE_IO_RATE_LIMITED" in codes
        finally:
            adapter.close()
            if original is not None:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_drill_slow_mode_higher_p95_latency_alerts_when_threshold_crossed(test_db, stub_client) -> None:
    """slow mode: higher p95 latency; latency guardrail only when threshold crossed."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "slow")
        m.setenv("LIVE_IO_MAX_TIMEOUTS", "10")
        m.setenv("LIVE_IO_MAX_RATE_LIMITED", "10")
        m.setenv("LIVE_IO_MAX_P95_MS", "100")
        reset_metrics()
        circuit_breaker_reset()
        adapter = StubLivePlatformAdapter()
        _adapter_using_stub_client(adapter, stub_client)
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            async with get_database_manager().session() as session:
                report = await run_shadow_batch(
                    session,
                    connector_name="stub_live_platform",
                    match_ids=["stub_live_001"],
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    dry_run=True,
                )
            assert "live_io_metrics" in report
            latency = report["live_io_metrics"].get("latency_ms") or {}
            assert latency.get("count", 0) >= 1
            p95 = latency.get("p95", 0)
            assert p95 >= 100
            codes = [a.get("code") for a in report["live_io_alerts"]]
            assert "LIVE_IO_HIGH_P95_LATENCY" in codes
        finally:
            adapter.close()
            if original is not None:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_drill_timeout_mode_increments_timeouts_and_may_open_circuit(test_db, stub_client) -> None:
    """timeout mode: timeouts_total incremented; guardrails alert on timeouts. Simulate timeout (TestClient may not enforce request timeout)."""
    from ingestion.live_io import LiveIOTimeoutError, circuit_breaker_record_failure as _cb_fail, record_request as _record_request

    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "timeout")
        m.setenv("LIVE_IO_MAX_TIMEOUTS", "0")
        m.setenv("LIVE_IO_MAX_RATE_LIMITED", "10")
        m.setenv("LIVE_IO_MAX_P95_MS", "10000")
        reset_metrics()
        circuit_breaker_reset()
        adapter = StubLivePlatformAdapter()
        _adapter_using_stub_client(adapter, stub_client)
        original_get = adapter._get
        call_count = [0]

        def _get_simulate_timeout(path: str):
            call_count[0] += 1
            if call_count[0] <= 2:
                _record_request(success=False, latency_ms=50.0, timeout=True)
                _cb_fail()
                raise LiveIOTimeoutError("Simulated timeout")
            return original_get(path)

        adapter._get = _get_simulate_timeout
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            async with get_database_manager().session() as session:
                report = await run_shadow_batch(
                    session,
                    connector_name="stub_live_platform",
                    match_ids=["stub_live_001"],
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    dry_run=True,
                )
            assert "live_io_metrics" in report
            counters = report["live_io_metrics"]["counters"]
            assert counters.get("timeouts_total", 0) >= 1
            codes = [a.get("code") for a in report["live_io_alerts"]]
            assert "LIVE_IO_TIMEOUTS" in codes
        finally:
            adapter.close()
            if original is not None:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_reports_include_live_io_metrics_and_alerts_fields(test_db, stub_client) -> None:
    """Reports include live_io_metrics and live_io_alerts; assert structure exists."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")
        reset_metrics()
        circuit_breaker_reset()
        adapter = StubLivePlatformAdapter()
        _adapter_using_stub_client(adapter, stub_client)
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            async with get_database_manager().session() as session:
                report = await run_shadow_batch(
                    session,
                    connector_name="stub_live_platform",
                    match_ids=["stub_live_001"],
                    now_utc=datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                    dry_run=True,
                )
            assert "live_io_metrics" in report
            assert "counters" in report["live_io_metrics"]
            assert "latency_ms" in report["live_io_metrics"]
            assert "requests_total" in report["live_io_metrics"]["counters"]
            assert "live_io_alerts" in report
            assert isinstance(report["live_io_alerts"], list)
        finally:
            adapter.close()
            if original is not None:
                register_connector("stub_live_platform", original)
