from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.fetch_log_repo import FetchLogRepository
from repositories.raw_payload_repo import RawPayloadRepository
from .cache import cache_payload, get_cached_payload
from .consensus import build_consensus
from .snapshot_envelope import build_envelope_for_recorded
from .quality import assess_quality
from .sources.registry import fetch as fetch_source
from .types import DomainData, EvidencePack, PipelineInput, PipelineResult

# Future source kinds (not yet called from pipeline): odds, injuries, lineups, head_to_head, recent_form.
# When added, register sources in backend/pipeline/sources/__init__.py and call
# fetch_source("odds", query) / fetch_source("injuries", query) / fetch_source("lineups", query)
# / fetch_source("head_to_head", query) / fetch_source("recent_form", query) as needed.


def _merged_to_normalized(merged: Dict[str, Any], domain: str) -> Dict[str, Any]:
    """Convert merged payload from multi-source fetch into one normalized payload for quality/consensus."""
    meta = merged.get("meta") or {}
    sources_list = meta.get("sources") or []
    source_name = sources_list[0]["source_name"] if sources_list else "multi_source"
    return {
        "source_name": source_name,
        "domain": domain,
        "data": merged.get("data", {}),
        "fetched_at_utc": merged.get("fetched_at_utc", ""),
        "source_confidence": merged.get("source_confidence", 0.5),
    }


def _compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Compute hash of normalized payload for deduplication."""
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(payload_str.encode()).hexdigest()[:16]


async def run_pipeline(
    session: AsyncSession, input_data: PipelineInput, *, dry_run: bool = False
) -> PipelineResult:
    """Run the data pipeline for a match.

    Steps:
    1. Check cache (unless force_refresh)
    2. Fetch from multi-source registry (fixtures/stats via stubs)
    3. Normalize payloads
    4. Run quality gates
    5. Build consensus
    6. Assemble Evidence Pack
    7. Persist RawPayloads + logs (skipped when dry_run=True)

    Args:
        session: AsyncSession for repository access
        input_data: Pipeline input with match_id, domains, etc.
        dry_run: If True, do not persist raw payloads or write cache.

    Returns:
        PipelineResult with status, evidence_pack, and notes
    """
    notes: List[str] = []
    fetch_log_repo = FetchLogRepository(session)
    raw_payload_repo = RawPayloadRepository(session)

    evidence_pack = EvidencePack(
        match_id=input_data.match_id,
        captured_at_utc=datetime.now(timezone.utc),
    )
    all_domains_ok = True
    any_domain_ok = False

    # Process each domain
    for domain in input_data.domains:
        # Step 1: Check cache
        cached = None
        if not input_data.force_refresh:
            cached = await get_cached_payload(
                session, input_data.match_id, domain, input_data.window_hours
            )
            if cached:
                notes.append(f"CACHE_HIT:{domain}")
                # TODO: Use cached data instead of fetching
                # For now, continue to fetch (cache implementation incomplete)

        if input_data.force_refresh:
            notes.append(f"CACHE_BYPASS_FORCE_REFRESH:{domain}")

        # Step 2: Fetch from multi-source registry (fixtures/stats via stubs; cache used unless force_refresh)
        query: Dict[str, Any] = {
            "match_id": input_data.match_id,
            "window_hours": input_data.window_hours,
        }
        if input_data.connector_name is not None:
            query["connector"] = input_data.connector_name
        merged = fetch_source(
            domain,
            query,
            force_refresh=input_data.force_refresh,
        )
        meta_sources = (merged.get("meta") or {}).get("sources") or []
        if not meta_sources and not merged.get("data"):
            notes.append(f"NO_SOURCES_AVAILABLE:{domain}")
            evidence_pack.domains[domain] = DomainData(
                data={},
                quality=assess_quality([], input_data.window_hours, []),
                sources=[],
            )
            all_domains_ok = False
            continue

        payloads = [_merged_to_normalized(merged, domain)]
        if not payloads:
            notes.append(f"NO_DATA_FETCHED:{domain}")
            evidence_pack.domains[domain] = DomainData(
                data={},
                quality=assess_quality([], input_data.window_hours, []),
                sources=[],
            )
            all_domains_ok = False
            continue

        if not dry_run:
            await fetch_log_repo.add_log(
                source_name=payloads[0].get("source_name", "multi_source"),
                domain=domain,
                status="success",
                latency_ms=0,
            )

        # Step 3: Normalize (done via _merged_to_normalized above)
        # Step 4: Persist raw payloads with G2 envelope (skip when dry_run)
        if not dry_run:
            now = datetime.now(timezone.utc)
            for payload in payloads:
                payload_hash = _compute_payload_hash(payload)
                envelope = build_envelope_for_recorded(
                    payload=payload,
                    snapshot_id=payload_hash,
                    created_at_utc=now,
                    source_name=payload.get("source_name", "recorded"),
                )
                payload_json = json.dumps(
                    {"metadata": envelope.to_dict(), "payload": payload},
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
                await raw_payload_repo.add_payload(
                    source_name=payload["source_name"],
                    domain=domain,
                    payload_hash=payload_hash,
                    payload_json=payload_json,
                    related_match_id=input_data.match_id,
                )

        # Step 5: Run quality gates
        # Determine required fields per domain
        # TODO: Make this configurable
        required_fields = []
        if domain == "fixtures":
            required_fields = ["match_id", "home_team", "away_team"]
        elif domain == "stats":
            required_fields = ["match_id"]

        quality_report = assess_quality(
            payloads, input_data.window_hours, required_fields
        )

        if not quality_report.passed:
            notes.append(f"QUALITY_GATE_FAILED:{domain}")
            all_domains_ok = False

        # Step 6: Build consensus
        domain_data = build_consensus(payloads, quality_report, domain)

        # Enrich fixtures with normalized team/league identifiers using the team registry.
        if domain == "fixtures":
            from services import team_registry  # Local import to avoid circular imports at module import time.

            data = dict(domain_data.data)
            home_name = data.get("home_team")
            away_name = data.get("away_team")
            league_name = data.get("competition")

            home_team = team_registry.resolve_team(home_name) if home_name else None
            away_team = team_registry.resolve_team(away_name) if away_name else None
            league = team_registry.resolve_league(league_name) if league_name else None

            if home_team is not None:
                data["home_team_id"] = home_team.get("id")
            if away_team is not None:
                data["away_team_id"] = away_team.get("id")
            if league is not None:
                data["league_id"] = league.get("id")

            domain_data = DomainData(
                data=data,
                quality=domain_data.quality,
                sources=domain_data.sources,
            )

        if quality_report.passed:
            any_domain_ok = True

        evidence_pack.domains[domain] = domain_data

        # Step 7: Cache result (if quality passed; skip when dry_run)
        if not dry_run and quality_report.passed and not input_data.force_refresh:
            # Cache the consensus data
            consensus_payload = {
                "source_name": "consensus",
                "domain": domain,
                "data": domain_data.data,
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_confidence": 1.0,
            }
            await cache_payload(
                session,
                input_data.match_id,
                domain,
                input_data.window_hours,
                consensus_payload,
            )

    # Collect flags from all domains
    for domain_data in evidence_pack.domains.values():
        evidence_pack.flags.extend(domain_data.quality.flags)

    # Determine overall status
    if all_domains_ok:
        status = "OK"
    elif any_domain_ok:
        status = "PARTIAL"
    else:
        status = "NO_DATA"

    return PipelineResult(
        status=status,
        evidence_pack=evidence_pack,
        notes=notes,
    )
