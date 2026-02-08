"""
Integration tests for live-awareness mode (J2 Part B).
Minimal DB: one recorded + one live_shadow (newer). Run live-awareness; assert JSON/MD and gap; assert analyzer not invoked.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from models.competition import Competition
from models.match import Match
from models.season import Season
from models.team import Team
from pipeline.snapshot_envelope import build_envelope_for_recorded, build_envelope_for_live_shadow
from repositories.analysis_run_repo import AnalysisRunRepository
from repositories.raw_payload_repo import RawPayloadRepository
from runner.live_awareness_runner import run_live_awareness, LIVE_AWARENESS_JSON, LIVE_AWARENESS_MD


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


async def _seed_minimal_match(session, match_id: str, kickoff: datetime) -> None:
    """Insert minimal Competition, Season, Teams, Match so RawPayload FK is satisfied."""
    comp = Competition(id="comp_la", name="Test League", country="XX", tier=1, is_active=True)
    season = Season(id="sea_la", competition_id="comp_la", name="2024/25", year_start=2024, year_end=2025, is_active=True)
    t1 = Team(id="team_a", name="Team A", country="XX", is_active=True)
    t2 = Team(id="team_b", name="Team B", country="XX", is_active=True)
    match = Match(
        id=match_id,
        competition_id="comp_la",
        season_id="sea_la",
        kickoff_utc=kickoff,
        status="FINAL",
        home_team_id="team_a",
        away_team_id="team_b",
        home_score=1,
        away_score=1,
    )
    session.add(comp)
    session.add(season)
    session.add(t1)
    session.add(t2)
    await session.flush()
    session.add(match)


@pytest.mark.asyncio
async def test_live_awareness_writes_artifacts_gap_correct_analyzer_not_invoked(test_db, tmp_path) -> None:
    """
    Create minimal DB: one recorded snapshot, one live_shadow (newer).
    Run live-awareness; assert JSON/MD exist, gap correct; assert no analysis run (analyzer not invoked).
    """
    match_id = "live_awareness_j2_m1"
    rec_ts = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    live_ts = datetime(2025, 6, 1, 12, 5, 30, tzinfo=timezone.utc)  # 5m30s later

    async with get_database_manager().session() as session:
        await _seed_minimal_match(session, match_id, rec_ts)
        payload_rec = {"match_id": match_id, "data": {}}
        payload_live = {"fixture_id": match_id, "data": {}}
        env_rec = build_envelope_for_recorded(payload_rec, "rec_sid", rec_ts, "pipeline_cache")
        env_live = build_envelope_for_live_shadow(payload_live, "live_sid", live_ts, "live_shadow", live_ts)
        raw_repo = RawPayloadRepository(session)
        await raw_repo.add_payload(
            source_name="pipeline_cache",
            domain="fixtures",
            payload_hash="rec_sid",
            payload_json=json.dumps({"metadata": env_rec.to_dict(), "payload": payload_rec}, sort_keys=True, default=str),
            related_match_id=match_id,
        )
        await raw_repo.add_payload(
            source_name="live_shadow",
            domain="fixture_detail",
            payload_hash="live_sid",
            payload_json=json.dumps({"metadata": env_live.to_dict(), "payload": payload_live}, sort_keys=True, default=str),
            related_match_id=match_id,
        )
        await session.commit()

    reports_dir = tmp_path
    async with get_database_manager().session() as session:
        result = await run_live_awareness(session, reports_dir=reports_dir, fixture_id=match_id)

    assert result.get("error") is None
    assert result.get("has_live_shadow") is True
    assert result.get("observed_gap_ms") == 330_000  # 5m30s in ms

    json_path = Path(result["json_path"])
    md_path = Path(result["md_path"])
    assert json_path.exists()
    assert md_path.exists()
    assert json_path.name == LIVE_AWARENESS_JSON
    assert md_path.name == LIVE_AWARENESS_MD

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["scope_id"] == match_id
    assert data["has_live_shadow"] is True
    assert data["observed_gap_ms"] == 330_000

    md_content = md_path.read_text(encoding="utf-8")
    assert "Live Awareness" in md_content
    assert match_id in md_content
    assert "330000" in md_content or "330 000" in md_content or "330,000" in md_content

    # Analyzer/evaluator not invoked: run_live_awareness does not create analysis runs
    async with get_database_manager().session() as session:
        run_repo = AnalysisRunRepository(session)
        runs_after = await run_repo.list_recent(limit=10)
    assert len(runs_after) == 0, "live-awareness must not invoke analyzer (no analysis runs)"
