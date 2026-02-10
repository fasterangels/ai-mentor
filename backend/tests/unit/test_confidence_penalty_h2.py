"""
Unit tests for H2 confidence penalty (Part A): lookup, missing params, determinism, clamping.
Read-only computation; no effect applied.
"""

from __future__ import annotations

from modeling.confidence_penalty import PenaltyResult, compute_penalty
from modeling.reason_decay.model import BAND_ORDER, DecayModelParams, FitDiagnostics


def _params(penalty_by_band: list[float], bands_with_support: int = 7) -> DecayModelParams:
    return DecayModelParams(
        market="one_x_two",
        reason_code="R1",
        bands=list(BAND_ORDER),
        penalty_by_band=penalty_by_band,
        fitted_at_utc="2025-01-01T00:00:00+00:00",
        fit_quality=FitDiagnostics(
            bands_with_support=bands_with_support,
            total_bands=len(BAND_ORDER),
            coverage_counts=[10] * len(BAND_ORDER),
            mse_vs_baseline=None,
        ),
    )


class TestPenaltyLookupByAgeBand:
    """penalty_for(age_band) returns correct penalty for band."""

    def test_lookup_youngest_band(self) -> None:
        params = _params([1.0, 0.9, 0.7, 0.5, 0.3, 0.2, 0.1])
        r = compute_penalty("m", "r", "0-30m", 0.8, params)
        assert r.penalty_factor == 1.0
        assert r.penalized_confidence == 0.8

    def test_lookup_oldest_band(self) -> None:
        params = _params([1.0, 0.9, 0.7, 0.5, 0.3, 0.2, 0.1])
        r = compute_penalty("m", "r", "7d+", 0.8, params)
        assert r.penalty_factor == 0.1
        assert abs(r.penalized_confidence - 0.08) < 1e-9

    def test_lookup_middle_band(self) -> None:
        params = _params([1.0, 0.9, 0.6, 0.5, 0.3, 0.2, 0.1])
        r = compute_penalty("m", "r", "2h-6h", 0.5, params)
        assert r.penalty_factor == 0.6
        assert r.penalized_confidence == 0.3


class TestMissingParamsPenaltyOne:
    """Missing or low-support params -> penalty_factor = 1.0."""

    def test_none_params(self) -> None:
        r = compute_penalty("m", "r", "7d+", 0.7, None)
        assert r.penalty_factor == 1.0
        assert r.penalized_confidence == 0.7

    def test_zero_bands_with_support(self) -> None:
        params = _params([0.1] * 7, bands_with_support=0)
        r = compute_penalty("m", "r", "7d+", 0.7, params)
        assert r.penalty_factor == 1.0
        assert r.penalized_confidence == 0.7


class TestDeterminism:
    """Same inputs -> same PenaltyResult."""

    def test_same_input_same_output(self) -> None:
        params = _params([1.0, 0.8, 0.5])
        a = compute_penalty("m", "r", "30m-2h", 0.6, params)
        b = compute_penalty("m", "r", "30m-2h", 0.6, params)
        assert a.penalty_factor == b.penalty_factor
        assert a.penalized_confidence == b.penalized_confidence

    def test_same_input_same_result_fields(self) -> None:
        params = _params([0.5])
        r = compute_penalty("one_x_two", "RC", "0-30m", 0.9, params)
        assert r.market == "one_x_two"
        assert r.reason_code == "RC"
        assert r.age_band == "0-30m"
        assert r.original_confidence == 0.9


class TestClamping:
    """penalty_factor and penalized_confidence are in [0, 1]. No boosts."""

    def test_penalty_factor_clamped_to_one(self) -> None:
        # If params had >1 (shouldn't), we clamp
        params = _params([1.5, 1.0, 0.5])  # first band 1.5
        r = compute_penalty("m", "r", "0-30m", 0.8, params)
        assert r.penalty_factor <= 1.0
        assert r.penalty_factor == 1.0

    def test_penalty_factor_clamped_to_zero(self) -> None:
        params = _params([-0.1, 0.0, 0.5])
        r = compute_penalty("m", "r", "0-30m", 0.8, params)
        assert r.penalty_factor >= 0.0
        assert r.penalty_factor == 0.0

    def test_penalized_confidence_clamped(self) -> None:
        params = _params([0.0])  # penalty 0
        r = compute_penalty("m", "r", "0-30m", 1.0, params)
        assert r.penalized_confidence >= 0.0
        assert r.penalized_confidence <= 1.0
        assert r.penalized_confidence == 0.0
