"""
Sidecar entrypoint for desktop build: fixed port 8000, no console.

- Used only when packaging the backend as Tauri sidecar (PyInstaller).
- Imports the existing FastAPI app from main; runs uvicorn on 127.0.0.1:8000.
- Writes backend_port.json so Tauri can read base_url for health checks.
- Logs/markers to %LOCALAPPDATA%\\AI Mentor\\backend\\ (sidecar_started.txt, sidecar_crash.log, backend.log).

Packaging glue only — no changes to analyzer/pipeline/resolver/business logic.
"""
from __future__ import annotations

import os
import sys

# MUST be first: PyInstaller windowed build (console=False) leaves stdout/stderr None.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import json
import logging
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# When not frozen, ensure backend dir is on path so "from main import app" works
if not getattr(sys, "frozen", False):
    _backend_dir = Path(__file__).resolve().parent
    if str(_backend_dir) not in sys.path:
        sys.path.insert(0, str(_backend_dir))

SIDECAR_PORT = 8000


def _get_base_dir() -> Path:
    """Base dir for runtime/data: AI_MENTOR_BASE_DIR if set, else %LOCALAPPDATA%\\AI_Mentor."""
    base = os.environ.get("AI_MENTOR_BASE_DIR", "")
    if base:
        return Path(base)
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        local_app_data = os.path.expanduser("~")
    return Path(local_app_data) / "AI_Mentor"


# Diagnostics: %LOCALAPPDATA%\AI_Mentor\logs\ (app.log from Rust, backend.log from here)
BASE_DIR = _get_base_dir()
LOG_DIR = BASE_DIR / "logs"
RUNTIME_DIR = BASE_DIR / "runtime"
DATA_DIR = BASE_DIR / "data"

# Immediately create LOG_DIR, write first line to backend.log (flush), then marker.
_backend_log_error_path = None
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    backend_log = LOG_DIR / "backend.log"
    base_dir_str = str(BASE_DIR)
    with open(backend_log, "a", encoding="utf-8") as f:
        f.write(
            f"BACKEND_PROCESS_START pid={os.getpid()} port=8000 base_dir={base_dir_str}\n"
        )
        f.flush()
    (LOG_DIR / "sidecar_started.txt").write_text(
        f"started at {datetime.now(timezone.utc).isoformat()} pid={os.getpid()}\n",
        encoding="utf-8",
    )
except Exception as e:
    _backend_log_error_path = Path(os.environ.get("TEMP", os.path.expanduser("~"))) / "backend_log_error.txt"
    try:
        _backend_log_error_path.write_text(
            f"{datetime.now(timezone.utc).isoformat()} exception writing backend.log: {e!r}\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def _setup_file_logging() -> None:
    """Configure logging to LOG_DIR/backend.log (file only, plain Formatter)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "backend.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(file_handler)
    root.setLevel(logging.INFO)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.INFO)


def _write_port_file(port: int) -> None:
    """Write backend_port.json to RUNTIME_DIR (Tauri reads this)."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNTIME_DIR / "backend_port.json"
    data = {
        "port": port,
        "base_url": f"http://127.0.0.1:{port}",
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _set_packaged_env() -> None:
    """Set env for packaged runtime (DB under %LOCALAPPDATA%\\AI_Mentor\\data)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["AI_MENTOR_PACKAGED"] = "1"


def custom_plain_log_config() -> dict:
    """Minimal log_config for uvicorn: file only, plain Formatter (no DefaultFormatter / isatty)."""
    log_file = LOG_DIR / "backend.log"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {
                "()": "logging.Formatter",
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "filename": str(log_file),
                "encoding": "utf-8",
                "formatter": "plain",
            },
        },
        "loggers": {
            "uvicorn": {"level": "INFO", "handlers": ["file"], "propagate": False},
            "uvicorn.error": {"level": "INFO", "handlers": ["file"], "propagate": False},
            "uvicorn.access": {"level": "INFO", "handlers": ["file"], "propagate": False},
        },
    }


def main() -> int:
    if getattr(sys, "frozen", False):
        _set_packaged_env()
    try:
        _setup_file_logging()
        _write_port_file(SIDECAR_PORT)
        logger = logging.getLogger(__name__)
        backend_log = LOG_DIR / "backend.log"
        with open(backend_log, "a", encoding="utf-8") as f:
            f.write("Uvicorn running on http://127.0.0.1:8000\n")
            f.flush()
        logger.info(
            "BACKEND_START __file__=%s host=127.0.0.1 port=%s CORS_allow_origins=[http://tauri.localhost,...]",
            __file__,
            SIDECAR_PORT,
        )
        from main import app
        import uvicorn
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_config=custom_plain_log_config(),
            access_log=False,
        )
        return 0
    except Exception:
        crash_log = LOG_DIR / "sidecar_crash.log"
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(crash_log, "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.now(timezone.utc).isoformat()} ---\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        time.sleep(10)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
