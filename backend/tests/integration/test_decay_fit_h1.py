"""
Integration test for H1 Part B: decay-fit reads G4 staleness JSON, writes params artifacts.
Decay-fit mode does not invoke analyzer or evaluator (offline-only, measurement/reporting).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from runner.decay_fit_runner import (
    DECAY_FIT_SUBDIR,
    PARAMS_JSON_NAME,
    run_decay_fit_mode,
    STALENESS_JSON_NAME,
)

# Use a subdir under integration tests to avoid tmp_path permission issues in some environments.
TMP_DECAY_FIT_DIR = Path(__file__).resolve().parent / "tmp_decay_fit_reports"


def _staleness_row(market: str, reason_code: str, age_band: str, total: int, correct: int) -> dict:
    wrong = total - correct
    accuracy = correct / (correct + wrong) if (correct + wrong) > 0 else None
    return {
        "market": market,
        "reason_code": reason_code,
        "age_band": age_band,
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "neutral_rate": None,
        "avg_confidence": None,
    }


@pytest.fixture
def tmp_reports_with_staleness():
    """Minimal G4 staleness metrics JSON so decay-fit has input (workspace dir)."""
    staleness_dir = TMP_DECAY_FIT_DIR / "with_staleness" / "staleness_eval"
    staleness_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        _staleness_row("one_x_two", "R1", "0-30m", 10, 8),
        _staleness_row("one_x_two", "R1", "30m-2h", 10, 6),
        _staleness_row("one_x_two", "R1", "2h-6h", 10, 4),
    ]
    path = staleness_dir / STALENESS_JSON_NAME
    path.write_text(
        json.dumps(
            {"run_id": "test_run", "computed_at_utc": "2025-01-01T00:00:00+00:00", "rows": rows},
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return TMP_DECAY_FIT_DIR / "with_staleness"


def test_decay_fit_writes_params_json_and_contains_expected_keys(tmp_reports_with_staleness):
    """
    Run decay-fit on a minimal staleness fixture; assert output JSON exists and has expected structure.
    Analyzer and evaluator are not invoked (runner only reads JSON and writes artifacts).
    """
    reports_dir = tmp_reports_with_staleness
    result = run_decay_fit_mode(reports_dir=reports_dir)
    assert result.get("error") is None, result.get("error")
    assert result.get("params_count", 0) >= 1
    params_path = result.get("params_path")
    assert params_path is not None
    path = Path(params_path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "params" in data
    assert "fitted_at_utc" in data
    params_list = data["params"]
    assert len(params_list) >= 1
    one = params_list[0]
    assert "market" in one
    assert "reason_code" in one
    assert "penalty_by_band" in one
    assert "model_type" in one
    assert one.get("model_type") == "PIECEWISE_V1"


def test_decay_fit_missing_staleness_returns_error():
    """When G4 staleness JSON is missing, decay-fit returns error and does not write params."""
    empty_dir = TMP_DECAY_FIT_DIR / "empty"
    empty_dir.mkdir(parents=True, exist_ok=True)
    result = run_decay_fit_mode(reports_dir=empty_dir)
    assert result.get("error") == "missing_staleness_json"
    assert result.get("params_count", 0) == 0
    out_dir = empty_dir / DECAY_FIT_SUBDIR
    assert not (out_dir / PARAMS_JSON_NAME).exists()
