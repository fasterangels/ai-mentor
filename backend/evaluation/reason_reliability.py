"""
Reason Reliability Index (metrics-only; no analyzer/decision behavior changes).

Computes a smoothed reliability score per reason, using activations/failures
from reason_failure_metrics and a simple Beta(alpha, beta) prior.
"""

from __future__ import annotations

from typing import Any, Dict

REASON_RELIABILITY_VERSION = 1
DEFAULT_ALPHA = 2.0
DEFAULT_BETA = 2.0


def _sorted_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy with keys sorted recursively for deterministic JSON."""
    out: Dict[str, Any] = {}
    for k in sorted(d.keys()):
        v = d[k]
        if isinstance(v, dict):
            out[k] = _sorted_dict(v)
        else:
            out[k] = v
    return out


def compute_reason_reliability(
    reason_failure_metrics: Dict[str, Any],
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> Dict[str, Any]:
    """
    Compute reliability per reason from reason_failure_metrics.

    reason_failure_metrics is expected to have the structure produced by
    backend/evaluation/reason_failure_metrics.py:

      {
        reason_code: {
          "global": {"activations": int, "failures": int, ...},
          "per_market": {
            market: {"activations": int, "failures": int, ...},
          },
        },
        ...
      }

    Reliability is defined as:
      base_failure_rate = failures / activations  (0 if activations == 0)
      smoothed_failure_rate = (failures + alpha) / (activations + alpha + beta)
      reliability = 1 - smoothed_failure_rate
    """
    if not reason_failure_metrics:
        return {}

    out: Dict[str, Any] = {}
    for code in sorted(reason_failure_metrics.keys()):
        entry = reason_failure_metrics.get(code) or {}
        g = entry.get("global") or {}
        ga = int(g.get("activations") or 0)
        gf = int(g.get("failures") or 0)
        denom_g = ga + alpha + beta
        smoothed_g = 0.0 if denom_g <= 0 else (gf + alpha) / denom_g
        reliability_g = 1.0 - smoothed_g

        global_block = {
            "activations": ga,
            "failures": gf,
            "reliability": reliability_g,
            "method": "beta_smoothing",
            "params": {"alpha": alpha, "beta": beta},
        }

        per_market_raw = entry.get("per_market") or {}
        per_market_out: Dict[str, Any] = {}
        for market in sorted(per_market_raw.keys()):
            m_stats = per_market_raw.get(market) or {}
            ma = int(m_stats.get("activations") or 0)
            mf = int(m_stats.get("failures") or 0)
            denom_m = ma + alpha + beta
            smoothed_m = 0.0 if denom_m <= 0 else (mf + alpha) / denom_m
            reliability_m = 1.0 - smoothed_m
            per_market_out[market] = {
                "activations": ma,
                "failures": mf,
                "reliability": reliability_m,
            }

        out[code] = {
            "global": global_block,
            "per_market": per_market_out,
        }

    return out


def reason_reliability_for_report(
    reason_failure_metrics: Dict[str, Any],
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> Dict[str, Any]:
    """
    Wrap compute_reason_reliability with versioned meta for evaluation reports.
    """
    metrics = compute_reason_reliability(reason_failure_metrics, alpha=alpha, beta=beta)
    return {
        "reason_reliability": _sorted_dict(metrics),
        "meta": {
            "reason_reliability_version": REASON_RELIABILITY_VERSION,
            "method": "beta_smoothing",
            "alpha": alpha,
            "beta": beta,
        },
    }

