"""
Tests for shadow runner batch: report shape, determinism, and match cap.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from limits.limits import get_max_matches_per_run
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


@pytest.mark.asyncio
async def test_batch_run_returns_report_with_correct_counts(test_db):
    """Batch run returns report with correct structure and counts for dummy connector."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    match_ids = ["batch-m1", "batch-m2"]

    async with get_database_manager().session() as session:
        report = await run_shadow_batch(
            session,
            connector_name="dummy",
            match_ids=match_ids,
            now_utc=now,
            final_scores={
                "batch-m1": {"home": 1, "away": 0},
                "batch-m2": {"home": 2, "away": 2},
            },
        )

    assert "error" not in report or report.get("error") is None
    assert report.get("run_meta") is not None
    assert report["run_meta"]["connector_name"] == "dummy"
    assert report["run_meta"]["matches_count"] == 2
    assert "started_at_utc" in report["run_meta"]

    assert "per_match" in report
    assert len(report["per_match"]) == 2
    for item in report["per_match"]:
        assert "match_id" in item
        assert "evaluation_checksum" in item
        assert "proposal_checksum" in item
        assert "audit_changed_count" in item
    match_ids_reported = {p["match_id"] for p in report["per_match"]}
    assert match_ids_reported == {"batch-m1", "batch-m2"}

    assert "aggregates" in report
    assert report["aggregates"]["total_matches"] == 2
    assert "total_changed_decisions" in report["aggregates"]
    assert "per_market_changed_counts" in report["aggregates"]

    assert "checksums" in report
    assert "batch_input_checksum" in report["checksums"]
    assert "batch_output_checksum" in report["checksums"]

    assert "failures" in report
    assert isinstance(report["failures"], list)


@pytest.mark.asyncio
async def test_deterministic_same_inputs_same_checksums(test_db):
    """Same inputs and fixed now_utc yield same batch_input_checksum and batch_output_checksum."""
    now = datetime(2025, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    match_ids = ["det-a", "det-b"]

    async def run_once():
        await init_database("sqlite+aiosqlite:///:memory:")
        engine = get_database_manager().engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with get_database_manager().session() as session:
            report = await run_shadow_batch(
                session,
                connector_name="dummy",
                match_ids=match_ids,
                now_utc=now,
                final_scores={"det-a": {"home": 0, "away": 0}, "det-b": {"home": 1, "away": 1}},
            )
        await dispose_database()
        return report

    report1 = await run_once()
    report2 = await run_once()

    assert report1.get("error") is None and report2.get("error") is None
    assert report1["checksums"]["batch_input_checksum"] == report2["checksums"]["batch_input_checksum"]
    assert report1["checksums"]["batch_output_checksum"] == report2["checksums"]["batch_output_checksum"]


@pytest.mark.asyncio
async def test_cap_enforced(test_db):
    """Requesting more than get_max_matches_per_run() returns error and no per_match execution (quota enforced)."""
    cap = get_max_matches_per_run()
    too_many = [f"m{i}" for i in range(cap + 1)]

    async with get_database_manager().session() as session:
        report = await run_shadow_batch(
            session,
            connector_name="dummy",
            match_ids=too_many,
        )

    assert report.get("error") == "MAX_MATCHES_EXCEEDED"
    assert "maximum allowed" in report.get("detail", "")
    detail = report.get("detail", "")
    assert str(cap) in detail or str(cap + 1) in detail
    assert report.get("run_meta") is None
    assert report.get("per_match") == []
    assert report.get("aggregates") is None
    assert report.get("checksums") is None
    assert report.get("failures") == []
