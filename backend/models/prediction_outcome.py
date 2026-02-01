from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PredictionOutcome(Base):
    """Evaluation of a prediction against final match results."""

    __tablename__ = "prediction_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id"), nullable=False, index=True
    )
    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.id"), nullable=False, index=True
    )
    evaluated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    final_home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    final_away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    final_result_1x2: Mapped[str] = mapped_column(String(3), nullable=False)
    final_ou25: Mapped[str] = mapped_column(String(10), nullable=False)
    final_ggng: Mapped[str] = mapped_column(String(10), nullable=False)
    hit_bool: Mapped[bool] = mapped_column(Boolean, nullable=False)

