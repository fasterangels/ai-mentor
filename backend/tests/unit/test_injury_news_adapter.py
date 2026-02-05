"""
Unit tests: recorded injury/news adapter (persist report+claims, determinism, no network).
"""

from __future__ import annotations

import asyncio
import json
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
from ingestion.injury_news_adapter import (
    ADAPTER_KEY,
    load_injury_news_fixtures,
    run_recorded_injury_news_ingestion,
    _content_checksum,
    _normalize_report,
)
from repositories.injury_news_claim_repo import InjuryNewsClaimRepository
from repositories.injury_news_report_repo import InjuryNewsReportRepository


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


@pytest.fixture
def fixtures_dir(tmp_path):
    """Two fixture files: one single claim, one multiple claims."""
    (tmp_path / "report_001.json").write_text(
        json.dumps({
            "source_ref": "https://test/1",
            "published_at": "2025-06-01T10:00:00+00:00",
            "title": "Team A: Player X out",
            "body": "Ankle injury.",
            "claims": [
                {
                    "team_ref": "team_a",
                    "player_ref": "player_x",
                    "claim_type": "INJURY_STATUS",
                    "status": "OUT",
                    "validity": "RANGE",
                    "valid_from": "2025-06-01T00:00:00+00:00",
                    "valid_to": "2025-06-15T23:59:59+00:00",
                    "confidence": 0.9,
                }
            ],
        }, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "report_002.json").write_text(
        json.dumps({
            "source_ref": "https://test/2",
            "title": "Team B update",
            "claims": [
                {"team_ref": "team_b", "player_ref": "y", "claim_type": "RETURN", "status": "FIT", "validity": "NEXT_MATCH", "confidence": 0.85},
                {"team_ref": "team_b", "player_ref": "z", "claim_type": "INJURY_STATUS", "status": "DOUBTFUL", "validity": "UNKNOWN", "confidence": 0.7},
            ],
        }, indent=2),
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.asyncio
async def test_adapter_persists_report_and_claims(test_db, fixtures_dir) -> None:
    """Given fixture artifacts, adapter persists 1 report per file with expected content_checksum and N claims."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    async with get_database_manager().session() as session:
        n = await run_recorded_injury_news_ingestion(
            session, fixtures_dir=fixtures_dir, now_utc=now
        )
        await session.commit()
    assert n == 2

    async with get_database_manager().session() as session:
        report_repo = InjuryNewsReportRepository(session)
        claim_repo = InjuryNewsClaimRepository(session)
        fixtures = load_injury_news_fixtures(fixtures_dir)
        for path, normalized in fixtures:
            content_checksum = _content_checksum(normalized)
            report_id = f"inj_{content_checksum[:24]}"
            report = await report_repo.get_by_id(report_id)
            assert report is not None, f"Report {report_id} should exist"
            assert report.content_checksum == content_checksum
            assert report.adapter_key == ADAPTER_KEY
            claims = await claim_repo.list_claims_by_report_id(report_id)
            assert len(claims) == len(normalized["claims"])
            for i, c in enumerate(normalized["claims"]):
                assert claims[i].team_ref == c["team_ref"]
                assert claims[i].claim_type == c["claim_type"]
                assert claims[i].status == c["status"]
                assert claims[i].confidence == c["confidence"]


@pytest.mark.asyncio
async def test_adapter_determinism_no_duplicate_reports(test_db, fixtures_dir) -> None:
    """Run adapter twice on same fixtures; no duplicate reports (second run skips existing)."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    async with get_database_manager().session() as session:
        n1 = await run_recorded_injury_news_ingestion(
            session, fixtures_dir=fixtures_dir, now_utc=now
        )
        await session.commit()
    async with get_database_manager().session() as session:
        n2 = await run_recorded_injury_news_ingestion(
            session, fixtures_dir=fixtures_dir, now_utc=now
        )
        await session.commit()
    assert n1 == 2
    assert n2 == 0
    async with get_database_manager().session() as session:
        from sqlalchemy import select, func
        from models.injury_news_report import InjuryNewsReport
        result = await session.execute(select(func.count()).select_from(InjuryNewsReport))
        total = result.scalar()
    assert total == 2


@pytest.mark.asyncio
async def test_adapter_only_reads_local_paths(test_db, fixtures_dir) -> None:
    """Adapter completes using only local fixtures dir and DB (no network)."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    async with get_database_manager().session() as session:
        n = await run_recorded_injury_news_ingestion(
            session, fixtures_dir=fixtures_dir, now_utc=now
        )
        await session.commit()
    assert n == 2


@pytest.mark.asyncio
async def test_normalize_claim_fail_fast_invalid_enum() -> None:
    """Invalid claim_type raises ValueError."""
    with pytest.raises(ValueError, match="claim_type"):
        _normalize_report({
            "source_ref": "x",
            "claims": [{"team_ref": "t", "claim_type": "INVALID", "status": "OUT", "validity": "UNKNOWN", "confidence": 0.5}],
        })
