"""Repository for InjuryNewsReport: upsert by content_checksum+adapter_key, list by team."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.injury_news_report import InjuryNewsReport
from .base import BaseRepository

# Bounded excerpt length for body_excerpt (provenance/safety)
BODY_EXCERPT_MAX_LENGTH = 2000


def _truncate_excerpt(text: Optional[str]) -> Optional[str]:
    """Truncate body excerpt to safe length."""
    if text is None:
        return None
    if len(text) <= BODY_EXCERPT_MAX_LENGTH:
        return text
    return text[: BODY_EXCERPT_MAX_LENGTH - 3] + "..."


class InjuryNewsReportRepository(BaseRepository[InjuryNewsReport]):
    """Repository for injury/news reports with dedupe by content_checksum + adapter_key."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, report_id: str) -> Optional[InjuryNewsReport]:
        return await super().get_by_id(InjuryNewsReport, report_id)

    async def find_by_content_checksum_and_adapter(
        self, content_checksum: str, adapter_key: str
    ) -> Optional[InjuryNewsReport]:
        """Find existing report by content_checksum + adapter_key (for dedupe)."""
        stmt = select(InjuryNewsReport).where(
            InjuryNewsReport.content_checksum == content_checksum,
            InjuryNewsReport.adapter_key == adapter_key,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert_report(
        self,
        report_id: str,
        adapter_key: str,
        artifact_path: str,
        artifact_checksum: str,
        content_checksum: str,
        recorded_at: datetime,
        created_at: datetime,
        source_ref: Optional[str] = None,
        published_at: Optional[datetime] = None,
        title: Optional[str] = None,
        body_excerpt: Optional[str] = None,
    ) -> InjuryNewsReport:
        """
        Insert or update report. Dedupe: same content_checksum + adapter_key updates existing.
        artifact_checksum and content_checksum are required (provenance).
        body_excerpt is truncated to BODY_EXCERPT_MAX_LENGTH.
        """
        excerpt = _truncate_excerpt(body_excerpt)
        existing = await self.find_by_content_checksum_and_adapter(
            content_checksum, adapter_key
        )
        if existing:
            existing.artifact_path = artifact_path
            existing.artifact_checksum = artifact_checksum
            existing.source_ref = source_ref
            existing.published_at = published_at
            existing.recorded_at = recorded_at
            existing.title = title
            existing.body_excerpt = excerpt
            existing.content_checksum = content_checksum
            self.session.add(existing)
            return existing
        report = InjuryNewsReport(
            report_id=report_id,
            adapter_key=adapter_key,
            artifact_path=artifact_path,
            artifact_checksum=artifact_checksum,
            content_checksum=content_checksum,
            recorded_at=recorded_at,
            created_at=created_at,
            source_ref=source_ref,
            published_at=published_at,
            title=title,
            body_excerpt=excerpt,
        )
        await self.add(report)
        return report

    async def list_reports_by_team(
        self,
        team_ref: str,
        since_ts: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[InjuryNewsReport]:
        """
        List reports that have at least one claim for team_ref.
        Uses injury_news_claims join; ordered by recorded_at desc.
        """
        from models.injury_news_claim import InjuryNewsClaim

        stmt = (
            select(InjuryNewsReport)
            .join(InjuryNewsClaim, InjuryNewsClaim.report_id == InjuryNewsReport.report_id)
            .where(InjuryNewsClaim.team_ref == team_ref)
            .order_by(InjuryNewsReport.recorded_at.desc())
            .limit(limit)
        )
        if since_ts is not None:
            stmt = stmt.where(InjuryNewsReport.recorded_at >= since_ts)
        result = await self.session.execute(stmt)
        seen: set[str] = set()
        reports: List[InjuryNewsReport] = []
        for row in result.scalars().all():
            if row.report_id not in seen:
                seen.add(row.report_id)
                reports.append(row)
        return reports
