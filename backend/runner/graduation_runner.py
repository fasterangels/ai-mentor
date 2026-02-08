"""
Graduation evaluation run mode: run criteria evaluator, write graduation_result.json and graduation_result.md.
Measurement-only; no enforcement. Must NOT run by default; invoked explicitly via --mode graduation-eval.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from graduation import evaluate_graduation
from graduation.criteria_v1 import (
    DEFAULT_DECAY_MIN_REASON_CODES,
    DEFAULT_DELTA_COVERAGE_MIN_FIXTURES,
    DEFAULT_DELTA_PAYLOAD_MATCH_MIN_RATE,
    DEFAULT_STALENESS_MIN_REASON_CODES,
    DEFAULT_UNCERTAINTY_MIN_DECISIONS,
    DEFAULT_WORST_CASE_MIN_ROWS,
    LATE_DATA_ACCURACY_DELTA_24H_MIN,
    LATE_DATA_REFUSAL_DELTA_24H_MIN,
)
from ops.ops_events import (
    log_graduation_eval_end,
    log_graduation_eval_failed_criteria,
    log_graduation_eval_start,
    log_graduation_eval_written,
)

MODE_GRADUATION_EVAL = "graduation-eval"

GRADUATION_RESULT_JSON = "graduation_result.json"
GRADUATION_RESULT_MD = "graduation_result.md"


def _thresholds_used() -> Dict[str, Any]:
    """Deterministic dict of thresholds used for reporting."""
    return {
        "delta_coverage_min_fixtures": DEFAULT_DELTA_COVERAGE_MIN_FIXTURES,
        "delta_payload_match_min_rate": DEFAULT_DELTA_PAYLOAD_MATCH_MIN_RATE,
        "staleness_min_reason_codes": DEFAULT_STALENESS_MIN_REASON_CODES,
        "decay_min_reason_codes": DEFAULT_DECAY_MIN_REASON_CODES,
        "uncertainty_min_decisions": DEFAULT_UNCERTAINTY_MIN_DECISIONS,
        "worst_case_min_rows": DEFAULT_WORST_CASE_MIN_ROWS,
        "late_data_accuracy_delta_24h_min": LATE_DATA_ACCURACY_DELTA_24H_MIN,
        "late_data_refusal_delta_24h_min": LATE_DATA_REFUSAL_DELTA_24H_MIN,
    }


def _result_to_json_payload(result: Any) -> Dict[str, Any]:
    """Build JSON-serializable payload (pass_ -> pass for JSON)."""
    return {
        "overall_pass": result.overall_pass,
        "computed_at_utc": result.computed_at_utc.isoformat(),
        "thresholds_used": _thresholds_used(),
        "criteria": [
            {"name": c.name, "pass": c.pass_, "details": c.details}
            for c in result.criteria
        ],
    }


def _result_to_md(result: Any) -> str:
    """Human-readable markdown: overall PASS/FAIL, each criterion, thresholds."""
    lines = [
        "# Graduation Result",
        "",
        f"**Overall: {'PASS' if result.overall_pass else 'FAIL'}**",
        "",
        f"Computed at (UTC): {result.computed_at_utc.isoformat()}",
        "",
        "## Criteria",
        "",
    ]
    for c in result.criteria:
        status = "PASS" if c.pass_ else "FAIL"
        lines.append(f"- **{c.name}**: {status}")
        for k, v in sorted(c.details.items()):
            lines.append(f"  - {k}: {v}")
        lines.append("")
    lines.append("## Thresholds used")
    lines.append("")
    for k, v in sorted(_thresholds_used().items()):
        lines.append(f"- {k}: {v}")
    lines.append("")
    return "\n".join(lines)


def run_graduation_eval(reports_dir: str | Path) -> Dict[str, Any]:
    """
    Run graduation evaluation and write graduation_result.json and graduation_result.md.
    Returns summary: error (if any), overall_pass, json_path, md_path, failed_criteria_count.
    """
    reports_path = Path(reports_dir)
    t0 = log_graduation_eval_start()
    try:
        result = evaluate_graduation(reports_path)
    except Exception as e:
        log_graduation_eval_end(overall_pass=False, criteria_count=0, duration_seconds=time.perf_counter() - t0)
        return {"error": str(e), "overall_pass": False, "json_path": None, "md_path": None, "failed_criteria_count": 0}

    reports_path.mkdir(parents=True, exist_ok=True)
    json_path = reports_path / GRADUATION_RESULT_JSON
    md_path = reports_path / GRADUATION_RESULT_MD

    payload = _result_to_json_payload(result)
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_result_to_md(result), encoding="utf-8")

    log_graduation_eval_written(str(json_path), str(md_path))
    failed_count = sum(1 for c in result.criteria if not c.pass_)
    if failed_count > 0:
        log_graduation_eval_failed_criteria(failed_count)
    log_graduation_eval_end(
        overall_pass=result.overall_pass,
        criteria_count=len(result.criteria),
        duration_seconds=time.perf_counter() - t0,
    )

    return {
        "error": None,
        "overall_pass": result.overall_pass,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "failed_criteria_count": failed_count,
    }
