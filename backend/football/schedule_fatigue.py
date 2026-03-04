from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

from .models import LastMatch


@dataclass
class ScheduleFatigue:
    days_since_last_match: int
    matches_last_14_days: int
    fatigue_score: float
    rotation_risk: float


def _parse_date(date_iso: str) -> datetime:
    if date_iso.endswith("Z"):
        date_iso = date_iso.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(date_iso)
    except Exception:
        return datetime.now(timezone.utc)


def _utc_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware UTC for comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def compute_days_since_last(
    matches: List[LastMatch],
    now: datetime | None = None,
) -> int:
    if not matches:
        return 7
    now = _utc_aware(now or datetime.now(timezone.utc))
    dates = [_parse_date(m.date_iso) for m in matches]
    last = max(dates)
    return max((now - last).days, 0)


def compute_matches_last_14_days(
    matches: List[LastMatch],
    now: datetime | None = None,
) -> int:
    now = _utc_aware(now or datetime.now(timezone.utc))
    cutoff = now - timedelta(days=14)
    count = 0
    for m in matches:
        d = _parse_date(m.date_iso)
        if d >= cutoff:
            count += 1
    return count


def compute_fatigue(days_since_last: int, matches_14: int) -> float:
    base = matches_14 * 0.15
    rest_penalty = 0.2 if days_since_last <= 2 else 0.1 if days_since_last <= 3 else 0.0
    fatigue = base + rest_penalty
    return min(fatigue, 1.0)


def compute_rotation_risk(fatigue_score: float) -> float:
    return min(0.2 + fatigue_score * 0.6, 1.0)


def build_schedule_fatigue(
    team_id: str,
    last_matches: List[LastMatch],
    now: datetime | None = None,
) -> ScheduleFatigue:
    days_since = compute_days_since_last(last_matches, now=now)
    matches_14 = compute_matches_last_14_days(last_matches, now=now)
    fatigue = compute_fatigue(days_since, matches_14)
    rotation = compute_rotation_risk(fatigue)
    return ScheduleFatigue(
        days_since_last_match=days_since,
        matches_last_14_days=matches_14,
        fatigue_score=fatigue,
        rotation_risk=rotation,
    )
