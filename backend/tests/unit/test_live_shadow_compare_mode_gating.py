"""
Unit tests for LIVE_SHADOW_COMPARE mode gating: no analyzer invoked, no writes unless LIVE_WRITES_ALLOWED.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.platform_base import IngestedMatchData
from reports.live_shadow_compare import ingested_to_dict
from runner.live_shadow_compare_runner import run_live_shadow_compare


def _make_data(match_id: str) -> IngestedMatchData:
    return IngestedMatchData(
        match_id=match_id,
        home_team="Home",
        away_team="Away",
        competition="League",
        kickoff_utc="2025-10-01T18:00:00+00:00",
        odds_1x2={"home": 2.0, "draw": 3.0, "away": 3.5},
        status="scheduled",
    )


def test_analyzer_not_invoked() -> None:
    """LIVE_SHADOW_COMPARE must not invoke the analyzer (mock analyze_v2 and assert not called)."""
    live = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1"))}]
    rec = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1"))}]
    with patch("analyzer.v2.engine.analyze_v2") as mock_analyze:
        result = run_live_shadow_compare(live_snapshots=live, recorded_snapshots=rec)
        mock_analyze.assert_not_called()
    assert "diff_report" in result
    assert result.get("error") is None


def test_no_writes_without_live_writes_allowed(tmp_path: Path) -> None:
    """When LIVE_WRITES_ALLOWED is false, report is not written to disk and index not updated."""
    live = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1"))}]
    rec = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1"))}]
    reports_dir = tmp_path / "reports"
    index_path = tmp_path / "index.json"
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_WRITES_ALLOWED", "0")
        result = run_live_shadow_compare(
            live_snapshots=live,
            recorded_snapshots=rec,
            reports_dir=str(reports_dir),
            index_path=str(index_path),
        )
    assert "_report_path" not in result
    compare_dir = reports_dir / "live_shadow_compare"
    assert not compare_dir.exists() or len(list(compare_dir.iterdir())) == 0
