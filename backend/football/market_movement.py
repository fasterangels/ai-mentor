"""
Market movement intelligence: odds snapshots, line movement, volatility.
Uses local JSONL files under runtime/odds_history/ (dir created as needed).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

# Overridable by tests for tmp_path
_HISTORY_DIR: Path = Path(__file__).resolve().parent.parent / "runtime" / "odds_history"

# Only consider this market for movement
_MARKET_1X2 = "1x2"
_OUTCOMES = ("home", "draw", "away")
_VOLATILITY_EPS = 1e-6
_DIRECTION_THRESHOLD = 0.01  # min gap to call a clear shortening


@dataclass
class OddsSnapshot:
    match_id: str
    captured_at_iso: str
    odds: List[dict]  # [{bookmaker, market, outcome, price}, ...]


@dataclass
class MarketMovement:
    has_history: bool
    points: int
    movement: dict  # per outcome: {"delta_price", "delta_implied"}
    volatility: float
    direction: str  # home_shortening|away_shortening|draw_shortening|mixed|none


def implied_prob(price: float) -> float:
    if price is None or price <= 0:
        return 0.0
    p = 1.0 / price
    return max(0.0, min(1.0, p))


def snapshot_path(match_id: str) -> Path:
    return _HISTORY_DIR / f"{match_id}.jsonl"


def _ensure_dir() -> None:
    try:
        _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def load_last_snapshot(match_id: str) -> dict | None:
    path = snapshot_path(match_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return None
        last_line = lines[-1].strip()
        if not last_line:
            return None
        return json.loads(last_line)
    except (OSError, json.JSONDecodeError):
        return None


def append_snapshot(match_id: str, snapshot_dict: dict) -> None:
    _ensure_dir()
    path = snapshot_path(match_id)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot_dict) + "\n")
    except OSError:
        pass


def _avg_prices_by_outcome(odds: List[dict]) -> dict[str, float]:
    """Average price per outcome for market 1x2."""
    by_outcome: dict[str, List[float]] = {o: [] for o in _OUTCOMES}
    for row in odds:
        if row.get("market") != _MARKET_1X2:
            continue
        out = row.get("outcome")
        price = row.get("price")
        if out in by_outcome and price is not None and isinstance(price, (int, float)):
            by_outcome[out].append(float(price))
    return {
        out: sum(p) / len(p) if p else 0.0
        for out, p in by_outcome.items()
    }


def compute_movement(
    prev_odds: List[dict],
    curr_odds: List[dict],
) -> MarketMovement:
    prev_avg = _avg_prices_by_outcome(prev_odds)
    curr_avg = _avg_prices_by_outcome(curr_odds)

    movement: dict = {}
    deltas: List[float] = []
    for out in _OUTCOMES:
        p_prev = prev_avg.get(out) or 0.0
        p_curr = curr_avg.get(out) or 0.0
        if p_prev <= 0:
            p_prev = 1.0
        if p_curr <= 0:
            p_curr = 1.0
        delta_price = p_curr - p_prev
        delta_implied = implied_prob(p_curr) - implied_prob(p_prev)
        movement[out] = {"delta_price": delta_price, "delta_implied": delta_implied}
        deltas.append(abs(delta_price))

    volatility = sum(deltas) / len(deltas) if deltas else 0.0

    if volatility < _VOLATILITY_EPS:
        direction = "none"
    else:
        by_delta = [(out, movement[out]["delta_price"]) for out in _OUTCOMES]
        by_delta.sort(key=lambda x: x[1])
        most_negative_outcome, most_neg = by_delta[0]
        second_delta = by_delta[1][1] if len(by_delta) > 1 else 0.0
        if second_delta - most_neg >= _DIRECTION_THRESHOLD:
            direction = f"{most_negative_outcome}_shortening"
        else:
            direction = "mixed"

    return MarketMovement(
        has_history=True,
        points=2,
        movement=movement,
        volatility=volatility,
        direction=direction,
    )


def _quotes_to_dicts(odds_quotes: List[Any]) -> List[dict]:
    from .models import OddsQuote

    result: List[dict] = []
    for q in odds_quotes:
        if isinstance(q, OddsQuote):
            result.append(
                {"bookmaker": q.bookmaker, "market": q.market, "outcome": q.outcome, "price": q.price}
            )
        elif isinstance(q, dict) and "outcome" in q and "price" in q:
            result.append(
                {
                    "bookmaker": q.get("bookmaker", ""),
                    "market": q.get("market", "1x2"),
                    "outcome": q["outcome"],
                    "price": q["price"],
                }
            )
    return result


def update_and_analyze(
    match_id: str,
    odds_quotes: List[Any],
) -> MarketMovement:
    """Convert quotes to dicts, compare to last snapshot, append current, return movement."""
    curr_odds = _quotes_to_dicts(odds_quotes)

    prev = load_last_snapshot(match_id)
    if prev is None or not prev.get("odds"):
        movement = MarketMovement(
            has_history=False,
            points=0,
            movement={o: {"delta_price": 0.0, "delta_implied": 0.0} for o in _OUTCOMES},
            volatility=0.0,
            direction="none",
        )
    else:
        movement = compute_movement(prev["odds"], curr_odds)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    snapshot_dict = {
        "match_id": match_id,
        "captured_at_iso": now_iso,
        "odds": curr_odds,
    }
    append_snapshot(match_id, snapshot_dict)

    return movement
