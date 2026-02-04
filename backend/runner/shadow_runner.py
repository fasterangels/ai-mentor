"""
Deterministic shadow runner: runs the end-to-end shadow pipeline in batch
and produces an offline BatchReport. No UI changes, no policy apply, no schedulers.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.live_io import live_io_metrics_snapshot, live_writes_allowed, reset_metrics
from guardrails.live_io_guardrails import evaluate as evaluate_live_io_guardrails
from pipeline.shadow_pipeline import run_shadow_pipeline
from policy.policy_store import stable_json_dumps
from repositories.raw_payload_repo import RawPayloadRepository

# Hard cap for determinism and resource limits
MAX_MATCHES_PER_RUN = 50


def _checksum(data: str | dict) -> str:
    if isinstance(data, dict):
        data = stable_json_dumps(data)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _normalize_utc(now: Optional[datetime]) -> datetime:
    if now is not None:
        return now.replace(microsecond=0) if now.tzinfo else now.replace(microsecond=0).astimezone(timezone.utc)
    return datetime.now(timezone.utc).replace(microsecond=0)


async def _get_cached_match_ids(session: AsyncSession, connector_name: str) -> List[str]:
    """Load all cached match IDs for the connector from ingestion cache."""
    repo = RawPayloadRepository(session)
    # Pipeline cache uses source_name "pipeline_cache"; connector-specific key could be extended later
    source = "pipeline_cache"
    return await repo.list_distinct_match_ids(source_name=source)


def _placeholder_final_score(match_id: str) -> Dict[str, int]:
    """Deterministic placeholder when caller does not provide final score."""
    return {"home": 0, "away": 0}


async def run_shadow_batch(
    session: AsyncSession,
    connector_name: str = "dummy",
    match_ids: Optional[List[str]] = None,
    *,
    now_utc: Optional[datetime] = None,
    final_scores: Optional[Dict[str, Dict[str, int]]] = None,
    dry_run: Optional[bool] = None,
    activation: bool = False,
    index_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Run shadow pipeline for each match and collect a BatchReport.
    If match_ids is None, load all cached matches for connector_name from ingestion cache.
    final_scores: optional map match_id -> {"home": int, "away": int} for tests; else placeholder.
    dry_run: if True, do not persist or write cache; if None, defaults to read-only (not live_writes_allowed()).
    activation: if True, check activation gate and persist if allowed (still requires env gates).
    index_path: optional path to reports/index for daily cap and rollout (no DB).
    """
    if dry_run is None:
        dry_run = not live_writes_allowed()
    now = _normalize_utc(now_utc)
    final_scores = final_scores or {}
    reset_metrics()

    if match_ids is None:
        match_ids = await _get_cached_match_ids(session, connector_name)

    if len(match_ids) > MAX_MATCHES_PER_RUN:
        return {
            "error": "MAX_MATCHES_EXCEEDED",
            "detail": f"Requested {len(match_ids)} matches; maximum allowed is {MAX_MATCHES_PER_RUN}.",
            "run_meta": None,
            "per_match": [],
            "aggregates": None,
            "checksums": None,
            "failures": [],
        }

    # Deterministic order
    match_ids = sorted(match_ids)

    # Check activation gate for batch (if activation requested)
    batch_activation_allowed = False
    batch_activation_reason = None
    if activation:
        from activation.gate import check_activation_gate_batch
        batch_activation_allowed, batch_activation_reason = check_activation_gate_batch(
            connector_name=connector_name,
            match_count=len(match_ids),
            index_path=index_path or "reports/index.json",
        )

    # Rollout and daily cap (deterministic selection)
    rollout_set: set = set()
    daily_cap_remaining_now = 0
    rollout_pct = 0.0
    daily_max = 0
    if activation and batch_activation_allowed:
        from activation.tiers import (
            select_rollout_match_ids,
            daily_cap_remaining,
            _rollout_pct,
            _daily_max_activations,
            get_tier_config,
        )
        rollout_pct = _rollout_pct()
        daily_max = _daily_max_activations()
        rollout_set = select_rollout_match_ids(match_ids, rollout_pct)
        daily_cap_remaining_now = daily_cap_remaining(index_path or "reports/index.json") if daily_max > 0 else len(match_ids)

    # Batch input checksum: connector + match list only (no volatile timestamps)
    batch_input_payload = {"connector_name": connector_name, "match_ids": match_ids}
    batch_input_checksum = _checksum(batch_input_payload)

    per_match: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    total_changed_decisions = 0
    per_market_changed_counts: Dict[str, int] = {}
    all_activation_audits: List[Dict[str, Any]] = []
    activations_used_this_batch = 0
    daily_rem = daily_cap_remaining_now

    for match_id in match_ids:
        allow_this_match = False
        if activation and batch_activation_allowed:
            allow_this_match = (match_id in rollout_set) and (daily_rem > 0)
        score = final_scores.get(match_id) or _placeholder_final_score(match_id)
        try:
            report = await run_shadow_pipeline(
                session,
                connector_name=connector_name,
                match_id=match_id,
                final_score=score,
                status="FINAL",
                now_utc=now,
                dry_run=dry_run,
                activation=activation,
                allow_activation_for_this_match=allow_this_match if activation else None,
            )
        except Exception as e:  # noqa: BLE001
            failures.append({"match_id": match_id, "error": str(e)})
            continue

        if report.get("error"):
            failures.append({
                "match_id": match_id,
                "error": report.get("error", "UNKNOWN"),
                "detail": report.get("detail", ""),
            })
            continue

        eval_checksum = report.get("evaluation_report_checksum")
        proposal_checksum = report.get("proposal", {}).get("proposal_checksum")
        audit = report.get("audit") or {}
        changed_count = int(audit.get("changed_count", 0))
        
        # Collect activation audits; track activations used for daily cap
        activation_section = report.get("activation") or {}
        if activation_section.get("audits"):
            all_activation_audits.extend(activation_section["audits"])
        if activation_section.get("activated") and allow_this_match:
            activations_used_this_batch += 1
            daily_rem = max(0, daily_rem - 1)
        per_market = audit.get("per_market_change_count") or {}

        per_match.append({
            "match_id": match_id,
            "evaluation_checksum": eval_checksum,
            "proposal_checksum": proposal_checksum,
            "audit_changed_count": changed_count,
        })
        total_changed_decisions += changed_count
        for market, count in per_market.items():
            per_market_changed_counts[market] = per_market_changed_counts.get(market, 0) + count

    # Batch output checksum: per_match summaries + aggregates (deterministic, no timestamps)
    aggregates = {
        "total_matches": len(per_match),
        "total_changed_decisions": total_changed_decisions,
        "per_market_changed_counts": dict(sorted(per_market_changed_counts.items())),
    }
    output_payload = {
        "per_match": per_match,
        "aggregates": aggregates,
    }
    batch_output_checksum = _checksum(output_payload)

    run_meta = {
        "started_at_utc": now.isoformat(),
        "connector_name": connector_name,
        "matches_count": len(match_ids),
    }

    live_io_metrics = live_io_metrics_snapshot()
    live_io_alerts = evaluate_live_io_guardrails(live_io_metrics, policy=None)

    # Build activation summary (tier, rollout_pct, daily cap, eligible vs activated)
    activated_count = sum(1 for a in all_activation_audits if a.get("activation_allowed"))
    activation_summary: Dict[str, Any] = {
        "activated": batch_activation_allowed and activated_count > 0 if activation else False,
        "reason": batch_activation_reason if not batch_activation_allowed and activation else None,
        "eligible_count": len(match_ids),
        "activated_count": activated_count,
    }
    if activation:
        try:
            from activation.tiers import get_tier_config, _rollout_pct, _daily_max_activations
            from activation.gate import get_activation_config
            cfg = get_activation_config()
            activation_summary["tier"] = cfg.get("activation_tier")
            activation_summary["rollout_pct"] = _rollout_pct()
            activation_summary["daily_max_activations"] = _daily_max_activations()
            activation_summary["daily_cap_remaining_before_run"] = daily_cap_remaining_now if activation and batch_activation_allowed else None
            if batch_activation_allowed and activated_count == 0 and len(rollout_set) == 0 and _rollout_pct() > 0:
                activation_summary["reason"] = activation_summary.get("reason") or "rollout_pct=0 or no matches in rollout set"
            elif batch_activation_allowed and daily_max > 0 and daily_cap_remaining_now == 0:
                activation_summary["reason"] = activation_summary.get("reason") or "daily activation cap exceeded"
        except Exception:  # noqa: BLE001
            pass
    if activation and all_activation_audits:
        from activation.audit import build_activation_summary
        activation_summary["activated_matches"] = [a.get("match_id") for a in all_activation_audits if a.get("activation_allowed")]
        activation_summary.update(build_activation_summary(all_activation_audits))
        # Preserve boolean activated (build_activation_summary returns activated count as int)
        activation_summary["activated"] = batch_activation_allowed and activated_count > 0

    # Burn-in: abort activation if any live IO alert (max_live_io_alerts = 0)
    from activation.gate import _activation_mode
    if activation and _activation_mode() == "burn_in":
        from activation.burn_in import BURN_IN_MAX_LIVE_IO_ALERTS, get_burn_in_config
        if len(live_io_alerts) > BURN_IN_MAX_LIVE_IO_ALERTS:
            activation_summary["activated"] = False
            activation_summary["reason"] = f"Burn-in: live IO alerts {len(live_io_alerts)} exceeds max {BURN_IN_MAX_LIVE_IO_ALERTS}"
        activation_summary["burn_in"] = {
            "activated_matches": [a.get("match_id") for a in all_activation_audits if a.get("activation_allowed")],
            "rejected_matches": [a.get("match_id") for a in all_activation_audits if not a.get("activation_allowed")],
            "rejected_reasons": list({a.get("activation_reason") for a in all_activation_audits if not a.get("activation_allowed")}),
            "burn_in_confidence_gate": get_burn_in_config().get("burn_in_min_confidence"),
            "guardrail_state": {"live_io_alerts_count": len(live_io_alerts), "max_live_io_alerts": BURN_IN_MAX_LIVE_IO_ALERTS},
        }

    result: Dict[str, Any] = {
        "run_meta": run_meta,
        "per_match": per_match,
        "aggregates": aggregates,
        "checksums": {
            "batch_input_checksum": batch_input_checksum,
            "batch_output_checksum": batch_output_checksum,
        },
        "failures": failures,
        "live_io_metrics": live_io_metrics,
        "live_io_alerts": live_io_alerts,
        "activation": activation_summary,
    }
    if dry_run:
        result["dry_run"] = True
    return result
