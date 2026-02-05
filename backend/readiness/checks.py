"""
Readiness checks before integrating real data platforms.
Returns list of CheckResult; FAIL if any critical prerequisite missing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

# CheckResult: code, status ("PASS"|"WARN"|"FAIL"), message


async def run_readiness_checks(
    *,
    repo_root: Optional[Path] = None,
    session: Any = None,
    app: Any = None,
) -> List[Dict[str, Any]]:
    """
    Run all readiness checks. Returns list of {"code": str, "status": "PASS"|"WARN"|"FAIL", "message": str}.
    Optional: repo_root (for CI/workflows), session (for DB/cache check), app (FastAPI app for endpoint check).
    """
    results: List[Dict[str, Any]] = []

    # 1) PR CI workflow exists (and optionally last run on main PASS - we cannot verify offline)
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
    workflows_dir = repo_root / ".github" / "workflows"
    if workflows_dir.exists() and workflows_dir.is_dir():
        ymls = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        if ymls:
            results.append({
                "code": "CI_WORKFLOW",
                "status": "PASS",
                "message": f"CI workflow(s) found: {len(ymls)} file(s).",
            })
        else:
            results.append({
                "code": "CI_WORKFLOW",
                "status": "FAIL",
                "message": "No .yml/.yaml files in .github/workflows.",
            })
    else:
        results.append({
            "code": "CI_WORKFLOW",
            "status": "FAIL",
            "message": ".github/workflows directory not found.",
        })

    # 2) Shadow pipeline endpoint exists and responds
    if app is not None:
        try:
            from fastapi.testclient import TestClient
            client = TestClient(app)
            # POST without match_id -> 422 or 400 with "match_id" in response
            resp = client.post("/api/v1/pipeline/shadow/run", json={})
            if resp.status_code in (200, 400, 422):
                results.append({
                    "code": "SHADOW_ENDPOINT",
                    "status": "PASS",
                    "message": "Shadow pipeline endpoint responds.",
                })
            else:
                results.append({
                    "code": "SHADOW_ENDPOINT",
                    "status": "FAIL",
                    "message": f"Shadow pipeline endpoint returned {resp.status_code}.",
                })
        except Exception as e:
            results.append({
                "code": "SHADOW_ENDPOINT",
                "status": "FAIL",
                "message": f"Shadow pipeline endpoint check failed: {e!s}.",
            })
    else:
        results.append({
            "code": "SHADOW_ENDPOINT",
            "status": "WARN",
            "message": "App not provided; cannot verify shadow endpoint.",
        })

    # 3) Policies directory exists and default policy loads
    try:
        from policy.policy_runtime import get_active_policy
        from policy.policy_store import default_policy_path
        get_active_policy()  # must not raise
        policies_dir = default_policy_path().parent
        if policies_dir.exists():
            results.append({
                "code": "POLICY",
                "status": "PASS",
                "message": "Policies directory exists and default policy loads.",
            })
        else:
            results.append({
                "code": "POLICY",
                "status": "PASS",
                "message": "Default in-code policy loads (policies dir missing).",
            })
    except Exception as e:
        results.append({
            "code": "POLICY",
            "status": "FAIL",
            "message": f"Policy check failed: {e!s}.",
        })

    # 4) Ingestion cache table exists
    if session is not None:
        try:
            from sqlalchemy import text
            await session.execute(text("SELECT 1 FROM raw_payloads LIMIT 1"))
            results.append({
                "code": "INGESTION_CACHE",
                "status": "PASS",
                "message": "Ingestion cache table (raw_payloads) exists.",
            })
        except Exception as e:
            results.append({
                "code": "INGESTION_CACHE",
                "status": "FAIL",
                "message": f"Ingestion cache table check failed: {e!s}.",
            })
    else:
        results.append({
            "code": "INGESTION_CACHE",
            "status": "WARN",
            "message": "Session not provided; cannot verify ingestion cache table.",
        })

    return results
