"""
Tests for odds intelligence: implied prob, favorite, spread, deterministic.
Deterministic; no network.
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
from backend.football.odds_intelligence import (
    OddsIntelligence,
    build_odds_intelligence,
    compute_implied_probs,
    compute_spread,
    find_favorite,
    implied_prob,
)


def _q(bookmaker: str, outcome: str, price: float, market: str = "1x2") -> OddsQuote:
    return OddsQuote(bookmaker=bookmaker, market=market, outcome=outcome, price=price)


def test_implied_probability_calculation() -> None:
    """implied_prob(price) = 1/price; compute_implied_probs averages per outcome."""
    assert implied_prob(2.0) == 0.5
    assert implied_prob(4.0) == 0.25
    assert implied_prob(0.0) == 0.0
    assert implied_prob(-1.0) == 0.0

    odds = [
        _q("B1", "home", 2.0),
        _q("B2", "home", 2.0),
        _q("B1", "draw", 4.0),
        _q("B1", "away", 4.0),
    ]
    probs = compute_implied_probs(odds)
    assert probs["home"] == 0.5
    assert probs["draw"] == 0.25
    assert probs["away"] == 0.25


def test_favorite_detection() -> None:
    """find_favorite returns outcome with highest implied prob; empty -> unknown, 0."""
    probs = {"home": 0.5, "draw": 0.25, "away": 0.25}
    fav, strength = find_favorite(probs)
    assert fav == "home"
    assert strength == 0.5

    fav_empty, str_empty = find_favorite({})
    assert fav_empty == "unknown"
    assert str_empty == 0.0


def test_spread_positive() -> None:
    """Spread is max(price) - min(price); positive when prices differ; empty odds -> 0."""
    odds = [_q("B1", "home", 2.0), _q("B1", "away", 5.0)]
    assert compute_spread(odds) == 3.0
    assert compute_spread([]) == 0.0
    odds_same = [_q("B1", "home", 2.0), _q("B1", "away", 2.0)]
    assert compute_spread(odds_same) == 0.0


def test_deterministic_result() -> None:
    """build_odds_intelligence returns same result for same input order."""
    odds = [
        _q("B1", "home", 2.0),
        _q("B1", "draw", 3.5),
        _q("B1", "away", 4.0),
    ]
    a = build_odds_intelligence(odds)
    b = build_odds_intelligence(odds)
    assert a.implied_probabilities == b.implied_probabilities
    assert a.bookmaker_spread == b.bookmaker_spread
    assert a.favorite == b.favorite
    assert a.favorite_strength == b.favorite_strength
    assert a.favorite == "home"
    assert a.favorite_strength == 0.5
