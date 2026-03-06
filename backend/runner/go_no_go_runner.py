"""
Go/No-Go run mode: read J1 graduation_result.json, compute decision, write go_no_go_decision.json and go_no_go_decision.md.
No automation; produces decision reports only. Must NOT run by default; explicit mode only.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from graduation.criteria_v1 import CriterionResult, GraduationResult
from graduation.go_no_go import compute_go_no_go
from graduation.go_no_go.model import GoNoGoDecision
from ops.ops_events import (
    log_go_no_go_end,
    log_go_no_go_start,
    log_go_no_go_written,
)

MODE_GO_NO_GO = "go-no-go"

GRADUATION_RESULT_JSON = "graduation_result.json"
GO_NO_GO_DECISION_JSON = "go_no_go_decision.json"
GO_NO_GO_DECISION_MD = "go_no_go_decision.md"


def _parse_graduation_result_json(data: Dict[str, Any]) -> GraduationResult:
    """Parse J1 graduation_result.json payload into GraduationResult."""
    computed_at = data.get("computed_at_utc") or ""
    if isinstance(computed_at, str):
        computed_at = datetime.fromisoformat(computed_at.replace("Z", "+00:00"))
    if computed_at.tzinfo is None:
        computed_at = computed_at.replace(tzinfo=timezone.utc)
    criteria: List[CriterionResult] = []
    for c in data.get("criteria") or []:
        criteria.append(
            CriterionResult(
                name=str(c.get("name", "")),
                pass_=bool(c.get("pass", False)),
                details=dict(c.get("details") or {}),
            )
        )
    return GraduationResult(
        overall_pass=bool(data.get("overall_pass", False)),
        criteria=criteria,
        computed_at_utc=computed_at,
    )


def _decision_to_dict(decision: GoNoGoDecision) -> Dict[str, Any]:
    """Stable key order for JSON."""
    return {
        "schema_version": decision.schema_version,
        "decision": decision.decision,
        "decision_time_utc": decision.decision_time_utc.isoformat(),
        "graduation_ref": decision.graduation_ref,
        "failed_criteria": list(decision.failed_criteria),
        "warnings": list(decision.warnings),
    }


def _decision_to_md(decision: GoNoGoDecision) -> str:
    """Human-readable: Decision, Timestamp, Reference, if NO_GO list failed criteria."""
    lines = [
        "# Go/No-Go Decision",
        "",
        f"**Decision: {decision.decision}**",
        "",
        f"Timestamp (UTC): {decision.decision_time_utc.isoformat()}",
        "",
    ]
    if decision.graduation_ref:
        lines.append(f"Reference: {decision.graduation_ref}")
        lines.append("")
    if decision.decision == "NO_GO" and decision.failed_criteria:
        lines.append("## Failed criteria")
        lines.append("")
        for f in decision.failed_criteria:
            lines.append(f"- **{f.get('name', '')}**")
            for k, v in sorted((f.get("details") or {}).items()):
                lines.append(f"  - {k}: {str(v)}")
        lines.append("")
    if decision.warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in decision.warnings:
            lines.append(f"- {w}")
        lines.append("")
    return "\n".join(lines)


def run_go_no_go(reports_dir: str | Path) -> Dict[str, Any]:
    """
    Read graduation_result.json from reports_dir, compute Go/No-Go, write artifacts.
    Returns: error (if any), decision, json_path, md_path.
    """
    reports_path = Path(reports_dir)
    grad_path = reports_path / GRADUATION_RESULT_JSON
    t0 = log_go_no_go_start()

    if not grad_path.exists():
        log_go_no_go_end(decision="NO_GO", duration_seconds=time.perf_counter() - t0)
        return {
            "error": f"graduation result not found: {grad_path}",
            "decision": None,
            "json_path": None,
            "md_path": None,
        }

    try:
        raw = json.loads(grad_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log_go_no_go_end(decision="NO_GO", duration_seconds=time.perf_counter() - t0)
        return {"error": str(e), "decision": None, "json_path": None, "md_path": None}

    graduation_result = _parse_graduation_result_json(raw)
    ref_path = str(grad_path)
    decision = compute_go_no_go(graduation_result, referenced_graduation_result_path=ref_path)

    reports_path.mkdir(parents=True, exist_ok=True)
    json_path = reports_path / GO_NO_GO_DECISION_JSON
    md_path = reports_path / GO_NO_GO_DECISION_MD

    json_path.write_text(json.dumps(_decision_to_dict(decision), indent=2, default=str), encoding="utf-8")
    md_path.write_text(_decision_to_md(decision), encoding="utf-8")

    log_go_no_go_written(str(json_path), str(md_path))
    log_go_no_go_end(decision=decision.decision, duration_seconds=time.perf_counter() - t0)

    return {
        "error": None,
        "decision": decision.decision,
        "json_path": str(json_path),
        "md_path": str(md_path),
    }
