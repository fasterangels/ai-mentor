"""Snapshot resolution: final score + market outcomes for an analysis run."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SnapshotResolution(Base):
    """Resolution of one analysis snapshot: final score and per-market outcomes."""

    __tablename__ = "snapshot_resolutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[str] = mapped_column(nullable=False, index=True)
    final_home_goals: Mapped[int] = mapped_column(Integer, nullable=False)
    final_away_goals: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)  # e.g. FINAL
    market_outcomes_json: Mapped[str] = mapped_column(Text, nullable=False)  # {"one_x_two":"SUCCESS",...}
    reason_codes_by_market_json: Mapped[str] = mapped_column(Text, nullable=False)  # {"one_x_two":["..."],...}
