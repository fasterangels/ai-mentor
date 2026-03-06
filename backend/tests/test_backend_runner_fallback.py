"""
Test backend runner interpreter fallback: when 'python' and 'python3' are missing,
the runner attempts py -3.11 next (Windows Python Launcher).

Run from repo root: python -m pytest backend/tests/test_backend_runner_fallback.py -v
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure repo root on path for backend imports
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.runner.start_backend import main  # type: ignore[import]


def test_fallback_to_py_311_when_python_and_python3_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """When 'python' and 'python3' raise FileNotFoundError, runner tries ['py', '-3.11'] next."""
    backend_root = Path(__file__).resolve().parents[1]
    app_server_path = str(backend_root / "app" / "app_server.py")

    # So sys.executable is not used as first candidate (treat as not a real file)
    def isfile(path: str) -> bool:
        if path == sys.executable:
            return False
        return os.path.isfile(path)

    monkeypatch.setattr(os.path, "isfile", isfile)

    popen_calls: list[list] = []
    real_popen = subprocess.Popen

    def fake_popen(args: list, *pargs: object, **kwargs: object) -> MagicMock:
        popen_calls.append(list(args))
        first = args[0] if args else ""
        if first in ("python", "python3"):
            raise FileNotFoundError(f"no such interpreter: {first}")
        # Allow py -3.11 (and py -3) to succeed
        return MagicMock()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    main()

    # Should have tried python, python3, then py -3.11 (and succeeded there)
    assert len(popen_calls) >= 3
    assert popen_calls[0] == ["python", app_server_path]
    assert popen_calls[1] == ["python3", app_server_path]
    assert popen_calls[2] == ["py", "-3.11", app_server_path]
