"""Injury/news claim: extracted claim from a report (team/player, status, validity)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class InjuryNewsClaim(Base):
    """One claim extracted from an injury/news report."""

    __tablename__ = "injury_news_claims"

    claim_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("injury_news_reports.report_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_ref: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    player_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)  # INJURY_STATUS, SUSPENSION, RETURN
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # OUT, DOUBTFUL, FIT, SUSPENDED, UNKNOWN
    validity: Mapped[str] = mapped_column(String(50), nullable=False)  # NEXT_MATCH, DATE, RANGE, UNKNOWN
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_ptr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON or excerpt keys
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
