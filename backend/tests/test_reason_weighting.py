"""
Unit tests for reason weighting v1 in the decision engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.decision_engine.decision_engine import (  # type: ignore[import-error]
    weighted_reason_strength,
)


def test_high_reliability_reasons_dominate() -> None:
    reliabilities = [("R1", 0.9), ("R2", 0.4)]
    simple_mean = (0.9 + 0.4) / 2.0
    weighted = weighted_reason_strength(reliabilities)

    assert weighted > simple_mean


def test_low_reliability_reasons_downweighted() -> None:
    reliabilities = [("R1", 0.2), ("R2", 0.25)]
    simple_mean = (0.2 + 0.25) / 2.0
    weighted = weighted_reason_strength(reliabilities)

    # With all values below the 0.3 cutoff, weighting should effectively
    # fall back to the simple mean.
    assert abs(weighted - simple_mean) < 1e-9


def test_all_low_weights_fallback_to_mean() -> None:
    reliabilities = [("R1", 0.1), ("R2", 0.2), ("R3", 0.25)]
    simple_mean = sum(r for _, r in reliabilities) / len(reliabilities)
    weighted = weighted_reason_strength(reliabilities)

    # All reliabilities are below 0.3, so weights are zero and we use the mean.
    assert abs(weighted - simple_mean) < 1e-9

