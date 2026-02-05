"""Repository for InjuryNewsResolution: save batch, list by fixture or team."""

from __future__ import annotations

import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.injury_news_resolution import InjuryNewsResolution
from .base import BaseRepository


def _json_list(value: List) -> str:
    """Serialize list to JSON string; default []."""
    if not value:
        return "[]"
    return json.dumps(value)


class InjuryNewsResolutionRepository(BaseRepository[InjuryNewsResolution]):
    """Repository for injury/news resolutions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def save_resolutions(
        self,
        batch: List[dict],
    ) -> List[InjuryNewsResolution]:
        """Insert a batch of resolutions. Each dict has resolution fields."""
        entities: List[InjuryNewsResolution] = []
        for r in batch:
            res = InjuryNewsResolution(
                fixture_id=r.get("fixture_id"),
                team_ref=r["team_ref"],
                player_ref=r.get("player_ref"),
                resolved_status=r["resolved_status"],
                resolution_confidence=float(r["resolution_confidence"]),
                resolution_method=r["resolution_method"],
                winning_claim_id=r.get("winning_claim_id"),
                supporting_claim_ids=_json_list(r.get("supporting_claim_ids") or []),
                conflicting_claim_ids=_json_list(r.get("conflicting_claim_ids") or []),
                policy_version=r["policy_version"],
                created_at=r["created_at"],
            )
            await self.add(res)
            entities.append(res)
        return entities

    async def list_resolutions(
        self,
        fixture_id: Optional[str] = None,
        team_ref: Optional[str] = None,
        limit: int = 500,
    ) -> List[InjuryNewsResolution]:
        """List resolutions by fixture_id and/or team_ref."""
        stmt = select(InjuryNewsResolution).order_by(
            InjuryNewsResolution.created_at.desc()
        ).limit(limit)
        if fixture_id is not None:
            stmt = stmt.where(InjuryNewsResolution.fixture_id == fixture_id)
        if team_ref is not None:
            stmt = stmt.where(InjuryNewsResolution.team_ref == team_ref)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
