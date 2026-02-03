#!/usr/bin/env python3
"""
Offline evaluator CLI: aggregate snapshot resolutions into evaluation_report.json.

Usage:
  python tools/offline_evaluator.py [--from-date ISO] [--to-date ISO] [--only-final] [--output PATH]

Uses the same DB as the backend (analysis_runs + snapshot_resolutions).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path when run from repo root
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_BACKEND = _REPO_ROOT / "backend"
if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.config import get_settings
from core.database import init_database, dispose_database
from evaluation.attribution import (
    emit_attribution_rows,
    market_outcomes_from_resolution,
    reason_codes_by_market_from_resolution,
)
from repositories.analysis_run_repo import AnalysisRunRepository
from repositories.prediction_repo import PredictionRepository
from repositories.snapshot_resolution_repo import SnapshotResolutionRepository

CONFIDENCE_BANDS = [
    (0.50, 0.55),
    (0.55, 0.60),
    (0.60, 0.65),
    (0.65, 0.70),
    (0.70, 1.00),
]


def _band_for_confidence(c: float) -> str | None:
    """Return band label like '0.50-0.55' or None if out of range."""
    for lo, hi in CONFIDENCE_BANDS:
        if lo <= c < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return None


async def run_evaluator(
    from_date: datetime | None,
    to_date: datetime | None,
    only_final: bool,
    output_path: Path,
) -> None:
    """Load snapshots (analysis runs), filter, aggregate, write report."""
    settings = get_settings()
    await init_database(settings.database_url)

    try:
        from core.database import get_database_manager
        async with get_database_manager().session() as session:
            run_repo = AnalysisRunRepository(session)
            resolution_repo = SnapshotResolutionRepository(session)
            pred_repo = PredictionRepository(session)

            runs = await run_repo.list_by_created_between(
                from_utc=from_date,
                to_utc=to_date,
                limit=5000,
            )
            total_snapshots = len(runs)

            resolved: list[tuple[any, any]] = []  # (run, resolution)
            for run in runs:
                res = await resolution_repo.get_by_analysis_run_id(run.id)
                if res is None and only_final:
                    continue
                if res is not None:
                    resolved.append((run, res))

            resolved_snapshots = len(resolved)

            # Per-market counts
            markets = ("one_x_two", "over_under_25", "gg_ng")
            per_market: dict[str, dict[str, int]] = {
                m: {"success_count": 0, "failure_count": 0, "neutral_count": 0}
                for m in markets
            }
            # Confidence bands per market
            bands_label = [f"{lo:.2f}-{hi:.2f}" for lo, hi in CONFIDENCE_BANDS]
            per_market_bands: dict[str, dict[str, dict[str, int]]] = {
                m: {b: {"success_count": 0, "failure_count": 0, "neutral_count": 0} for b in bands_label}
                for m in markets
            }
            # Reason effectiveness: per reason_code per market
            reason_stats: dict[str, dict[str, dict[str, int]]] = {}  # code -> market -> count

            for run, res in resolved:
                mo_raw = res.market_outcomes_json
                try:
                    mo = json.loads(mo_raw) if isinstance(mo_raw, str) else (mo_raw or {})
                except (TypeError, ValueError):
                    mo = {}
                for m in markets:
                    outcome = mo.get(m, "UNRESOLVED")
                    if outcome == "SUCCESS":
                        per_market[m]["success_count"] += 1
                    elif outcome == "FAILURE":
                        per_market[m]["failure_count"] += 1
                    else:
                        per_market[m]["neutral_count"] += 1

                # Confidence banding: get predictions for this run
                preds = await pred_repo.list_by_analysis_run(run.id)
                market_to_confidence: dict[str, float] = {}
                key_map = {"1X2": "one_x_two", "OU25": "over_under_25", "OU_2.5": "over_under_25", "GGNG": "gg_ng", "BTTS": "gg_ng"}
                for p in preds:
                    k = key_map.get((p.market or "").upper(), "")
                    if k and k in markets:
                        market_to_confidence[k] = getattr(p, "confidence", None) if hasattr(p, "confidence") else None
                if all(market_to_confidence.get(m) is not None for m in markets):
                    for m in markets:
                        c = market_to_confidence.get(m)
                        if c is not None:
                            band = _band_for_confidence(float(c))
                            if band and band in per_market_bands[m]:
                                outcome = mo.get(m, "UNRESOLVED")
                                if outcome == "SUCCESS":
                                    per_market_bands[m][band]["success_count"] += 1
                                elif outcome == "FAILURE":
                                    per_market_bands[m][band]["failure_count"] += 1
                                else:
                                    per_market_bands[m][band]["neutral_count"] += 1

                # Reason attribution
                reason_codes = reason_codes_by_market_from_resolution({
                    "reason_codes_by_market_json": getattr(res, "reason_codes_by_market_json", None),
                })
                outcomes = market_outcomes_from_resolution({
                    "market_outcomes_json": getattr(res, "market_outcomes_json", None),
                })
                for row in emit_attribution_rows(reason_codes, outcomes):
                    code = row.reason_code
                    if code not in reason_stats:
                        reason_stats[code] = {m: {"success": 0, "failure": 0, "neutral": 0} for m in markets}
                    if row.market not in reason_stats[code]:
                        reason_stats[code][row.market] = {"success": 0, "failure": 0, "neutral": 0}
                    if row.outcome == "SUCCESS":
                        reason_stats[code][row.market]["success"] += 1
                    elif row.outcome == "FAILURE":
                        reason_stats[code][row.market]["failure"] += 1
                    else:
                        reason_stats[code][row.market]["neutral"] += 1

            # Build report
            def accuracy(s: int, f: int) -> float | None:
                if s + f == 0:
                    return None
                return round(s / (s + f), 4)

            per_market_report = {}
            for m in markets:
                d = per_market[m]
                s, f, n = d["success_count"], d["failure_count"], d["neutral_count"]
                per_market_report[m] = {
                    "success_count": s,
                    "failure_count": f,
                    "neutral_count": n,
                    "accuracy": accuracy(s, f),
                }
                if any(per_market_bands[m][b]["success_count"] or per_market_bands[m][b]["failure_count"] for b in bands_label):
                    per_market_report[m]["confidence_bands"] = {}
                    for b in bands_label:
                        sb = per_market_bands[m][b]
                        if sb["success_count"] + sb["failure_count"] + sb["neutral_count"] > 0:
                            per_market_report[m]["confidence_bands"][b] = {
                                **sb,
                                "accuracy": accuracy(sb["success_count"], sb["failure_count"]),
                            }

            reason_effectiveness = {}
            for code, by_market in reason_stats.items():
                reason_effectiveness[code] = {}
                for m, counts in by_market.items():
                    s = counts["success"]
                    f = counts["failure"]
                    reason_effectiveness[code][m] = {
                        "success": s,
                        "failure": f,
                        "neutral": counts["neutral"],
                        "success_rate": round(s / (s + f), 4) if (s + f) > 0 else None,
                    }

            report = {
                "overall": {
                    "total_snapshots": total_snapshots,
                    "resolved_snapshots": resolved_snapshots,
                },
                "per_market_accuracy": per_market_report,
                "reason_effectiveness": reason_effectiveness,
            }
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(f"Wrote {output_path}", file=sys.stderr)
    except Exception as e:
        if "no such table" in str(e).lower() or "OperationalError" in type(e).__name__:
            report = {
                "overall": {"total_snapshots": 0, "resolved_snapshots": 0},
                "per_market_accuracy": {},
                "reason_effectiveness": {},
                "warnings": ["NO_SCHEMA_DETECTED"],
            }
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(f"DB not initialized or empty; wrote empty report to {output_path}", file=sys.stderr)
        else:
            raise
    finally:
        await dispose_database()


def _parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def main() -> int:
    ap = argparse.ArgumentParser(description="Offline evaluator: snapshot resolutions -> evaluation_report.json")
    ap.add_argument("--from-date", type=str, default=None, help="Filter snapshots from this date (ISO8601)")
    ap.add_argument("--to-date", type=str, default=None, help="Filter snapshots to this date (ISO8601)")
    ap.add_argument("--only-final", action="store_true", default=True, help="Only include resolved snapshots (default: True)")
    ap.add_argument("--all", action="store_true", help="Include all snapshots (not only resolved)")
    ap.add_argument("--output", type=Path, default=Path("evaluation_report.json"), help="Output JSON path")
    args = ap.parse_args()

    from_date = _parse_iso(args.from_date) if args.from_date else None
    to_date = _parse_iso(args.to_date) if args.to_date else None
    only_final = args.only_final and not args.all

    asyncio.run(run_evaluator(from_date, to_date, only_final, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
