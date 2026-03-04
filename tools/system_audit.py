#!/usr/bin/env python3
"""
Full-system audit CLI: verify environment, determinism, evaluation metrics, and artifact integrity.

Usage:
  python -m tools.system_audit

Metrics-only: does not change analyzer or production behavior.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure backend on path when run from repo root
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_BACKEND = _REPO_ROOT / "backend"
if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from evaluation.harness_v1_v2 import load_payloads, run_v2
from tools import offline_evaluator  # type: ignore[import]
from tools.audit_bundle import build_bundle  # type: ignore[import]


def _git_info() -> Tuple[str | None, str | None]:
    """Return (commit_hash, branch_name) or (None, None) on failure."""
    try:
        commit = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT)
            .decode("utf-8")
            .strip()
        )
    except Exception:
        commit = None
    try:
        branch = (
            subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=_REPO_ROOT)
            .decode("utf-8")
            .strip()
        )
    except Exception:
        branch = None
    return commit, branch


def _read_requirements(path: Path) -> List[str]:
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _determinism_check() -> Dict[str, Any]:
    """Run analyzer v2 twice on the same fixtures and confirm identical outputs."""
    details: Dict[str, Any] = {"status": "FAIL", "details": ""}
    try:
        fixtures_path = _BACKEND / "evaluation" / "fixtures" / "sample_payloads.json"
        payloads = load_payloads(str(fixtures_path))
        if not payloads:
            details["details"] = "No payloads found"
            return details
        markets = ["1X2", "OU25", "GGNG"]
        run1: List[Dict[str, Any]] = []
        run2: List[Dict[str, Any]] = []
        for i, item in enumerate(payloads):
            match_id = item.get("match_id", f"match-{i}")
            ep = item.get("evidence_pack")
            out1 = run_v2(ep, match_id, markets)
            out2 = run_v2(ep, match_id, markets)
            run1.append(out1)
            run2.append(out2)
        # Compare JSON-serialized for deterministic ordering
        def _stable(o: Any) -> str:
            return json.dumps(o, sort_keys=True, separators=(",", ":"))

        if all(_stable(a) == _stable(b) for a, b in zip(run1, run2)):
            details["status"] = "PASS"
            details["details"] = f"{len(payloads)} payload(s) deterministic"
        else:
            details["details"] = "Analyzer outputs diverged across runs"
    except Exception as e:
        details["details"] = f"Exception during determinism check: {e}"
    return details


def _run_offline_evaluator(report_path: Path) -> Dict[str, Any]:
    """Run tools.offline_evaluator.run_evaluator into report_path and return parsed JSON (or {})."""
    try:
        from_date = None
        to_date = None
        only_final = True
        report_path.parent.mkdir(parents=True, exist_ok=True)
        # tools.offline_evaluator.run_evaluator is async
        import asyncio

        asyncio.run(offline_evaluator.run_evaluator(from_date, to_date, only_final, report_path))
    except Exception:
        # Fallback: if run_evaluator fails entirely, try reading existing file (if any)
        pass
    if not report_path.is_file():
        return {}
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _audit_evaluation_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    """Check presence of reason_metrics, reason_failure_metrics, and baseline metadata."""
    status = "PASS"
    reasons: List[str] = []

    if "reason_metrics" not in report:
        status = "FAIL"
        reasons.append("reason_metrics missing")
    if "reason_failure_metrics" not in report:
        status = "FAIL"
        reasons.append("reason_failure_metrics missing")

    meta = report.get("meta") or {}
    baseline = meta.get("baseline") or {}
    baseline_keys = ["baseline_hash", "policy_digest", "analyzer_version", "schema_versions"]
    missing_baseline = [k for k in baseline_keys if k not in baseline]
    if missing_baseline:
        status = "FAIL"
        reasons.append(f"baseline meta missing keys: {', '.join(missing_baseline)}")

    return {"status": status, "details": "; ".join(reasons) if reasons else "OK"}


def _audit_artifact_integrity(report_path: Path, out_dir: Path) -> Dict[str, Any]:
    """Generate an audit bundle and verify manifest checksums."""
    status = "PASS"
    details = "OK"
    try:
        bundle_path = build_bundle(report_path=report_path, out_dir=out_dir, deterministic=True)
        if not bundle_path.is_file():
            return {"status": "FAIL", "details": "audit bundle not created"}
        with zipfile.ZipFile(bundle_path, "r") as zf:
            if "manifest.json" not in zf.namelist():
                return {"status": "FAIL", "details": "manifest.json missing in bundle"}
            manifest = json.loads(zf.read("manifest.json"))
            files = manifest.get("files") or []
            for entry in files:
                rel = entry.get("path")
                expected_sha = entry.get("sha256")
                expected_size = entry.get("size_bytes")
                content = zf.read(rel)
                actual_sha = hashlib.sha256(content).hexdigest()
                if actual_sha != expected_sha:
                    return {"status": "FAIL", "details": f"checksum mismatch for {rel}"}
                if len(content) != expected_size:
                    return {"status": "FAIL", "details": f"size mismatch for {rel}"}
    except Exception as e:
        status = "FAIL"
        details = f"Exception during artifact integrity audit: {e}"
    return {"status": status, "details": details}


def _audit_metrics_sanity(report: Dict[str, Any]) -> Dict[str, Any]:
    """Sanity checks on reason_metrics and reason_failure_metrics (non-empty, no NaN)."""
    import math

    status = "PASS"
    reasons: List[str] = []

    rm = report.get("reason_metrics") or {}
    co = (rm.get("coactivation") or {}).get("global") or {}
    if not co:
        status = "FAIL"
        reasons.append("coactivation matrix empty")

    rf = report.get("reason_failure_metrics") or {}
    if not rf:
        status = "FAIL"
        reasons.append("reason_failure_metrics empty")

    def _walk_values(obj: Any) -> List[float]:
        vals: List[float] = []
        if isinstance(obj, dict):
            for v in obj.values():
                vals.extend(_walk_values(v))
        elif isinstance(obj, list):
            for v in obj:
                vals.extend(_walk_values(v))
        elif isinstance(obj, float):
            vals.append(obj)
        return vals

    floats = _walk_values(report)
    bad = [v for v in floats if not math.isfinite(v)]
    if bad:
        status = "FAIL"
        reasons.append("non-finite metric values present")

    return {"status": status, "details": "; ".join(reasons) if reasons else "OK"}


def main() -> int:
    commit, branch = _git_info()
    python_info = {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
    }
    requirements = _read_requirements(_BACKEND / "requirements.txt")

    determinism = _determinism_check()

    reports_root = _REPO_ROOT / "reports" / "system_audit"
    eval_report_path = reports_root / "evaluation_report_for_audit.json"
    eval_report = _run_offline_evaluator(eval_report_path)
    eval_metrics = _audit_evaluation_metrics(eval_report)

    bundles_dir = reports_root / "bundles"
    artifact = _audit_artifact_integrity(eval_report_path, bundles_dir)

    metrics_sanity = _audit_metrics_sanity(eval_report)

    checks = [determinism, eval_metrics, artifact, metrics_sanity]
    all_pass = all(c.get("status") == "PASS" for c in checks)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = reports_root / f"system_audit_{timestamp}.json"

    report = {
        "system_audit": {
            "commit": commit,
            "branch": branch,
            "python": python_info,
            "requirements_snapshot": requirements,
            "tests_passed": all_pass,
            "determinism_check": determinism,
            "evaluation_metrics_present": eval_metrics,
            "artifact_integrity": artifact,
            "metrics_sanity": metrics_sanity,
            "overall_status": "PASS" if all_pass else "FAIL",
        }
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print(str(out_path), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

