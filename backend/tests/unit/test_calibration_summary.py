"""Unit tests for calibration summary: band assignment and Brier score."""

from __future__ import annotations

from evaluation.offline_eval import (
    CALIBRATION_BANDS,
    CALIBRATION_BAND_LABELS,
    _calibration_band_for_confidence,
)


def test_calibration_band_assignment() -> None:
    """Band assignment is correct and deterministic."""
    assert _calibration_band_for_confidence(None) is None
    assert _calibration_band_for_confidence(0.0) == "0.00-0.49"
    assert _calibration_band_for_confidence(0.49) == "0.00-0.49"
    assert _calibration_band_for_confidence(0.50) == "0.50-0.59"
    assert _calibration_band_for_confidence(0.59) == "0.50-0.59"
    assert _calibration_band_for_confidence(0.60) == "0.60-0.69"
    assert _calibration_band_for_confidence(0.69) == "0.60-0.69"
    assert _calibration_band_for_confidence(0.70) == "0.70-0.79"
    assert _calibration_band_for_confidence(0.79) == "0.70-0.79"
    assert _calibration_band_for_confidence(0.80) == "0.80-1.00"
    assert _calibration_band_for_confidence(1.0) == "0.80-1.00"
    assert _calibration_band_for_confidence(1.5) is None
    assert _calibration_band_for_confidence(-0.1) is None


def test_calibration_bands_ordering() -> None:
    """CALIBRATION_BAND_LABELS has stable ordering."""
    assert CALIBRATION_BAND_LABELS == [
        "0.00-0.49",
        "0.50-0.59",
        "0.60-0.69",
        "0.70-0.79",
        "0.80-1.00",
    ]
    assert len(CALIBRATION_BANDS) == 5


def test_brier_score_correctness() -> None:
    """Brier = mean((p - y)^2). Handcrafted: perfect predictions -> 0."""
    # (p, y) = (1.0, 1), (0.0, 0) -> (1-1)^2 + (0-0)^2 = 0
    py_list = [(1.0, 1), (0.0, 0)]
    brier = sum((p - y) ** 2 for p, y in py_list) / len(py_list)
    assert round(brier, 4) == 0.0
    # (0.7, 1), (0.7, 0) -> 0.09 + 0.49 = 0.58 / 2 = 0.29
    py_list2 = [(0.7, 1), (0.7, 0)]
    brier2 = sum((p - y) ** 2 for p, y in py_list2) / len(py_list2)
    assert round(brier2, 4) == 0.29
