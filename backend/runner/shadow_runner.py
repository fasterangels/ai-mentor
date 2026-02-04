"""
Deterministic shadow runner: runs the end-to-end shadow pipeline in batch
and produces an offline BatchReport. No UI changes, no policy apply, no schedulers.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.live_io import live_writes_allowed
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
) -> Dict[str, Any]:
    """
    Run shadow pipeline for each match and collect a BatchReport.
    If match_ids is None, load all cached matches for connector_name from ingestion cache.
    final_scores: optional map match_id -> {"home": int, "away": int} for tests; else placeholder.
    dry_run: if True, do not persist or write cache; if None, defaults to read-only (not live_writes_allowed()).
    """
    if dry_run is None:
        dry_run = not live_writes_allowed()
    now = _normalize_utc(now_utc)
    final_scores = final_scores or {}

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

    # Batch input checksum: connector + match list only (no volatile timestamps)
    batch_input_payload = {"connector_name": connector_name, "match_ids": match_ids}
    batch_input_checksum = _checksum(batch_input_payload)

    per_match: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    total_changed_decisions = 0
    per_market_changed_counts: Dict[str, int] = {}

    for match_id in match_ids:
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

    result: Dict[str, Any] = {
        "run_meta": run_meta,
        "per_match": per_match,
        "aggregates": aggregates,
        "checksums": {
            "batch_input_checksum": batch_input_checksum,
            "batch_output_checksum": batch_output_checksum,
        },
        "failures": failures,
    }
    if dry_run:
        result["dry_run"] = True
    return result
