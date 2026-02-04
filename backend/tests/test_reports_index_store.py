"""
Tests for reports index_store: append_run updates latest_run_id and stable JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from reports.index_store import load_index, append_run, save_index


def test_load_index_missing_returns_empty(tmp_path: Path) -> None:
    index = load_index(tmp_path / "nonexistent.json")
    assert index["runs"] == []
    assert index["latest_run_id"] is None


def test_load_index_invalid_json_returns_empty(tmp_path: Path) -> None:
    invalid_path = tmp_path / "index.json"
    invalid_path.write_text("not valid json {", encoding="utf-8")
    index = load_index(invalid_path)
    assert index["runs"] == []
    assert index["latest_run_id"] is None


def test_append_run_updates_latest_run_id_and_persists_stable_json(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    index = load_index(index_path)
    assert index["latest_run_id"] is None

    run_meta = {
        "run_id": "shadow_batch_20250601_120000_abc12345",
        "created_at_utc": "2025-06-01T12:00:00+00:00",
        "connector_name": "dummy",
        "matches_count": 2,
        "batch_output_checksum": "abc123",
        "alerts_count": 0,
    }
    append_run(index, run_meta)
    assert index["latest_run_id"] == "shadow_batch_20250601_120000_abc12345"
    assert len(index["runs"]) == 1
    assert index["runs"][0]["run_id"] == run_meta["run_id"]
    assert index["runs"][0]["alerts_count"] == 0

    save_index(index, index_path)
    assert index_path.exists()
    raw = index_path.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert parsed["latest_run_id"] == run_meta["run_id"]
    assert len(parsed["runs"]) == 1

    # Stable JSON: keys sorted (alphabetically "latest_run_id" before "runs")
    assert raw.index('"latest_run_id"') < raw.index('"runs"')

    # Second append
    run_meta2 = {
        "run_id": "shadow_batch_20250602_100000_def67890",
        "created_at_utc": "2025-06-02T10:00:00+00:00",
        "connector_name": "dummy",
        "matches_count": 3,
        "batch_output_checksum": "def678",
        "alerts_count": 1,
    }
    index2 = load_index(index_path)
    append_run(index2, run_meta2)
    assert index2["latest_run_id"] == "shadow_batch_20250602_100000_def67890"
    assert len(index2["runs"]) == 2
    save_index(index2, index_path)
    index3 = load_index(index_path)
    assert index3["latest_run_id"] == run_meta2["run_id"]
    assert len(index3["runs"]) == 2
