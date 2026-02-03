"""
Ingestion orchestration: fetch from connector, enrich with provenance/checksums, write to cache.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.cache_repo import IngestionCacheRepository
from ingestion.checksums import ingested_checksum, odds_checksum
from ingestion.registry import get_connector
from ingestion.schema import IngestedMatchData, OddsSnapshot


def _enrich_payload(
    data: IngestedMatchData,
    connector_name: str,
    collected_at_utc: datetime,
) -> IngestedMatchData:
    """Set provenance and checksums on a copy of the payload."""
    odds_with_checksums: List[OddsSnapshot] = []
    for o in data.odds:
        c = odds_checksum(o)
        odds_with_checksums.append(
            OddsSnapshot(
                market=o.market,
                selection=o.selection,
                odds=o.odds,
                source=o.source,
                collected_at_utc=o.collected_at_utc,
                checksum=c,
            )
        )
    enriched = IngestedMatchData(
        identity=data.identity,
        odds=odds_with_checksums,
        state=data.state,
        source=connector_name,
        collected_at_utc=collected_at_utc,
        checksum=None,
    )
    # Set payload checksum after building (uses odds checksums)
    enriched.checksum = ingested_checksum(enriched)
    return enriched


async def ingest_all(
    session: AsyncSession,
    connector_name: str,
) -> Dict[str, Any]:
    """
    Fetch all matches from connector, fetch_match_data for each, enrich and upsert to cache.
    Returns summary: fetched_matches, cached_writes, failures (list of { match_id, error }).
    """
    connector = get_connector(connector_name)
    cache_repo = IngestionCacheRepository(session)
    collected_at = datetime.now(timezone.utc)

    matches = connector.fetch_matches()
    fetched_matches = len(matches)
    cached_writes = 0
    failures: List[Dict[str, Any]] = []

    for identity in matches:
        match_id = identity.match_id
        try:
            data = connector.fetch_match_data(match_id)
            enriched = _enrich_payload(data, connector_name, collected_at)
            payload_json = enriched.model_dump_json()
            checksum = enriched.checksum or ingested_checksum(enriched)
            await cache_repo.upsert(
                match_id=match_id,
                connector_name=connector_name,
                collected_at_utc=collected_at,
                payload_json=payload_json,
                payload_checksum=checksum,
            )
            cached_writes += 1
        except Exception as e:
            failures.append({"match_id": match_id, "error": str(e)})

    return {
        "fetched_matches": fetched_matches,
        "cached_writes": cached_writes,
        "failures": failures,
    }


async def ingest_one(
    session: AsyncSession,
    connector_name: str,
    match_id: str,
) -> IngestedMatchData:
    """Fetch one match from connector, enrich, upsert, return enriched payload."""
    connector = get_connector(connector_name)
    cache_repo = IngestionCacheRepository(session)
    collected_at = datetime.now(timezone.utc)

    data = connector.fetch_match_data(match_id)
    enriched = _enrich_payload(data, connector_name, collected_at)
    payload_json = enriched.model_dump_json()
    checksum = enriched.checksum or ingested_checksum(enriched)
    await cache_repo.upsert(
        match_id=match_id,
        connector_name=connector_name,
        collected_at_utc=collected_at,
        payload_json=payload_json,
        payload_checksum=checksum,
    )
    return enriched
