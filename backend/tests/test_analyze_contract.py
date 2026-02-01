"""
Contract lock: assert critical keys in analyze API response JSON.
No schema validation — guardrails only. Fail with explicit message if keys missing.

Run from repo root: python -m pytest backend/tests/test_analyze_contract.py -v
Or from backend: python -m pytest tests/test_analyze_contract.py -v
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _find_match_id(obj: dict) -> bool:
    """Return True if match_id appears anywhere in obj (top-level or nested)."""
    if "match_id" in obj and obj["match_id"] is not None:
        return True
    for v in obj.values():
        if isinstance(v, dict) and _find_match_id(v):
            return True
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and _find_match_id(item):
                    return True
    return False


def test_analyze_response_critical_keys():
    """Analyze response must have resolver.status, analyzer (outcome or decisions), match_id somewhere."""
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    sample_path = fixtures_dir / "analyze_response_sample.json"
    if not sample_path.exists():
        pytest.fail(f"Fixture not found: {sample_path}")

    data = json.loads(sample_path.read_text(encoding="utf-8"))

    if "resolver" not in data or not isinstance(data["resolver"], dict):
        pytest.fail("Analyze response must contain resolver (object). Missing key: resolver")
    if "status" not in data["resolver"]:
        pytest.fail("Analyze response must contain resolver.status. Missing key: resolver.status")

    analyzer = data.get("analyzer")
    if analyzer is None or not isinstance(analyzer, dict):
        pytest.fail("Analyze response must contain analyzer (object). Missing key: analyzer")
    has_outcome = "outcome" in analyzer
    has_decisions = "decisions" in analyzer
    has_status = "status" in analyzer
    if not (has_outcome or has_decisions or has_status):
        pytest.fail(
            "Analyze response must contain analyzer.outcome OR analyzer.decisions OR analyzer.status. "
            "Missing: analyzer.outcome, analyzer.decisions, analyzer.status"
        )

    if not _find_match_id(data):
        pytest.fail("Analyze response must contain match_id somewhere (top-level or nested). Missing: match_id")
