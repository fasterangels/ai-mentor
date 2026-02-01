"""Aggregate KPIs over evaluation outcomes (day / week / month)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prediction_outcome import PredictionOutcome

from .types import KPIReport, PERIOD_DAY, PERIOD_MONTH, PERIOD_WEEK


def _day_bounds(reference_utc: datetime) -> tuple[datetime, datetime]:
    """Return (start, end) for the day of reference_utc in UTC."""
    start = reference_utc.replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
    )
    if reference_utc.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    # End = start of next day (exclusive)
    from datetime import timedelta

    end = start + timedelta(days=1)
    return start, end


def _week_bounds(reference_utc: datetime) -> tuple[datetime, datetime]:
    """Return (start, end) for the ISO week of reference_utc (Monday 00:00 UTC)."""
    from datetime import timedelta

    if reference_utc.tzinfo is None:
        ref = reference_utc.replace(tzinfo=timezone.utc)
    else:
        ref = reference_utc
    # Monday = 0 in isoweekday()
    weekday = ref.isoweekday()  # 1=Monday, 7=Sunday
    days_back = weekday - 1
    start = (ref.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_back))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    return start, end


def _month_bounds(reference_utc: datetime) -> tuple[datetime, datetime]:
    """Return (start, end) for the month of reference_utc in UTC."""
    from datetime import timedelta

    if reference_utc.tzinfo is None:
        ref = reference_utc.replace(tzinfo=timezone.utc)
    else:
        ref = reference_utc
    start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # First day of next month
    if ref.month == 12:
        end = start.replace(year=ref.year + 1, month=1)
    else:
        end = start.replace(month=ref.month + 1)
    return start, end


async def get_kpis(
    session: AsyncSession,
    period: str,
    reference_date_utc: datetime,
) -> KPIReport:
    """Compute KPIs for a time period (DAY, WEEK, or MONTH).

    Uses UTC date boundaries. Excludes N/A outcomes (only HIT/MISS count).
    hit_rate + miss_rate = 1.0 when total_predictions > 0.
    """
    if reference_date_utc.tzinfo is None:
        reference_date_utc = reference_date_utc.replace(tzinfo=timezone.utc)

    if period == PERIOD_DAY:
        start, end = _day_bounds(reference_date_utc)
    elif period == PERIOD_WEEK:
        start, end = _week_bounds(reference_date_utc)
    elif period == PERIOD_MONTH:
        start, end = _month_bounds(reference_date_utc)
    else:
        # TODO: Support custom periods or raise
        start, end = _day_bounds(reference_date_utc)

    # Query outcomes in range (each row is one evaluated prediction = HIT or MISS)
    stmt = (
        select(PredictionOutcome)
        .where(PredictionOutcome.evaluated_at_utc >= start)
        .where(PredictionOutcome.evaluated_at_utc < end)
    )
    result = await session.execute(stmt)
    outcomes: List[PredictionOutcome] = list(result.scalars().all())

    total_predictions = len(outcomes)
    hits = sum(1 for o in outcomes if o.hit_bool)
    misses = total_predictions - hits

    if total_predictions == 0:
        hit_rate = 0.0
        miss_rate = 0.0
    else:
        hit_rate = hits / total_predictions
        miss_rate = misses / total_predictions
        # Ensure hit_rate + miss_rate = 1.0
        miss_rate = 1.0 - hit_rate

    return KPIReport(
        period=period,
        reference_date_utc=reference_date_utc,
        total_predictions=total_predictions,
        hits=hits,
        misses=misses,
        hit_rate=hit_rate,
        miss_rate=miss_rate,
    )
