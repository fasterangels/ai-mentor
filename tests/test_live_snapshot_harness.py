"""
Tests for live_snapshot harness stub: gates, writes under allowed base, invalid filename rejected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parent.parent
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from ai_mentor.live_snapshot.harness import run_live_snapshot
from ai_mentor.live_snapshot.live_connector_stub import LiveIODisabledError


def test_default_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """A) Default (no flags or false): run_live_snapshot raises LiveIODisabledError."""
    monkeypatch.delenv("LIVE_IO_ALLOWED", raising=False)
    monkeypatch.delenv("SNAPSHOT_WRITES_ALLOWED", raising=False)
    with pytest.raises(LiveIODisabledError):
        run_live_snapshot("validRun_01", ["a.json"])


def test_writes_flag_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """B) LIVE_IO_ALLOWED=true, SNAPSHOT_WRITES_ALLOWED=false -> PermissionError."""
    monkeypatch.setenv("LIVE_IO_ALLOWED", "true")
    monkeypatch.setenv("SNAPSHOT_WRITES_ALLOWED", "false")
    with pytest.raises(PermissionError) as exc_info:
        run_live_snapshot("validRun_01", ["a.json"])
    assert "SNAPSHOT_WRITES_ALLOWED" in str(exc_info.value)


def test_writes_only_under_allowed_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """C) Both flags true: file written under reports/snapshots/<run_id>/; JSON has note/run_id."""
    monkeypatch.setenv("LIVE_IO_ALLOWED", "true")
    monkeypatch.setenv("SNAPSHOT_WRITES_ALLOWED", "true")
    result = run_live_snapshot("validRun_01", ["a.json"])
    assert result["note"] == "stub-only"
    assert result["run_id"] == "validRun_01"
    assert result["written_files"]
    path = result["written_files"][0]
    assert "/reports/snapshots/validRun_01/" in path.replace("\\", "/")
    assert Path(path).exists()
    with open(path, encoding="utf-8") as f:
        import json
        data = json.load(f)
    assert data.get("note") == "live snapshot harness stub"
    assert data.get("run_id") == "validRun_01"
    assert "created_at" in data
    assert data.get("filename") == "a.json"


def test_invalid_filename_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """D) Filename with ../ raises ValueError."""
    monkeypatch.setenv("LIVE_IO_ALLOWED", "true")
    monkeypatch.setenv("SNAPSHOT_WRITES_ALLOWED", "true")
    with pytest.raises(ValueError):
        run_live_snapshot("validRun_01", ["../x.json"])
