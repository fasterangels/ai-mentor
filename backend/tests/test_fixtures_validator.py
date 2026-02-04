"""Tests for fixture validator."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.fixtures.validator import validate_fixtures


def test_validate_fixtures_sample_platform_ok() -> None:
    """Valid sample_platform fixtures pass validation."""
    path = _backend / "ingestion" / "fixtures" / "sample_platform"
    report = validate_fixtures(path)
    assert report.ok is True
    assert len(report.errors) == 0


def test_validate_fixtures_missing_required_fails(tmp_path: Path) -> None:
    """Fixture missing required field fails validation."""
    (tmp_path / "bad.json").write_text('{"match_id": "x"}', encoding="utf-8")
    report = validate_fixtures(tmp_path)
    assert report.ok is False
    assert any("required" in e.lower() for e in report.errors)


def test_validate_fixtures_duplicate_match_id_fails(tmp_path: Path) -> None:
    """Duplicate match_id in fixtures fails validation."""
    (tmp_path / "a.json").write_text(
        '{"match_id": "same", "home_team": "A", "away_team": "B", "competition": "C", '
        '"kickoff_utc": "2025-01-01T12:00:00Z", "odds_1x2": {"home": 2, "draw": 3, "away": 4}, "status": "scheduled"}',
        encoding="utf-8",
    )
    (tmp_path / "b.json").write_text(
        '{"match_id": "same", "home_team": "X", "away_team": "Y", "competition": "C", '
        '"kickoff_utc": "2025-01-01T12:00:00Z", "odds_1x2": {"home": 1.5, "draw": 4, "away": 5}, "status": "scheduled"}',
        encoding="utf-8",
    )
    report = validate_fixtures(tmp_path)
    assert report.ok is False
    assert any("duplicate" in e.lower() for e in report.errors)
