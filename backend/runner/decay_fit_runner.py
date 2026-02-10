"""
Decay fit runner (H1 Part B): load G4 staleness metrics, fit piecewise decay, write artifacts.
Measurement-only; no analyzer, no policy changes. Offline-first (reads existing JSON).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from modeling.reason_decay import fit_piecewise_decay
from modeling.reason_decay.model import DecayModelParams
from ops.ops_events import (
    log_decay_fit_end,
    log_decay_fit_skipped_low_support,
    log_decay_fit_start,
    log_decay_fit_written,
)


STALENESS_JSON_NAME = "staleness_metrics_by_reason.json"
DECAY_FIT_SUBDIR = "decay_fit"
PARAMS_JSON_NAME = "reason_decay_params.json"
BY_MARKET_SUBDIR = "reason_decay_params_by_market"
SUMMARY_CSV_NAME = "reason_decay_summary.csv"


def _load_staleness_rows(reports_dir: str | Path) -> tuple[List[Dict[str, Any]], str | None]:
    """
    Load staleness metrics rows from G4 JSON. Returns (rows, error).
    Prefer reports_dir/staleness_eval/staleness_metrics_by_reason.json.
    """
    path = Path(reports_dir) / "staleness_eval" / STALENESS_JSON_NAME
    if not path.exists():
        return [], "missing_staleness_json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [], f"read_error:{e!s}"
    rows = data.get("rows")
    if not isinstance(rows, list):
        return [], "invalid_rows"
    return rows, None


def _write_params_json(params: List[DecayModelParams], out_path: Path, fitted_at_utc: str) -> None:
    """Write single reason_decay_params.json with stable ordering."""
    payload: Dict[str, Any] = {
        "fitted_at_utc": fitted_at_utc,
        "params": [p.to_dict() for p in params],
        "schema_version": "1",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, default=str),
        encoding="utf-8",
    )


def _write_by_market(params: List[DecayModelParams], out_dir: Path, fitted_at_utc: str) -> None:
    """Write one JSON per market under reason_decay_params_by_market/."""
    by_market: Dict[str, List[Dict[str, Any]]] = {}
    for p in params:
        by_market.setdefault(p.market, []).append(p.to_dict())
    out_dir.mkdir(parents=True, exist_ok=True)
    for market in sorted(by_market.keys()):
        payload = {
            "fitted_at_utc": fitted_at_utc,
            "market": market,
            "params": by_market[market],
            "schema_version": "1",
        }
        (out_dir / f"{market}.json").write_text(
            json.dumps(payload, sort_keys=True, indent=2, default=str),
            encoding="utf-8",
        )


def _write_summary_csv(params: List[DecayModelParams], out_path: Path) -> None:
    """Write small summary CSV: market, reason_code, bands_with_support, penalty_0, ..."""
    import csv
    bands = params[0].bands if params else []
    fieldnames = ["market", "reason_code", "bands_with_support"] + [f"penalty_{b}" for b in bands]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p in params:
            row: Dict[str, Any] = {
                "market": p.market,
                "reason_code": p.reason_code,
                "bands_with_support": p.fit_quality.bands_with_support if p.fit_quality else 0,
            }
            for i, b in enumerate(p.bands):
                row[f"penalty_{b}"] = p.penalty_by_band[i] if i < len(p.penalty_by_band) else ""
            w.writerow(row)


def run_decay_fit_mode(
    reports_dir: str | Path = "reports",
    write_by_market: bool = True,
    write_summary_csv: bool = True,
) -> Dict[str, Any]:
    """
    Load G4 staleness metrics JSON, fit decay params per (market, reason_code), write artifacts.
    Does not use DB or run analyzer. Deterministic outputs; stable ordering and filenames.
    """
    t_start = log_decay_fit_start()
    reports_dir = Path(reports_dir)
    out_base = reports_dir / DECAY_FIT_SUBDIR

    rows, err = _load_staleness_rows(reports_dir)
    if err:
        log_decay_fit_end(0, time.perf_counter() - t_start, skipped_low_support=0)
        return {
            "error": err,
            "params_count": 0,
            "params_path": None,
            "skipped_low_support": 0,
        }

    if not rows:
        log_decay_fit_written(0)
        log_decay_fit_end(0, time.perf_counter() - t_start, skipped_low_support=0)
        return {
            "params_count": 0,
            "params_path": str(out_base / PARAMS_JSON_NAME),
            "skipped_low_support": 0,
        }

    fitted_at_utc = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    params_list = fit_piecewise_decay(rows, fitted_at_utc=fitted_at_utc)
    skipped = sum(1 for p in params_list if p.fit_quality and p.fit_quality.bands_with_support == 0)
    if skipped:
        log_decay_fit_skipped_low_support(skipped)

    params_path = out_base / PARAMS_JSON_NAME
    _write_params_json(params_list, params_path, fitted_at_utc)
    log_decay_fit_written(len(params_list))

    if write_by_market:
        _write_by_market(params_list, out_base / BY_MARKET_SUBDIR, fitted_at_utc)
    if write_summary_csv:
        _write_summary_csv(params_list, out_base / SUMMARY_CSV_NAME)

    log_decay_fit_end(len(params_list), time.perf_counter() - t_start, skipped_low_support=skipped)
    return {
        "params_count": len(params_list),
        "params_path": str(params_path),
        "skipped_low_support": skipped,
    }
