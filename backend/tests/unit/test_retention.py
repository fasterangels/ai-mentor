"""
Tests for report retention: safe directory boundary, dry-run, deterministic cleanup.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from limits.retention import cleanup_reports, _safe_under_root
from reports.index_store import load_index, save_index, append_burn_in_ops_run


def test_safe_under_root_allows_under() -> None:
    """Paths under root are allowed."""
    root = Path("/tmp/reports").resolve()
    assert _safe_under_root(root / "burn_in" / "run1", root) is True
    assert _safe_under_root(root / "index.json", root) is True


def test_safe_under_root_blocks_traversal(tmp_path: Path) -> None:
    """Paths outside root (traversal) are not allowed."""
    root = tmp_path / "reports"
    root.mkdir()
    # Path that would escape (e.g. symlink or normalized ..)
    outside = tmp_path / "other"
    outside.mkdir()
    assert _safe_under_root(outside, root) is False
    assert _safe_under_root(root / ".." / "other", root) is False


def test_retention_dry_run_no_deletion(tmp_path: Path) -> None:
    """Dry-run must not delete any files; only report what would be removed."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "burn_in").mkdir()
    index_path = reports_dir / "index.json"
    index = load_index(index_path)
    for i in range(5):
        append_burn_in_ops_run(index, {
            "run_id": f"run_{i}",
            "created_at_utc": "2025-01-01T12:00:00Z",
            "connector_name": "dummy",
            "matches_count": 0,
            "status": "ok",
            "alerts_count": 0,
            "activated": False,
        })
    save_index(index, index_path)
    # Create artifact dirs for first 3 runs
    for i in range(3):
        (reports_dir / "burn_in" / f"run_{i}").mkdir(parents=True)
    before_count = sum(1 for _ in (reports_dir / "burn_in").iterdir())
    assert before_count == 3

    index_out, deleted_paths, _ = cleanup_reports(
        str(reports_dir),
        keep_last_n=2,
        dry_run=True,
        index_path=index_path,
    )
    # Dry-run: no actual deletion; deleted_paths lists what would be removed
    assert len(deleted_paths) >= 1
    after_count = sum(1 for _ in (reports_dir / "burn_in").iterdir())
    assert after_count == 3, "Dry-run must not delete any directories"


def test_retention_does_not_delete_outside_reports_dir(tmp_path: Path) -> None:
    """Cleanup must never delete paths outside the reports directory."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "burn_in").mkdir()
    safe_file = tmp_path / "must_remain.txt"
    safe_file.write_text("do not delete")
    index_path = reports_dir / "index.json"
    index = load_index(index_path)
    append_burn_in_ops_run(index, {"run_id": "only_run", "created_at_utc": "2025-01-01T12:00:00Z", "connector_name": "dummy", "matches_count": 0, "status": "ok", "alerts_count": 0, "activated": False})
    save_index(index, index_path)
    (reports_dir / "burn_in" / "only_run").mkdir()

    cleanup_reports(str(reports_dir), keep_last_n=0, dry_run=False, index_path=index_path)
    assert safe_file.exists()
    assert safe_file.read_text() == "do not delete"


def test_retention_keep_last_n_deterministic(tmp_path: Path) -> None:
    """Keep last N runs; pruned list is deterministic (sorted by run_id)."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "burn_in").mkdir()
    index_path = reports_dir / "index.json"
    index = load_index(index_path)
    for i in range(5):
        append_burn_in_ops_run(index, {
            "run_id": f"run_{i:03d}",
            "created_at_utc": "2025-01-01T12:00:00Z",
            "connector_name": "dummy",
            "matches_count": 0,
            "status": "ok",
            "alerts_count": 0,
            "activated": False,
        })
    save_index(index, index_path)
    for i in range(5):
        (reports_dir / "burn_in" / f"run_{i:03d}").mkdir(parents=True)

    index_out, deleted_paths, errs = cleanup_reports(
        str(reports_dir),
        keep_last_n=2,
        dry_run=False,
        index_path=index_path,
    )
    assert errs == 0
    run_ids_left = {e.get("run_id") for e in index_out.get("burn_in_ops_runs") or []}
    assert run_ids_left == {"run_003", "run_004"}
    assert not (reports_dir / "burn_in" / "run_000").exists()
    assert not (reports_dir / "burn_in" / "run_001").exists()
    assert not (reports_dir / "burn_in" / "run_002").exists()
    assert (reports_dir / "burn_in" / "run_003").exists()
    assert (reports_dir / "burn_in" / "run_004").exists()
