from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TeamAlias(Base):
    """Alternate names for teams from different sources/languages."""

    __tablename__ = "team_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_norm: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="und")
    quality: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    team = relationship("Team")

    __table_args__ = (
        Index("ix_team_alias_alias_norm", "alias_norm"),
    )

