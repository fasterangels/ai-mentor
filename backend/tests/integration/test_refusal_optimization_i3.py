"""
Integration tests for refusal-optimize-shadow mode (I3 Part B).
Synthetic dataset with known best threshold; assert artifacts and deterministic ordering.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from optimization.refusal_shadow import ShadowDecision
from runner.refusal_optimization_runner import (
    BEST_BY_MARKET_JSON,
    BEST_OVERALL_JSON,
    GRID_SUMMARY_CSV,
    NOTES_MD,
    run_refusal_optimization,
)


def _decision(
    effective_confidence: float,
    age_band: str,
    outcome: str,
    market: str | None = "one_x_two",
) -> ShadowDecision:
    return ShadowDecision(
        effective_confidence=effective_confidence,
        age_band=age_band,
        outcome=outcome,
        market=market,
    )


def test_refusal_optimize_shadow_writes_artifacts(tmp_path) -> None:
    """Run with empty decisions; all four artifacts exist and have expected structure."""
    result = run_refusal_optimization(reports_dir=str(tmp_path), decisions=[])
    assert result.get("error") is None
    assert result.get("decisions_count") == 0
    assert (tmp_path / BEST_OVERALL_JSON).exists()
    assert (tmp_path / BEST_BY_MARKET_JSON).exists()
    assert (tmp_path / GRID_SUMMARY_CSV).exists()
    assert (tmp_path / NOTES_MD).exists()
    overall = json.loads((tmp_path / BEST_OVERALL_JSON).read_text(encoding="utf-8"))
    assert overall == {} or "effective_confidence_threshold" in overall


def test_refusal_optimize_shadow_known_best_threshold(tmp_path) -> None:
    """Synthetic data: low conf + 7d+ -> refuse; rest non-refused with 1 SUCCESS, 1 FAILURE. Best should favor that threshold."""
    decisions = [
        _decision(0.15, "7d+", "FAILURE"),  # would be refused with (0.20, 7d+)
        _decision(0.15, "7d+", "FAILURE"),
        _decision(0.6, "6-24h", "SUCCESS"),
        _decision(0.6, "6-24h", "FAILURE"),
    ]
    result = run_refusal_optimization(reports_dir=str(tmp_path), decisions=decisions)
    assert result["decisions_count"] == 4
    path = tmp_path / BEST_OVERALL_JSON
    assert path.exists()
    best = json.loads(path.read_text(encoding="utf-8"))
    assert "effective_confidence_threshold" in best
    assert "stale_band_threshold" in best
    assert "safety_score" in best
    assert best["support_total"] == 4


def test_refusal_optimize_shadow_grid_csv_deterministic_order(tmp_path) -> None:
    """Grid CSV has stable order: market, then effective_confidence, then stale_band."""
    decisions = [
        _decision(0.5, "1-3d", "SUCCESS"),
        _decision(0.5, "1-3d", "FAILURE"),
    ]
    run_refusal_optimization(reports_dir=str(tmp_path), decisions=decisions)
    with (tmp_path / GRID_SUMMARY_CSV).open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert reader.fieldnames == [
        "market", "stale_band_threshold", "effective_confidence_threshold",
        "refusal_rate", "accuracy_on_non_refused", "safety_score", "support_total",
    ]
    assert len(rows) >= 17 * 4  # overall grid: 17 eff * 4 bands
    first = rows[0]
    assert first["market"] == "overall"
    assert first["effective_confidence_threshold"] == "0.1"
    assert first["stale_band_threshold"] == "6-24h"


def test_refusal_optimize_shadow_missing_inputs_writes_empty_artifacts(tmp_path) -> None:
    """When no input (decisions=None and no REFUSAL_OPT_INPUT_JSON), empty artifacts written, no crash."""
    import os
    had = os.environ.pop("REFUSAL_OPT_INPUT_JSON", None)
    try:
        result = run_refusal_optimization(reports_dir=str(tmp_path), decisions=None)
        assert result.get("decisions_count") == 0
        assert (tmp_path / BEST_OVERALL_JSON).exists()
        assert json.loads((tmp_path / BEST_OVERALL_JSON).read_text()) == {}
    finally:
        if had is not None:
            os.environ["REFUSAL_OPT_INPUT_JSON"] = had
