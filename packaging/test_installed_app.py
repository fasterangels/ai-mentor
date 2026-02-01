"""
Automated installed-build test: install NSIS -> launch app -> wait /health 200 -> POST /api/v1/analyze -> PASS.

Finds latest NSIS installer in src-tauri/target/release/bundle/nsis, runs silent install to a temp
dir, launches the installed desktop app, waits up to 10s for GET /health 200, then POST /api/v1/analyze
with minimal payload. Prints last 80 lines of app.log and backend.log.
Exit code 0 only if both /health and analyze succeed.

Usage:
  python packaging/test_installed_app.py [--repo-root PATH] [--keep-install]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = _THIS_DIR.parent

NSIS_SUBDIR = Path("app/frontend/src-tauri/target/release/bundle/nsis")
HEALTH_URL = "http://127.0.0.1:8000/health"
ANALYZE_URL = "http://127.0.0.1:8000/api/v1/analyze"
MAX_WAIT_HEALTH_S = 10
MAX_WAIT_APP_LOG_S = 25
POLL_INTERVAL_S = 0.5
LOG_TAIL_LINES = 80
BUILD_ID_PREFIX = "BUILD_ID="
BACKEND_PATH_EXISTS = "exists=true"
BACKEND_SPAWN_OK = "BACKEND_SPAWN_OK"


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
    # NSIS: /S = silent, /D=path must be last (no quotes)
    cmd = [str(installer), "/S", f"/D={install_dir}"]
    subprocess.run(cmd, check=True, timeout=180)


def _find_app_exe(install_dir: Path) -> Path | None:
    """Find main app exe (not Uninstall*, not ai-mentor-backend*)."""
    for p in install_dir.rglob("*.exe"):
        name = p.name
        if name.startswith("Uninstall"):
            continue
        if "ai-mentor-backend" in name.lower():
            continue
        # Prefer top-level exe (Tauri app)
        if p.parent == install_dir:
            return p
    for p in install_dir.rglob("*.exe"):
        name = p.name
        if name.startswith("Uninstall") or "ai-mentor-backend" in name.lower():
            continue
        return p
    return None


def _get(url: str, timeout: int = 5) -> tuple[int, bytes]:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _post(url: str, data: bytes, timeout: int = 10) -> tuple[int, bytes]:
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


def _app_log_content(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def main() -> int:
    repo_root = DEFAULT_REPO_ROOT
    keep = False
    args = list(sys.argv[1:])
    while args:
        if args[0] == "--repo-root" and len(args) > 1:
            repo_root = Path(args[1])
            args = args[2:]
        elif args[0] == "--keep-install":
            keep = True
            args = args[1:]
        else:
            args = args[1:]

    if sys.platform != "win32":
        print("test_installed_app: Windows only (NSIS install)")
        return 1

    installer = _find_latest_installer(repo_root)
    if not installer:
        print(f"No NSIS installer found under {repo_root / NSIS_SUBDIR}")
        return 1
    print(f"Installer: {installer}")

    install_dir = Path(tempfile.gettempdir()) / "AI_Mentor_Installed_Test"
    if install_dir.exists():
        try:
            for f in install_dir.iterdir():
                f.unlink()
            install_dir.rmdir()
        except Exception:
            pass
    install_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("Installing (silent)...")
        _install_silent(installer, install_dir)
    except subprocess.CalledProcessError as e:
        print(f"Install failed: {e}")
        return 1
    except Exception as e:
        print(f"Install error: {e}")
        return 1

    app_exe = _find_app_exe(install_dir)
    if not app_exe:
        print(f"No app exe found under {install_dir}")
        return 1
    print(f"App exe: {app_exe}")

    # Clear or truncate logs so we see only this run (optional; we tail last 80 anyway)
    log_dir = _log_dir()
    proc = subprocess.Popen(
        [str(app_exe)],
        cwd=str(app_exe.parent),
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    app_log_path = log_dir / "app.log"
    backend_log_path = log_dir / "backend.log"
    try:
        # Wait for app.log to contain BUILD_ID= and BACKEND_PATH exists=true (or BACKEND_SPAWN_OK)
        deadline_log = time.monotonic() + MAX_WAIT_APP_LOG_S
        has_build_id = False
        has_backend_ok = False
        while time.monotonic() < deadline_log:
            content = _app_log_content(app_log_path)
            if BUILD_ID_PREFIX in content:
                has_build_id = True
            if (BACKEND_PATH_EXISTS in content or BACKEND_SPAWN_OK in content):
                has_backend_ok = True
            if has_build_id and has_backend_ok:
                print(f"app.log: {BUILD_ID_PREFIX!r} and backend path exists / BACKEND_SPAWN_OK detected")
                break
            time.sleep(POLL_INTERVAL_S)
        if not has_build_id:
            print("app.log did not contain BUILD_ID= within timeout")
            proc.terminate()
            proc.wait(timeout=5)
            print("--- app.log (last 80) ---")
            for line in _tail(app_log_path, LOG_TAIL_LINES):
                print(line)
            return 1
        if not has_backend_ok:
            print("app.log did not contain BACKEND_PATH exists=true or BACKEND_SPAWN_OK within timeout")
            proc.terminate()
            proc.wait(timeout=5)
            print("--- app.log (last 80) ---")
            for line in _tail(app_log_path, LOG_TAIL_LINES):
                print(line)
            return 1

        deadline = time.monotonic() + MAX_WAIT_HEALTH_S
        health_ok = False
        while time.monotonic() < deadline:
            try:
                status, _ = _get(HEALTH_URL, timeout=2)
                if status == 200:
                    health_ok = True
                    print("/health -> 200")
                    break
            except Exception:
                pass
            time.sleep(POLL_INTERVAL_S)
        if not health_ok:
            print("/health did not return 200 within 10s")
            proc.terminate()
            proc.wait(timeout=5)
            print("--- app.log (last 80) ---")
            for line in _tail(app_log_path, LOG_TAIL_LINES):
                print(line)
            print("--- backend.log (last 80) ---")
            for line in _tail(backend_log_path, LOG_TAIL_LINES):
                print(line)
            return 1

        try:
            status, body = _post(ANALYZE_URL, b"{}", timeout=15)
            if status != 200:
                print(f"POST /api/v1/analyze -> {status} body={body[:500]!r}")
                proc.terminate()
                proc.wait(timeout=5)
                print("--- app.log (last 80) ---")
                for line in _tail(app_log_path, LOG_TAIL_LINES):
                    print(line)
                print("--- backend.log (last 80) ---")
                for line in _tail(backend_log_path, LOG_TAIL_LINES):
                    print(line)
                return 1
            print("POST /api/v1/analyze -> 200")
            json.loads(body.decode("utf-8", errors="replace"))
        except Exception as e:
            print(f"POST /api/v1/analyze error: {e}")
            proc.terminate()
            proc.wait(timeout=5)
            return 1
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        time.sleep(1)
        if not keep:
            try:
                for f in install_dir.rglob("*"):
                    if f.is_file():
                        f.unlink()
                for d in sorted(install_dir.rglob("*"), key=lambda x: -len(x.parts)):
                    if d.is_dir():
                        d.rmdir()
                install_dir.rmdir()
            except Exception:
                pass

    app_log_path = log_dir / "app.log"
    backend_log_path = log_dir / "backend.log"
    print("--- app.log (last 80) ---")
    print(f"  path: {app_log_path}")
    lines_app = _tail(app_log_path, LOG_TAIL_LINES)
    for line in lines_app:
        print(line)
    if not lines_app:
        print("  (no lines or file missing)")
    print("--- backend.log (last 80) ---")
    print(f"  path: {backend_log_path}")
    lines_backend = _tail(backend_log_path, LOG_TAIL_LINES)
    for line in lines_backend:
        print(line)
    if not lines_backend:
        print("  (no lines or file missing)")
    # Final assertion: BUILD_ID must be present in app.log
    app_content = _app_log_content(app_log_path)
    if BUILD_ID_PREFIX not in app_content:
        print("FAIL: BUILD_ID= not found in app.log")
        return 1
    if BACKEND_PATH_EXISTS not in app_content and BACKEND_SPAWN_OK not in app_content:
        print("FAIL: BACKEND_PATH exists=true or BACKEND_SPAWN_OK not found in app.log")
        return 1
    print("INSTALLED-BUILD TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
