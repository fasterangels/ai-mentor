"""Injury/news resolution: resolved status for a fixture/team/player with policy version."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class InjuryNewsResolution(Base):
    """Resolved injury/news status for a fixture/team/player (policy version + claim refs)."""

    __tablename__ = "injury_news_resolutions"

    resolution_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    fixture_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    team_ref: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    player_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    resolved_status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # AVAILABLE, QUESTIONABLE, OUT, SUSPENDED, UNKNOWN
    resolution_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    resolution_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # LATEST_WINS, PRIORITY_OVERRIDE, CONSENSUS, UNRESOLVED_CONFLICT
    winning_claim_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    supporting_claim_ids: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON list, default "[]"
    conflicting_claim_ids: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON list, default "[]"
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("ix_injury_news_resolutions_fixture_team", "fixture_id", "team_ref"),
        Index("ix_injury_news_resolutions_team_player", "team_ref", "player_ref"),
    )
