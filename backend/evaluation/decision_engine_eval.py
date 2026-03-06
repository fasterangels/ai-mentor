"""
Decision Engine evaluation helpers for offline reports (shadow-only).

This module wires the GO/NO-GO decision engine into the offline
evaluation pipeline without changing any existing analyzer or
policy behavior. It consumes existing reliability metrics and
per-decision prediction info to produce summary metrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.calibration.confidence_calibration import (
    ConfidenceCalibrator,
    load_calibrator,
)
from backend.decision_engine.decision_engine import (
    DecisionArtifacts,
    DecisionInput,
    decide,
)
from backend.policies.decision_engine_policy import load_policy


def build_reliability_table_from_reason_reliability(
    reason_reliability: Dict[str, Any],
) -> Dict[str, Dict[str, float]]:
    """
    Build a market -> reason -> reliability table from a reason_reliability block.

    Expected input shape:
      {
        "global": {reason_code: reliability_float},
        "per_market": {
          market: {reason_code: reliability_float},
        },
      }

    Semantics:
      - Per-market values take precedence for that market.
      - Global values act as a fallback for markets that omit a reason.
      - If per_market is empty but global exists, a synthetic "default" market
        is created using the global values.
    """
    global_rr: Dict[str, float] = {
        k: float(v) for k, v in (reason_reliability.get("global") or {}).items()
    }
    per_market_raw: Dict[str, Dict[str, float]] = {
        mk: {rk: float(rv) for rk, rv in (rv_dict or {}).items()}
        for mk, rv_dict in (reason_reliability.get("per_market") or {}).items()
    }

    table: Dict[str, Dict[str, float]] = {}

    # Start with explicit per-market values
    for market, reasons in per_market_raw.items():
        table[market] = dict(reasons)

    if not table and global_rr:
        # No per-market values at all; use a synthetic default bucket.
        table["default"] = dict(global_rr)
        return table

    # Apply global fallbacks for any missing reasons in each market.
    for reason, rel in global_rr.items():
        for market in table.keys():
            table[market].setdefault(reason, rel)

    return table


def _iter_predictions(
    predictions: Iterable[Dict[str, Any]],
) -> Iterable[Tuple[Dict[str, Any], DecisionInput]]:
    """
    Normalize raw prediction dicts into DecisionInput objects.

    The raw dict is preserved alongside the DecisionInput so that
    we can retain ids and any other metadata for examples.
    """
    for pred in predictions:
        market = (
            pred.get("market")
            or (pred.get("meta") or {}).get("market")
            or "default"
        )

        conf_raw = pred.get("confidence")
        if conf_raw is None:
            conf_raw = pred.get("conf")
        if conf_raw is None:
            conf_raw = pred.get("prob")
        if conf_raw is None:
            conf_raw = 0.0

        reasons = pred.get("reason_codes") or pred.get("reasons") or []
        if not isinstance(reasons, list):
            reasons = list(reasons or [])

        reason_conflicts = bool(pred.get("reason_conflicts") or False)

        di = DecisionInput(
            market=str(market),
            conf_raw=float(conf_raw),
            reasons=[str(r) for r in reasons],
            reason_conflicts=reason_conflicts,
            meta=pred.get("meta"),
        )
        yield pred, di


def evaluate_decision_engine(
    predictions: List[Dict[str, Any]],
    reason_reliability: Dict[str, Any],
    *,
    thresholds: Optional[Dict[str, float]] = None,
    calibrator: Optional[ConfidenceCalibrator] = None,
) -> Dict[str, Any]:
    """
    Run the decision engine in shadow mode over a list of predictions.

    Each prediction dict may contain:
      - market: str
      - confidence | conf | prob: float
      - reason_codes | reasons: list[str]
      - reason_conflicts: bool
      - id: opaque identifier (for examples)

    reason_reliability is expected to have:
      - global: {reason: reliability}
      - per_market: {market: {reason: reliability}}

    Returns a metrics block:
      {
        "version": "v0",
        "summary": { "n": int, "go": int, "no_go": int, "go_rate": float },
        "flag_counts": {flag: count},
        "per_market": {
          market: { "n": int, "go": int, "no_go": int, "go_rate": float },
        },
        "examples": [ up to 20 example entries ],
      }
    """
    reliability_table = build_reliability_table_from_reason_reliability(reason_reliability)
    artifacts = DecisionArtifacts(
        reliability_table=reliability_table,
        thresholds=dict(thresholds or {}),
        version="v0",
    )

    n = 0
    go = 0
    no_go = 0
    flag_counts: Dict[str, int] = {}
    per_market: Dict[str, Dict[str, Any]] = {}

    example_entries: List[Dict[str, Any]] = []
    outputs: List[Dict[str, Any]] = []
    sum_conf_raw = 0.0
    sum_conf_cal = 0.0

    for pred, di in _iter_predictions(predictions):
        out = decide(di, artifacts, calibrator=calibrator)
        n += 1
        sum_conf_raw += float(di.conf_raw)
        sum_conf_cal += float(out.conf_cal)
        if out.decision == "GO":
            go += 1
        else:
            no_go += 1

        m = di.market
        stats = per_market.setdefault(
            m,
            {"n": 0, "go": 0, "no_go": 0},
        )
        stats["n"] += 1
        if out.decision == "GO":
            stats["go"] += 1
        else:
            stats["no_go"] += 1

        for flag in out.flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

        # Full per-prediction output (lightweight) for training artifacts.
        outputs.append(
            {
                "id": pred.get("id"),
                "market": di.market,
                "score": out.score,
                "conf_raw": float(di.conf_raw),
                "conf_cal": float(out.conf_cal),
                "decision": out.decision,
                "flags": list(out.flags),
                "outcome": pred.get("outcome"),
            }
        )

        if len(example_entries) < 20:
            example_entries.append(
                {
                    "id": pred.get("id"),
                    "market": di.market,
                    "decision": out.decision,
                    "score": out.score,
                    "flags": list(out.flags),
                    "top_reasons": list(out.top_reasons),
                }
            )

    def _rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator > 0 else 0.0

    summary = {
        "n": n,
        "go": go,
        "no_go": no_go,
        "go_rate": _rate(go, n),
    }

    avg_conf_raw = sum_conf_raw / n if n > 0 else 0.0
    avg_conf_cal = sum_conf_cal / n if n > 0 else 0.0

    per_market_out: Dict[str, Any] = {}
    for market in sorted(per_market.keys()):
        stats = per_market[market]
        per_market_out[market] = {
            "n": stats["n"],
            "go": stats["go"],
            "no_go": stats["no_go"],
            "go_rate": _rate(stats["go"], stats["n"]),
        }

    flag_counts_sorted = {k: flag_counts[k] for k in sorted(flag_counts.keys())}

    return {
        "version": artifacts.version,
        "summary": summary,
        "flag_counts": flag_counts_sorted,
        "per_market": per_market_out,
        "examples": example_entries,
        "avg_conf_raw": avg_conf_raw,
        "avg_conf_cal": avg_conf_cal,
        "outputs": outputs,
    }


def evaluate_decision_engine_with_policy(
    predictions: List[Dict[str, Any]],
    reason_reliability: Dict[str, Any],
    policy_path: Optional[str] = None,
    calibrator_path: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str, str]:
    """
    Convenience wrapper that loads a versioned policy and evaluates the engine.

    Returns a tuple of (metrics, policy_version, calibrator_version).
    """
    base_dir = Path(__file__).resolve().parents[2]

    if policy_path is None:
        # Resolve the default policy file relative to the repository root.
        policy_path = str(base_dir / "backend" / "policies" / "decision_engine_policy.json")

    if calibrator_path is None:
        calibrator_path = str(base_dir / "backend" / "calibration" / "confidence_calibrator.json")

    policy = load_policy(policy_path)
    calibrator = load_calibrator(calibrator_path)

    metrics = evaluate_decision_engine(
        predictions,
        reason_reliability,
        thresholds=policy.thresholds,
        calibrator=calibrator,
    )
    outputs = metrics.get("outputs") or []
    return metrics, outputs, policy.version, calibrator.version


