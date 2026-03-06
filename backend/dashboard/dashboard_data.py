from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class DashboardConfig:
    top_k_markets: int = 10
    version: str = "v0"


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def build_dashboard_data(report: Dict[str, Any], cfg: DashboardConfig) -> Dict[str, Any]:
    """
    Aggregate dashboard-ready metrics from an offline evaluation report.
    """
    de_metrics = report.get("decision_engine_metrics") or {}
    summary = de_metrics.get("summary") or {}

    n_predictions = int(summary.get("n") or 0)
    go = int(summary.get("go") or 0)
    no_go = int(summary.get("no_go") or 0)

    if "go_rate" in summary:
        go_rate = _safe_float(summary.get("go_rate"), 0.0)
    else:
        go_rate = go / float(n_predictions) if n_predictions > 0 else 0.0
    no_go_rate = 1.0 - go_rate if n_predictions > 0 else 0.0

    avg_conf_raw = _safe_float(de_metrics.get("avg_conf_raw"), 0.0)
    avg_conf_cal = _safe_float(de_metrics.get("avg_conf_cal"), 0.0)

    global_block: Dict[str, Any] = {
        "n_predictions": n_predictions,
        "go_rate": round(go_rate, 4),
        "no_go_rate": round(no_go_rate, 4),
        "avg_conf_raw": round(avg_conf_raw, 4),
        "avg_conf_cal": round(avg_conf_cal, 4),
    }

    # Markets
    markets: List[Dict[str, Any]] = []
    per_market = de_metrics.get("per_market") or {}
    if isinstance(per_market, dict):
        for market, m in per_market.items():
            if not isinstance(m, dict):
                continue
            n_m = int(m.get("n") or 0)
            if "go_rate" in m:
                go_rate_m = _safe_float(m.get("go_rate"), 0.0)
            else:
                go_m = int(m.get("go") or 0)
                go_rate_m = go_m / float(n_m) if n_m > 0 else 0.0
            no_go_rate_m = 1.0 - go_rate_m if n_m > 0 else 0.0
            markets.append(
                {
                    "market": str(market),
                    "n": n_m,
                    "go_rate": round(go_rate_m, 4),
                    "no_go_rate": round(no_go_rate_m, 4),
                }
            )

    # Sort markets by n desc, then market name asc
    markets.sort(key=lambda x: (-x["n"], x["market"]))
    if cfg.top_k_markets > 0:
        markets = markets[: cfg.top_k_markets]

    # Reasons from reason_reliability
    reasons: List[Dict[str, Any]] = []
    reason_rel = report.get("reason_reliability") or {}
    global_rr = reason_rel.get("global")
    if isinstance(global_rr, dict):
        # Shape: {"reason": reliability}
        for reason, rel in global_rr.items():
            reasons.append(
                {
                    "reason": str(reason),
                    "reliability": _safe_float(rel, 0.0),
                }
            )
    else:
        # Fallback: reason-centric shape: {reason: {"global": {"reliability": x}, ...}}
        if isinstance(reason_rel, dict):
            for reason, entry in reason_rel.items():
                if not isinstance(entry, dict):
                    continue
                g = entry.get("global") or {}
                rel_val = g.get("reliability")
                if rel_val is None:
                    continue
                reasons.append(
                    {
                        "reason": str(reason),
                        "reliability": _safe_float(rel_val, 0.0),
                    }
                )

    # Sort reasons by reliability asc, then reason name
    reasons.sort(key=lambda x: (x["reliability"], x["reason"]))
    reasons = reasons[:10]

    # Audit
    system_audit = report.get("system_audit") or {}
    red_flags = system_audit.get("red_flags") or []
    audit_block = {
        "red_flags": len(red_flags) if isinstance(red_flags, list) else 0,
    }

    # Meta pass-through
    meta_in = report.get("meta") or {}
    meta_keys = [
        "decision_engine_version",
        "decision_policy_version",
        "calibrator_version",
        "refusal_tradeoff_version",
        "system_audit_version",
    ]
    meta_out: Dict[str, Any] = {}
    for k in sorted(meta_keys):
        if k in meta_in:
            meta_out[k] = meta_in[k]

    return {
        "version": cfg.version,
        "global": global_block,
        "markets": markets,
        "reasons": reasons,
        "audit": audit_block,
        "meta": meta_out,
    }

