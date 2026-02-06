"""
Recorded evidence ingestion: parse JSON, upsert to evidence_items_v1, emit ops events.
Offline-only; no live IO. Does not affect analysis/decision outputs.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.evidence_schema import parse_recorded_evidence_payload
from ops.ops_events import log_evidence_ingestion_end, log_evidence_ingestion_start
from repositories.evidence_repo import EvidenceRepository


async def ingest_evidence_for_fixture(
    session: AsyncSession,
    fixture_id: str,
    payload: Dict[str, Any] | List[Dict[str, Any]] | None = None,
    file_path: Path | None = None,
    created_at: datetime | None = None,
) -> Dict[str, Any]:
    """
    Ingest evidence items for one fixture from a payload dict or a JSON file.
    payload: either { "fixture_id": "...", "items": [ ... ] } or a list of item dicts (fixture_id used).
    file_path: if set, read JSON from file (must contain fixture_id and items).
    Returns summary: items_written, deduped, conflict_detected, errors (list).
    """
    if file_path is not None:
        text = file_path.read_text(encoding="utf-8")
        payload = json.loads(text)
    if payload is None:
        return {"items_written": 0, "deduped": 0, "conflict_detected": 0, "errors": ["no payload or file_path"]}

    if isinstance(payload, list):
        payload = {"fixture_id": fixture_id, "items": payload}

    try:
        items = parse_recorded_evidence_payload(payload, created_at=created_at)
    except ValueError as e:
        return {"items_written": 0, "deduped": 0, "conflict_detected": 0, "errors": [str(e)]}

    if not items:
        return {"items_written": 0, "deduped": 0, "conflict_detected": 0, "errors": []}

    t_start = log_evidence_ingestion_start(fixture_id, len(items))
    repo = EvidenceRepository(session)
    items_written = 0
    deduped = 0
    conflict_detected = 0
    errors: List[str] = []

    for item in items:
        try:
            _, outcome = await repo.upsert_evidence_item(item)
            if outcome == "inserted":
                items_written += 1
            elif outcome == "deduped":
                deduped += 1
            elif outcome == "updated":
                items_written += 1
                conflict_detected += 1
        except Exception as e:
            errors.append(f"{item.evidence_id}: {e}")

    duration = time.perf_counter() - t_start
    log_evidence_ingestion_end(fixture_id, duration, items_written, deduped, conflict_detected)

    return {
        "items_written": items_written,
        "deduped": deduped,
        "conflict_detected": conflict_detected,
        "errors": errors,
    }
