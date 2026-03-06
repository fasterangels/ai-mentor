"""
End-to-end test: NSIS silent install -> AI_Mentor_Backend task registered + run -> GET /health -> POST /api/v1/analyze (expect 501, ANALYZE_ENDPOINT_NOT_SUPPORTED).
Uses cmd/subprocess only (NO PowerShell). Exit 0 only if ALL pass.
Tees exact console output to packaging/artifacts/e2e_stdout.txt (for CI artifacts).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = _THIS_DIR.parent
ARTIFACTS_DIR_NAME = Path("packaging/artifacts")
E2E_STDOUT_NAME = "e2e_stdout.txt"


class _Tee:
    """Write to multiple streams (e.g. stdout + file)."""

    def __init__(self, *writers):
        self._writers = writers

    def write(self, data: str) -> None:
        for w in self._writers:
            w.write(data)

    def flush(self) -> None:
        for w in self._writers:
            w.flush()

NSIS_SUBDIR = Path("app/frontend/src-tauri/target/release/bundle/nsis")
HEALTH_URL = "http://127.0.0.1:8000/health"
ANALYZE_URL = "http://127.0.0.1:8000/api/v1/analyze"
TASK_NAME = "AI_Mentor_Backend"
MAX_WAIT_HEALTH_S = 30
POLL_INTERVAL_S = 0.5
LOG_TAIL_LINES = 120
HEALTH_BODY_MAX = 1024
ANALYZE_BODY_MAX = 2048
ANALYZE_BODY = b'{"home_team":"PAOK","away_team":"AEK"}'


def _log_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "AI_Mentor" / "logs"


def _find_latest_installer(repo_root: Path) -> Path | None:
    nsis_dir = repo_root / NSIS_SUBDIR
    if not nsis_dir.is_dir():
        return None
    exes = list(nsis_dir.glob("*.exe"))
    if not exes:
        return None
    return max(exes, key=lambda p: p.stat().st_mtime)


def _install_silent(installer: Path, install_dir: Path) -> None:
    cmd = [str(installer), "/S", f"/D={install_dir}"]
    subprocess.run(cmd, check=True, timeout=300)


def _schtasks_query(task_name: str) -> tuple[int, str]:
    """Run schtasks /Query /TN TASK_NAME; return (returncode, stdout+stderr)."""
    proc = subprocess.run(
        ["schtasks", "/Query", "/TN", task_name],
        capture_output=True,
        text=True,
        timeout=10,
        shell=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _schtasks_run(task_name: str) -> tuple[int, str]:
    """Run schtasks /Run /TN TASK_NAME; return (returncode, stdout+stderr)."""
    proc = subprocess.run(
        ["schtasks", "/Run", "/TN", task_name],
        capture_output=True,
        text=True,
        timeout=10,
        shell=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _get(url: str, timeout: int = 5) -> tuple[int, bytes]:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _post(url: str, data: bytes, timeout: int = 15) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _tail(path: Path, n: int) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-n:] if len(lines) > n else lines
    except Exception:
        return []


def main() -> int:
    repo_root = DEFAULT_REPO_ROOT
    args = list(sys.argv[1:])
    while args:
        if args[0] == "--repo-root" and len(args) > 1:
            repo_root = Path(args[1])
            args = args[2:]
        else:
            args = args[1:]

    if sys.platform != "win32":
        print("test_installed_task_end_to_end: Windows only")
        return 1

    # Tee console output to packaging/artifacts/e2e_stdout.txt (CI artifacts)
    artifacts_dir = repo_root / ARTIFACTS_DIR_NAME
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    tee_path = artifacts_dir / E2E_STDOUT_NAME
    real_stdout = sys.stdout
    tee_file = open(tee_path, "w", encoding="utf-8")
    sys.stdout = _Tee(real_stdout, tee_file)
    try:
        return _run_e2e(repo_root)
    finally:
        sys.stdout = real_stdout
        tee_file.close()


def _run_e2e(repo_root: Path) -> int:
    """Run E2E steps; all print() is teed to e2e_stdout.txt by main()."""
    installer = _find_latest_installer(repo_root)
    if not installer:
        print(f"FAIL: No NSIS installer under {repo_root / NSIS_SUBDIR}")
        return 1
    print(f"Installer path: {installer}")

    install_dir = Path(tempfile.gettempdir()) / "AI_Mentor_Task_E2E_Test"
    if install_dir.exists():
        try:
            for f in install_dir.iterdir():
                f.unlink()
            install_dir.rmdir()
        except Exception:
            pass
    install_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("Silent install...")
        _install_silent(installer, install_dir)
    except subprocess.CalledProcessError as e:
        print(f"FAIL: Install failed: {e}")
        return 1
    except Exception as e:
        print(f"FAIL: Install error: {e}")
        return 1

    # Verify task exists
    rc, query_out = _schtasks_query(TASK_NAME)
    print("--- schtasks /Query output ---")
    print(query_out)
    if rc != 0:
        print(f"FAIL: schtasks /Query returned {rc}")
        return 1

    # Run task (ensure backend is started; installer may have already run it)
    print("--- schtasks /Run ---")
    rc_run, run_out = _schtasks_run(TASK_NAME)
    print(run_out or "(no output)")
    if rc_run != 0:
        print(f"WARN: schtasks /Run returned {rc_run}")
    time.sleep(3)

    # GET /health (retry up to MAX_WAIT_HEALTH_S)
    deadline = time.monotonic() + MAX_WAIT_HEALTH_S
    health_status = 0
    health_body = b""
    while time.monotonic() < deadline:
        try:
            health_status, health_body = _get(HEALTH_URL, timeout=5)
            if health_status == 200:
                break
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_S)
    health_preview = (health_body[:HEALTH_BODY_MAX] or b"").decode("utf-8", errors="replace")
    print("--- health status/body ---")
    print(f"status={health_status} body={health_preview!r}")
    if health_status != 200:
        print("FAIL: /health did not return 200")
        log_path = _log_dir() / "backend.log"
        print(f"--- backend.log (last {LOG_TAIL_LINES}) ---")
        for line in _tail(log_path, LOG_TAIL_LINES):
            print(line)
        return 1

    # POST /api/v1/analyze → 501 and ANALYZE_ENDPOINT_NOT_SUPPORTED (disabled by design; use /pipeline/shadow/run)
    try:
        analyze_status, analyze_body = _post(ANALYZE_URL, ANALYZE_BODY, timeout=15)
    except Exception as e:
        print(f"FAIL: POST /api/v1/analyze error: {e}")
        return 1
    analyze_preview = (analyze_body[:ANALYZE_BODY_MAX] or b"").decode("utf-8", errors="replace")
    print("--- analyze status/body (first 2KB) ---")
    print(f"status={analyze_status} body={analyze_preview!r}")
    if analyze_status != 501:
        print("FAIL: POST /api/v1/analyze did not return 501")
        log_path = _log_dir() / "backend.log"
        print(f"--- backend.log (last {LOG_TAIL_LINES}) ---")
        for line in _tail(log_path, LOG_TAIL_LINES):
            print(line)
        return 1
    try:
        data = json.loads(analyze_body.decode("utf-8", errors="replace"))
        err = (data or {}).get("error") or {}
        if err.get("code") != "ANALYZE_ENDPOINT_NOT_SUPPORTED":
            print("FAIL: analyze 501 response missing error.code ANALYZE_ENDPOINT_NOT_SUPPORTED")
            return 1
    except Exception as e:
        print(f"FAIL: analyze response is not valid JSON: {e}")
        return 1

    # Proof: last 120 lines of backend.log
    log_path = _log_dir() / "backend.log"
    print(f"--- backend.log (last {LOG_TAIL_LINES}) ---")
    for line in _tail(log_path, LOG_TAIL_LINES):
        print(line)

    print("TASK E2E TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
