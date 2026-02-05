"""
Tests for operational_run CLI: produces report file and index.json; stable with fixed now_utc.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Repo root (parent of backend)
_repo_root = Path(__file__).resolve().parent.parent.parent
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def _run_operational_cli(
    output_dir: Path,
    connector: str = "dummy",
    match_ids: str | None = "op-m1,op-m2",
    now_utc: str | None = "2025-06-01T12:00:00+00:00",
) -> tuple[int, str, str]:
    """Run tools/operational_run.py; return (returncode, stdout, stderr)."""
    cmd = [
        sys.executable,
        str(_repo_root / "tools" / "operational_run.py"),
        "--connector",
        connector,
        "--output-dir",
        str(output_dir),
        "--now-utc",
        now_utc or "",
    ]
    if match_ids:
        cmd.extend(["--match-ids", match_ids])
    env = {**__import__("os").environ, "DATABASE_URL": "sqlite+aiosqlite:///:memory:"}
    result = subprocess.run(
        cmd,
        cwd=str(_repo_root),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    return result.returncode, result.stdout or "", result.stderr or ""


def test_operational_run_produces_report_and_index(tmp_path: Path) -> None:
    """Run tool in temp dir; expect report file and index.json."""
    code, out, err = _run_operational_cli(tmp_path, match_ids="op-m1,op-m2", now_utc="2025-06-01T12:00:00+00:00")
    assert code == 0, f"stderr: {err}"
    lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
    assert len(lines) >= 1
    parts = lines[0].split(",")
    assert len(parts) == 3
    run_id, report_path_str, alerts_count_str = parts[0], parts[1], parts[2]
    assert run_id.startswith("shadow_batch_")
    assert alerts_count_str.isdigit()

    report_path = Path(report_path_str)
    assert report_path.is_absolute() or (tmp_path / report_path.name).exists()
    # Report file should be under tmp_path
    report_file = tmp_path / report_path.name if not report_path.is_absolute() else report_path
    if not report_file.exists():
        report_file = tmp_path / list(tmp_path.glob("shadow_batch_*.json"))[0].name
    assert report_file.exists()
    data = json.loads(report_file.read_text(encoding="utf-8"))
    assert "run_meta" in data or "error" in data
    assert "alerts" in data
    assert isinstance(data["alerts"], list)

    index_file = tmp_path / "index.json"
    assert index_file.exists()
    index = json.loads(index_file.read_text(encoding="utf-8"))
    assert "runs" in index
    assert "latest_run_id" in index
    assert len(index["runs"]) >= 1
    assert index["runs"][-1]["run_id"] == run_id
    assert index["runs"][-1]["alerts_count"] == int(alerts_count_str)


def test_operational_run_stable_when_now_utc_fixed(tmp_path: Path) -> None:
    """Two runs with same now_utc and match_ids yield same report filename (deterministic)."""
    code1, out1, err1 = _run_operational_cli(tmp_path, match_ids="det-a,det-b", now_utc="2025-07-01T10:00:00+00:00")
    assert code1 == 0, f"stderr: {err1}"
    code2, out2, err2 = _run_operational_cli(tmp_path, match_ids="det-a,det-b", now_utc="2025-07-01T10:00:00+00:00")
    assert code2 == 0, f"stderr: {err2}"

    run_id1 = out1.strip().split(",")[0].strip()
    run_id2 = out2.strip().split(",")[0].strip()
    # Same timestamp in run_id (20250701_100000); checksum part should match for same inputs
    assert run_id1 == run_id2, "Same now_utc and match_ids should produce same run_id"

    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert len(index["runs"]) == 2
    assert index["runs"][0]["run_id"] == index["runs"][1]["run_id"]
