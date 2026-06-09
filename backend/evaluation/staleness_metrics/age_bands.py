"""
Age band constants for staleness metrics (G4). Fixed, deterministic.
All values in milliseconds. Measurement only; no decay.
"""

from __future__ import annotations

# Exclusive upper bounds in ms. Band i = (prev_bound, BAND_UPPER_BOUNDS_MS[i]).
# 0–30m, 30–120m, 2–6h, 6–24h, 1–3d, 3–7d, 7d+
MINUTES_MS = 60 * 1000
HOURS_MS = 60 * MINUTES_MS
DAYS_MS = 24 * HOURS_MS

BAND_UPPER_BOUNDS_MS = (
    30 * MINUTES_MS,   # 0–30m
    120 * MINUTES_MS,  # 30–120m (2h)
    6 * HOURS_MS,      # 2–6h
    24 * HOURS_MS,     # 6–24h
    3 * DAYS_MS,       # 1–3d
    7 * DAYS_MS,       # 3–7d
    None,              # 7d+ (no upper bound)
)

BAND_LABELS = (
    "0-30m",
    "30-120m",
    "2-6h",
    "6-24h",
    "1-3d",
    "3-7d",
    "7d+",
)


def band_for_age_ms(age_ms: int) -> str:
    """
    Map evidence age in milliseconds to a deterministic band label.
    Negative or zero age is treated as freshest band (0-30m).
    """
    if age_ms < 0:
        age_ms = 0
    for i, bound in enumerate(BAND_UPPER_BOUNDS_MS):
        if bound is None:
            return BAND_LABELS[i]
        if age_ms < bound:
            return BAND_LABELS[i]
    return BAND_LABELS[-1]
