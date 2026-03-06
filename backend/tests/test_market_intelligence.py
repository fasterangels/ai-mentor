from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from backend.services.market_intelligence import (  # noqa: E402
    record_odds_snapshot,
    calculate_movement,
    detect_market_signal,
)


def test_record_odds_snapshot_persists_to_disk(tmp_path: Path):
    root = tmp_path / "odds_history"
    match_id = "m1"
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    record_odds_snapshot(
        match_id,
        {"home": 2.0, "draw": 3.5, "away": 4.0},
        root=root,
        timestamp=now,
    )

    path = root / f"{match_id}.json"
    assert path.exists()
    data = path.read_text(encoding="utf-8")
    assert "2.0" in data
    assert "3.5" in data
    assert "4.0" in data


def test_calculate_movement_uses_first_and_last_snapshot(tmp_path: Path):
    root = tmp_path / "odds_history"
    match_id = "m2"
    t0 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=1)

    record_odds_snapshot(
        match_id,
        {"home": 2.0, "draw": 3.5, "away": 4.0},
        root=root,
        timestamp=t0,
    )
    record_odds_snapshot(
        match_id,
        {"home": 1.8, "draw": 3.6, "away": 4.2},
        root=root,
        timestamp=t1,
    )

    mv = calculate_movement(match_id, root=root)
    assert mv["home_change"] == pytest.approx(1.8 - 2.0)
    assert mv["draw_change"] == pytest.approx(3.6 - 3.5)
    assert mv["away_change"] == pytest.approx(4.2 - 4.0)


def test_detect_market_signal_flags_strengthening_and_balanced(tmp_path: Path):
    root = tmp_path / "odds_history"
    match_id = "m3"
    t0 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=1)

    # Home odds shorten significantly; away roughly flat.
    record_odds_snapshot(
        match_id,
        {"home": 2.5, "draw": 3.5, "away": 3.0},
        root=root,
        timestamp=t0,
    )
    record_odds_snapshot(
        match_id,
        {"home": 2.0, "draw": 3.4, "away": 3.05},
        root=root,
        timestamp=t1,
    )

    sig = detect_market_signal(match_id, root=root, threshold=0.2)
    assert sig["market_signal"] in {"home_strengthening", "volatile"}

    # New match with very small changes should be balanced.
    match_id2 = "m4"
    record_odds_snapshot(
        match_id2,
        {"home": 2.0, "draw": 3.5, "away": 3.0},
        root=root,
        timestamp=t0,
    )
    record_odds_snapshot(
        match_id2,
        {"home": 2.02, "draw": 3.49, "away": 3.01},
        root=root,
        timestamp=t1,
    )
    sig2 = detect_market_signal(match_id2, root=root, threshold=0.2)
    assert sig2["market_signal"] == "balanced"

