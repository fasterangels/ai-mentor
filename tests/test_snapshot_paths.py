"""
Unit tests for path-safe snapshot helper (safe_snapshot_path).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parent.parent
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from ai_mentor.utils.snapshot_paths import (
    ALLOWED_SNAPSHOT_BASE,
    safe_snapshot_path,
)


def test_valid_run_id_and_filename_returns_path_under_base() -> None:
    """A) Valid run_id + filename returns a path under reports/snapshots/<run_id>/."""
    p = safe_snapshot_path("run-abc1", "snap.json")
    assert "reports" in p
    assert "snapshots" in p
    assert "run-abc1" in p
    assert p.endswith("snap.json") or "snap.json" in p
    base = Path(ALLOWED_SNAPSHOT_BASE).resolve()
    resolved = Path(p).resolve()
    resolved.relative_to(base)


def test_run_id_too_short_raises_value_error() -> None:
    """B) run_id too short -> ValueError."""
    with pytest.raises(ValueError) as exc_info:
        safe_snapshot_path("short", "ok.json")  # 5 chars < 6
    assert "run_id" in str(exc_info.value).lower() or "6" in str(exc_info.value)


def test_filename_with_traversal_or_separators_raises_value_error() -> None:
    """C) filename with ../ or path separators -> ValueError."""
    with pytest.raises(ValueError) as exc_info:
        safe_snapshot_path("run-id-1", "../other.json")
    assert "filename" in str(exc_info.value).lower() or "separator" in str(exc_info.value).lower()
    with pytest.raises(ValueError):
        safe_snapshot_path("run-id-1", "dir/file.json")


def test_filename_with_invalid_chars_raises_value_error() -> None:
    """D) filename with invalid chars -> ValueError."""
    with pytest.raises(ValueError) as exc_info:
        safe_snapshot_path("run-id-1", "bad file.json")  # space not allowed
    assert "filename" in str(exc_info.value).lower()
    with pytest.raises(ValueError):
        safe_snapshot_path("run-id-1", "bad@.json")


def test_run_id_with_invalid_chars_raises_value_error() -> None:
    """E) run_id with invalid chars -> ValueError."""
    with pytest.raises(ValueError) as exc_info:
        safe_snapshot_path("run id!", "ok.json")
    assert "run_id" in str(exc_info.value).lower()
    with pytest.raises(ValueError):
        safe_snapshot_path("run/id", "ok.json")
