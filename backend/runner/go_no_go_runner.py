"""
Go/No-Go decision runner: read graduation_result.json and write decision JSON + MD.
Deterministic, no decision logic change—only maps existing graduation result to artifacts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GRADUATION_RESULT_JSON = "graduation_result.json"
GO_NO_GO_DECISION_JSON = "go_no_go_decision.json"
GO_NO_GO_DECISION_MD = "go_no_go_decision.md"

SCHEMA_VERSION = 1


def run_go_no_go(reports_dir: str | Path) -> dict[str, Any]:
    """
    Read graduation_result.json from reports_dir; write go_no_go_decision.json and .md.
    Returns {"decision": "GO"|"NO_GO", "error": None} or {"error": str, "decision": None} if file missing.
    """
    reports_path = Path(reports_dir)
    grad_path = reports_path / GRADUATION_RESULT_JSON

    if not grad_path.is_file():
        return {"error": "graduation_result.json not found", "decision": None}

    try:
        data = json.loads(grad_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"Failed to read graduation result: {e}", "decision": None}

    overall_pass = data.get("overall_pass", False)
    criteria = data.get("criteria") if isinstance(data.get("criteria"), list) else []
    failed_criteria = [c for c in criteria if isinstance(c, dict) and not c.get("pass")]

    decision = "GO" if overall_pass else "NO_GO"
    decision_time_utc = data.get("computed_at_utc") or datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"

    payload = {
        "decision": decision,
        "schema_version": SCHEMA_VERSION,
        "decision_time_utc": decision_time_utc,
        "failed_criteria": failed_criteria,
    }
    (reports_path / GO_NO_GO_DECISION_JSON).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines = [
        f"**Decision: {decision}**",
        "",
        "Timestamp: " + decision_time_utc,
    ]
    if failed_criteria:
        md_lines.append("")
        md_lines.append("Failed criteria:")
        for c in failed_criteria:
            name = c.get("name", "?")
            details = c.get("details") or {}
            md_lines.append(f"- {name}: {details}")
    (reports_path / GO_NO_GO_DECISION_MD).write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return {"decision": decision, "error": None}
