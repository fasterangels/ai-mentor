"""
Deterministic piecewise decay fit from G4 staleness metrics.
No optimization libraries, no randomness. Same inputs -> same params.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

from evaluation.age_bands import AGE_BAND_LABELS
from modeling.reason_decay.model import (
    BAND_ORDER,
    DecayModelParams,
    FitDiagnostics,
    MODEL_TYPE_PIECEWISE_V1,
    SCHEMA_VERSION,
)

# Bands with total < MIN_SUPPORT are not used for fitting; penalty is carried forward.
MIN_SUPPORT = 5


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp value to [low, high]. Deterministic."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _band_index(age_band: str) -> int:
    """Index of age_band in BAND_ORDER (youngest=0). If unknown, return 0."""
    try:
        return BAND_ORDER.index(age_band)
    except ValueError:
        return 0


def _rows_by_market_reason(
    rows: Sequence[Dict[str, Any]],
) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    """
    Group rows by (market, reason_code). Each group sorted by age band (youngest first).
    Deterministic.
    """
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in rows:
        market = r.get("market", "")
        reason_code = r.get("reason_code", "")
        key = (market, reason_code)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(dict(r))
    for key in grouped:
        grouped[key].sort(key=lambda x: _band_index(x.get("age_band", "0-30m")))
    return grouped


def fit_piecewise_decay(
    rows: Sequence[Dict[str, Any]],
    fitted_at_utc: str | None = None,
) -> List[DecayModelParams]:
    """
    Deterministic fit: one DecayModelParams per (market, reason_code).
    - baseline_accuracy = accuracy at youngest band (with support)
    - observed_drop = max(0, baseline_accuracy - band_accuracy)
    - penalty = clamp(1 - observed_drop, 0, 1)
    - Enforce monotonic non-increasing: penalty[i] >= penalty[i+1] (young to old).
    - Bands with total < MIN_SUPPORT: carry forward previous penalty (or 1.0 if first).
    """
    if fitted_at_utc is None:
        fitted_at_utc = datetime.now(timezone.utc).isoformat()

    grouped = _rows_by_market_reason(rows)
    result: List[DecayModelParams] = []

    for (market, reason_code), band_rows in sorted(grouped.items()):
        # Build accuracy and total per band index (0..6)
        band_acc: List[float | None] = [None] * len(BAND_ORDER)
        band_total: List[int] = [0] * len(BAND_ORDER)
        for r in band_rows:
            age_band = r.get("age_band", "0-30m")
            idx = _band_index(age_band)
            if 0 <= idx < len(BAND_ORDER):
                band_total[idx] = int(r.get("total", 0))
                acc = r.get("accuracy")
                band_acc[idx] = float(acc) if acc is not None else None

        # Baseline: accuracy at youngest band with total >= MIN_SUPPORT
        baseline_accuracy: float | None = None
        for i in range(len(BAND_ORDER)):
            if band_total[i] >= MIN_SUPPORT and band_acc[i] is not None:
                baseline_accuracy = band_acc[i]
                break
        if baseline_accuracy is None:
            baseline_accuracy = 1.0

        # Raw penalty per band: penalty = clamp(1 - observed_drop, 0, 1)
        penalties: List[float] = []
        for i in range(len(BAND_ORDER)):
            if band_total[i] < MIN_SUPPORT:
                # Carry forward: use previous penalty or 1.0
                prev = penalties[-1] if penalties else 1.0
                penalties.append(prev)
            else:
                acc = band_acc[i] if band_acc[i] is not None else baseline_accuracy
                observed_drop = max(0.0, baseline_accuracy - acc)
                penalty = _clamp(1.0 - observed_drop, 0.0, 1.0)
                penalties.append(penalty)

        # Enforce monotonic non-increasing (young to old): penalty[i] >= penalty[i+1]
        for i in range(1, len(penalties)):
            if penalties[i] > penalties[i - 1]:
                penalties[i] = penalties[i - 1]

        # Fit diagnostics
        bands_with_support = sum(1 for i in range(len(BAND_ORDER)) if band_total[i] >= MIN_SUPPORT)
        coverage_counts = list(band_total)

        # Optional MSE: (penalty - (1 - observed_drop))^2 over bands with support
        mse: float | None = None
        sq_sum = 0.0
        n_support = 0
        for i in range(len(BAND_ORDER)):
            if band_total[i] < MIN_SUPPORT:
                continue
            acc = band_acc[i] if band_acc[i] is not None else baseline_accuracy
            observed_drop = max(0.0, baseline_accuracy - acc)
            ideal_penalty = _clamp(1.0 - observed_drop, 0.0, 1.0)
            sq_sum += (penalties[i] - ideal_penalty) ** 2
            n_support += 1
        if n_support > 0:
            mse = sq_sum / n_support

        fit_quality = FitDiagnostics(
            bands_with_support=bands_with_support,
            total_bands=len(BAND_ORDER),
            coverage_counts=coverage_counts,
            mse_vs_baseline=round(mse, 6) if mse is not None else None,
        )

        result.append(DecayModelParams(
            schema_version=SCHEMA_VERSION,
            model_type=MODEL_TYPE_PIECEWISE_V1,
            market=market,
            reason_code=reason_code,
            bands=list(BAND_ORDER),
            penalty_by_band=penalties,
            fitted_at_utc=fitted_at_utc,
            fit_quality=fit_quality,
        ))

    # Stable ordering: by (market, reason_code)
    result.sort(key=lambda p: (p.market, p.reason_code))
    return result
