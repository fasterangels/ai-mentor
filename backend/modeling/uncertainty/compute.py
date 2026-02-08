"""
Uncertainty signal computation (H3). Pure, deterministic. No refusals; measurement only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from modeling.reason_decay.model import DecayModelParams
from modeling.uncertainty.model import (
    LOW_EFFECTIVE_CONFIDENCE,
    LOW_SUPPORT,
    STALE_EVIDENCE,
    UncertaintyProfile,
    UncertaintySignal,
)

# Documented thresholds (explicit rules, no heuristics)
STALE_EVIDENCE_BANDS = ("3d-7d", "7d+")  # age_band in these -> STALE_EVIDENCE
LOW_EFFECTIVE_CONFIDENCE_THRESHOLD = 0.5  # penalized_confidence < this -> LOW_EFFECTIVE_CONFIDENCE
LOW_SUPPORT_BANDS_WITH_SUPPORT = 0  # decay fit_quality.bands_with_support == 0 -> LOW_SUPPORT

# CONFLICTING_REASONS: not implemented (no polarity/direction in repo); signal skipped when unavailable


def _shadow_rows_for_run(shadow_rows: List[Dict[str, Any]], run_id: str) -> List[Dict[str, Any]]:
    """Filter shadow rows by run_id. Deterministic."""
    return [r for r in shadow_rows if str(r.get("run_id", "")) == str(run_id)]


def compute_uncertainty_profile(
    decision_record: Dict[str, Any],
    shadow_rows: List[Dict[str, Any]],
    decay_params_map: Dict[Tuple[str, str], DecayModelParams],
    *,
    stale_bands: Tuple[str, ...] = STALE_EVIDENCE_BANDS,
    low_confidence_threshold: float = LOW_EFFECTIVE_CONFIDENCE_THRESHOLD,
) -> UncertaintyProfile:
    """
    Compute uncertainty signals for one decision. Deterministic; same inputs -> same profile.
    Missing optional inputs (shadow, decay) -> signal not triggered or skipped, never guessed.
    No refusals; output is for reporting only.
    """
    run_id = str(decision_record.get("run_id", ""))
    age_band = decision_record.get("age_band") or "0-30m"
    reason_codes_by_market = decision_record.get("reason_codes_by_market") or {}
    market_to_confidence = decision_record.get("market_to_confidence") or {}

    signals: List[UncertaintySignal] = []

    # STALE_EVIDENCE: any reason age_band >= configured threshold
    triggered_stale = age_band in stale_bands
    signals.append(UncertaintySignal(
        signal_type=STALE_EVIDENCE,
        reason_code=age_band,
        triggered=triggered_stale,
    ))

    # CONFLICTING_REASONS: skipped (no polarity in repo)
    # (Would add signal with triggered=False if we had polarity; spec says skip.)

    # Per (market, reason) from this decision: LOW_EFFECTIVE_CONFIDENCE, LOW_SUPPORT
    run_shadow = _shadow_rows_for_run(shadow_rows, run_id)
    shadow_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in run_shadow:
        m = r.get("market", "")
        rc = r.get("reason_code", "")
        shadow_by_key[(m, rc)] = r

    seen_low_conf = False
    seen_low_support = False
    for market, codes in sorted(reason_codes_by_market.items()):
        for code in codes or []:
            reason_code = str(code)
            decay_params = decay_params_map.get((market, reason_code))
            shadow_row = shadow_by_key.get((market, reason_code))

            # LOW_EFFECTIVE_CONFIDENCE: hypothetical penalized confidence < threshold
            if shadow_row is not None:
                penalized = shadow_row.get("penalized_confidence")
                if penalized is not None:
                    try:
                        p = float(penalized)
                        if p < low_confidence_threshold:
                            seen_low_conf = True
                    except (TypeError, ValueError):
                        pass
            # If shadow missing for this (market, reason): skip, do not guess

            # LOW_SUPPORT: decay params marked low support
            if decay_params is not None and decay_params.fit_quality is not None:
                if decay_params.fit_quality.bands_with_support <= LOW_SUPPORT_BANDS_WITH_SUPPORT:
                    seen_low_support = True

    signals.append(UncertaintySignal(
        signal_type=LOW_EFFECTIVE_CONFIDENCE,
        reason_code=f"threshold_{low_confidence_threshold}",
        triggered=seen_low_conf,
    ))
    signals.append(UncertaintySignal(
        signal_type=LOW_SUPPORT,
        reason_code="decay_fit_low_support",
        triggered=seen_low_support,
    ))

    return UncertaintyProfile(run_id=run_id, signals=signals)


def compute_would_refuse(profile: UncertaintyProfile) -> bool:
    """
    Simulated refusal rule (fixed). Would-refuse = TRUE if:
    - (STALE_EVIDENCE AND LOW_EFFECTIVE_CONFIDENCE) OR
    - (>=2 uncertainty signals triggered).
    Simulation only; no enforcement.
    """
    triggered = [s for s in profile.signals if s.triggered]
    count = len(triggered)
    stale = any(s.signal_type == STALE_EVIDENCE for s in triggered)
    low_conf = any(s.signal_type == LOW_EFFECTIVE_CONFIDENCE for s in triggered)
    if stale and low_conf:
        return True
    if count >= 2:
        return True
    return False
