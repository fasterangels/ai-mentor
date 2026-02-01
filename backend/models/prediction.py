from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Prediction(Base):
    """Canonical prediction record produced by an analysis run."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=False, index=True
    )
    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.id"), nullable=False
    )
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    pick: Mapped[str] = mapped_column(String(50), nullable=True)

    probabilities_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # TODO: Use JSON type when supported.
    separation: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk: Mapped[float] = mapped_column(Float, nullable=False)
    reasons_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # TODO: Use JSON type when supported.
    evidence_pack_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # TODO: Use JSON type when supported.

    __table_args__ = (
        Index(
            "ix_prediction_match_market_created",
            "match_id",
            "market",
            "created_at_utc",
        ),
    )

