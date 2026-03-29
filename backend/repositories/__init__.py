"""Repository layer for DB access only (CRUD + simple queries).

This package provides repositories that operate on canonical models from
backend/models/. Repositories are pure DB access - no business logic.

All repositories accept AsyncSession explicitly and use the existing
DatabaseManager from core/database.py (no new engines created).
"""

from .base import BaseRepository
from .competition_repo import CompetitionRepository
from .season_repo import SeasonRepository
from .team_repo import TeamRepository
from .match_repo import MatchRepository
from .standings_repo import StandingsRepository
from .source_mapping_repo import SourceMappingRepository
from .fetch_log_repo import FetchLogRepository
from .raw_payload_repo import RawPayloadRepository
from .analysis_run_repo import AnalysisRunRepository
from .prediction_repo import PredictionRepository
from .prediction_outcome_repo import PredictionOutcomeRepository
from .snapshot_resolution_repo import SnapshotResolutionRepository
from .evidence_repo import EvidenceRepository

__all__ = [
    "BaseRepository",
    "CompetitionRepository",
    "SeasonRepository",
    "TeamRepository",
    "MatchRepository",
    "StandingsRepository",
    "SourceMappingRepository",
    "FetchLogRepository",
    "RawPayloadRepository",
    "AnalysisRunRepository",
    "PredictionRepository",
    "PredictionOutcomeRepository",
    "SnapshotResolutionRepository",
    "EvidenceRepository",
]
