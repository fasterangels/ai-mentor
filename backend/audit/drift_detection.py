from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import math


@dataclass
class DriftConfig:
    score_drift_threshold: float = 0.15
    reason_drift_threshold: float = 0.20
    min_samples: int = 50
    version: str = "v0"


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def compute_score_drift(prev_scores: List[float], curr_scores: List[float]) -> float:
    return abs(mean(curr_scores) - mean(prev_scores))


def compute_reason_drift(prev: Dict[str, int], curr: Dict[str, int]) -> Dict[str, float]:
    """
    Compute relative change in activation frequency per reason.

    Drift per reason r is defined as:
      abs(curr_count - prev_count) / max(prev_count, 1)
    with deterministic key ordering.
    """
    drift: Dict[str, float] = {}
    all_reasons = sorted(set(prev.keys()) | set(curr.keys()))
    for r in all_reasons:
        p = int(prev.get(r, 0))
        c = int(curr.get(r, 0))
        if p == 0 and c == 0:
            drift[r] = 0.0
        else:
            drift[r] = abs(c - p) / float(max(p, 1))
    return drift


def detect_drift(prev_report: Dict[str, Any], curr_report: Dict[str, Any], cfg: DriftConfig) -> Dict[str, Any]:
    """
    Detect score and reason drift between two evaluation reports.

    Uses decision_engine_outputs from each report, treating "flags" as
    proxy for reason/condition activations for v1.
    """
    prev_scores: List[float] = []
    curr_scores: List[float] = []

    prev_reason_counts: Dict[str, int] = {}
    curr_reason_counts: Dict[str, int] = {}

    for r in prev_report.get("decision_engine_outputs", []):
        if not isinstance(r, dict):
            continue
        score = r.get("score", 0.0)
        try:
            prev_scores.append(float(score))
        except (TypeError, ValueError):
            continue
        for rc in r.get("flags", []) or []:
            rc_str = str(rc)
            prev_reason_counts[rc_str] = prev_reason_counts.get(rc_str, 0) + 1

    for r in curr_report.get("decision_engine_outputs", []):
        if not isinstance(r, dict):
            continue
        score = r.get("score", 0.0)
        try:
            curr_scores.append(float(score))
        except (TypeError, ValueError):
            continue
        for rc in r.get("flags", []) or []:
            rc_str = str(rc)
            curr_reason_counts[rc_str] = curr_reason_counts.get(rc_str, 0) + 1

    score_drift = compute_score_drift(prev_scores, curr_scores)
    reason_drift = compute_reason_drift(prev_reason_counts, curr_reason_counts)

    alerts: List[Dict[str, Any]] = []

    # Only consider score drift if we have enough samples in both sets.
    if len(prev_scores) >= cfg.min_samples and len(curr_scores) >= cfg.min_samples:
        if score_drift > cfg.score_drift_threshold:
            alerts.append({"type": "score_drift", "value": round(score_drift, 4)})

    # Reason drift alerts, enforced with min_samples based on previous counts.
    for reason in sorted(reason_drift.keys()):
        v = float(reason_drift[reason])
        prev_count = prev_reason_counts.get(reason, 0)
        if prev_count < cfg.min_samples:
            continue
        if v > cfg.reason_drift_threshold:
            alerts.append(
                {
                    "type": "reason_drift",
                    "reason": reason,
                    "value": round(v, 4),
                }
            )

    return {
        "version": cfg.version,
        "score_drift": round(score_drift, 4),
        "reason_drift": {k: float(reason_drift[k]) for k in sorted(reason_drift.keys())},
        "alerts": alerts,
    }

