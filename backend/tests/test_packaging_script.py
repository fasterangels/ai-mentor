from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import build_packaging.build_app as build_module  # type: ignore[import]


def test_build_script_import() -> None:
    assert hasattr(build_module, "build")

