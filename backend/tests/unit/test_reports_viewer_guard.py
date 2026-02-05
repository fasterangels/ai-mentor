"""
Unit tests for reports viewer: path safety and token guard.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from reports.viewer_guard import (
    check_reports_token,
    get_reports_root,
    reports_token_required,
    safe_path_under_reports,
)


def test_safe_path_under_reports_allows_relative_subpath(tmp_path: Path) -> None:
    """Allowed: path under reports root."""
    rel = "burn_in/run_123/summary.json"
    resolved = safe_path_under_reports(tmp_path, rel)
    assert resolved is not None
    assert resolved == (tmp_path / "burn_in" / "run_123" / "summary.json").resolve()


def test_safe_path_under_reports_blocks_traversal(tmp_path: Path) -> None:
    """Path traversal (..) must not escape reports root."""
    assert safe_path_under_reports(tmp_path, "../other/index.json") is None
    assert safe_path_under_reports(tmp_path, "burn_in/../../etc/passwd") is None
    assert safe_path_under_reports(tmp_path, "..") is None


def test_safe_path_under_reports_empty_path(tmp_path: Path) -> None:
    """Empty or blank path returns None."""
    assert safe_path_under_reports(tmp_path, "") is None
    assert safe_path_under_reports(tmp_path, "   ") is None


def test_safe_path_under_reports_strips_leading_slash(tmp_path: Path) -> None:
    """Leading slash is stripped so path is relative."""
    resolved = safe_path_under_reports(tmp_path, "/index.json")
    assert resolved is not None
    assert resolved == (tmp_path / "index.json").resolve()


def test_check_reports_token_allows_when_not_required() -> None:
    """When REPORTS_READ_TOKEN is not set, any or no token is allowed."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("REPORTS_READ_TOKEN", raising=False)
        os.environ.pop("REPORTS_READ_TOKEN", None)
        assert check_reports_token(None) is True
        assert check_reports_token("") is True
        assert check_reports_token("anything") is True


def test_check_reports_token_requires_match_when_set() -> None:
    """When REPORTS_READ_TOKEN is set, only matching token is allowed."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REPORTS_READ_TOKEN", "secret123")
        assert check_reports_token("secret123") is True
        assert check_reports_token("wrong") is False
        assert check_reports_token(None) is False
        assert check_reports_token("") is False


def test_reports_token_required() -> None:
    """reports_token_required reflects env."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("REPORTS_READ_TOKEN", raising=False)
        os.environ.pop("REPORTS_READ_TOKEN", None)
        assert reports_token_required() is False
        m.setenv("REPORTS_READ_TOKEN", "x")
        assert reports_token_required() is True
