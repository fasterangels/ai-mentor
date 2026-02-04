"""Shadow tuner: deterministic proposal from evaluation report."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from policy.policy_model import MarketPolicy, Policy, PolicyVersion, ReasonPolicy
from policy.policy_store import checksum_report, default_policy
from policy.policy_runtime import get_active_policy

MIN_SAMPLE_SIZE = 30
CONFIDENCE_BAND_DRIFT = (0.55, 0.60)
FAILURE_RATE_THRESHOLD = 0.65
MIN_CONFIDENCE_BUMP = 0.03
MAX_MIN_CONFIDENCE = 0.75
SUCCESS_RATE_FLOOR = 0.45
DAMPENING_MULTIPLIER = 0.8
DAMPENING_FLOOR = 0.3
MAX_MIN_CONFIDENCE_DELTA = 0.05
MAX_DAMPENING_DECREASE_PCT = 0.25


@dataclass
class PolicyProposal:
    proposed_policy: Policy
    diffs: list[tuple[str, Any, Any, str]]
    guardrails_results: list[tuple[str, bool, str]]
    evaluation_report_checksum: str


def _band_label(lo: float, hi: float) -> str:
    return f"{lo:.2f}-{hi:.2f}"


def _failure_rate_in_band(report: dict, market: str, band_label: str) -> tuple[float | None, int]:
    per_market = report.get("per_market_accuracy") or {}
    m = per_market.get(market) or {}
    bands = m.get("confidence_bands") or {}
    b = bands.get(band_label)
    if not b:
        return None, 0
    s, f = b.get("success_count") or 0, b.get("failure_count") or 0
    total = s + f + (b.get("neutral_count") or 0)
    if s + f == 0:
        return None, total
    return f / (s + f), total


def _reason_success_rate(report: dict, reason_code: str, market: str) -> tuple[float | None, int]:
    re = report.get("reason_effectiveness") or {}
    by_market = (re.get(reason_code) or {}).get(market)
    if not by_market:
        return None, 0
    s = by_market.get("success", 0) or 0
    f = by_market.get("failure", 0) or 0
    return (s / (s + f), s + f) if (s + f) > 0 else (None, s + f)


def run_tuner(evaluation_report: dict[str, Any]) -> PolicyProposal:
    from datetime import datetime, timezone

    current = get_active_policy()
    eval_checksum = checksum_report(evaluation_report)
    markets = {
        k: MarketPolicy(min_confidence=v.min_confidence, confidence_bands=v.confidence_bands)
        for k, v in current.markets.items()
    }
    reasons = {k: ReasonPolicy(reason_code=v.reason_code, dampening_factor=v.dampening_factor) for k, v in current.reasons.items()}
    diffs: list[tuple[str, Any, Any, str]] = []
    band_label = _band_label(CONFIDENCE_BAND_DRIFT[0], CONFIDENCE_BAND_DRIFT[1])

    for market in ("one_x_two", "over_under_25", "gg_ng"):
        failure_rate, sample_size = _failure_rate_in_band(evaluation_report, market, band_label)
        if failure_rate is not None and sample_size >= MIN_SAMPLE_SIZE and failure_rate > FAILURE_RATE_THRESHOLD:
            old_mc = markets[market].min_confidence
            new_mc = min(MAX_MIN_CONFIDENCE, old_mc + MIN_CONFIDENCE_BUMP)
            if new_mc > old_mc:
                markets[market] = MarketPolicy(min_confidence=new_mc, confidence_bands=markets[market].confidence_bands)
                diffs.append((f"markets.{market}.min_confidence", old_mc, new_mc, f"failure_rate {failure_rate:.2f} in band {band_label}"))

    re = evaluation_report.get("reason_effectiveness") or {}
    for reason_code in re:
        should_dampen = False
        worst_sr: float | None = None
        for market in ("one_x_two", "over_under_25", "gg_ng"):
            sr, n = _reason_success_rate(evaluation_report, reason_code, market)
            if sr is not None and n >= MIN_SAMPLE_SIZE and sr < SUCCESS_RATE_FLOOR:
                should_dampen = True
                worst_sr = sr if worst_sr is None else min(worst_sr, sr)
        if should_dampen and worst_sr is not None:
            if reason_code not in reasons:
                reasons[reason_code] = ReasonPolicy(reason_code=reason_code, dampening_factor=1.0)
            old_df = reasons[reason_code].dampening_factor
            new_df = max(DAMPENING_FLOOR, old_df * DAMPENING_MULTIPLIER)
            if new_df < old_df:
                reasons[reason_code] = ReasonPolicy(reason_code=reason_code, dampening_factor=new_df)
                diffs.append((f"reasons.{reason_code}.dampening_factor", old_df, new_df, f"success_rate {worst_sr:.2f}"))

    proposed = Policy(
        meta=PolicyVersion(
            version=current.meta.version + "-tuned",
            created_at_utc=datetime.now(timezone.utc),
            notes="Shadow proposal",
        ),
        markets=markets,
        reasons=reasons,
    )

    guardrails_results: list[tuple[str, bool, str]] = []
    for market in ("one_x_two", "over_under_25", "gg_ng"):
        cur = current.markets.get(market)
        prop = proposed.markets.get(market)
        if cur and prop:
            delta = prop.min_confidence - cur.min_confidence
            guardrails_results.append(("min_confidence_delta", delta <= MAX_MIN_CONFIDENCE_DELTA, f"{market}: {delta:.3f}"))
    for key, prop_r in proposed.reasons.items():
        cur_r = current.reasons.get(key)
        if cur_r and cur_r.dampening_factor > 0:
            pct = (cur_r.dampening_factor - prop_r.dampening_factor) / cur_r.dampening_factor
            guardrails_results.append(("dampening_decrease", pct <= MAX_DAMPENING_DECREASE_PCT, f"{key}: ok"))
        else:
            guardrails_results.append(("dampening_decrease", True, f"{key}: new"))

    return PolicyProposal(
        proposed_policy=proposed,
        diffs=diffs,
        guardrails_results=guardrails_results,
        evaluation_report_checksum=eval_checksum,
    )
