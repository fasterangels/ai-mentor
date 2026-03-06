"""
Windows Service host for AI Mentor Backend.
Runs as service AI_Mentor_Backend; in SvcDoRun launches ai-mentor-backend.exe
and keeps it running. Logs to %LOCALAPPDATA%\\AI_Mentor\\logs\\backend.log.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# When running as service, argv may be minimal; we need pywin32
try:
    import win32serviceutil
    import win32service
    import win32event
    import win32api
except ImportError:
    win32serviceutil = None  # type: ignore
    win32service = None  # type: ignore
    win32event = None  # type: ignore
    win32api = None  # type: ignore

SERVICE_NAME = "AI_Mentor_Backend"
DISPLAY_NAME = "AI Mentor Backend"
BACKEND_EXE_NAME = "ai-mentor-backend.exe"


def _get_local_app_data() -> Path:
    v = os.environ.get("LOCALAPPDATA", "")
    if v:
        return Path(v)
    return Path(os.path.expanduser("~"))


def _get_base_dir() -> Path:
    base = os.environ.get("AI_MENTOR_BASE_DIR", "")
    if base:
        return Path(base)
    return _get_local_app_data() / "AI_Mentor"


def _get_service_dir() -> Path:
    """Folder where ai-mentor-service.exe and ai-mentor-backend.exe live."""
    if getattr(sys, "frozen", False) and sys.executable:
        return Path(sys.executable).resolve().parent
    # Dev: same folder as this script
    return Path(__file__).resolve().parent


def _get_backend_exe_path() -> Path:
    return _get_service_dir() / BACKEND_EXE_NAME


def _ensure_dirs() -> None:
    base = _get_base_dir()
    (base / "service").mkdir(parents=True, exist_ok=True)
    (base / "logs").mkdir(parents=True, exist_ok=True)


def _log_line(msg: str) -> None:
    base = _get_base_dir()
    log_path = base / "logs" / "backend.log"
    base.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
            f.flush()
    except Exception:
        pass


if win32serviceutil is not None and win32service is not None:

    class AIMentorBackendService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = DISPLAY_NAME
        _svc_description_ = "Runs AI Mentor backend API (http://127.0.0.1:8000)."

        def __init__(self, args: list[str]) -> None:
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.child_process: subprocess.Popen | None = None

        def SvcDoRun(self) -> None:
            _ensure_dirs()
            exe_path = _get_backend_exe_path()
            log_path = _get_base_dir() / "logs" / "backend.log"
            env = os.environ.copy()
            env["AI_MENTOR_BASE_DIR"] = str(_get_base_dir())
            env["AI_MENTOR_PORT"] = "8000"
            env["AI_MENTOR_PACKAGED"] = "1"

            try:
                # Start child with PIPE so we write SERVICE_START first (flushed), then stream stdout to log
                self.child_process = subprocess.Popen(
                    [str(exe_path)],
                    cwd=str(_get_service_dir()),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=False,
                )
                pid = self.child_process.pid
                at = datetime.now(timezone.utc).isoformat()
                first_line = f"SERVICE_START pid={pid} exe_path={exe_path} at={at}"
                with open(log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(first_line + "\n")
                    log_file.flush()
                _log_line(first_line)

                def stream_to_log() -> None:
                    if self.child_process is None or self.child_process.stdout is None:
                        return
                    with open(log_path, "ab") as f:
                        while True:
                            buf = self.child_process.stdout.read(4096)
                            if not buf:
                                break
                            f.write(buf)
                            f.flush()

                import threading
                t = threading.Thread(target=stream_to_log, daemon=True)
                t.start()
            except Exception as e:
                _log_line(f"SERVICE_START_ERROR exe_path={exe_path} error={e!r}")
                return

            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

        def SvcStop(self) -> None:
            _log_line("SERVICE_STOP requested")
            win32event.SetEvent(self.stop_event)
            if self.child_process is not None:
                try:
                    self.child_process.terminate()
                    self.child_process.wait(timeout=10)
                except Exception:
                    try:
                        self.child_process.kill()
                    except Exception:
                        pass
                self.child_process = None
            _log_line("SERVICE_STOP completed")

else:
    AIMentorBackendService = None  # type: ignore
