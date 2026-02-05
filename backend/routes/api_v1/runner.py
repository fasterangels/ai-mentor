"""POST /api/v1/runner/shadow/run — run shadow batch (read-only; no policy apply)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from runner.shadow_runner import run_shadow_batch

router = APIRouter(prefix="/runner", tags=["runner"])


@router.post(
    "/shadow/run",
    summary="Run shadow batch",
    response_description="BatchReport (run_meta, per_match, aggregates, checksums, failures). Does NOT apply policy.",
)
async def shadow_batch_run(
    body: dict,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Run shadow pipeline in batch for the given connector and match list.
    Body: connector_name (default dummy), match_ids (optional list).
    If match_ids omitted, uses all cached matches for the connector.
    Returns BatchReport. No side effects beyond existing shadow pipeline persistence.
    """
    connector_name = (body.get("connector_name") or "dummy").strip()
    match_ids = body.get("match_ids")
    if match_ids is not None and not isinstance(match_ids, list):
        match_ids = [str(m) for m in match_ids] if match_ids else None
    elif match_ids is not None:
        match_ids = [str(m).strip() for m in match_ids if str(m).strip()]
    dry_run = bool(body.get("dry_run", False))

    report = await run_shadow_batch(
        session,
        connector_name=connector_name,
        match_ids=match_ids,
        dry_run=dry_run,
    )
    await session.commit()
    return report
