"""Data source abstractions for the pipeline."""

from .base import BaseSource, Source, SourceRegistry
from .registry import fetch, get_registry
from .stub_fixtures import StubFixturesSource
from .stub_stats import StubStatsSource

_reg = get_registry()
_reg.register(StubFixturesSource())
_reg.register(StubStatsSource())

__all__ = [
    "BaseSource",
    "Source",
    "SourceRegistry",
    "StubFixturesSource",
    "StubStatsSource",
    "fetch",
    "get_registry",
]
