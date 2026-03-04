"""
Unit tests for the confidence calibration artifact.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.calibration.confidence_calibration import (  # type: ignore[import-error]
    ConfidenceCalibrator,
    apply,
    fit_binning_calibrator,
    load_calibrator,
    save_calibrator,
)


def test_fit_and_apply_simple() -> None:
    """Basic sanity: higher raw confidence should map to higher calibrated value."""
    confidences = [0.1, 0.2, 0.8, 0.9]
    outcomes = [0, 0, 1, 1]

    calibrator = fit_binning_calibrator(confidences, outcomes, n_bins=2, version="v_test")

    low = apply(calibrator, 0.1)
    high = apply(calibrator, 0.9)

    assert low < high


def test_empty_bin_uses_default() -> None:
    """Bins without observations should use the default value (overall mean)."""
    confidences = [0.1]  # Only hits the first bin when n_bins=2
    outcomes = [1]

    calibrator = fit_binning_calibrator(confidences, outcomes, n_bins=2, version="v_test")

    # Second bin has no samples and should use overall mean (which is 1.0 here).
    assert calibrator.bin_values[1] == calibrator.default_value == 1.0


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """Saving and loading a calibrator should preserve its parameters."""
    confidences = [0.1, 0.9]
    outcomes = [0, 1]
    original = fit_binning_calibrator(confidences, outcomes, n_bins=4, version="v_roundtrip")

    path = tmp_path / "calibrator.json"
    save_calibrator(original, str(path))

    reloaded = load_calibrator(str(path))

    assert isinstance(reloaded, ConfidenceCalibrator)
    assert reloaded.version == original.version
    assert reloaded.n_bins == original.n_bins
    assert reloaded.bin_edges == original.bin_edges
    assert reloaded.bin_values == original.bin_values
    assert reloaded.default_value == original.default_value

