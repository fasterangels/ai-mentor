"""Canonical SQLAlchemy models for the offline-first football analyzer.

NOTE:
- This package is intentionally separate from the legacy ``models.py`` module in
  the backend root. It defines the canonical schema only and does not wire any
  business logic.
- TODO: Decide on the final import path and integration strategy to avoid
  ambiguity between ``models.py`` and this ``models`` package.
"""

from .base import Base
from .analysis_run import AnalysisRun
from .competition import Competition
from .snapshot_resolution import SnapshotResolution
from .fetch_log import SourceFetchLog
from .injury_news_claim import InjuryNewsClaim
from .injury_news_report import InjuryNewsReport
from .injury_news_resolution import InjuryNewsResolution
from .match import Match
from .prediction import Prediction
from .prediction_outcome import PredictionOutcome
from .raw_payload import RawPayload
from .season import Season
from .source_mapping import SourceEntityMap
from .standings import StandingsRow, StandingsSnapshot
from .team import Team
from .team_alias import TeamAlias
from .team_match_result import TeamMatchResult

__all__ = [
    "Base",
    "AnalysisRun",
    "Competition",
    "SnapshotResolution",
    "SourceFetchLog",
    "InjuryNewsClaim",
    "InjuryNewsReport",
    "InjuryNewsResolution",
    "Match",
    "Prediction",
    "PredictionOutcome",
    "RawPayload",
    "Season",
    "SourceEntityMap",
    "StandingsRow",
    "StandingsSnapshot",
    "Team",
    "TeamAlias",
    "TeamMatchResult",
]

