"""
Tests for market movement: first call no history, second call home shortening, volatility, deterministic.
Uses tmp_path and monkeypatch for history dir. No network.
"""
from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.football.models import OddsQuote
from backend.football import market_movement


def _q(bookmaker: str, outcome: str, price: float, market: str = "1x2") -> OddsQuote:
    return OddsQuote(bookmaker=bookmaker, market=market, outcome=outcome, price=price)


def test_first_call_has_no_history_and_direction_none(monkeypatch, tmp_path):
    """First call: has_history=False, direction='none'."""
    history_dir = tmp_path / "odds_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(market_movement, "_HISTORY_DIR", history_dir)

    odds = [
        _q("B1", "home", 1.90),
        _q("B1", "draw", 3.50),
        _q("B1", "away", 4.00),
    ]
    movement = market_movement.update_and_analyze("M1", odds)

    assert movement.has_history is False
    assert movement.direction == "none"
    assert movement.points == 0


def test_second_call_lower_home_price_home_shortening(monkeypatch, tmp_path):
    """Second call with lower home price (1.90 -> 1.75): direction=home_shortening, home delta_price negative."""
    history_dir = tmp_path / "odds_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(market_movement, "_HISTORY_DIR", history_dir)

    odds_first = [
        _q("B1", "home", 1.90),
        _q("B1", "draw", 3.50),
        _q("B1", "away", 4.00),
    ]
    market_movement.update_and_analyze("M2", odds_first)

    odds_second = [
        _q("B1", "home", 1.75),
        _q("B1", "draw", 3.50),
        _q("B1", "away", 4.00),
    ]
    movement = market_movement.update_and_analyze("M2", odds_second)

    assert movement.has_history is True
    assert movement.direction == "home_shortening"
    assert movement.movement["home"]["delta_price"] < 0
    assert movement.movement["home"]["delta_implied"] > 0


def test_volatility_computed_positive(monkeypatch, tmp_path):
    """After two different snapshots, volatility > 0."""
    history_dir = tmp_path / "odds_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(market_movement, "_HISTORY_DIR", history_dir)

    market_movement.update_and_analyze("M3", [_q("B1", "home", 2.0), _q("B1", "draw", 3.5), _q("B1", "away", 4.0)])
    movement = market_movement.update_and_analyze("M3", [_q("B1", "home", 1.8), _q("B1", "draw", 3.6), _q("B1", "away", 4.2)])

    assert movement.volatility >= 0
    assert movement.has_history is True
    assert movement.volatility > 0


def test_compute_movement_deterministic():
    """Given same prev/curr odds lists, compute_movement returns identical result."""
    prev = [
        {"bookmaker": "B1", "market": "1x2", "outcome": "home", "price": 2.0},
        {"bookmaker": "B1", "market": "1x2", "outcome": "draw", "price": 3.5},
        {"bookmaker": "B1", "market": "1x2", "outcome": "away", "price": 4.0},
    ]
    curr = [
        {"bookmaker": "B1", "market": "1x2", "outcome": "home", "price": 1.9},
        {"bookmaker": "B1", "market": "1x2", "outcome": "draw", "price": 3.5},
        {"bookmaker": "B1", "market": "1x2", "outcome": "away", "price": 4.0},
    ]
    a = market_movement.compute_movement(prev, curr)
    b = market_movement.compute_movement(prev, curr)
    assert a.has_history == b.has_history
    assert a.points == b.points
    assert a.volatility == b.volatility
    assert a.direction == b.direction
    assert a.movement == b.movement
