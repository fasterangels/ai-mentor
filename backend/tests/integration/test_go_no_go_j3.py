"""
Integration tests for go-no-go mode (J3 Part B).
Temp reports dir with fake graduation_result.json (PASS/FAIL); assert JSON/MD and GO/NO_GO.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from runner.go_no_go_runner import (
    GO_NO_GO_DECISION_JSON,
    GO_NO_GO_DECISION_MD,
    GRADUATION_RESULT_JSON,
    run_go_no_go,
)


@pytest.fixture
def tmp_reports_path(tmp_path: Path) -> Path:
    """Use pytest tmp_path (deterministic per test)."""
    return tmp_path


def _write_graduation_result(reports_dir: Path, overall_pass: bool, criteria: list | None = None) -> None:
    if criteria is None:
        if overall_pass:
            criteria = [
                {"name": "c1", "pass": True, "details": {}},
                {"name": "c2", "pass": True, "details": {}},
            ]
        else:
            criteria = [
                {"name": "c1", "pass": True, "details": {}},
                {"name": "c2", "pass": False, "details": {"reason": "below threshold"}},
            ]
    payload = {
        "overall_pass": overall_pass,
        "computed_at_utc": "2025-02-01T12:00:00+00:00",
        "criteria": criteria,
    }
    (reports_dir / GRADUATION_RESULT_JSON).write_text(json.dumps(payload), encoding="utf-8")


def test_go_no_go_pass_produces_go(tmp_reports_path: Path) -> None:
    """PASS graduation_result -> GO decision; JSON and MD written."""
    _write_graduation_result(tmp_reports_path, overall_pass=True)
    result = run_go_no_go(reports_dir=str(tmp_reports_path))
    assert result.get("error") is None
    assert result.get("decision") == "GO"
    assert (tmp_reports_path / GO_NO_GO_DECISION_JSON).exists()
    assert (tmp_reports_path / GO_NO_GO_DECISION_MD).exists()

    data = json.loads((tmp_reports_path / GO_NO_GO_DECISION_JSON).read_text(encoding="utf-8"))
    assert data["decision"] == "GO"
    assert data["schema_version"] == 1
    assert "decision_time_utc" in data
    assert data.get("failed_criteria") == []

    md = (tmp_reports_path / GO_NO_GO_DECISION_MD).read_text(encoding="utf-8")
    assert "**Decision: GO**" in md
    assert "Timestamp" in md


def test_go_no_go_fail_produces_no_go(tmp_reports_path: Path) -> None:
    """FAIL graduation_result -> NO_GO decision; failed criteria in JSON and MD."""
    _write_graduation_result(tmp_reports_path, overall_pass=False)
    result = run_go_no_go(reports_dir=str(tmp_reports_path))
    assert result.get("error") is None
    assert result.get("decision") == "NO_GO"
    assert (tmp_reports_path / GO_NO_GO_DECISION_JSON).exists()
    assert (tmp_reports_path / GO_NO_GO_DECISION_MD).exists()

    data = json.loads((tmp_reports_path / GO_NO_GO_DECISION_JSON).read_text(encoding="utf-8"))
    assert data["decision"] == "NO_GO"
    assert len(data.get("failed_criteria", [])) >= 1
    assert any(f.get("name") == "c2" for f in data["failed_criteria"])

    md = (tmp_reports_path / GO_NO_GO_DECISION_MD).read_text(encoding="utf-8")
    assert "**Decision: NO_GO**" in md
    assert "Failed criteria" in md
    assert "c2" in md


def test_go_no_go_missing_graduation_returns_error(tmp_reports_path: Path) -> None:
    """Missing graduation_result.json -> error, no artifacts."""
    result = run_go_no_go(reports_dir=str(tmp_reports_path))
    assert result.get("error") is not None
    assert "not found" in result["error"]
    assert result.get("decision") is None
    assert not (tmp_reports_path / GO_NO_GO_DECISION_JSON).exists()
    assert not (tmp_reports_path / GO_NO_GO_DECISION_MD).exists()
