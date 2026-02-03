"""Ingestion API: list connectors, trigger ingest, read cache (read-only + trigger)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from ingestion.cache_repo import IngestionCacheRepository
from ingestion.ingestion_service import ingest_all
from ingestion.registry import list_connector_names

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.get(
    "/connectors",
    summary="List connector names",
    description="Returns names of registered data connectors.",
)
async def get_connectors() -> dict:
    """GET /api/v1/ingestion/connectors -> { connectors: string[] }."""
    return {"connectors": list_connector_names()}


@router.post(
    "/run/{connector_name}",
    summary="Run ingestion for a connector",
    description="Fetches all matches from the connector, enriches with provenance/checksums, writes to cache. Returns summary.",
)
async def post_ingestion_run(
    connector_name: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """POST /api/v1/ingestion/run/{connector_name} -> summary with fetched_matches, cached_writes, failures."""
    try:
        summary = await ingest_all(session, connector_name)
        return summary
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/cache/matches/{connector_name}",
    summary="List cached matches for connector",
    description="Returns MatchIdentity list from cache for the given connector.",
)
async def get_cache_matches(
    connector_name: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """GET /api/v1/ingestion/cache/matches/{connector_name} -> { identities: MatchIdentity[] }."""
    repo = IngestionCacheRepository(session)
    identities = await repo.list_latest_matches(connector_name)
    return {
        "identities": [
            {
                "match_id": i.match_id,
                "home_team": i.home_team,
                "away_team": i.away_team,
                "competition": i.competition,
                "kickoff_utc": i.kickoff_utc.isoformat(),
            }
            for i in identities
        ]
    }


@router.get(
    "/cache/match/{match_id}",
    summary="Get latest cached payload for a match",
    description="Returns IngestedMatchData or 404.",
)
async def get_cache_match(
    match_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """GET /api/v1/ingestion/cache/match/{match_id} -> IngestedMatchData as JSON or 404."""
    repo = IngestionCacheRepository(session)
    data = await repo.get_latest(match_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No cached data for match_id={match_id}")
    return data.model_dump(mode="json")
