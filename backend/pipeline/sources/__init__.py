"""Data source abstractions for the pipeline."""

from .base import BaseSource, Source, SourceRegistry
from .registry import fetch, get_registry
from .stub_fixtures import StubFixturesSource
from .stub_stats import StubStatsSource
from .football_data_api import FootballDataAPISource
from .odds_api_source import OddsAPISource
from .injuries_lineups_source import InjuriesLineupsSource

_reg = get_registry()
_reg.register(StubFixturesSource())
_reg.register(StubStatsSource())
_reg.register(FootballDataAPISource())
_reg.register(OddsAPISource())
_reg.register(InjuriesLineupsSource())

__all__ = [
    "BaseSource",
    "Source",
    "SourceRegistry",
    "StubFixturesSource",
    "StubStatsSource",
    "FootballDataAPISource",
    "OddsAPISource",
    "InjuriesLineupsSource",
    "fetch",
    "get_registry",
]

