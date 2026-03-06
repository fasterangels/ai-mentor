from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_HISTORY_ROOT = _BACKEND_ROOT / "runtime" / "odds_history"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_dir(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)


def _snapshot_path(root: Path, match_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-._" else "_" for c in (match_id or "unknown"))
    return root / f"{safe}.json"


def record_odds_snapshot(
    match_id: str,
    odds: Dict[str, float],
    *,
    root: Optional[Path] = None,
    timestamp: Optional[datetime] = None,
) -> None:
    """Append an odds snapshot for a match to disk.

    Args:
        match_id: Unique match identifier.
        odds: Simple 1X2 odds dict: {'home': float, 'draw': float, 'away': float}.
        root: Optional override for history root (used in tests).
        timestamp: Optional override for snapshot time (used in tests).
    """
    if not match_id or not isinstance(odds, dict):
        return

    root = root or _DEFAULT_HISTORY_ROOT
    _ensure_dir(root)
    path = _snapshot_path(root, match_id)

    snap = {
        "timestamp": (timestamp or _now_utc()).isoformat(),
        "odds": {
            "home": float(odds.get("home")) if odds.get("home") is not None else None,
            "draw": float(odds.get("draw")) if odds.get("draw") is not None else None,
            "away": float(odds.get("away")) if odds.get("away") is not None else None,
        },
    }

    history: List[Dict[str, Any]] = []
    if path.exists():
        try:
            history = json.loads(path.read_text(encoding="utf-8")) or []
            if not isinstance(history, list):
                history = []
        except json.JSONDecodeError:
            history = []

    history.append(snap)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_history(match_id: str, root: Optional[Path] = None) -> List[Dict[str, Any]]:
    if not match_id:
        return []
    root = root or _DEFAULT_HISTORY_ROOT
    path = _snapshot_path(root, match_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def calculate_movement(match_id: str, *, root: Optional[Path] = None) -> Dict[str, float]:
    """Compute change in odds between first and last snapshots for a match."""
    history = _load_history(match_id, root=root)
    if len(history) < 2:
        return {"home_change": 0.0, "draw_change": 0.0, "away_change": 0.0}

    first = history[0].get("odds") or {}
    last = history[-1].get("odds") or {}

    def _delta(key: str) -> float:
        try:
            a = float(first.get(key))
            b = float(last.get(key))
            return b - a
        except (TypeError, ValueError):
            return 0.0

    return {
        "home_change": _delta("home"),
        "draw_change": _delta("draw"),
        "away_change": _delta("away"),
    }


def detect_market_signal(
    match_id: str,
    *,
    root: Optional[Path] = None,
    threshold: float = 0.2,
) -> Dict[str, Any]:
    """Detect simple market signal based on odds movement.

    Signals:
        - 'home_strengthening'  (home odds shortened beyond threshold)
        - 'away_strengthening'  (away odds shortened beyond threshold)
        - 'balanced'            (all movements within threshold)
        - 'volatile'            (large conflicting moves)
    """
    mv = calculate_movement(match_id, root=root)
    home_change = mv["home_change"]
    draw_change = mv["draw_change"]
    away_change = mv["away_change"]

    # Lower odds -> implied strength increase.
    home_drop = -home_change
    away_drop = -away_change

    max_abs = max(abs(home_change), abs(draw_change), abs(away_change))
    if max_abs <= threshold:
        signal = "balanced"
    elif home_drop > threshold and home_drop >= abs(away_change) and home_drop >= abs(draw_change):
        signal = "home_strengthening"
    elif away_drop > threshold and away_drop >= abs(home_change) and away_drop >= abs(draw_change):
        signal = "away_strengthening"
    else:
        signal = "volatile"

    return {
        "market_signal": signal,
        "movement": mv,
    }

