"""
Unit tests for H3 uncertainty signals (Part A): STALE_EVIDENCE, LOW_EFFECTIVE_CONFIDENCE, determinism, missing skip.
"""

from __future__ import annotations

from modeling.uncertainty import (
    LOW_EFFECTIVE_CONFIDENCE_THRESHOLD,
    STALE_EVIDENCE_BANDS,
    compute_uncertainty_profile,
)
from modeling.uncertainty.model import (
    LOW_EFFECTIVE_CONFIDENCE,
    LOW_SUPPORT,
    STALE_EVIDENCE,
)
from modeling.reason_decay.model import DecayModelParams, FitDiagnostics, BAND_ORDER


def _decision(run_id: str, age_band: str, reason_codes: dict, market_confidence: dict | None = None) -> dict:
    return {
        "run_id": run_id,
        "age_band": age_band,
        "reason_codes_by_market": reason_codes or {},
        "market_to_confidence": market_confidence or {},
    }


def _shadow_row(run_id: str, market: str, reason_code: str, penalized_confidence: float) -> dict:
    return {
        "run_id": run_id,
        "market": market,
        "reason_code": reason_code,
        "penalized_confidence": penalized_confidence,
    }


def _decay_params(market: str, reason_code: str, bands_with_support: int) -> DecayModelParams:
    return DecayModelParams(
        market=market,
        reason_code=reason_code,
        bands=list(BAND_ORDER),
        penalty_by_band=[1.0] * len(BAND_ORDER),
        fit_quality=FitDiagnostics(
            bands_with_support=bands_with_support,
            total_bands=len(BAND_ORDER),
            coverage_counts=[10] * len(BAND_ORDER),
            mse_vs_baseline=None,
        ),
    )


class TestStaleEvidence:
    """STALE_EVIDENCE triggers at configured age bands."""

    def test_stale_triggered_7d_plus(self) -> None:
        rec = _decision("r1", "7d+", {"one_x_two": ["R1"]})
        profile = compute_uncertainty_profile(rec, [], {})
        stale = next(s for s in profile.signals if s.signal_type == STALE_EVIDENCE)
        assert stale.triggered is True
        assert stale.reason_code == "7d+"

    def test_stale_triggered_3d_7d(self) -> None:
        rec = _decision("r1", "3d-7d", {"one_x_two": ["R1"]})
        profile = compute_uncertainty_profile(rec, [], {})
        stale = next(s for s in profile.signals if s.signal_type == STALE_EVIDENCE)
        assert stale.triggered is True
        assert stale.reason_code == "3d-7d"

    def test_stale_not_triggered_young_band(self) -> None:
        rec = _decision("r1", "0-30m", {"one_x_two": ["R1"]})
        profile = compute_uncertainty_profile(rec, [], {})
        stale = next(s for s in profile.signals if s.signal_type == STALE_EVIDENCE)
        assert stale.triggered is False
        assert stale.reason_code == "0-30m"

    def test_stale_not_triggered_1d_3d(self) -> None:
        rec = _decision("r1", "1d-3d", {})
        profile = compute_uncertainty_profile(rec, [], {})
        stale = next(s for s in profile.signals if s.signal_type == STALE_EVIDENCE)
        assert stale.triggered is False


class TestLowEffectiveConfidence:
    """LOW_EFFECTIVE_CONFIDENCE triggers when penalized_confidence < threshold."""

    def test_low_conf_triggered_below_threshold(self) -> None:
        rec = _decision("r1", "0-30m", {"one_x_two": ["R1"]}, {"one_x_two": 0.8})
        shadow = [_shadow_row("r1", "one_x_two", "R1", 0.3)]
        profile = compute_uncertainty_profile(rec, shadow, {})
        low = next(s for s in profile.signals if s.signal_type == LOW_EFFECTIVE_CONFIDENCE)
        assert low.triggered is True

    def test_low_conf_not_triggered_above_threshold(self) -> None:
        rec = _decision("r1", "0-30m", {"one_x_two": ["R1"]})
        shadow = [_shadow_row("r1", "one_x_two", "R1", 0.7)]
        profile = compute_uncertainty_profile(rec, shadow, {})
        low = next(s for s in profile.signals if s.signal_type == LOW_EFFECTIVE_CONFIDENCE)
        assert low.triggered is False

    def test_low_conf_at_threshold_not_triggered(self) -> None:
        rec = _decision("r1", "0-30m", {"one_x_two": ["R1"]})
        shadow = [_shadow_row("r1", "one_x_two", "R1", LOW_EFFECTIVE_CONFIDENCE_THRESHOLD)]
        profile = compute_uncertainty_profile(rec, shadow, {})
        low = next(s for s in profile.signals if s.signal_type == LOW_EFFECTIVE_CONFIDENCE)
        assert low.triggered is False


class TestDeterminism:
    """Same inputs -> same signals."""

    def test_same_input_same_profile(self) -> None:
        rec = _decision("r1", "7d+", {"one_x_two": ["R1"]})
        shadow = [_shadow_row("r1", "one_x_two", "R1", 0.4)]
        a = compute_uncertainty_profile(rec, shadow, {})
        b = compute_uncertainty_profile(rec, shadow, {})
        assert len(a.signals) == len(b.signals)
        for sa, sb in zip(a.signals, b.signals):
            assert sa.signal_type == sb.signal_type
            assert sa.triggered == sb.triggered
            assert sa.reason_code == sb.reason_code


class TestMissingOptionalInputs:
    """Missing optional inputs -> signal skipped (not guessed)."""

    def test_no_shadow_low_conf_not_triggered(self) -> None:
        rec = _decision("r1", "0-30m", {"one_x_two": ["R1"]})
        profile = compute_uncertainty_profile(rec, [], {})
        low = next(s for s in profile.signals if s.signal_type == LOW_EFFECTIVE_CONFIDENCE)
        assert low.triggered is False

    def test_no_decay_params_low_support_not_triggered(self) -> None:
        rec = _decision("r1", "0-30m", {"one_x_two": ["R1"]})
        profile = compute_uncertainty_profile(rec, [], {})
        low_sup = next(s for s in profile.signals if s.signal_type == LOW_SUPPORT)
        assert low_sup.triggered is False

    def test_decay_with_support_low_support_not_triggered(self) -> None:
        rec = _decision("r1", "0-30m", {"one_x_two": ["R1"]})
        params_map = {("one_x_two", "R1"): _decay_params("one_x_two", "R1", bands_with_support=5)}
        profile = compute_uncertainty_profile(rec, [], params_map)
        low_sup = next(s for s in profile.signals if s.signal_type == LOW_SUPPORT)
        assert low_sup.triggered is False

    def test_decay_zero_support_low_support_triggered(self) -> None:
        rec = _decision("r1", "0-30m", {"one_x_two": ["R1"]})
        params_map = {("one_x_two", "R1"): _decay_params("one_x_two", "R1", bands_with_support=0)}
        profile = compute_uncertainty_profile(rec, [], params_map)
        low_sup = next(s for s in profile.signals if s.signal_type == LOW_SUPPORT)
        assert low_sup.triggered is True
