"""
Unit tests for the decision engine backtesting / simulation module.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.simulation.backtest_engine import (  # type: ignore[import-error]
    BacktestConfig,
    extract_rows_from_report,
    simulate_backtest,
    simulate_from_report,
)


def test_basic_simulation_precision_positive() -> None:
    rows: List[Dict[str, object]] = [
        {"market": "A", "score": 0.9, "outcome": 1},
        {"market": "A", "score": 0.8, "outcome": 1},
        {"market": "A", "score": 0.2, "outcome": 0},
        {"market": "A", "score": 0.1, "outcome": 0},
    ]

    cfg = BacktestConfig(thresholds=None, version="v_test")
    result = simulate_backtest(rows, cfg)
    metrics = result["metrics"]

    assert metrics["n_predictions"] == 4
    assert metrics["precision"] > 0.0


def test_threshold_change_effect_on_go_rate() -> None:
    rows: List[Dict[str, object]] = [
        {"market": "A", "score": 0.9, "outcome": 1},
        {"market": "A", "score": 0.8, "outcome": 1},
        {"market": "A", "score": 0.6, "outcome": 0},
        {"market": "A", "score": 0.4, "outcome": 0},
    ]

    low_cfg = BacktestConfig(thresholds={"default": 0.3}, version="low")
    high_cfg = BacktestConfig(thresholds={"default": 0.7}, version="high")

    low_result = simulate_backtest(rows, low_cfg)
    high_result = simulate_backtest(rows, high_cfg)

    low_go_rate = low_result["metrics"]["go_rate"]
    high_go_rate = high_result["metrics"]["go_rate"]

    assert low_go_rate >= high_go_rate


def test_simulate_from_report_uses_extracted_rows() -> None:
    report = {
        "predictions": [
            {"id": "p1", "outcome": 1, "market": "A"},
            {"id": "p2", "outcome": 0, "market": "A"},
        ],
        "decision_engine_outputs": [
            {"id": "p1", "market": "A", "score": 0.9},
            {"id": "p2", "market": "A", "score": 0.4},
        ],
    }

    rows = extract_rows_from_report(report)
    assert len(rows) == 2

    cfg = BacktestConfig(thresholds={"default": 0.5}, version="v_report")
    result = simulate_from_report(report, cfg)
    metrics = result["metrics"]

    assert metrics["n_predictions"] == 2
    # With threshold 0.5, only p1 should be GO and correct.
    assert metrics["precision"] == 1.0

