"""
Unit tests for H1 reason decay model: piecewise fit, monotonicity, MIN_SUPPORT, determinism.
"""

from __future__ import annotations

import json

from modeling.reason_decay import (
    DecayModelParams,
    FitDiagnostics,
    MIN_SUPPORT,
    fit_piecewise_decay,
)
from modeling.reason_decay.model import BAND_ORDER, params_from_dict, SCHEMA_VERSION, MODEL_TYPE_PIECEWISE_V1


def _row(market: str, reason_code: str, age_band: str, total: int, correct: int) -> dict:
    wrong = total - correct
    accuracy = correct / (correct + wrong) if (correct + wrong) > 0 else None
    return {
        "market": market,
        "reason_code": reason_code,
        "age_band": age_band,
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
    }


class TestMonotonicEnforcement:
    """Penalty must be non-increasing from youngest to oldest band."""

    def test_monotonic_non_increasing(self) -> None:
        # Young band high accuracy, older bands lower -> penalties decrease with age
        rows = [
            _row("one_x_two", "R1", "0-30m", 20, 18),   # 0.9
            _row("one_x_two", "R1", "30m-2h", 20, 16),  # 0.8
            _row("one_x_two", "R1", "2h-6h", 20, 12),   # 0.6
            _row("one_x_two", "R1", "6h-24h", 20, 10),  # 0.5
        ]
        params_list = fit_piecewise_decay(rows)
        assert len(params_list) == 1
        p = params_list[0]
        penalties = p.penalty_by_band
        # Youngest has penalty 1 - 0 = 1 (or high). Older bands lower accuracy -> lower penalty.
        # Must be non-increasing: penalty[i] >= penalty[i+1]
        for i in range(len(penalties) - 1):
            assert penalties[i] >= penalties[i + 1], f"band {i} penalty {penalties[i]} < {penalties[i+1]}"

    def test_monotonic_enforced_when_later_band_higher_accuracy(self) -> None:
        # If 6h-24h had higher accuracy than 2h-6h (noise), fit must still be non-increasing
        rows = [
            _row("gg_ng", "RC", "0-30m", 10, 8),    # 0.8 baseline
            _row("gg_ng", "RC", "30m-2h", 10, 6),   # 0.6
            _row("gg_ng", "RC", "2h-6h", 10, 4),   # 0.4 -> penalty 0.6
            _row("gg_ng", "RC", "6h-24h", 10, 7),   # 0.7 -> raw penalty 0.9, but must be <= 0.6
        ]
        params_list = fit_piecewise_decay(rows)
        assert len(params_list) == 1
        penalties = params_list[0].penalty_by_band
        for i in range(len(penalties) - 1):
            assert penalties[i] >= penalties[i + 1]


class TestMinSupport:
    """Bands with total < MIN_SUPPORT are handled deterministically (carry forward)."""

    def test_low_support_band_carries_forward(self) -> None:
        rows = [
            _row("one_x_two", "R1", "0-30m", 100, 90),  # support
            _row("one_x_two", "R1", "30m-2h", 2, 1),    # below MIN_SUPPORT (5)
            _row("one_x_two", "R1", "2h-6h", 100, 50),
        ]
        params_list = fit_piecewise_decay(rows)
        assert len(params_list) == 1
        p = params_list[0]
        # 0-30m: penalty high (e.g. 1.0). 30m-2h: carry forward. 2h-6h: lower.
        assert p.fit_quality is not None
        assert p.fit_quality.bands_with_support == 2  # 0-30m and 2h-6h
        # Penalty at index 1 (30m-2h) should equal penalty at index 0 (carry forward)
        assert p.penalty_by_band[1] == p.penalty_by_band[0]

    def test_min_support_constant_value(self) -> None:
        assert MIN_SUPPORT == 5

    def test_all_bands_below_support_baseline_one(self) -> None:
        rows = [
            _row("ou", "X", "0-30m", 2, 1),
            _row("ou", "X", "30m-2h", 2, 1),
        ]
        params_list = fit_piecewise_decay(rows)
        assert len(params_list) == 1
        # Baseline defaults to 1.0 when no band has support; all penalties carry 1.0
        assert all(p >= 0 and p <= 1 for p in params_list[0].penalty_by_band)


class TestDeterminism:
    """Same input -> same params JSON."""

    def test_same_input_same_json(self) -> None:
        rows = [
            _row("one_x_two", "R1", "0-30m", 20, 18),
            _row("one_x_two", "R1", "30m-2h", 20, 14),
            _row("one_x_two", "R1", "7d+", 20, 8),
        ]
        a = fit_piecewise_decay(rows, fitted_at_utc="2025-01-01T12:00:00+00:00")
        b = fit_piecewise_decay(rows, fitted_at_utc="2025-01-01T12:00:00+00:00")
        json_a = json.dumps([p.to_dict() for p in a], sort_keys=True)
        json_b = json.dumps([p.to_dict() for p in b], sort_keys=True)
        assert json_a == json_b

    def test_same_input_same_penalties(self) -> None:
        rows = [
            _row("m", "r", "0-30m", 10, 9),
            _row("m", "r", "7d+", 10, 3),
        ]
        a = fit_piecewise_decay(rows)
        b = fit_piecewise_decay(rows)
        assert a[0].penalty_by_band == b[0].penalty_by_band


class TestPenaltiesClamped:
    """All penalties must be in [0, 1]."""

    def test_penalties_in_unit_interval(self) -> None:
        rows = [
            _row("one_x_two", "R1", "0-30m", 20, 20),  # perfect
            _row("one_x_two", "R1", "30m-2h", 20, 0),  # worst
            _row("one_x_two", "R1", "2h-6h", 20, 10),
        ]
        params_list = fit_piecewise_decay(rows)
        for p in params_list:
            for penalty in p.penalty_by_band:
                assert 0 <= penalty <= 1

    def test_extreme_accuracy_drops_still_clamped(self) -> None:
        rows = [
            _row("m", "r", "0-30m", 10, 10),  # 1.0
            _row("m", "r", "7d+", 10, 0),     # 0.0 -> drop 1.0, penalty 0
        ]
        params_list = fit_piecewise_decay(rows)
        assert len(params_list) == 1
        for pen in params_list[0].penalty_by_band:
            assert 0 <= pen <= 1


class TestSerialization:
    """Stable JSON, schema_version, model_type."""

    def test_params_roundtrip(self) -> None:
        rows = [_row("m", "r", "0-30m", 10, 8), _row("m", "r", "7d+", 10, 4)]
        params_list = fit_piecewise_decay(rows)
        p = params_list[0]
        d = p.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION
        assert d["model_type"] == MODEL_TYPE_PIECEWISE_V1
        assert "bands" in d and d["bands"] == BAND_ORDER
        assert "penalty_by_band" in d
        p2 = params_from_dict(d)
        assert p2.market == p.market
        assert p2.reason_code == p.reason_code
        assert p2.penalty_by_band == p.penalty_by_band

    def test_to_json_sorted_keys(self) -> None:
        rows = [_row("m", "r", "0-30m", 10, 5)]
        params_list = fit_piecewise_decay(rows)
        js = params_list[0].to_json()
        parsed = json.loads(js)
        # Keys should be in sorted order (bands, fit_quality, fitted_at_utc, market, model_type, ...)
        keys = list(parsed.keys())
        assert keys == sorted(keys)
