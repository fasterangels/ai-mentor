"""
Integration test: MULTI_PROVIDER_PARITY using recorded fixtures for both providers.
No external network.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from runner.provider_parity_runner import run_provider_parity
from reports.index_store import load_index


def test_multi_provider_parity_recorded_fixtures(tmp_path: Path) -> None:
    """Run MULTI_PROVIDER_PARITY with sample_platform and real_provider_2 (recorded fixtures)."""
    index_path = tmp_path / "index.json"
    reports_dir = tmp_path / "reports"
    result = run_provider_parity(
        provider_a_name="sample_platform",
        provider_b_name="real_provider_2",
        match_ids=None,
        reports_dir=reports_dir,
        index_path=str(index_path),
    )
    assert "error" not in result or result.get("error") != "CONNECTOR_NOT_AVAILABLE"
    assert "run_id" in result
    assert result.get("provider_a") == "sample_platform"
    assert result.get("provider_b") == "real_provider_2"
    assert "parity" in result
    assert "summary" in result["parity"]
    assert "alerts" in result["parity"]
    assert "_report_path" in result
    assert (tmp_path / "reports" / "provider_parity").exists()
    index = load_index(index_path)
    assert "provider_parity_runs" in index
    assert len(index["provider_parity_runs"]) >= 1
    assert index["latest_provider_parity_run_id"] == result["run_id"]
