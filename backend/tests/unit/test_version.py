"""
Unit tests for version: get_version, is_semver, CLI version output.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from version import get_version, is_semver


def test_is_semver_valid() -> None:
    assert is_semver("1.0.0") is True
    assert is_semver("0.0.1") is True
    assert is_semver("1.0.0-alpha") is True
    assert is_semver("2.1.3-beta.1") is True


def test_is_semver_invalid() -> None:
    assert is_semver("") is False
    assert is_semver("1.0") is False
    assert is_semver("v1.0.0") is False
    assert is_semver("1.0.0.1") is False


def test_get_version_returns_string() -> None:
    v = get_version()
    assert isinstance(v, str)
    assert len(v) >= 1


def test_get_version_semver_when_version_file_present() -> None:
    """When VERSION file exists at repo root, get_version returns a string (semver or 0.0.0)."""
    v = get_version()
    assert v in ("0.0.0", "1.0.0") or is_semver(v)


def test_cli_version_output() -> None:
    """ai-mentor --version (python tools/ops.py --version) prints version string to stdout."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    ops_py = repo_root / "tools" / "ops.py"
    if not ops_py.is_file():
        pytest.skip("tools/ops.py not found (run from repo root)")
    result = subprocess.run(
        [sys.executable, str(ops_py), "--version"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    out = (result.stdout or "").strip()
    assert out, "expected non-empty version"
    assert is_semver(out) or out == "0.0.0", f"expected semver or 0.0.0, got {out!r}"
