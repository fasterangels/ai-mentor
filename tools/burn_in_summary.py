"""
Daily summary extractor: read latest burn-in bundle and print concise text summary.
No persistence changes. Use from repo root: python tools/burn_in_summary.py [--reports-dir reports]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
_backend = _repo_root / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def load_latest_bundle(reports_dir: str | Path) -> dict | None:
    """Load latest burn-in bundle (summary + live_compare + live_analyze). Returns None if no run."""
    reports_path = Path(reports_dir)
    index_path = reports_path / "index.json"
    if not index_path.is_file():
        return None
    from reports.index_store import load_index
    index = load_index(index_path)
    run_id = index.get("latest_burn_in_ops_run_id")
    if not run_id:
        return None
    bundle_dir = reports_path / "burn_in" / run_id
    if not bundle_dir.is_dir():
        return None
    summary_path = bundle_dir / "summary.json"
    if not summary_path.is_file():
        return None
    out = {"run_id": run_id, "summary": json.loads(summary_path.read_text(encoding="utf-8"))}
    for name, f in (("live_compare", "live_compare.json"), ("live_analyze", "live_analyze.json")):
        p = bundle_dir / f
        if p.is_file():
            try:
                out[name] = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                out[name] = {}
    return out


def format_burn_in_summary(bundle: dict) -> str:
    """Produce a concise text summary from a loaded bundle (no persistence)."""
    lines = []
    summary = bundle.get("summary") or {}
    run_id = summary.get("run_id") or bundle.get("run_id") or "?"
    lines.append(f"Run: {run_id}")
    lines.append(f"Status: {summary.get('status', '?')}")
    lines.append(f"Alerts: {summary.get('alerts_count', 0)}")
    lines.append(f"Activated: {summary.get('activated', False)}")
    lines.append(f"Matches: {summary.get('matches_count', 0)}")
    lines.append(f"Connector: {summary.get('connector_name', '?')}")

    live_analyze = bundle.get("live_analyze") or {}
    alerts = live_analyze.get("alerts") or []
    if alerts:
        lines.append("Alert details:")
        for a in alerts[:10]:
            code = a.get("code") or a.get("type") or "?"
            msg = a.get("message") or a.get("detail") or str(a)[:80]
            lines.append(f"  - {code}: {msg}")
        if len(alerts) > 10:
            lines.append(f"  ... and {len(alerts) - 10} more")

    # Avg latency: from live_compare or live_analyze if present (e.g. summary.latency_ms)
    latency_ms = None
    for src in (bundle.get("live_compare"), bundle.get("live_analyze")):
        if not src:
            continue
        lm = src.get("latency_ms") or src.get("summary", {}).get("latency_ms")
        if isinstance(lm, (int, float)):
            latency_ms = lm
            break
        if isinstance(lm, dict) and "p50" in lm:
            latency_ms = lm.get("p50") or lm.get("p95")
            break
    if latency_ms is not None:
        lines.append(f"Avg latency (ms): {latency_ms:.0f}")

    # Confidence stats: from live_analyze per_match or live_analysis_reports
    confs = []
    for match_id, report in (live_analyze.get("live_analysis_reports") or {}).items():
        dec = report.get("analyzer", {}).get("decisions") or report.get("decisions") or []
        for d in dec:
            c = d.get("confidence")
            if c is not None:
                try:
                    confs.append(float(c))
                except (TypeError, ValueError):
                    pass
    if confs:
        avg = sum(confs) / len(confs)
        lines.append(f"Confidence: avg={avg:.2f} count={len(confs)}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print concise summary of latest burn-in bundle")
    parser.add_argument("--reports-dir", default="reports", help="Reports directory")
    args = parser.parse_args()
    bundle = load_latest_bundle(args.reports_dir)
    if not bundle:
        print("No latest burn-in bundle found.", file=sys.stderr)
        return 1
    print(format_burn_in_summary(bundle))
    return 0


if __name__ == "__main__":
    sys.exit(main())
