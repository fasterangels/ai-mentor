from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .models import OddsQuote


@dataclass
class OddsIntelligence:
    implied_probabilities: Dict[str, float]
    bookmaker_spread: float
    favorite: str
    favorite_strength: float


def implied_prob(price: float) -> float:
    if price <= 0:
        return 0.0
    return 1.0 / price


def compute_implied_probs(odds: List[OddsQuote]) -> Dict[str, float]:
    probs: Dict[str, List[float]] = {}
    for q in odds:
        probs.setdefault(q.outcome, []).append(implied_prob(q.price))
    return {k: sum(v) / len(v) for k, v in probs.items()}


def compute_spread(odds: List[OddsQuote]) -> float:
    prices = [q.price for q in odds]
    if not prices:
        return 0.0
    return max(prices) - min(prices)


def find_favorite(probs: Dict[str, float]) -> tuple[str, float]:
    if not probs:
        return "unknown", 0.0
    fav = max(probs.items(), key=lambda x: x[1])
    return fav[0], fav[1]


def build_odds_intelligence(odds: List[OddsQuote]) -> OddsIntelligence:
    probs = compute_implied_probs(odds)
    spread = compute_spread(odds)
    favorite, strength = find_favorite(probs)
    return OddsIntelligence(
        implied_probabilities=probs,
        bookmaker_spread=spread,
        favorite=favorite,
        favorite_strength=strength,
    )
