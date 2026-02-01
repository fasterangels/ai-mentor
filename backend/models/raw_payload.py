from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RawPayload(Base):
    """Raw JSON/text payloads from external sources for reproducibility and debugging."""

    __tablename__ = "raw_payloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # TODO: Use proper JSON type when migrating off SQLite.
    related_match_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("matches.id"), nullable=True, index=True
    )

