"""
Staleness metrics per reason (G4): measure how reason effectiveness varies by evidence age.
Measurement-only; no decay, no policy changes. Deterministic.
Evidence age is a provisional proxy: decision_time_utc - snapshot.observed_at_utc (snapshot-level).
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.age_bands import assign_age_band
from pipeline.snapshot_envelope import _parse_iso, parse_payload_json

from models.raw_payload import RawPayload
from repositories.analysis_run_repo import AnalysisRunRepository
from repositories.prediction_repo import PredictionRepository
from repositories.raw_payload_repo import RawPayloadRepository
from repositories.snapshot_resolution_repo import SnapshotResolutionRepository

MARKETS = ("one_x_two", "over_under_25", "gg_ng")
KEY_MAP = {"1X2": "one_x_two", "OU25": "over_under_25", "OU_2.5": "over_under_25", "GGNG": "gg_ng", "BTTS": "gg_ng"}


def _observed_at_from_row(row: RawPayload) -> Optional[str]:
    """Parse payload_json envelope; return observed_at_utc or effective_from_utc. Provisional proxy."""
    meta_dict, _ = parse_payload_json(row.payload_json, created_at_utc_fallback=row.fetched_at_utc)
    observed = meta_dict.get("observed_at_utc") or meta_dict.get("observed_at")
    if observed:
        return observed
    return meta_dict.get("effective_from_utc")


async def _evidence_observed_at_utc_for_run(
    session: AsyncSession,
    match_id: Optional[str],
    decision_time_utc: datetime,
) -> Tuple[Optional[str], bool]:
    """
    Get the evidence timestamp used for this decision (provisional proxy).
    Returns (observed_at_utc_str or None, missing_ts_flag).
    Uses latest pipeline_cache payload for match_id with observed_at <= decision_time.
    """
    if not match_id:
        return None, True
    repo = RawPayloadRepository(session)
    rows = await repo.list_rows_by_source_and_match_id("pipeline_cache", match_id)
    if not rows:
        return None, True
    best_observed: Optional[str] = None
    decision_ts = decision_time_utc if decision_time_utc.tzinfo else decision_time_utc.replace(tzinfo=timezone.utc)
    for row in rows:
        observed_str = _observed_at_from_row(row)
        if not observed_str:
            continue
        obs_dt = _parse_iso(observed_str)
        if not obs_dt or obs_dt.tzinfo is None:
            obs_dt = obs_dt.replace(tzinfo=timezone.utc) if obs_dt else None
        if not obs_dt or obs_dt > decision_ts:
            continue
        if best_observed is None or (obs_dt > _parse_iso(best_observed) or (obs_dt == _parse_iso(best_observed) and observed_str > best_observed)):
            best_observed = observed_str
    return best_observed, best_observed is None


@dataclass
class StalenessRow:
    """One row of staleness metrics: (market, reason_code, age_band)."""
    market: str
    reason_code: str
    age_band: str
    total: int
    correct: int
    accuracy: Optional[float]
    neutral_rate: Optional[float]
    avg_confidence: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "market": self.market,
            "reason_code": self.reason_code,
            "age_band": self.age_band,
            "total": self.total,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4) if self.accuracy is not None else None,
            "neutral_rate": round(self.neutral_rate, 4) if self.neutral_rate is not None else None,
            "avg_confidence": round(self.avg_confidence, 4) if self.avg_confidence is not None else None,
        }
        return d


async def _run_record_to_evidence_age_ms(
    session: AsyncSession,
    run_created_at_utc: Any,
    match_id: Optional[str],
) -> Tuple[Optional[float], bool]:
    """Compute evidence_age_ms for one run. Returns (age_ms or None, missing_ts)."""
    if hasattr(run_created_at_utc, "isoformat"):
        decision_dt = run_created_at_utc
    else:
        s = str(run_created_at_utc).strip().replace("Z", "+00:00")
        decision_dt = datetime.fromisoformat(s)
    if decision_dt.tzinfo is None:
        decision_dt = decision_dt.replace(tzinfo=timezone.utc)
    observed_str, missing = await _evidence_observed_at_utc_for_run(session, match_id, decision_dt)
    if missing or not observed_str:
        return None, missing
    obs_dt = _parse_iso(observed_str)
    if not obs_dt:
        return None, True
    if obs_dt.tzinfo is None:
        obs_dt = obs_dt.replace(tzinfo=timezone.utc)
    age_ms = (decision_dt - obs_dt).total_seconds() * 1000
    return age_ms, False


async def _load_evaluation_data_with_evidence_age(
    session: AsyncSession,
    from_utc: Optional[datetime] = None,
    to_utc: Optional[datetime] = None,
    limit: int = 5000,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Load runs + resolutions + predictions; attach evidence_age_ms per run (provisional proxy).
    Returns (list of run records with evidence_age_ms and age_band, missing_timestamps_count).
    """
    run_repo = AnalysisRunRepository(session)
    resolution_repo = SnapshotResolutionRepository(session)
    pred_repo = PredictionRepository(session)
    runs = await run_repo.list_by_created_between(from_utc=from_utc, to_utc=to_utc, limit=limit)
    records: List[Dict[str, Any]] = []
    missing_count = 0
    for run in runs:
        res = await resolution_repo.get_by_analysis_run_id(run.id)
        if res is None:
            continue
        try:
            mo = json.loads(res.market_outcomes_json) if isinstance(res.market_outcomes_json, str) else (res.market_outcomes_json or {})
        except (TypeError, ValueError):
            mo = {}
        try:
            rc = json.loads(res.reason_codes_by_market_json) if isinstance(res.reason_codes_by_market_json, str) else (res.reason_codes_by_market_json or {})
        except (TypeError, ValueError):
            rc = {}
        preds = await pred_repo.list_by_analysis_run(run.id)
        market_to_confidence: Dict[str, float] = {}
        for p in preds:
            k = KEY_MAP.get((p.market or "").upper(), "") or KEY_MAP.get(p.market, "")
            if k and k in MARKETS:
                c = getattr(p, "confidence", None)
                if c is not None:
                    market_to_confidence[k] = float(c)
        match_id = getattr(run, "match_id", None) or getattr(res, "match_id", None)
        created = getattr(run, "created_at_utc", None)
        evidence_age_ms, missing = await _run_record_to_evidence_age_ms(session, created, match_id)
        if missing:
            missing_count += 1
        age_band = assign_age_band(evidence_age_ms)
        records.append({
            "run_id": run.id,
            "created_at_utc": created.isoformat() if hasattr(created, "isoformat") else str(created),
            "match_id": match_id,
            "market_outcomes": mo,
            "reason_codes_by_market": rc,
            "market_to_confidence": market_to_confidence,
            "evidence_age_ms": evidence_age_ms,
            "age_band": age_band,
        })
    return records, missing_count


def _aggregate_staleness_rows(records: List[Dict[str, Any]]) -> List[StalenessRow]:
    """Aggregate (market, reason_code, age_band) -> total, correct, accuracy, neutral_rate, avg_confidence. Deterministic sort."""
    agg: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for rec in records:
        outcomes = rec.get("market_outcomes") or {}
        reason_codes = rec.get("reason_codes_by_market") or {}
        market_to_confidence = rec.get("market_to_confidence") or {}
        age_band = rec.get("age_band", "0-30m")
        for market in MARKETS:
            outcome = outcomes.get(market, "UNRESOLVED")
            correct = 1 if outcome == "SUCCESS" else 0
            neutral = 1 if outcome not in ("SUCCESS", "FAILURE") else 0
            confidence = market_to_confidence.get(market)
            for code in (reason_codes.get(market) or []):
                code = str(code)
                key = (market, code, age_band)
                if key not in agg:
                    agg[key] = {"total": 0, "correct": 0, "neutral": 0, "sum_confidence": 0.0, "confidence_count": 0}
                agg[key]["total"] += 1
                agg[key]["correct"] += correct
                agg[key]["neutral"] += neutral
                if confidence is not None:
                    agg[key]["sum_confidence"] += confidence
                    agg[key]["confidence_count"] += 1
    rows: List[StalenessRow] = []
    for (market, reason_code, age_band), v in sorted(agg.items()):
        total = v["total"]
        correct = v["correct"]
        wrong = total - correct - v["neutral"]
        accuracy = correct / (correct + wrong) if (correct + wrong) > 0 else None
        neutral_rate = v["neutral"] / total if total else None
        avg_confidence = (v["sum_confidence"] / v["confidence_count"]) if v["confidence_count"] else None
        rows.append(StalenessRow(
            market=market,
            reason_code=reason_code,
            age_band=age_band,
            total=total,
            correct=correct,
            accuracy=accuracy,
            neutral_rate=neutral_rate,
            avg_confidence=avg_confidence,
        ))
    return rows


async def run_staleness_evaluation(
    session: AsyncSession,
    reports_dir: str | Path = "reports",
    index_path: Optional[str | Path] = None,
    from_utc: Optional[datetime] = None,
    to_utc: Optional[datetime] = None,
    limit: int = 5000,
) -> Dict[str, Any]:
    """
    Run staleness evaluation: load evaluation data with evidence age, aggregate by (market, reason_code, age_band), write CSV/JSON.
    Returns summary: reports_written, row_count, missing_timestamps_count, run_id, report_path_csv, report_path_json.
    """
    from ops.ops_events import (
        log_staleness_eval_end,
        log_staleness_eval_missing_timestamps,
        log_staleness_eval_start,
        log_staleness_eval_written,
    )
    from reports.index_store import load_index, save_index

    t_start = log_staleness_eval_start()
    records, missing_count = await _load_evaluation_data_with_evidence_age(
        session, from_utc=from_utc, to_utc=to_utc, limit=limit
    )
    if missing_count:
        log_staleness_eval_missing_timestamps(missing_count)
    rows = _aggregate_staleness_rows(records)
    computed_at = datetime.now(timezone.utc)
    reports_path = Path(reports_dir) / "staleness_eval"
    reports_path.mkdir(parents=True, exist_ok=True)
    run_id = f"staleness_eval_{computed_at.strftime('%Y%m%d_%H%M%S')}"
    csv_path = reports_path / f"staleness_metrics_by_reason_{run_id}.csv"
    json_path = reports_path / f"staleness_metrics_by_reason_{run_id}.json"

    # Also write canonical names for "latest" (overwrite)
    csv_latest = Path(reports_dir) / "staleness_eval" / "staleness_metrics_by_reason.csv"
    json_latest = Path(reports_dir) / "staleness_eval" / "staleness_metrics_by_reason.json"

    # CSV
    fieldnames = ["market", "reason_code", "age_band", "total", "correct", "accuracy", "neutral_rate", "avg_confidence"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            d = r.to_dict()
            w.writerow({k: d.get(k) for k in fieldnames})
    with open(csv_latest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            d = r.to_dict()
            w.writerow({k: d.get(k) for k in fieldnames})

    # JSON
    report_data = {
        "run_id": run_id,
        "computed_at_utc": computed_at.isoformat(),
        "missing_timestamps_count": missing_count,
        "rows": [r.to_dict() for r in rows],
    }
    json_str = json.dumps(report_data, sort_keys=True, indent=2, default=str)
    json_path.write_text(json_str, encoding="utf-8")
    json_latest.write_text(json_str, encoding="utf-8")

    log_staleness_eval_written(len(rows))
    index_path = index_path or Path(reports_dir) / "index.json"
    index = load_index(index_path)
    staleness_runs = index.get("staleness_eval_runs") or []
    staleness_runs.append({
        "run_id": run_id,
        "created_at_utc": computed_at.isoformat(),
        "row_count": len(rows),
        "missing_timestamps_count": missing_count,
    })
    index["staleness_eval_runs"] = staleness_runs
    index["latest_staleness_eval_run_id"] = run_id
    save_index(index, index_path)
    log_staleness_eval_end(len(rows), missing_count, time.perf_counter() - t_start)
    return {
        "reports_written": 2,
        "row_count": len(rows),
        "missing_timestamps_count": missing_count,
        "run_id": run_id,
        "report_path_csv": str(csv_path),
        "report_path_json": str(json_path),
    }
