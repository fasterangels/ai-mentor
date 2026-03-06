"""
Unit tests for time-aware reason reliability window selection.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.evaluation.reason_metrics import (  # type: ignore[import-error]
    select_reliability,
)


def test_prefer_90d_over_all_time() -> None:
    rr = {
        "global": {
            "all_time": {"R1": 0.8},
            "90d": {"R1": 0.9},
        },
        "per_market": {
            "A": {
                "all_time": {"R1": 0.7},
                "90d": {"R1": 0.95},
            }
        },
    }

    # For market A and window 90d, per-market 90d should be used.
    rel = select_reliability("R1", "A", rr, window="90d")
    assert rel == 0.95


def test_fallback_to_global_if_market_missing() -> None:
    rr = {
        "global": {
            "all_time": {"R1": 0.75},
            "90d": {"R1": 0.85},
        },
        "per_market": {
            "A": {
                "all_time": {"R1": 0.7},
            }
        },
    }

    # For market B, there is no per-market data; should use global 90d.
    rel = select_reliability("R1", "B", rr, window="90d")
    assert rel == 0.85


def test_fallback_to_default_when_missing_everywhere() -> None:
    rr = {
        "global": {},
        "per_market": {},
    }
    rel = select_reliability("R_UNKNOWN", "X", rr, window="90d")
    assert rel == 0.5

