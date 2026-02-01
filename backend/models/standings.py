from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class StandingsSnapshot(Base):
    """Snapshot of league standings at a specific time from a given source."""

    __tablename__ = "standings_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id"), nullable=False
    )
    season_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("seasons.id"), nullable=True
    )
    captured_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class StandingsRow(Base):
    """One row in a standings snapshot for a specific team."""

    __tablename__ = "standings_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("standings_snapshots.id"), nullable=False, index=True
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id"), nullable=False, index=True
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False)
    played: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, nullable=False)

    gf: Mapped[int] = mapped_column(Integer, nullable=False)
    ga: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)

