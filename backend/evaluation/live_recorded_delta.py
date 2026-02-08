"""
Live vs Recorded Delta Evaluation (G3): measure timing deltas between LIVE_SHADOW and RECORDED snapshots.
Measurement-only; no analysis, no decisions. Deterministic.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pipeline.snapshot_envelope import _parse_iso, parse_payload_json
from sqlalchemy.ext.asyncio import AsyncSession

from models.raw_payload import RawPayload
from repositories.raw_payload_repo import RawPayloadRepository


# Status when one side is missing
STATUS_INCOMPLETE = "INCOMPLETE"
STATUS_COMPLETE = "COMPLETE"


@dataclass
class SnapshotMeta:
    """Parsed envelope metadata for delta computation."""
    snapshot_id: str
    snapshot_type: str
    observed_at_utc: str
    payload_checksum: str
    envelope_checksum: Optional[str]
    latency_ms: Optional[float]
    source_name: str
    row_id: int


def _meta_from_row(row: RawPayload) -> Tuple[Optional[SnapshotMeta], Optional[str]]:
    """
    Parse row.payload_json; return (SnapshotMeta, fixture_id) or (None, None) on parse failure.
    fixture_id: for recorded (pipeline_cache) use row.related_match_id; for live_shadow from payload.
    """
    meta_dict, payload = parse_payload_json(row.payload_json, created_at_utc_fallback=row.fetched_at_utc)
    observed = meta_dict.get("observed_at_utc") or meta_dict.get("observed_at") or ""
    if not observed:
        return None, None
    snapshot_meta = SnapshotMeta(
        snapshot_id=meta_dict.get("snapshot_id") or meta_dict.get("payload_checksum") or meta_dict.get("checksum") or "",
        snapshot_type=meta_dict.get("snapshot_type", "recorded"),
        observed_at_utc=observed,
        payload_checksum=meta_dict.get("payload_checksum") or meta_dict.get("checksum") or "",
        envelope_checksum=meta_dict.get("envelope_checksum"),
        latency_ms=meta_dict.get("latency_ms"),
        source_name=meta_dict.get("source", {}).get("name", "") if isinstance(meta_dict.get("source"), dict) else "",
        row_id=row.id,
    )
    # fixture_id: recorded has related_match_id; live_shadow has it in payload
    if row.related_match_id:
        return snapshot_meta, row.related_match_id
    if isinstance(payload, dict):
        fid = payload.get("fixture_id") or payload.get("match_id") or payload.get("id")
        if fid is not None:
            return snapshot_meta, str(fid)
    return snapshot_meta, None


def _observed_at_key(observed_at_utc: str) -> datetime:
    """Sort key for observed_at_utc (ISO string)."""
    dt = _parse_iso(observed_at_utc)
    return dt or datetime.min.replace(tzinfo=timezone.utc)


@dataclass
class DeltaReport:
    """Per-fixture delta metrics. No good/bad judgment."""
    fixture_id: str
    status: str  # COMPLETE | INCOMPLETE
    recorded_snapshot_id: Optional[str] = None
    live_snapshot_id: Optional[str] = None
    observed_at_delta_ms: Optional[float] = None  # live.observed_at - recorded.observed_at
    fetch_latency_delta_ms: Optional[float] = None  # live.latency_ms - recorded.latency_ms (if both exist)
    payload_match: Optional[bool] = None  # live.payload_checksum == recorded.payload_checksum
    envelope_match: Optional[bool] = None  # live.envelope_checksum == recorded.envelope_checksum
    computed_at_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "fixture_id": self.fixture_id,
            "status": self.status,
            "computed_at_utc": self.computed_at_utc,
        }
        if self.recorded_snapshot_id is not None:
            d["recorded_snapshot_id"] = self.recorded_snapshot_id
        if self.live_snapshot_id is not None:
            d["live_snapshot_id"] = self.live_snapshot_id
        if self.observed_at_delta_ms is not None:
            d["observed_at_delta_ms"] = round(self.observed_at_delta_ms, 2)
        if self.fetch_latency_delta_ms is not None:
            d["fetch_latency_delta_ms"] = round(self.fetch_latency_delta_ms, 2)
        if self.payload_match is not None:
            d["payload_match"] = self.payload_match
        if self.envelope_match is not None:
            d["envelope_match"] = self.envelope_match
        return d


def _compute_delta(
    fixture_id: str,
    recorded: Optional[SnapshotMeta],
    live: Optional[SnapshotMeta],
    computed_at: datetime,
) -> DeltaReport:
    """Build DeltaReport from latest recorded and live meta. No judgment."""
    computed_str = computed_at.isoformat()
    if recorded is None or live is None:
        return DeltaReport(
            fixture_id=fixture_id,
            status=STATUS_INCOMPLETE,
            recorded_snapshot_id=recorded.snapshot_id if recorded else None,
            live_snapshot_id=live.snapshot_id if live else None,
            computed_at_utc=computed_str,
        )
    # observed_at_delta_ms = live.observed_at - recorded.observed_at (ms)
    rec_dt = _parse_iso(recorded.observed_at_utc)
    live_dt = _parse_iso(live.observed_at_utc)
    observed_delta_ms: Optional[float] = None
    if rec_dt and live_dt:
        observed_delta_ms = (live_dt - rec_dt).total_seconds() * 1000
    # fetch_latency_delta_ms
    latency_delta_ms: Optional[float] = None
    if recorded.latency_ms is not None and live.latency_ms is not None:
        latency_delta_ms = live.latency_ms - recorded.latency_ms
    return DeltaReport(
        fixture_id=fixture_id,
        status=STATUS_COMPLETE,
        recorded_snapshot_id=recorded.snapshot_id,
        live_snapshot_id=live.snapshot_id,
        observed_at_delta_ms=observed_delta_ms,
        fetch_latency_delta_ms=latency_delta_ms,
        payload_match=(recorded.payload_checksum == live.payload_checksum) if (recorded.payload_checksum and live.payload_checksum) else None,
        envelope_match=(recorded.envelope_checksum == live.envelope_checksum) if (recorded.envelope_checksum and live.envelope_checksum) else None,
        computed_at_utc=computed_str,
    )


async def load_snapshots_by_fixture(
    session: AsyncSession,
) -> Tuple[Dict[str, SnapshotMeta], Dict[str, SnapshotMeta]]:
    """
    Load latest recorded and latest live_shadow snapshot per fixture_id.
    Returns (recorded_by_fixture, live_by_fixture). Each value is the latest by observed_at_utc.
    """
    repo = RawPayloadRepository(session)
    recorded_by: Dict[str, SnapshotMeta] = {}
    for row in await repo.list_rows_by_source("pipeline_cache"):
        meta, fixture_id = _meta_from_row(row)
        if meta and fixture_id:
            existing = recorded_by.get(fixture_id)
            if existing is None or _observed_at_key(meta.observed_at_utc) > _observed_at_key(existing.observed_at_utc):
                recorded_by[fixture_id] = meta
    live_by: Dict[str, SnapshotMeta] = {}
    for row in await repo.list_rows_by_source("live_shadow"):
        meta, fixture_id = _meta_from_row(row)
        if meta and fixture_id:
            existing = live_by.get(fixture_id)
            if existing is None or _observed_at_key(meta.observed_at_utc) > _observed_at_key(existing.observed_at_utc):
                live_by[fixture_id] = meta
    return recorded_by, live_by


async def run_delta_evaluation(
    session: AsyncSession,
    reports_dir: str | Path = "reports",
    index_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Run delta evaluation: match recorded vs live_shadow per fixture, compute metrics, write report.
    Returns summary: reports_written, incomplete_count, complete_count, run_id.
    """
    from ops.ops_events import (
        log_delta_eval_end,
        log_delta_eval_incomplete,
        log_delta_eval_start,
        log_delta_eval_written,
    )
    from reports.index_store import load_index, save_index

    t_start = log_delta_eval_start()
    recorded_by, live_by = await load_snapshots_by_fixture(session)
    all_fixture_ids = sorted(set(recorded_by.keys()) | set(live_by.keys()))
    computed_at = datetime.now(timezone.utc)
    reports: List[DeltaReport] = []
    incomplete_count = 0
    for fid in all_fixture_ids:
        rec = recorded_by.get(fid)
        live = live_by.get(fid)
        if rec is None or live is None:
            incomplete_count += 1
            log_delta_eval_incomplete(fid, "recorded" if rec else "live_shadow")
        reports.append(_compute_delta(fid, rec, live, computed_at))
    complete_count = len(reports) - incomplete_count

    reports_path = Path(reports_dir) / "delta_eval"
    reports_path.mkdir(parents=True, exist_ok=True)
    run_id = f"delta_eval_{computed_at.strftime('%Y%m%d_%H%M%S')}"
    report_file = reports_path / f"{run_id}.json"
    report_data = {
        "run_id": run_id,
        "computed_at_utc": computed_at.isoformat(),
        "reports": [r.to_dict() for r in reports],
        "summary": {"complete": complete_count, "incomplete": incomplete_count, "total": len(reports)},
    }
    report_file.write_text(json.dumps(report_data, sort_keys=True, indent=2, default=str), encoding="utf-8")
    log_delta_eval_written(len(reports))

    index_path = index_path or Path(reports_dir) / "index.json"
    index = load_index(index_path)
    delta_runs = index.get("delta_eval_runs") or []
    delta_runs.append({
        "run_id": run_id,
        "created_at_utc": computed_at.isoformat(),
        "reports_count": len(reports),
        "complete_count": complete_count,
        "incomplete_count": incomplete_count,
    })
    index["delta_eval_runs"] = delta_runs
    index["latest_delta_eval_run_id"] = run_id
    save_index(index, index_path)

    log_delta_eval_end(len(reports), complete_count, incomplete_count, time.perf_counter() - t_start)
    return {
        "reports_written": len(reports),
        "incomplete_count": incomplete_count,
        "complete_count": complete_count,
        "run_id": run_id,
        "report_path": str(report_file),
    }
