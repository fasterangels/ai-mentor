# Ensure backend is on sys.path when pytest is run from repo root (e.g. pytest backend/tests/)
import sys
from pathlib import Path

_tests_dir = Path(__file__).resolve().parent
_backend = _tests_dir.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
