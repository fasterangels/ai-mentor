"""
Build EvidencePack from IngestedMatchData for use in shadow pipeline.
Deterministic: same fixture -> same EvidencePack shape; no randomness.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from pipeline.types import DomainData, EvidencePack, QualityReport

from ingestion.connectors.platform_base import IngestedMatchData


def _deterministic_stats_from_fixture(match_id: str, home_team: str, away_team: str) -> Dict[str, Any]:
    """Produce deterministic stats domain data from fixture (no live fetch)."""
    # Use match_id hash-like behavior for stable but varied numbers
    seed = sum(ord(c) for c in match_id) % 1000
    return {
        "match_id": match_id,
        "home_team_stats": {
            "goals_scored": 1.5 + (seed % 10) / 10,
            "goals_conceded": 1.2 + ((seed + 1) % 10) / 10,
            "shots_per_game": 11.0 + (seed % 5),
            "possession_avg": 50.0 + (seed % 10),
        },
        "away_team_stats": {
            "goals_scored": 1.3 + ((seed + 2) % 10) / 10,
            "goals_conceded": 1.4 + ((seed + 3) % 10) / 10,
            "shots_per_game": 10.0 + ((seed + 1) % 5),
            "possession_avg": 50.0 - (seed % 10),
        },
        "head_to_head": {
            "matches_played": 5 + (seed % 5),
            "home_wins": 2 + (seed % 2),
            "away_wins": 1 + ((seed + 1) % 2),
            "draws": 1,
        },
    }


def ingested_to_evidence_pack(
    ingested: IngestedMatchData,
    captured_at_utc: datetime | None = None,
) -> EvidencePack:
    """
    Convert IngestedMatchData to EvidencePack (fixtures + stats domains).
    Odds map: ingested.odds_1x2 home/draw/away -> internal 1X2 as-is.
    Timestamps: use provided captured_at_utc or now(UTC).
    """
    if captured_at_utc is None:
        captured_at_utc = datetime.now(timezone.utc)

    fixtures_data: Dict[str, Any] = {
        "match_id": ingested.match_id,
        "home_team": ingested.home_team,
        "away_team": ingested.away_team,
        "kickoff_utc": ingested.kickoff_utc,
        "competition": ingested.competition,
        "status": ingested.status,
        "odds_1x2": dict(ingested.odds_1x2),
    }

    stats_data = _deterministic_stats_from_fixture(
        ingested.match_id, ingested.home_team, ingested.away_team
    )

    return EvidencePack(
        match_id=ingested.match_id,
        domains={
            "fixtures": DomainData(
                data=fixtures_data,
                quality=QualityReport(passed=True, score=1.0, flags=[]),
                sources=["sample_platform"],
            ),
            "stats": DomainData(
                data=stats_data,
                quality=QualityReport(passed=True, score=1.0, flags=[]),
                sources=["sample_platform"],
            ),
        },
        captured_at_utc=captured_at_utc,
        flags=[],
    )
