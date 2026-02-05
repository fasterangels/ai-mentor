"""
Phase B: UI must call only /pipeline/shadow/run; no code path must call /api/v1/analyze.
Static checks on frontend source (CI-safe; no new tooling).
"""

from __future__ import annotations

from pathlib import Path

# Repo root: backend/tests -> backend -> repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_FRONTEND_SRC = _REPO_ROOT / "app" / "frontend" / "src"

# Only these files may mention /api/v1/analyze (guard in client, comment in analyzer)
_ALLOWED_ANALYZE_MENTIONS = {"client.ts", "analyzer.ts"}


def test_frontend_no_call_to_analyze_endpoint() -> None:
    """No UI code path must call /api/v1/analyze. Only client (guard) and analyzer (comment) may mention it."""
    if not _FRONTEND_SRC.exists():
        return
    forbidden = []
    for path in list(_FRONTEND_SRC.rglob("*.ts")) + list(_FRONTEND_SRC.rglob("*.tsx")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "/api/v1/analyze" in text and path.name not in _ALLOWED_ANALYZE_MENTIONS:
            forbidden.append(str(path.relative_to(_REPO_ROOT)))
    assert not forbidden, (
        "UI must not reference /api/v1/analyze except in client.ts (guard) and analyzer.ts (comment). Found in: "
        + ", ".join(forbidden)
    )


def test_frontend_analyze_action_uses_pipeline_shadow_run() -> None:
    """Analyze action must call /pipeline/shadow/run."""
    if not _FRONTEND_SRC.exists():
        return
    pipeline_ts = _FRONTEND_SRC / "api" / "pipeline.ts"
    assert pipeline_ts.exists(), "app/frontend/src/api/pipeline.ts must exist"
    text = pipeline_ts.read_text(encoding="utf-8", errors="replace")
    assert "/api/v1/pipeline/shadow/run" in text, (
        "pipeline.ts must call /api/v1/pipeline/shadow/run"
    )
