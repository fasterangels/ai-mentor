from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AnalysisRun(Base):
    """Top-level record for one analysis execution."""

    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    logic_version: Mapped[str] = mapped_column(String(50), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    match_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("matches.id"), nullable=True, index=True
    )
    data_quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    flags_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # TODO: Use JSON type when supported.

