"""Snapshot resolution: final result and market outcomes for an analysis run (snapshot)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SnapshotResolution(Base):
    """
    Final result and per-market outcomes for one snapshot (analysis run).

    Each snapshot is resolvable with final score + per-market outcomes.
    reason_codes_by_market stores string[] per market for attribution.
    """

    __tablename__ = "snapshot_resolutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # final_result
    home_goals: Mapped[int] = mapped_column(Integer, nullable=False)
    away_goals: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # FINAL | ABANDONED | POSTPONED | UNKNOWN
    resolved_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # market_outcomes: SUCCESS | FAILURE | NEUTRAL | UNRESOLVED per market
    market_outcomes_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # {"one_x_two": "...", "over_under_25": "...", "gg_ng": "..."}

    # reason_codes_by_market: list of reason codes per market (for attribution)
    reason_codes_by_market_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # {"one_x_two": ["code1"], "over_under_25": [], "gg_ng": []}
