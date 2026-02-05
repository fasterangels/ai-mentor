"""Repository for InjuryNewsClaim: add claims for a report, list by team/player/since."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.injury_news_claim import InjuryNewsClaim
from .base import BaseRepository


class InjuryNewsClaimRepository(BaseRepository[InjuryNewsClaim]):
    """Repository for injury/news claims."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def add_claims(
        self,
        report_id: str,
        claims: List[dict],
        created_at: datetime,
    ) -> List[InjuryNewsClaim]:
        """Insert multiple claims for a report. Each dict must have required claim fields."""
        entities: List[InjuryNewsClaim] = []
        for c in claims:
            claim = InjuryNewsClaim(
                report_id=report_id,
                team_ref=c["team_ref"],
                player_ref=c.get("player_ref"),
                claim_type=c["claim_type"],
                status=c["status"],
                validity=c["validity"],
                valid_from=c.get("valid_from"),
                valid_to=c.get("valid_to"),
                confidence=float(c["confidence"]),
                evidence_ptr=c.get("evidence_ptr"),
                created_at=created_at,
            )
            await self.add(claim)
            entities.append(claim)
        return entities

    async def list_claims(
        self,
        team_ref: str,
        player_ref: Optional[str] = None,
        since_ts: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[InjuryNewsClaim]:
        """List claims for team (and optionally player), optionally since timestamp."""
        stmt = (
            select(InjuryNewsClaim)
            .where(InjuryNewsClaim.team_ref == team_ref)
            .order_by(InjuryNewsClaim.created_at.desc())
            .limit(limit)
        )
        if player_ref is not None:
            stmt = stmt.where(InjuryNewsClaim.player_ref == player_ref)
        if since_ts is not None:
            stmt = stmt.where(InjuryNewsClaim.created_at >= since_ts)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_claims_by_report_id(self, report_id: str) -> List[InjuryNewsClaim]:
        """List all claims for a report."""
        stmt = (
            select(InjuryNewsClaim)
            .where(InjuryNewsClaim.report_id == report_id)
            .order_by(InjuryNewsClaim.claim_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
