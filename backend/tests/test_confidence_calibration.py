"""
Tests for confidence calibration: bins, calibration modifies probability, normalization.
Uses in-memory records or tmp_path + monkeypatch. Deterministic; no network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.football import confidence_calibration


def test_bins_created_correctly():
    """build_calibration_bins produces fixed number of bins with correct lower/upper and counts."""
    records = []
    for i in range(30):
        # Spread predicted home prob across [0.05, 0.95] so we hit several bins
        p = 0.05 + (i / 29) * 0.9
        draw = (1 - p) / 2
        away = (1 - p) / 2
        records.append({
            "match_id": f"M{i}",
            "predicted_home": p,
            "predicted_draw": draw,
            "predicted_away": away,
            "result": "home" if i % 2 == 0 else "away",
        })
    bins = confidence_calibration.build_calibration_bins(records, bins=10)
    assert len(bins) == 10
    size = 1.0 / 10
    for i, b in enumerate(bins):
        assert b.lower == i * size
        assert b.upper == b.lower + size
    total_count = sum(b.count for b in bins)
    assert total_count == 30
    # All bins exist and have consistent bounds
    assert bins[0].lower == 0.0 and bins[0].upper == 0.1
    assert bins[9].lower == 0.9 and bins[9].upper == 1.0


def test_calibration_modifies_probability():
    """apply_calibration changes probabilities when bin accuracies differ from raw probs."""
    # One bin [0.5, 0.6) with accuracy 0.8 (so calibration should map 0.55 -> 0.8 for that outcome)
    records = [
        {"match_id": "M1", "predicted_home": 0.55, "predicted_draw": 0.25, "predicted_away": 0.2, "result": "home"},
        {"match_id": "M2", "predicted_home": 0.55, "predicted_draw": 0.25, "predicted_away": 0.2, "result": "home"},
        {"match_id": "M3", "predicted_home": 0.55, "predicted_draw": 0.25, "predicted_away": 0.2, "result": "away"},
    ]
    bins = confidence_calibration.build_calibration_bins(records, bins=10)
    prediction = {"home_prob": 0.55, "draw_prob": 0.25, "away_prob": 0.2}
    calibrated = confidence_calibration.apply_calibration(prediction, bins)
    # Raw home_prob 0.55 falls in bin [0.5, 0.6); that bin has accuracy 2/3
    # So home should become 2/3 (after norm). Calibration should differ from original.
    assert calibrated["home_prob"] != prediction["home_prob"]
    assert calibrated["draw_prob"] != prediction["draw_prob"]
    assert calibrated["away_prob"] != prediction["away_prob"]


def test_probabilities_normalized():
    """apply_calibration returns home_prob + draw_prob + away_prob == 1.0."""
    records = [
        {"match_id": f"M{i}", "predicted_home": 0.4, "predicted_draw": 0.35, "predicted_away": 0.25, "result": "home"}
        for i in range(25)
    ]
    bins = confidence_calibration.build_calibration_bins(records, bins=10)
    prediction = {"home_prob": 0.4, "draw_prob": 0.35, "away_prob": 0.25}
    calibrated = confidence_calibration.apply_calibration(prediction, bins)
    total = calibrated["home_prob"] + calibrated["draw_prob"] + calibrated["away_prob"]
    assert abs(total - 1.0) < 1e-9
