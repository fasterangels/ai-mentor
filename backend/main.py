import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.database import init_database, dispose_database
from core.logging import setup_logging
from routes.api_v1 import api_v1_router
from sources.base import FetchRequest
from sources.cache import load_cache, save_cache
from sources.registry import get_source, list_sources
from football.feature_builder import build_features_payload
from football.match_finder import find_match_by_teams, find_matches_by_team
from football.mock_fixtures import get_mock_fixtures
from football.mock_providers import MockFootballOddsProvider, MockFootballStatsProvider
from football.http_providers import HttpJsonFootballOddsProvider, HttpJsonFootballStatsProvider
from football.adapters import ApiFootballStatsProvider, OddsApiProvider

# Football stats: A) API_FOOTBALL_KEY -> ApiFootball, B) FOOTBALL_STATS_BASE_URL -> HttpJson, C) Mock
_api_football_key = os.environ.get("API_FOOTBALL_KEY", "").strip()
_stats_base = os.environ.get("FOOTBALL_STATS_BASE_URL", "").strip()
if _api_football_key:
    stats_provider = ApiFootballStatsProvider(api_key=_api_football_key)
elif _stats_base:
    stats_provider = HttpJsonFootballStatsProvider(
        _stats_base,
        api_key=os.environ.get("FOOTBALL_STATS_API_KEY") or None,
    )
else:
    stats_provider = MockFootballStatsProvider()

# Football odds: A) ODDS_API_KEY -> OddsApi, B) FOOTBALL_ODDS_BASE_URL -> HttpJson, C) Mock
_odds_api_key = os.environ.get("ODDS_API_KEY", "").strip()
_odds_base = os.environ.get("FOOTBALL_ODDS_BASE_URL", "").strip()
if _odds_api_key:
    odds_provider = OddsApiProvider(api_key=_odds_api_key)
elif _odds_base:
    odds_provider = HttpJsonFootballOddsProvider(
        _odds_base,
        api_key=os.environ.get("FOOTBALL_ODDS_API_KEY") or None,
    )
else:
    odds_provider = MockFootballOddsProvider()


# Block 1 skeleton + Block 8.1 API wiring.
# TODO: Re-introduce legacy endpoints and services using the new core
#       configuration, logging, and async database infrastructure.

settings = get_settings()
setup_logging(settings)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

# CORS: single source of truth — defined here only, before any routers. OPTIONS preflight handled by CORSMiddleware.
ALLOWED_ORIGINS = [
    "http://tauri.localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(api_v1_router)


@app.on_event("startup")
async def on_startup() -> None:
    """Application startup hook."""
    await init_database(settings.database_url)
    logger.info("FastAPI app from %s: CORS allow_origins=%s allow_credentials=%s", __file__, ALLOWED_ORIGINS, False)
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Application shutdown hook."""
    await dispose_database()
    logger.info("Application shutdown complete")


@app.get("/health")
async def health() -> dict:
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "football_stats_provider": getattr(stats_provider, "name", "unknown"),
        "football_odds_provider": getattr(odds_provider, "name", "unknown"),
    }


@app.get("/sources")
def sources() -> dict:
    """List registered data source names."""
    return {"sources": list_sources()}


@app.post("/fetch")
def fetch(req: dict) -> dict:
    """Fetch data from a source for a market; uses cache when valid."""
    source = req.get("source")
    market = req.get("market")

    cached = load_cache(source, market)

    if cached:
        return {
            "source": source,
            "market": market,
            "cached": True,
            "payload": cached,
        }

    s = get_source(source)
    result = s.fetch(FetchRequest(source=source, market=market))
    save_cache(source, market, result.payload)

    return {
        "source": source,
        "market": market,
        "cached": False,
        "payload": result.payload,
    }


@app.get("/football/demo_match")
def football_demo_match() -> dict:
    """Return aggregated football features for demo_match (deterministic, mock providers)."""
    return build_features_payload(
        "demo_match", stats_provider, odds_provider, last_n=6, h2h_n=6
    )


@app.post("/football/features")
def football_features(req: dict) -> dict:
    """Build and return football features for the given match_id. Uses mock providers."""
    match_id = (req.get("match_id") or "").strip()
    if not match_id:
        return {"error": "missing_match_id"}
    return build_features_payload(
        match_id, stats_provider, odds_provider, last_n=6, h2h_n=6
    )


@app.post("/football/find_match")
def find_match(req: dict) -> dict:
    """Find a match by team names query (e.g. 'Arsenal Chelsea'). Returns match or error."""
    query = req.get("query") or ""
    fixtures = get_mock_fixtures()
    match = find_match_by_teams(query, fixtures)
    if not match:
        return {"error": "match_not_found"}
    return match.__dict__


@app.post("/football/team_matches")
def team_matches(req: dict) -> dict:
    """Return all fixtures matching a team name (e.g. 'Barcelona')."""
    team = req.get("team") or ""
    fixtures = get_mock_fixtures()
    matches = find_matches_by_team(team, fixtures)
    return {"matches": [m.__dict__ for m in matches]}


@app.post("/football/analyze_match")
def analyze_match(req: dict) -> dict:
    """Run full pipeline for a match query and return match + analysis. Uses mock fixtures and configured providers."""
    query = req.get("query") or ""
    fixtures = get_mock_fixtures()
    match = find_match_by_teams(query, fixtures)
    if not match:
        return {"error": "match_not_found"}
    payload = build_features_payload(
        match.match_id, stats_provider, odds_provider, last_n=6, h2h_n=6
    )
    return {
        "match": match.__dict__,
        "analysis": payload,
    }

