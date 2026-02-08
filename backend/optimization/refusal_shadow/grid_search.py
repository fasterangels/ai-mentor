"""
Deterministic grid search for refusal thresholds (shadow-only).
Refuse rule: refuse = (age_band >= stale_band_threshold) AND (effective_confidence < effective_confidence_threshold).
Objective: maximize safety_score = accuracy_on_non_refused - ALPHA * refusal_rate.
Tie-breakers: higher safety_score, then lower refusal_rate, then higher accuracy_on_non_refused, then lowest thresholds.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .model import (
    ALPHA,
    BestThresholds,
    ShadowDecision,
    STALE_BANDS,
    effective_confidence_grid,
)

# Band order: index 0 = least stale, higher = staler. "age_band >= threshold" means band_index >= threshold_index.
_STALE_BAND_INDEX: Dict[str, int] = {b: i for i, b in enumerate(STALE_BANDS)}


def _band_order(band: str) -> int:
    """Return order index for band (0 = least stale). Unknown band treated as most stale (refuse more)."""
    return _STALE_BAND_INDEX.get(band, len(STALE_BANDS))


def would_refuse(
    decision: ShadowDecision,
    effective_confidence_threshold: float,
    stale_band_threshold: str,
) -> bool:
    """
    Refuse rule (simulation): refuse = TRUE if
    (age_band >= stale_band_threshold) AND (effective_confidence < effective_confidence_threshold).
    """
    band_ok = _band_order(decision.age_band) >= _band_order(stale_band_threshold)
    conf_ok = decision.effective_confidence < effective_confidence_threshold
    return bool(band_ok and conf_ok)


def _accuracy_on_non_refused(decisions: List[ShadowDecision], refused_mask: List[bool]) -> Tuple[float, int, int, int]:
    """
    Accuracy among non-refused, ignoring neutrals (success / (success + failure)).
    Returns (accuracy, success_count, failure_count, non_refused_count).
    """
    success = 0
    failure = 0
    for d, ref in zip(decisions, refused_mask):
        if ref:
            continue
        if d.outcome == "SUCCESS":
            success += 1
        elif d.outcome == "FAILURE":
            failure += 1
    total = success + failure
    acc = round(success / total, 4) if total > 0 else 0.0
    return acc, success, failure, len(decisions) - sum(refused_mask)


def _evaluate_thresholds(
    decisions: List[ShadowDecision],
    effective_confidence_threshold: float,
    stale_band_threshold: str,
) -> Tuple[float, float, float, int, int, int, int, int]:
    """
    Compute refusal_rate, accuracy_on_non_refused, safety_score, and support counts.
    Returns (refusal_rate, accuracy_on_non_refused, safety_score, support_total, support_refused,
             support_non_refused, success_non_refused, failure_non_refused).
    """
    n = len(decisions)
    if n == 0:
        return 0.0, 0.0, 0.0, 0, 0, 0, 0, 0
    refused = [would_refuse(d, effective_confidence_threshold, stale_band_threshold) for d in decisions]
    ref_count = sum(refused)
    refusal_rate = round(ref_count / n, 4)
    acc, success_nr, failure_nr, non_ref_count = _accuracy_on_non_refused(decisions, refused)
    safety_score = round(acc - ALPHA * refusal_rate, 4)
    return refusal_rate, acc, safety_score, n, ref_count, non_ref_count, success_nr, failure_nr


def _tie_break_key(
    effective_confidence_threshold: float,
    stale_band_threshold: str,
    refusal_rate: float,
    accuracy_on_non_refused: float,
    safety_score: float,
) -> Tuple[float, float, float, float, float]:
    """
    Sort key for best: higher safety_score, then lower refusal_rate, then higher accuracy,
    then lowest thresholds (eff_conf then stale_band index).
    We use negative for "higher is better" when we sort ascending and take last, or we sort descending.
    For deterministic "best": sort candidates by (-safety_score, refusal_rate, -accuracy, eff_conf, stale_index).
    Then best is first (highest safety, then lowest refusal, then highest acc, then lowest thresholds).
    """
    stale_idx = _band_order(stale_band_threshold)
    return (
        -safety_score,  # higher safety first
        refusal_rate,   # lower refusal first
        -accuracy_on_non_refused,  # higher accuracy first
        effective_confidence_threshold,  # lower threshold first
        stale_idx,  # lower band index first (less stale threshold)
    )


def grid_search_best_thresholds(
    decisions: List[ShadowDecision],
    markets: Optional[List[str]] = None,
) -> Dict[Optional[str], BestThresholds]:
    """
    Run grid search over (effective_confidence_threshold, stale_band_threshold).
    Returns best per market and overall (key None = overall).
    Tie-breakers: higher safety_score, then lower refusal_rate, then higher accuracy_on_non_refused,
    then lowest effective_confidence_threshold, then lowest stale_band_threshold (earliest in STALE_BANDS).
    """
    eff_grid = effective_confidence_grid()
    results: Dict[Optional[str], BestThresholds] = {}

    # Overall
    _run_grid(decisions, None, eff_grid, results)

    # Per market
    if markets is not None:
        for m in markets:
            subset = [d for d in decisions if d.market == m]
            _run_grid(subset, m, eff_grid, results)

    return results


def _run_grid(
    decisions: List[ShadowDecision],
    market_key: Optional[str],
    eff_grid: List[float],
    results: Dict[Optional[str], BestThresholds],
) -> None:
    candidates: List[Tuple[float, float, BestThresholds]] = []
    for eff in eff_grid:
        for stale in STALE_BANDS:
            rr, acc, safety, total, ref_count, non_ref, success_nr, failure_nr = _evaluate_thresholds(
                decisions, eff, stale
            )
            bt = BestThresholds(
                effective_confidence_threshold=eff,
                stale_band_threshold=stale,
                refusal_rate=rr,
                accuracy_on_non_refused=acc,
                safety_score=safety,
                support_total=total,
                support_refused=ref_count,
                support_non_refused=non_ref,
                success_non_refused=success_nr,
                failure_non_refused=failure_nr,
            )
            key = _tie_break_key(eff, stale, rr, acc, safety)
            candidates.append((key, 0, bt))  # second element for stable sort

    if not candidates:
        return
    candidates.sort(key=lambda x: (x[0], x[1]))
    # Best is first (smallest key: -safety is smallest when safety is highest, etc.)
    _, _, best = candidates[0]
    results[market_key] = best
