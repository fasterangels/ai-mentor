"""
Tests for limits: pruning keeps newest N runs.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from limits.limits import MAX_REPORTS_RETAINED, prune_index
from reports.index_store import load_index, append_run, save_index


def test_prune_keeps_newest_n(tmp_path: Path) -> None:
    """Pruning keeps at most MAX_REPORTS_RETAINED newest runs."""
    index_path = tmp_path / "index.json"
    index = load_index(index_path)
    for i in range(MAX_REPORTS_RETAINED + 10):
        append_run(index, {
            "run_id": f"run_{i:03d}",
            "created_at_utc": f"2025-01-01T{i:02d}:00:00+00:00",
            "connector_name": "dummy",
            "matches_count": 1,
            "batch_output_checksum": f"c{i}",
            "alerts_count": 0,
        })
    assert len(index["runs"]) == MAX_REPORTS_RETAINED + 10
    prune_index(index, max_retained=MAX_REPORTS_RETAINED)
    assert len(index["runs"]) == MAX_REPORTS_RETAINED
    # Newest run is last appended
    assert index["runs"][0]["run_id"] == "run_010"
    assert index["runs"][-1]["run_id"] == "run_109"
    assert index["latest_run_id"] == "run_109"
    save_index(index, index_path)
    reloaded = load_index(index_path)
    assert len(reloaded["runs"]) == MAX_REPORTS_RETAINED
    assert reloaded["latest_run_id"] == "run_109"


def test_prune_under_limit_unchanged(tmp_path: Path) -> None:
    """When runs <= max_retained, prune does not remove any."""
    index = {"runs": [{"run_id": "r1", "alerts_count": 0}], "latest_run_id": "r1"}
    prune_index(index, max_retained=100)
    assert len(index["runs"]) == 1
    assert index["latest_run_id"] == "r1"


def test_prune_empty_runs_consistent() -> None:
    """Prune with no runs leaves latest_run_id None."""
    index = {"runs": [], "latest_run_id": None}
    prune_index(index, max_retained=10)
    assert index["runs"] == []
    assert index["latest_run_id"] is None
