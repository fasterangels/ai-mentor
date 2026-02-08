"""
Integration tests for worst-case-tracking mode (I2 Part B).
Run mode on fixtures; assert report files exist and contain expected columns/keys.
No analyzer behavior changes.
"""

from __future__ import annotations

import asyncio
import csv
import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from evaluation.worst_case_errors import EvaluatedDecision, compute_worst_case_report
from evaluation.worst_case_errors.reporting import write_csv, write_json, CSV_COLUMNS, DEFAULT_TOP_N
from runner.worst_case_runner import run_worst_case_tracking


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
async def test_worst_case_tracking_writes_reports_with_empty_db(test_db, tmp_path) -> None:
    """Run worst-case-tracking with no evaluation data; report files still written with expected structure."""
    async with get_database_manager().session() as session:
        result = await run_worst_case_tracking(session, reports_dir=str(tmp_path))

    assert result.get("error") is None
    assert result.get("decisions_count") == 0
    assert result.get("rows_written") == 0

    csv_path = tmp_path / "worst_case_errors_top.csv"
    json_path = tmp_path / "worst_case_errors_top.json"
    assert csv_path.exists(), "CSV report should exist"
    assert json_path.exists(), "JSON report should exist"

    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        for col in ["fixture_id", "market", "prediction", "outcome", "original_confidence", "worst_case_score", "snapshot_type"]:
            assert col in reader.fieldnames, f"CSV must have column {col}"
        rows = list(reader)
    assert len(rows) == 0

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "computed_at_utc" in data
    assert "top_n" in data
    assert data["top_n"] == DEFAULT_TOP_N
    assert "rows" in data
    assert data["rows"] == []


def test_worst_case_report_files_have_expected_columns_when_data(tmp_path) -> None:
    """With synthetic decisions, written CSV/JSON have expected columns and keys (deterministic)."""
    decisions = [
        EvaluatedDecision(
            fixture_id="fx1",
            market="one_x_two",
            prediction="home",
            outcome="FAILURE",
            original_confidence=0.8,
            snapshot_type="live_shadow",
        ),
    ]
    report = compute_worst_case_report(decisions)
    write_csv(report, tmp_path / "worst_case_errors_top.csv", top_n=50)
    write_json(report, tmp_path / "worst_case_errors_top.json", top_n=50)

    csv_path = tmp_path / "worst_case_errors_top.csv"
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == CSV_COLUMNS
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["fixture_id"] == "fx1"
    assert rows[0]["market"] == "one_x_two"
    assert rows[0]["worst_case_score"] == "1.8"
    assert rows[0]["snapshot_type"] == "live_shadow"

    data = json.loads((tmp_path / "worst_case_errors_top.json").read_text(encoding="utf-8"))
    assert "computed_at_utc" in data
    assert len(data["rows"]) == 1
    assert data["rows"][0]["fixture_id"] == "fx1"
    assert data["rows"][0]["snapshot_type"] == "live_shadow"
