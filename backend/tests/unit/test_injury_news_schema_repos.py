"""
Unit tests: injury/news schema + repositories (tables exist, insert/read, dedupe, cascade).
Deterministic; no resolver logic.
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

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from models.injury_news_claim import InjuryNewsClaim
from models.injury_news_report import InjuryNewsReport
from models.injury_news_resolution import InjuryNewsResolution
from repositories.injury_news_claim_repo import InjuryNewsClaimRepository
from repositories.injury_news_report_repo import InjuryNewsReportRepository
from repositories.injury_news_resolution_repo import InjuryNewsResolutionRepository


@pytest.fixture
def test_db():
    """In-memory SQLite with all tables (including injury_news_*)."""
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
async def test_injury_news_tables_exist(test_db) -> None:
    """Schema init creates injury_news_reports, injury_news_claims, injury_news_resolutions."""
    from sqlalchemy import inspect, text

    engine = get_database_manager().engine
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = {row[0] for row in result.fetchall()}
    assert "injury_news_reports" in tables
    assert "injury_news_claims" in tables
    assert "injury_news_resolutions" in tables


@pytest.mark.asyncio
async def test_insert_report_and_claims_read_back(test_db) -> None:
    """Insert one report + claims; read back; assert exact equality."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    report_id = "rpt-001"
    content_checksum = "sha256-abc"
    artifact_checksum = "sha256-artifact"

    async with get_database_manager().session() as session:
        report_repo = InjuryNewsReportRepository(session)
        claim_repo = InjuryNewsClaimRepository(session)

        report = await report_repo.upsert_report(
            report_id=report_id,
            adapter_key="adapter1",
            artifact_path="reports/injury/rpt-001.json",
            artifact_checksum=artifact_checksum,
            content_checksum=content_checksum,
            recorded_at=now,
            created_at=now,
            title="Team A injury update",
            body_excerpt="Player X out for 2 weeks.",
        )
        await session.commit()

        claims = await claim_repo.add_claims(
            report_id=report_id,
            claims=[
                {
                    "team_ref": "team_a",
                    "player_ref": "player_x",
                    "claim_type": "INJURY_STATUS",
                    "status": "OUT",
                    "validity": "RANGE",
                    "confidence": 0.9,
                    "valid_from": now,
                    "valid_to": datetime(2025, 6, 15, 0, 0, 0, tzinfo=timezone.utc),
                },
            ],
            created_at=now,
        )
        await session.commit()

    async with get_database_manager().session() as session:
        report_repo = InjuryNewsReportRepository(session)
        claim_repo = InjuryNewsClaimRepository(session)

        read_report = await report_repo.get_by_id(report_id)
        assert read_report is not None
        assert read_report.report_id == report_id
        assert read_report.adapter_key == "adapter1"
        assert read_report.artifact_checksum == artifact_checksum
        assert read_report.content_checksum == content_checksum
        assert read_report.title == "Team A injury update"
        assert read_report.body_excerpt == "Player X out for 2 weeks."

        read_claims = await claim_repo.list_claims_by_report_id(report_id)
        assert len(read_claims) == 1
        assert read_claims[0].team_ref == "team_a"
        assert read_claims[0].player_ref == "player_x"
        assert read_claims[0].claim_type == "INJURY_STATUS"
        assert read_claims[0].status == "OUT"
        assert read_claims[0].confidence == 0.9


@pytest.mark.asyncio
async def test_upsert_dedupe_by_content_checksum_adapter(test_db) -> None:
    """Inserting same content_checksum + adapter_key twice does not create duplicate report."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    content_checksum = "sha256-dedup"
    adapter_key = "adapter1"

    async with get_database_manager().session() as session:
        report_repo = InjuryNewsReportRepository(session)

        r1 = await report_repo.upsert_report(
            report_id="rpt-dedup-1",
            adapter_key=adapter_key,
            artifact_path="reports/injury/a.json",
            artifact_checksum="art1",
            content_checksum=content_checksum,
            recorded_at=now,
            created_at=now,
        )
        await session.commit()

        r2 = await report_repo.upsert_report(
            report_id="rpt-dedup-2",
            adapter_key=adapter_key,
            artifact_path="reports/injury/b.json",
            artifact_checksum="art2",
            content_checksum=content_checksum,
            recorded_at=now,
            created_at=now,
        )
        await session.commit()

        # Same row updated (report_id stays first one's id in our upsert logic - we update existing)
        assert r1.report_id == "rpt-dedup-1"
        existing = await report_repo.find_by_content_checksum_and_adapter(
            content_checksum, adapter_key
        )
        assert existing is not None
        assert existing.report_id == "rpt-dedup-1"
        assert existing.artifact_checksum == "art2"


@pytest.mark.asyncio
async def test_cascade_delete_report_removes_claims(test_db) -> None:
    """Deleting a report removes its claims (FK CASCADE)."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    report_id = "rpt-cascade"

    async with get_database_manager().session() as session:
        report_repo = InjuryNewsReportRepository(session)
        claim_repo = InjuryNewsClaimRepository(session)

        await report_repo.upsert_report(
            report_id=report_id,
            adapter_key="a1",
            artifact_path="p",
            artifact_checksum="c1",
            content_checksum="c2",
            recorded_at=now,
            created_at=now,
        )
        await session.flush()
        await claim_repo.add_claims(
            report_id=report_id,
            claims=[{"team_ref": "t", "claim_type": "INJURY_STATUS", "status": "OUT", "validity": "UNKNOWN", "confidence": 0.8}],
            created_at=now,
        )
        await session.commit()

        report = await report_repo.get_by_id(report_id)
        assert report is not None
        await report_repo.delete(report)
        await session.commit()

    async with get_database_manager().session() as session:
        claim_repo = InjuryNewsClaimRepository(session)
        claims = await claim_repo.list_claims_by_report_id(report_id)
        assert len(claims) == 0


@pytest.mark.asyncio
async def test_resolution_repo_save_and_list(test_db) -> None:
    """Save resolution batch; list by fixture_id and team_ref."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    async with get_database_manager().session() as session:
        res_repo = InjuryNewsResolutionRepository(session)
        batch = [
            {
                "fixture_id": "fix-1",
                "team_ref": "team_a",
                "player_ref": "p1",
                "resolved_status": "OUT",
                "resolution_confidence": 0.9,
                "resolution_method": "LATEST_WINS",
                "winning_claim_id": "cl-1",
                "supporting_claim_ids": ["cl-1"],
                "conflicting_claim_ids": [],
                "policy_version": "v1",
                "created_at": now,
            },
        ]
        saved = await res_repo.save_resolutions(batch)
        await session.commit()
        assert len(saved) == 1
        assert saved[0].fixture_id == "fix-1"
        assert saved[0].team_ref == "team_a"

    async with get_database_manager().session() as session:
        res_repo = InjuryNewsResolutionRepository(session)
        by_fixture = await res_repo.list_resolutions(fixture_id="fix-1")
        assert len(by_fixture) == 1
        by_team = await res_repo.list_resolutions(team_ref="team_a")
        assert len(by_team) == 1


@pytest.mark.asyncio
async def test_body_excerpt_truncated(test_db) -> None:
    """body_excerpt is truncated to BODY_EXCERPT_MAX_LENGTH."""
    from repositories.injury_news_report_repo import BODY_EXCERPT_MAX_LENGTH

    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    long_excerpt = "x" * (BODY_EXCERPT_MAX_LENGTH + 100)
    async with get_database_manager().session() as session:
        report_repo = InjuryNewsReportRepository(session)
        await report_repo.upsert_report(
            report_id="rpt-long",
            adapter_key="a",
            artifact_path="p",
            artifact_checksum="c1",
            content_checksum="c2",
            recorded_at=now,
            created_at=now,
            body_excerpt=long_excerpt,
        )
        await session.commit()

    async with get_database_manager().session() as session:
        report_repo = InjuryNewsReportRepository(session)
        r = await report_repo.get_by_id("rpt-long")
        assert r is not None
        assert len(r.body_excerpt or "") <= BODY_EXCERPT_MAX_LENGTH
        assert (r.body_excerpt or "").endswith("...")
