"""
Tests for recorded snapshot replay runner: path validation and replay with stub JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parent.parent
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from ai_mentor.live_snapshot.replay import replay_from_snapshots


def test_reject_non_allowed_directory() -> None:
    """A) Reject directory not under reports/snapshots."""
    with pytest.raises(ValueError) as exc_info:
        replay_from_snapshots("/tmp/other")
    assert "reports/snapshots" in str(exc_info.value) or "must be under" in str(exc_info.value).lower()
    with pytest.raises(ValueError):
        replay_from_snapshots("reports/other")


def test_replay_from_snapshots_returns_count_and_report() -> None:
    """B) With a dir under reports/snapshots containing 1-2 stub JSON files, replay runs, returns snapshots_used, produces report."""
    base = Path("reports/snapshots").resolve()
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / "replay_run_01"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "a.json").write_text(
        json.dumps({"note": "stub", "run_id": "replay_run_01", "filename": "a.json"}),
        encoding="utf-8",
    )
    (run_dir / "b.json").write_text(
        json.dumps({"note": "stub", "run_id": "replay_run_01", "filename": "b.json"}),
        encoding="utf-8",
    )
    try:
        result = replay_from_snapshots(str(run_dir))
        assert result["note"] == "recorded replay"
        assert result["snapshots_used"] == 2
        assert "report_path" in result
        report_path = Path(result["report_path"])
        assert report_path.exists()
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        assert report["snapshots_used"] == 2
        assert len(report["recorded_inputs"]) == 2
        assert report["note"] == "recorded replay"
    finally:
        replay_report = run_dir / "replay_report.json"
        if replay_report.exists():
            replay_report.unlink()
