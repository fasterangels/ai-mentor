"""
Evidence items v1: injuries, suspensions, team news, disruptions.
Offline-first; schema + storage only; no decision logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EvidenceItemV1(Base):
    """Stored evidence item (injuries, news, etc.). Table: evidence_items_v1."""

    __tablename__ = "evidence_items_v1"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fixture_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    team_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    player_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_class: Mapped[str] = mapped_column(String(32), nullable=False)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    reliability_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    effective_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expected_valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    conflict_group_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_evidence_items_v1_fixture_observed", "fixture_id", "observed_at"),
    )
