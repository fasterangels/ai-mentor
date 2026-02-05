"""Unit tests for shadow tuner constraint logic: step cap, total cap, drift budgets, freeze, determinism."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from policy.tuner_constraints import (
    TunerConstraintsConfig,
    apply_constraints,
    get_tuner_constraints,
)


def test_per_param_step_max_clamping():
    """Per-parameter step cap clamps each delta to +/- per_param_step_max."""
    config = TunerConstraintsConfig(
        drift_budgets={"per_market": {}, "per_param_group": {}},
        hard_caps={"per_param_step_max": 0.01, "per_run_total_delta_max": 1.0},
        freeze_params=[],
    )
    current_m = {}
    current_r = {}
    # One delta +0.05 -> clamped to +0.01
    diffs = [("markets.one_x_two.min_confidence", 0.50, 0.55, "test")]
    out, summary = apply_constraints(current_m, current_r, diffs, config=config)
    assert len(out) == 1
    path, old, new, _ = out[0]
    assert path == "markets.one_x_two.min_confidence"
    assert old == 0.50
    assert abs((new - old) - 0.01) < 1e-9
    assert summary["clamped_params_count"] == 1
    assert summary["caps_applied"] is True


def test_per_run_total_scaling_deterministic():
    """If sum(|delta|) > per_run_total_delta_max, scale down proportionally; deterministic."""
    config = TunerConstraintsConfig(
        drift_budgets={"per_market": {}, "per_param_group": {}},
        hard_caps={"per_param_step_max": 0.1, "per_run_total_delta_max": 0.05},
        freeze_params=[],
    )
    current_m = {}
    current_r = {}
    # Two deltas 0.03 each -> total 0.06 > 0.05 -> scale by 0.05/0.06
    diffs = [
        ("markets.one_x_two.min_confidence", 0.50, 0.53, "a"),
        ("markets.over_under_25.min_confidence", 0.52, 0.55, "b"),
    ]
    out1, summary1 = apply_constraints(current_m, current_r, diffs, config=config)
    out2, summary2 = apply_constraints(current_m, current_r, diffs, config=config)
    assert summary1["scaled_down"] is True
    assert summary2["scaled_down"] is True
    total_abs = sum(abs(out1[i][2] - out1[i][1]) for i in range(len(out1)))
    assert total_abs <= 0.05 + 1e-9
    assert out1[0][1] == out2[0][1] and out1[0][2] == out2[0][2]
    assert out1[1][1] == out2[1][1] and out1[1][2] == out2[1][2]


def test_drift_budget_enforcement_deterministic():
    """Per-market budget scales group when exceeded; result deterministic."""
    config = TunerConstraintsConfig(
        drift_budgets={
            "per_market": {"one_x_two": 0.02},
            "per_param_group": {"thresholds": 0.05},
        },
        hard_caps={"per_param_step_max": 0.1, "per_run_total_delta_max": 0.2},
        freeze_params=[],
    )
    current_m = {}
    current_r = {}
    # Single market one_x_two with delta 0.04 > budget 0.02 -> scale to 0.02
    diffs = [("markets.one_x_two.min_confidence", 0.50, 0.54, "test")]
    out, summary = apply_constraints(current_m, current_r, diffs, config=config)
    assert len(out) == 1
    delta = out[0][2] - out[0][1]
    assert abs(delta) <= 0.02 + 1e-9
    out2, _ = apply_constraints(current_m, current_r, diffs, config=config)
    assert out[0][2] == out2[0][2]


def test_freeze_params_zeroed():
    """Params in freeze_params get delta=0 (new_val = old_val)."""
    config = TunerConstraintsConfig(
        drift_budgets={"per_market": {}, "per_param_group": {}},
        hard_caps={"per_param_step_max": 0.1, "per_run_total_delta_max": 0.2},
        freeze_params=["markets.one_x_two.min_confidence"],
    )
    current_m = {}
    current_r = {}
    diffs = [("markets.one_x_two.min_confidence", 0.50, 0.60, "test")]
    out, summary = apply_constraints(current_m, current_r, diffs, config=config)
    assert len(out) == 1
    assert out[0][1] == out[0][2] == 0.50
    assert summary["top_deltas"] == [] or all(d == 0 for _, d in summary["top_deltas"]) is False  # frozen has 0 delta


def test_deterministic_ordering():
    """Same diffs in different order produce same constrained output (sort by path)."""
    config = get_tuner_constraints()
    current_m = {}
    current_r = {}
    diffs_a = [
        ("markets.gg_ng.min_confidence", 0.55, 0.57, "c"),
        ("markets.one_x_two.min_confidence", 0.50, 0.52, "a"),
        ("markets.over_under_25.min_confidence", 0.52, 0.54, "b"),
    ]
    diffs_b = [
        ("markets.over_under_25.min_confidence", 0.52, 0.54, "b"),
        ("markets.one_x_two.min_confidence", 0.50, 0.52, "a"),
        ("markets.gg_ng.min_confidence", 0.55, 0.57, "c"),
    ]
    out_a, _ = apply_constraints(current_m, current_r, diffs_a, config=config)
    out_b, _ = apply_constraints(current_m, current_r, diffs_b, config=config)
    out_a_sorted = sorted(out_a, key=lambda x: x[0])
    out_b_sorted = sorted(out_b, key=lambda x: x[0])
    for (p1, o1, n1, _), (p2, o2, n2, _) in zip(out_a_sorted, out_b_sorted):
        assert p1 == p2 and o1 == o2 and n1 == n2


def test_summary_structure():
    """Summary contains budgets_used, caps_applied, scaled_down, clamped_params_count, top_deltas (max 5)."""
    config = get_tuner_constraints()
    diffs = [("markets.one_x_two.min_confidence", 0.50, 0.51, "test")]
    _, summary = apply_constraints({}, {}, diffs, config=config)
    assert "budgets_used" in summary
    assert "caps_applied" in summary
    assert "scaled_down" in summary
    assert "clamped_params_count" in summary
    assert "top_deltas" in summary
    assert len(summary["top_deltas"]) <= 5
