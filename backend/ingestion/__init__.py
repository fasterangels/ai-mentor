"""Ingestion: normalized schema and data connectors (Phase 2)."""

from .schema import (
    IngestedMatchData,
    MatchIdentity,
    MatchState,
    OddsSnapshot,
)

__all__ = [
    "IngestedMatchData",
    "MatchIdentity",
    "MatchState",
    "OddsSnapshot",
]
