"""
Unit tests for the policy experiment runner.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.experiments.policy_experiment_runner import (  # type: ignore[import-error]
    ExperimentConfig,
    run_policy_experiment,
)


def _make_synthetic_report() -> Dict[str, Any]:
    # Construct a minimal report with predictions and decision_engine_outputs
    # such that higher thresholds yield higher precision but lower coverage.
    return {
        "predictions": [
            {"id": "p1", "outcome": 1, "market": "A"},
            {"id": "p2", "outcome": 1, "market": "A"},
            {"id": "p3", "outcome": 0, "market": "A"},
            {"id": "p4", "outcome": 0, "market": "A"},
        ],
        "decision_engine_outputs": [
            {"id": "p1", "market": "A", "score": 0.9},
            {"id": "p2", "market": "A", "score": 0.8},
            {"id": "p3", "market": "A", "score": 0.6},
            {"id": "p4", "market": "A", "score": 0.3},
        ],
    }


def test_policy_experiment_basic_properties() -> None:
    report = _make_synthetic_report()
    cfg = ExperimentConfig(
        version="v_exp",
        objective="precision",
        min_coverage=0.20,
        threshold_grid=[0.3, 0.5, 0.7],
    )

    out = run_policy_experiment(report, cfg)

    assert out["version"] == "v_exp"
    assert out["n_rows"] == 4
    assert out["objective"] == "precision"
    assert out["min_coverage"] == 0.20

    best = out["best"]
    assert best is not None
    best_t = float(best["thresholds"]["default"])
    assert 0.30 <= best_t <= 0.80

    table = out["table"]
    # Sorted ascending by threshold
    ts = [row["t"] for row in table]
    assert ts == sorted(ts)

    # At least one row meets min_coverage
    assert any(row["meets_min_coverage"] for row in table)

