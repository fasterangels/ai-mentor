"""
Age band thresholds for staleness metrics (G4). Fixed, deterministic.
All values in milliseconds. No decay; measurement only.
"""

from __future__ import annotations

# Band exclusive upper bounds in ms. Band i = (thresholds[i-1], thresholds[i]).
# 0–30m, 30m–2h, 2–6h, 6–24h, 1–3d, 3–7d, 7d+
MINUTES_MS = 60 * 1000
HOURS_MS = 60 * MINUTES_MS
DAYS_MS = 24 * HOURS_MS

AGE_BAND_THRESHOLDS_MS = [
    30 * MINUTES_MS,   # 0–30m
    120 * MINUTES_MS,  # 30m–2h
    6 * HOURS_MS,      # 2–6h
    24 * HOURS_MS,     # 6–24h
    3 * DAYS_MS,       # 1–3d
    7 * DAYS_MS,       # 3–7d
    None,              # 7d+ (no upper bound)
]

# Human-readable labels; same order as thresholds (pairs: (low, high) per band)
AGE_BAND_LABELS = [
    "0-30m",
    "30m-2h",
    "2h-6h",
    "6h-24h",
    "1d-3d",
    "3d-7d",
    "7d+",
]


def assign_age_band(evidence_age_ms: float | None) -> str:
    """
    Map evidence_age_ms to a deterministic age band label.
    If evidence_age_ms is None or negative, return "0-30m" (treat as freshest).
    """
    if evidence_age_ms is None or evidence_age_ms < 0:
        return "0-30m"
    for i, threshold in enumerate(AGE_BAND_THRESHOLDS_MS):
        if threshold is None:
            # Last band (7d+)
            return AGE_BAND_LABELS[i]
        if evidence_age_ms < threshold:
            return AGE_BAND_LABELS[i]
    return AGE_BAND_LABELS[-1]
