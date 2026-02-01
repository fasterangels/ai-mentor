from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SourceEntityMap(Base):
    """Mapping between external source entity IDs and canonical entities."""

    __tablename__ = "source_entity_maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

