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
from .quality import assess_quality
from .sources import BaseSource, StubFixturesSource, StubStatsSource
from .types import DomainData, EvidencePack, PipelineInput, PipelineResult


# Registry of available sources by domain
_SOURCE_REGISTRY: Dict[str, List[BaseSource]] = {
    "fixtures": [StubFixturesSource()],
    "stats": [StubStatsSource()],
}


def _normalize_payload(
    source: BaseSource, raw_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Normalize raw payload into canonical structure."""
    return {
        "source_name": source.source_name,
        "domain": source.domain,
        "data": raw_payload.get("data", {}),
        "fetched_at_utc": raw_payload.get("fetched_at_utc", ""),
        "source_confidence": raw_payload.get("source_confidence", 0.5),
    }


def _compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Compute hash of normalized payload for deduplication."""
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(payload_str.encode()).hexdigest()[:16]


async def _fetch_from_sources(
    sources: List[BaseSource],
    match_id: str,
    window_hours: int,
    fetch_log_repo: FetchLogRepository,
) -> List[Dict[str, Any]]:
    """Fetch data from multiple sources and normalize."""
    normalized_payloads: List[Dict[str, Any]] = []

    for source in sources:
        try:
            start_time = datetime.now(timezone.utc)
            raw_payload = await source.fetch(match_id, window_hours)
            latency_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            normalized = _normalize_payload(source, raw_payload)
            normalized_payloads.append(normalized)

            # Log successful fetch
            await fetch_log_repo.add_log(
                source_name=source.source_name,
                domain=source.domain,
                status="success",
                latency_ms=latency_ms,
            )
        except Exception as e:
            # Log failed fetch
            await fetch_log_repo.add_log(
                source_name=source.source_name,
                domain=source.domain,
                status="error",
                latency_ms=0,
                notes=str(e),
            )
            # Continue with other sources

    return normalized_payloads


async def run_pipeline(
    session: AsyncSession, input_data: PipelineInput
) -> PipelineResult:
    """Run the data pipeline for a match.

    Steps:
    1. Check cache (unless force_refresh)
    2. Fetch from stub sources
    3. Normalize payloads
    4. Run quality gates
    5. Build consensus
    6. Assemble Evidence Pack
    7. Persist RawPayloads + logs

    Args:
        session: AsyncSession for repository access
        input_data: Pipeline input with match_id, domains, etc.

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

        # Step 2: Fetch from sources
        sources = _SOURCE_REGISTRY.get(domain, [])
        if not sources:
            notes.append(f"NO_SOURCES_AVAILABLE:{domain}")
            evidence_pack.domains[domain] = DomainData(
                data={},
                quality=assess_quality([], input_data.window_hours, []),
                sources=[],
            )
            all_domains_ok = False
            continue

        payloads = await _fetch_from_sources(
            sources, input_data.match_id, input_data.window_hours, fetch_log_repo
        )

        if not payloads:
            notes.append(f"NO_DATA_FETCHED:{domain}")
            evidence_pack.domains[domain] = DomainData(
                data={},
                quality=assess_quality([], input_data.window_hours, []),
                sources=[],
            )
            all_domains_ok = False
            continue

        # Step 3: Normalize (already done in _fetch_from_sources)
        # Step 4: Persist raw payloads
        for payload in payloads:
            payload_hash = _compute_payload_hash(payload)
            await raw_payload_repo.add_payload(
                source_name=payload["source_name"],
                domain=domain,
                payload_hash=payload_hash,
                payload_json=json.dumps(payload, default=str),
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

        if quality_report.passed:
            any_domain_ok = True

        evidence_pack.domains[domain] = domain_data

        # Step 7: Cache result (if quality passed)
        if quality_report.passed and not input_data.force_refresh:
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
