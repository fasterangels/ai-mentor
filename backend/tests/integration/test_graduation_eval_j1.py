"""
Integration tests for graduation-eval mode (J1 Part B).
Run graduation evaluation; assert graduation_result.json and graduation_result.md written and reflect PASS/FAIL.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.graduation_runner import run_graduation_eval, GRADUATION_RESULT_JSON, GRADUATION_RESULT_MD


def _build_minimal_pass_artifacts(reports_dir: Path) -> None:
    """Create minimal artifacts under reports_dir so all graduation criteria pass."""
    delta_dir = reports_dir / "delta_eval"
    delta_dir.mkdir(parents=True)
    N = 60
    reports = [
        {"fixture_id": f"f{i}", "recorded_snapshot_id": "r", "live_snapshot_id": "l", "payload_match": True}
        for i in range(N)
    ]
    (delta_dir / "delta_eval_001.json").write_text(
        json.dumps({"reports": reports, "summary": {"complete": N, "total": N}}, indent=2),
        encoding="utf-8",
    )
    (reports_dir / "staleness_eval").mkdir(parents=True)
    rows = [{"reason_code": f"R{i}", "total": 10} for i in range(25)]
    (reports_dir / "staleness_eval" / "staleness_metrics_by_reason.json").write_text(
        json.dumps({"rows": rows}, indent=2),
        encoding="utf-8",
    )
    (reports_dir / "decay_fit").mkdir(parents=True)
    params = [{"reason_code": f"R{i}", "fit_quality": {"bands_with_support": 3}} for i in range(25)]
    (reports_dir / "decay_fit" / "reason_decay_params.json").write_text(
        json.dumps({"params": params}, indent=2),
        encoding="utf-8",
    )
    (reports_dir / "uncertainty_shadow_decisions.json").write_text(
        json.dumps({"decisions": [{"id": i} for i in range(250)]}, indent=2),
        encoding="utf-8",
    )
    (reports_dir / "replay_scenarios" / "late_data").mkdir(parents=True)
    (reports_dir / "replay_scenarios" / "late_data" / "late_data_summary.json").write_text(
        json.dumps({"accuracy_delta_24h": -0.05, "refusal_delta_24h": 0.0}, indent=2),
        encoding="utf-8",
    )
    (reports_dir / "worst_case_errors_top.json").write_text(
        json.dumps({"rows": [{"reason_code": f"R{i}"} for i in range(25)]}, indent=2),
        encoding="utf-8",
    )
    (reports_dir / "refusal_optimization_best_overall.json").write_text(json.dumps({}), encoding="utf-8")
    (reports_dir / "refusal_optimization_grid_summary.csv").write_text("a,b\n1,2\n", encoding="utf-8")


def test_graduation_eval_writes_artifacts_and_overall_pass(tmp_path):
    """With minimal pass artifacts, run graduation-eval; JSON and MD written, overall PASS."""
    _build_minimal_pass_artifacts(tmp_path)
    result = run_graduation_eval(tmp_path)
    assert result.get("error") is None
    assert result.get("overall_pass") is True
    assert result.get("failed_criteria_count") == 0

    json_path = Path(result["json_path"])
    md_path = Path(result["md_path"])
    assert json_path.exists()
    assert md_path.exists()
    assert json_path.name == GRADUATION_RESULT_JSON
    assert md_path.name == GRADUATION_RESULT_MD

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["overall_pass"] is True
    assert "thresholds_used" in data
    assert "criteria" in data
    assert len(data["criteria"]) >= 1

    md_content = md_path.read_text(encoding="utf-8")
    assert "**Overall: PASS**" in md_content or "Overall: PASS" in md_content
    assert "Thresholds used" in md_content or "thresholds" in md_content.lower()


def test_graduation_eval_writes_artifacts_and_overall_fail(tmp_path):
    """With empty reports dir, run graduation-eval; JSON and MD written, overall FAIL."""
    # No artifacts created -> all criteria fail
    result = run_graduation_eval(tmp_path)
    assert result.get("error") is None
    assert result.get("overall_pass") is False
    assert result.get("failed_criteria_count", 0) >= 1

    json_path = Path(result["json_path"])
    md_path = Path(result["md_path"])
    assert json_path.exists()
    assert md_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["overall_pass"] is False
    assert "thresholds_used" in data

    md_content = md_path.read_text(encoding="utf-8")
    assert "FAIL" in md_content
