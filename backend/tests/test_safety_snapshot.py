"""
Unit tests for backend core.safety_snapshot (safety_defaults_snapshot, safety_summary_for_report).
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from core.safety_snapshot import safety_defaults_snapshot, safety_summary_for_report


def test_safety_defaults_snapshot_all_false_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """With env vars unset, all returned values are False."""
    for name in (
        "LIVE_IO_ALLOWED",
        "SNAPSHOT_WRITES_ALLOWED",
        "SNAPSHOT_REPLAY_ENABLED",
        "INJ_NEWS_ENABLED",
        "INJ_NEWS_SHADOW_ATTACH_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    snap = safety_defaults_snapshot()
    assert snap["LIVE_IO_ALLOWED"] is False
    assert snap["SNAPSHOT_WRITES_ALLOWED"] is False
    assert snap["SNAPSHOT_REPLAY_ENABLED"] is False
    assert snap["INJ_NEWS_ENABLED"] is False
    assert snap["INJ_NEWS_SHADOW_ATTACH_ENABLED"] is False


def test_safety_summary_for_report_has_flags_and_note(monkeypatch: pytest.MonkeyPatch) -> None:
    """safety_summary_for_report returns flags dict and note."""
    for name in (
        "LIVE_IO_ALLOWED",
        "SNAPSHOT_WRITES_ALLOWED",
        "SNAPSHOT_REPLAY_ENABLED",
        "INJ_NEWS_ENABLED",
        "INJ_NEWS_SHADOW_ATTACH_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    summary = safety_summary_for_report()
    assert "flags" in summary
    assert "note" in summary
    assert summary["note"] == "All unsafe modes require explicit opt-in"
    for k, v in summary["flags"].items():
        assert isinstance(v, bool)
