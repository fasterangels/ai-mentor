# Ensure backend is at sys.path[0] when pytest runs (from repo root or from backend dir)
import sys
from pathlib import Path

_tests_dir = Path(__file__).resolve().parent
_backend = _tests_dir.parent
_str_backend = str(_backend)
if sys.path[0:1] != [_str_backend]:
    sys.path.insert(0, _str_backend)
