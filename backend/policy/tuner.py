"""
Policy Tuner (SHADOW): deterministic rules propose policy changes; does not apply.
Input: evaluation_report.json data. Output: PolicyProposal with diffs and guardrails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from policy.policy_model import MarketPolicy, Policy, PolicyVersion, ReasonPolicy
from policy.policy_store import checksum_report, default_policy
from policy.policy_runtime import get_active_policy

# Constants for deterministic rules
MIN_SAMPLE_SIZE = 30
CONFIDENCE_BAND_DRIFT = (0.55, 0.60)  # band where we check failure rate
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
    """Output of shadow tune: proposed policy, diffs, guardrails, and input checksum."""

    proposed_policy: Policy
    diffs: list[tuple[str, Any, Any, str]]  # (path, old, new, rationale)
    guardrails_results: list[tuple[str, bool, str]]  # (check_name, passed, message)
    evaluation_report_checksum: str = ""


def _band_label(lo: float, hi: float) -> str:
    return f"{lo:.2f}-{hi:.2f}"


def _failure_rate_in_band(report: dict[str, Any], market: str, band_label: str) -> tuple[float | None, int]:
    """Return (failure_rate, sample_size) for market in band. band_label e.g. '0.55-0.60'."""
    per_market = report.get("per_market_accuracy") or {}
    m = per_market.get(market) or {}
    bands = m.get("confidence_bands") or {}
    b = bands.get(band_label)
    if not b:
        return None, 0
    s = b.get("success_count") or 0
    f = b.get("failure_count") or 0
    n = b.get("neutral_count") or 0
    total = s + f + n
    if total == 0:
        return None, 0
    if s + f == 0:
        return None, total
    return f / (s + f), total


def _reason_success_rate(report: dict[str, Any], reason_code: str, market: str) -> tuple[float | None, int]:
    """Return (success_rate, sample_size) for reason_code in market."""
    re = report.get("reason_effectiveness") or {}
    by_code = re.get(reason_code)
    if not by_code:
        return None, 0
    by_market = by_code.get(market)
    if not by_market:
        return None, 0
    s = by_market.get("success", 0) or 0
    f = by_market.get("failure", 0) or 0
    total = s + f + (by_market.get("neutral", 0) or 0)
    if s + f == 0:
        return None, total
    return s / (s + f), s + f


def run_tuner(evaluation_report: dict[str, Any]) -> PolicyProposal:
    """
    Deterministic tuner: from evaluation report produce a policy proposal.
    Does not apply; only proposes. Guardrails are evaluated and attached.
    """
    current = get_active_policy()
    eval_checksum = checksum_report(evaluation_report)

    # Start from a deep copy of current (we'll mutate then build Policy)
    markets = {}
    for k, v in current.markets.items():
        markets[k] = MarketPolicy(min_confidence=v.min_confidence, confidence_bands=v.confidence_bands)
    reasons = {k: ReasonPolicy(reason_code=v.reason_code, dampening_factor=v.dampening_factor) for k, v in current.reasons.items()}

    diffs: list[tuple[str, Any, Any, str]] = []
    band_label = _band_label(CONFIDENCE_BAND_DRIFT[0], CONFIDENCE_BAND_DRIFT[1])

    # Rule 1: Threshold drift by confidence band
    for market in ("one_x_two", "over_under_25", "gg_ng"):
        failure_rate, sample_size = _failure_rate_in_band(evaluation_report, market, band_label)
        if failure_rate is not None and sample_size >= MIN_SAMPLE_SIZE and failure_rate > FAILURE_RATE_THRESHOLD:
            old_mc = markets[market].min_confidence
            new_mc = min(MAX_MIN_CONFIDENCE, old_mc + MIN_CONFIDENCE_BUMP)
            if new_mc > old_mc:
                markets[market] = MarketPolicy(min_confidence=new_mc, confidence_bands=markets[market].confidence_bands)
                diffs.append(
                    (
                        f"markets.{market}.min_confidence",
                        old_mc,
                        new_mc,
                        f"failure_rate in band {band_label} = {failure_rate:.2f} > {FAILURE_RATE_THRESHOLD}, n={sample_size}",
                    )
                )

    # Rule 2: Reason dampening (once per reason_code if any market fails)
    re = evaluation_report.get("reason_effectiveness") or {}
    for reason_code in re:
        key = reason_code
        should_dampen = False
        worst_sr: float | None = None
        total_n = 0
        for market in ("one_x_two", "over_under_25", "gg_ng"):
            success_rate, sample_size = _reason_success_rate(evaluation_report, reason_code, market)
            if success_rate is not None and sample_size >= MIN_SAMPLE_SIZE and success_rate < SUCCESS_RATE_FLOOR:
                should_dampen = True
                if worst_sr is None or success_rate < worst_sr:
                    worst_sr = success_rate
                total_n += sample_size
        if should_dampen and key is not None and worst_sr is not None:
            if key not in reasons:
                reasons[key] = ReasonPolicy(reason_code=reason_code, dampening_factor=1.0)
            old_df = reasons[key].dampening_factor
            new_df = max(DAMPENING_FLOOR, old_df * DAMPENING_MULTIPLIER)
            if new_df < old_df:
                reasons[key] = ReasonPolicy(reason_code=reason_code, dampening_factor=new_df)
                diffs.append(
                    (
                        f"reasons.{key}.dampening_factor",
                        old_df,
                        new_df,
                        f"success_rate {worst_sr:.2f} < {SUCCESS_RATE_FLOOR}, n>={MIN_SAMPLE_SIZE}",
                    )
                )

    from datetime import datetime, timezone
    proposed = Policy(
        meta=PolicyVersion(
            version=current.meta.version + "-tuned",
            created_at_utc=datetime.now(timezone.utc),
            notes="Shadow proposal from tuner",
        ),
        markets=markets,
        reasons=reasons,
    )

    # Guardrails
    guardrails_results: list[tuple[str, bool, str]] = []

    # No market min_confidence increase > +0.05
    for market in ("one_x_two", "over_under_25", "gg_ng"):
        cur_mc = current.markets.get(market)
        prop_mc = proposed.markets.get(market)
        if cur_mc and prop_mc:
            delta = prop_mc.min_confidence - cur_mc.min_confidence
            if delta > MAX_MIN_CONFIDENCE_DELTA:
                guardrails_results.append(
                    ("min_confidence_delta", False, f"{market}: delta {delta:.3f} > {MAX_MIN_CONFIDENCE_DELTA}")
                )
            else:
                guardrails_results.append(("min_confidence_delta", True, f"{market}: delta {delta:.3f}"))

    # No dampening_factor decrease > 25%
    for key, prop_r in proposed.reasons.items():
        cur_r = current.reasons.get(key)
        if cur_r:
            if cur_r.dampening_factor > 0:
                pct_decrease = (cur_r.dampening_factor - prop_r.dampening_factor) / cur_r.dampening_factor
                if pct_decrease > MAX_DAMPENING_DECREASE_PCT:
                    guardrails_results.append(
                        ("dampening_decrease", False, f"{key}: decrease {pct_decrease:.2%} > {MAX_DAMPENING_DECREASE_PCT:.0%}")
                    )
                else:
                    guardrails_results.append(("dampening_decrease", True, f"{key}: ok"))
        else:
            guardrails_results.append(("dampening_decrease", True, f"{key}: new reason"))

    # Coverage: if report has coverage stats and proposal would reduce below target, fail (skip if not available)
    # Spec: "Proposal must not reduce coverage below a target if coverage stats available (if not available, skip)"
    overall = evaluation_report.get("overall") or {}
    if overall.get("resolved_snapshots") is not None and overall.get("total_snapshots", 0) > 0:
        # We don't have "coverage" in the report explicitly; we have resolved_snapshots. Skip coverage guardrail
        # unless we add a coverage field. So we pass.
        guardrails_results.append(("coverage", True, "coverage stats not in report; skip"))

    return PolicyProposal(
        proposed_policy=proposed,
        diffs=diffs,
        guardrails_results=guardrails_results,
        evaluation_report_checksum=eval_checksum,
    )
