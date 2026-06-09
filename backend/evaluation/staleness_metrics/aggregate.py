"""
Pure aggregation for staleness metrics (G4). No I/O; deterministic.
Proxy mapping: reason_age_ms := decision_time_utc - snapshot.observed_at_utc (or effective_from_utc).
Refined later when per-reason evidence timestamps exist.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from evaluation.staleness_metrics.age_bands import band_for_age_ms
from evaluation.staleness_metrics.model import StalenessReport, StalenessRow

# Align with evaluation/offline_eval
MARKETS = ("one_x_two", "over_under_25", "gg_ng")

# EvaluationRecord: dict with market_outcomes, reason_codes_by_market, market_to_confidence (optional).
# No text parsing; resolver provides evidence_age_ms per record (proxy mapping).
EvidenceAgeResolver = Callable[[Dict[str, Any]], int | None]


def compute_staleness_metrics(
    records: List[Dict[str, Any]],
    resolver: EvidenceAgeResolver,
    computed_at_utc: str | None = None,
    notes: str = "",
) -> StalenessReport:
    """
    Pure function: aggregate (market, reason_code, age_band) from evaluation records.
    resolver(record) -> evidence_age_ms (int) or None. None/missing uses band 0-30m (proxy default).
    Deterministic; stable sort by (market, reason_code, age_band).
    """
    computed_at_utc = computed_at_utc or datetime.now(timezone.utc).isoformat()
    agg: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    for rec in records:
        outcomes = rec.get("market_outcomes") or {}
        reason_codes = rec.get("reason_codes_by_market") or {}
        market_to_confidence = rec.get("market_to_confidence") or {}
        age_ms = resolver(rec)
        if age_ms is None:
            age_ms = 0
        age_band = band_for_age_ms(age_ms)
        for market in MARKETS:
            outcome = outcomes.get(market, "UNRESOLVED")
            correct = 1 if outcome == "SUCCESS" else 0
            neutral = 1 if outcome not in ("SUCCESS", "FAILURE") else 0
            confidence = market_to_confidence.get(market)
            for code in (reason_codes.get(market) or []):
                code = str(code)
                key = (market, code, age_band)
                if key not in agg:
                    agg[key] = {"total": 0, "correct": 0, "neutral": 0, "sum_confidence": 0.0, "n_confidence": 0}
                agg[key]["total"] += 1
                agg[key]["correct"] += correct
                agg[key]["neutral"] += neutral
                if confidence is not None:
                    agg[key]["sum_confidence"] += float(confidence)
                    agg[key]["n_confidence"] += 1
    rows: List[StalenessRow] = []
    for (market, reason_code, age_band), v in sorted(agg.items()):
        n_conf = v["n_confidence"]
        avg_confidence = (v["sum_confidence"] / n_conf) if n_conf else None
        rows.append(StalenessRow(
            market=market,
            reason_code=reason_code,
            age_band=age_band,
            total=v["total"],
            correct=v["correct"],
            neutral=v["neutral"],
            avg_confidence=avg_confidence,
        ))
    return StalenessReport(rows=rows, computed_at_utc=computed_at_utc, notes=notes)
