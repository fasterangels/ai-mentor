"""
Unit tests for refusal tradeoff metrics (coverage/precision/F1 curves).
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.evaluation.refusal_tradeoff import (  # type: ignore[import-error]
    TradeoffConfig,
    compute_tradeoff,
    extract_rows_for_tradeoff,
)


def test_compute_tradeoff_basic_properties() -> None:
    # Synthetic rows for two markets.
    rows = [
        {"market": "A", "score": 0.2, "outcome": 0},
        {"market": "A", "score": 0.5, "outcome": 1},
        {"market": "A", "score": 0.9, "outcome": 1},
        {"market": "B", "score": 0.3, "outcome": 0},
        {"market": "B", "score": 0.7, "outcome": 1},
        {"market": "B", "score": 0.8, "outcome": 1},
    ]

    cfg = TradeoffConfig(thresholds=[0.3, 0.5, 0.7])
    tradeoff = compute_tradeoff(rows, cfg)

    global_points = tradeoff["global"]["points"]
    assert len(global_points) == len(cfg.thresholds)

    # coverage should be non-increasing as threshold increases
    coverages = [p["coverage"] for p in global_points]
    for c1, c2 in zip(coverages, coverages[1:]):
        assert c1 >= c2

    # Each point should have required keys
    for p in global_points:
        for key in ("t", "coverage", "precision", "recall", "f1", "go", "n"):
            assert key in p

    # per_market keys should be sorted deterministically
    per_market = tradeoff["per_market"]
    assert list(per_market.keys()) == sorted(per_market.keys())


def test_extract_rows_for_tradeoff_join_by_id() -> None:
    # Fake report where decision_engine_outputs need to be joined with predictions.
    report = {
        "predictions": [
            {"id": "p1", "outcome": 1, "market": "A"},
            {"id": "p2", "outcome": 0, "market": "B"},
        ],
        "decision_engine_outputs": [
            {"id": "p1", "market": "A", "score": 0.8},
            {"id": "p2", "market": "B", "score": 0.4},
        ],
    }

    rows = extract_rows_for_tradeoff(report)
    assert len(rows) == 2
    markets = {r["market"] for r in rows}
    assert markets == {"A", "B"}
    for r in rows:
        assert "score" in r and "outcome" in r
        assert r["outcome"] in (0, 1)

