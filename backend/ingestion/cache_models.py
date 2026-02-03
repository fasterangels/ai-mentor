"""
DB model for ingested match cache (offline-first, one row per match per connector).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class IngestedMatchCache(Base):
    """Cached IngestedMatchData per match_id (latest write wins per match)."""

    __tablename__ = "ingested_match_cache"

    match_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    collected_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
