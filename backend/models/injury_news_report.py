"""Injury/news report: normalized storage with full provenance and checksums."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class InjuryNewsReport(Base):
    """One ingested injury/news report from an adapter (artifact + content checksums)."""

    __tablename__ = "injury_news_reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    adapter_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    artifact_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("ix_injury_news_reports_adapter_recorded", "adapter_key", "recorded_at"),
        Index(
            "ix_injury_news_reports_content_checksum_uniq",
            "content_checksum",
            "adapter_key",
            unique=True,
        ),
    )
