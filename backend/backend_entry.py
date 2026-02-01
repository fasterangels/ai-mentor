"""
Packaging entrypoint: no-console backend with file logging and port selection.

- Logs to %LOCALAPPDATA%\\AI_Mentor\\logs\\
- Picks first free port in 8000..8010
- Writes backend_port.json to %LOCALAPPDATA%\\AI_Mentor\\runtime\\
- Starts uvicorn with FastAPI app on 127.0.0.1 only (offline/local).

Run as script from backend dir: python backend_entry.py
Or as frozen exe (PyInstaller --noconsole).
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

# When not frozen, ensure backend dir is on path so "from main import app" works
if not getattr(sys, "frozen", False):
    _backend_dir = Path(__file__).resolve().parent
    if str(_backend_dir) not in sys.path:
        sys.path.insert(0, str(_backend_dir))

def _get_base_dir() -> Path:
    """Base dir for logs, runtime, and (when frozen) data: %LOCALAPPDATA%\\AI_Mentor."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        local_app_data = os.path.expanduser("~")
    return Path(local_app_data) / "AI_Mentor"


BASE_DIR = _get_base_dir()
LOG_DIR = BASE_DIR / "logs"
RUNTIME_DIR = BASE_DIR / "runtime"
DATA_DIR = BASE_DIR / "data"


def _setup_file_logging() -> None:
    """Configure logging to a file under BASE_DIR/logs. Create dirs if needed."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "backend.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(file_handler)
    root.setLevel(logging.INFO)
    # Reduce console noise when running as exe (no console anyway)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.INFO)


def _pick_port() -> int:
    """Return first free port in 8000..8010. Bind test then close."""
    for port in range(8000, 8011):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return 8000  # fallback (may fail later if all busy)


def _write_port_file(port: int) -> None:
    """Write backend_port.json to RUNTIME_DIR."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNTIME_DIR / "backend_port.json"
    data = {
        "port": port,
        "base_url": f"http://127.0.0.1:{port}",
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _set_packaged_env() -> None:
    """Set env for packaged runtime so core.config uses %LOCALAPPDATA%\\AI_Mentor\\data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["AI_MENTOR_PACKAGED"] = "1"


def main() -> int:
    # When packaged, use LOCALAPPDATA paths for DB and logs
    if getattr(sys, "frozen", False):
        _set_packaged_env()
    _setup_file_logging()
    port = _pick_port()
    _write_port_file(port)
    logger = logging.getLogger(__name__)
    logger.info("Backend entry: port=%s, base_dir=%s", port, BASE_DIR)
    # Import app after env and logging are set
    from main import app
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
