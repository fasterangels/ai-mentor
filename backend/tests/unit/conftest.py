# Ensure backend is at sys.path[0] when collecting unit tests (e.g. pipeline, replay)
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
_str_backend = str(_backend)
if _str_backend not in sys.path:
    sys.path.insert(0, _str_backend)
