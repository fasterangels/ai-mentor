"""
Ops CLI: burn-in-run (ingestion -> compare -> analyze -> optional activation) and health-check.
Usage: python tools/ops.py burn-in-run [--connector NAME] [--dry-run] [--activation]
        python tools/ops.py health-check
Invoke as 'ai-mentor ops burn-in-run' or 'ai-mentor ops health-check' when ai-mentor is on PATH.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def _cmd_burn_in_run(args: argparse.Namespace) -> int:
    import models  # noqa: F401
    from core.config import get_settings
    from core.database import init_database, dispose_database, get_database_manager
    from runner.burn_in_ops_runner import run_burn_in_ops

    async def _run() -> int:
        settings = get_settings()
        await init_database(settings.database_url)
        try:
            async with get_database_manager().session() as session:
                result = await run_burn_in_ops(
                    session,
                    connector_name=args.connector,
                    match_ids=args.match_ids.split(",") if getattr(args, "match_ids", None) else None,
                    enable_activation=args.activation,
                    dry_run=args.dry_run,
                    reports_dir=args.output_dir,
                    index_path=Path(args.output_dir) / "index.json",
                    max_bundles_retained=args.max_bundles,
                )
        finally:
            await dispose_database()

        if result.get("error"):
            print(result.get("detail", result.get("error")), file=sys.stderr)
            return 1
        bundle_dir = result.get("_bundle_dir", "")
        print(f"{result.get('run_id')},{result.get('status')},{result.get('alerts_count', 0)},{result.get('activated', False)},{bundle_dir}")
        return 0

    return asyncio.run(_run())


def _cmd_health_check(_args: argparse.Namespace) -> int:
    import models  # noqa: F401
    from pathlib import Path
    from readiness.checks import run_readiness_checks
    from policy.policy_runtime import get_active_policy
    from ingestion.registry import list_registered_connectors
    from ingestion.live_io import get_connector_safe

    async def _run() -> int:
        repo_root = Path(__file__).resolve().parent.parent
        from core.config import get_settings
        from core.database import init_database, dispose_database, get_database_manager

        settings = get_settings()
        await init_database(settings.database_url)
        results = []
        try:
            async with get_database_manager().session() as session:
                results = await run_readiness_checks(repo_root=repo_root, session=session)
        except Exception as e:
            results = [{"code": "SESSION", "status": "FAIL", "message": str(e)}]
        finally:
            await dispose_database()

        # Policy presence
        try:
            get_active_policy()
            results.append({"code": "POLICY_LOAD", "status": "PASS", "message": "Active policy loads."})
        except Exception as e:
            results.append({"code": "POLICY_LOAD", "status": "FAIL", "message": str(e)})

        # Connector availability (at least one recorded-first)
        connectors = list_registered_connectors()
        available = [c for c in connectors if get_connector_safe(c) is not None]
        if available:
            results.append({"code": "CONNECTOR", "status": "PASS", "message": f"Available connectors: {', '.join(sorted(available))}."})
        else:
            results.append({"code": "CONNECTOR", "status": "WARN", "message": f"No connector available (LIVE_IO_ALLOWED or recorded). Registered: {', '.join(connectors)}."})

        failed = [r for r in results if r.get("status") == "FAIL"]
        for r in results:
            print(f"{r.get('status')}\t{r.get('code')}\t{r.get('message', '')}")
        return 1 if failed else 0

    return asyncio.run(_run())


def _cmd_plan_tuning(args: argparse.Namespace) -> int:
    import models  # noqa: F401
    from core.config import get_settings
    from core.database import init_database, dispose_database, get_database_manager
    from offline_eval.decision_quality import compute_decision_quality_report, load_history_from_session
    from runner.tuning_plan_runner import run_plan_tuning

    async def _run() -> int:
        settings = get_settings()
        await init_database(settings.database_url)
        try:
            async with get_database_manager().session() as session:
                records = await load_history_from_session(session, limit=args.last_n)
                quality_report = compute_decision_quality_report(records) if records else {}
                result = await run_plan_tuning(
                    session,
                    last_n=args.last_n,
                    quality_audit_report=quality_report,
                    records=records,
                    dry_run=args.dry_run,
                    reports_dir=args.output_dir,
                    index_path=Path(args.output_dir) / "index.json",
                )
        finally:
            await dispose_database()

        status = result.get("status", "FAIL")
        reasons = result.get("reasons") or []
        print(status)
        for r in reasons:
            print(r)
        return 0 if status == "PASS" else 1

    return asyncio.run(_run())


def _read_version() -> str:
    """Read version from repo root VERSION file (ai-mentor --version)."""
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.is_file():
        try:
            return version_file.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        except OSError:
            pass
    return "0.0.0"


def main() -> int:
    if "--version" in sys.argv or "-V" in sys.argv:
        print(_read_version())
        return 0
    parser = argparse.ArgumentParser(prog="ops", description="Ops: burn-in-run, health-check")
    sub = parser.add_subparsers(dest="command", required=True)

    burn_in = sub.add_parser("burn-in-run", help="Run ingestion -> compare -> analyze -> (optional) activation; write bundle and update index.")
    burn_in.add_argument("--connector", default="stub_live_platform", help="Connector name")
    burn_in.add_argument("--match-ids", default=None, help="Comma-separated match IDs (default: from connector)")
    burn_in.add_argument("--dry-run", action="store_true", help="Skip activation only; bundle and index are still written (default: False)")
    burn_in.add_argument("--activation", action="store_true", help="Enable burn-in activation if gates pass")
    burn_in.add_argument("--output-dir", default="reports", help="Reports directory")
    burn_in.add_argument("--max-bundles", type=int, default=30, help="Max burn-in bundles to retain")
    burn_in.set_defaults(func=_cmd_burn_in_run)

    health = sub.add_parser("health-check", help="Validate readiness, tables, connector, policy; exit nonzero on failure.")
    health.set_defaults(func=_cmd_health_check)

    plan_tuning = sub.add_parser("plan-tuning", help="Run quality_audit -> tuning plan -> replay regression; output PASS/FAIL (deterministic).")
    plan_tuning.add_argument("--last-n", type=int, default=500, help="Use last N runs for quality_audit and replay")
    plan_tuning.add_argument("--dry-run", action="store_true", help="Do not write tuning_plan report or index")
    plan_tuning.add_argument("--output-dir", default="reports", help="Reports directory")
    plan_tuning.set_defaults(func=_cmd_plan_tuning)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
