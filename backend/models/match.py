from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Match(Base):
    """Canonical match between two teams."""

    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id"), nullable=False
    )
    season_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("seasons.id"), nullable=True
    )
    kickoff_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    home_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )
    away_team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )

    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_match_competition_kickoff", "competition_id", "kickoff_utc"),
        Index(
            "ix_match_teams_kickoff",
            "home_team_id",
            "away_team_id",
            "kickoff_utc",
        ),
    )

