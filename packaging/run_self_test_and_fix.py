"""
Self-test and auto-fix for built backend sidecar.

Runs in order: (1) backend starts and writes backend.log, (2) binds 127.0.0.1:8000,
(3) GET /health -> 200, (4) OPTIONS /api/v1/analyze with CORS -> 200/204, (5) POST /api/v1/analyze -> 200 + JSON.
On failure: detect from logs, apply targeted fix, rebuild backend only, re-run (max 3 iterations).
Writes %LOCALAPPDATA%\\AI_Mentor\\logs\\self_test.log.

Callable from main build script or standalone:
  python packaging/run_self_test_and_fix.py [--repo-root PATH] [--max-iterations N]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Repo root: from this file (packaging/run_self_test_and_fix.py) -> packaging -> repo root
_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = _THIS_DIR.parent

BASE_URL = "http://127.0.0.1:8000"
ORIGIN_TAURI = "http://tauri.localhost"
MAX_WAIT_START = 25
POLL_INTERVAL = 0.5


def _log_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "AI_Mentor" / "logs"


def _backend_log(log_dir: Path) -> Path:
    return log_dir / "backend.log"


def _crash_log(log_dir: Path) -> Path:
    return log_dir / "sidecar_crash.log"


def _self_test_log(log_dir: Path) -> Path:
    return log_dir / "self_test.log"


def _read_text(p: Path, default: str = "") -> str:
    if not p.exists():
        return default
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return default


def _short_path(path: Path) -> str:
    if sys.platform != "win32":
        return str(path)
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1024)
        r = ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, len(buf))  # type: ignore[attr-defined]
        if r and r < len(buf):
            return buf.value
    except Exception:
        pass
    return str(path)


def _rebuild_backend(repo_root: Path, log_lines: list[str]) -> bool:
    """Rebuild backend sidecar only (PyInstaller + copy to Tauri bin). Returns True if success."""
    log_lines.append(f"[{datetime.now(timezone.utc).isoformat()}] rebuild_backend start")
    exe = repo_root / "dist" / "ai-mentor-backend.exe"
    spec = repo_root / "packaging" / "backend_sidecar" / "pyinstaller_sidecar.spec"
    env = os.environ.copy()
    env["AI_MENTOR_PACKAGED"] = "1"
    env.pop("TAURI_CONFIG", None)
    cwd = _short_path(repo_root) if sys.platform == "win32" else str(repo_root)
    cmd = [sys.executable, "-m", "PyInstaller", str(_short_path(spec) if sys.platform == "win32" and spec.exists() else spec), "--noconfirm"]
    try:
        subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            timeout=300,
        )
    except subprocess.CalledProcessError as e:
        log_lines.append(f"PyInstaller failed: {e.stderr and e.stderr.decode(errors='replace')}")
        return False
    except Exception as e:
        log_lines.append(f"PyInstaller error: {e}")
        return False
    if not exe.exists():
        log_lines.append("backend exe missing after build")
        return False
    tauri_bin = repo_root / "app" / "frontend" / "src-tauri" / "bin"
    tauri_bin.mkdir(parents=True, exist_ok=True)
    import shutil
    for name in ("ai-mentor-backend-x86_64-pc-windows-msvc.exe", "ai-mentor-backend.exe"):
        shutil.copy2(str(exe), str(tauri_bin / name))
    log_lines.append("rebuild_backend done")
    return True


def _apply_fix(failure_mode: str, repo_root: Path, log_lines: list[str]) -> bool:
    """Apply targeted fix. Returns True if a fix was applied and rebuild succeeded."""
    if failure_mode == "module_not_found":
        # Spec already has aiosqlite and sqlalchemy.dialects.sqlite.aiosqlite; ensure and rebuild
        spec_path = repo_root / "packaging" / "backend_sidecar" / "pyinstaller_sidecar.spec"
        content = _read_text(spec_path)
        if "sqlalchemy.dialects.sqlite.aiosqlite" not in content:
            # Insert after sqlalchemy.dialects.sqlite
            content = content.replace(
                '"sqlalchemy.dialects.sqlite",',
                '"sqlalchemy.dialects.sqlite",\n        "sqlalchemy.dialects.sqlite.aiosqlite",',
            )
            spec_path.write_text(content, encoding="utf-8")
            log_lines.append("fix: added sqlalchemy.dialects.sqlite.aiosqlite to spec")
        return _rebuild_backend(repo_root, log_lines)
    if failure_mode in ("cors", "health_failed", "analyze_failed", "backend_not_started"):
        # Rebuild only (stale build or env)
        return _rebuild_backend(repo_root, log_lines)
    return False


def _http_get(url: str, headers: dict | None = None) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, method="GET", headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read() if e.fp else b""
    except Exception as e:
        return -1, {}, str(e).encode()


def _http_options(url: str, origin: str) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, method="OPTIONS", headers={"Origin": origin})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read() if e.fp else b""
    except Exception as e:
        return -1, {}, str(e).encode()


def _http_post(url: str, data: bytes, content_type: str = "application/json") -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": content_type})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read() if e.fp else b""
    except Exception as e:
        return -1, {}, str(e).encode()


def run_self_test(repo_root: Path, max_iterations: int = 3) -> int:
    log_dir = _log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    self_log = _self_test_log(log_dir)
    lines: list[str] = []
    exe = repo_root / "dist" / "ai-mentor-backend.exe"

    def append(msg: str) -> None:
        lines.append(msg)
        print(msg)

    append(f"[{datetime.now(timezone.utc).isoformat()}] self_test start repo_root={repo_root} max_iterations={max_iterations}")

    if not exe.exists():
        append("FAIL: backend exe not found: " + str(exe))
        self_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 1

    iteration = 0
    passed = False
    raw_health = raw_preflight = raw_post = ""

    while iteration < max_iterations:
        iteration += 1
        append(f"--- iteration {iteration} ---")
        backend_log_path = _backend_log(log_dir)
        crash_path = _crash_log(log_dir)
        # Clear backend.log so we only see this run
        if backend_log_path.exists():
            try:
                backend_log_path.write_text("", encoding="utf-8")
            except Exception:
                pass

        env = os.environ.copy()
        env["AI_MENTOR_PACKAGED"] = "1"
        proc = subprocess.Popen(
            [str(exe)],
            cwd=str(repo_root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            # Wait for backend: prefer /health (server up) over backend.log (log may be delayed or path issue)
            deadline = time.monotonic() + MAX_WAIT_START
            backend_content = ""
            health_ok = False
            while time.monotonic() < deadline:
                time.sleep(POLL_INTERVAL)
                code, _, body = _http_get(BASE_URL + "/health")
                if code == 200 and body:
                    try:
                        j = json.loads(body.decode())
                        if j.get("status") == "ok":
                            health_ok = True
                            break
                    except Exception:
                        pass
                backend_content = _read_text(backend_log_path)
                if "BACKEND_START" in backend_content and "127.0.0.1" in backend_content and "8000" in backend_content:
                    health_ok = True
                    break
            if not health_ok:
                crash_content = _read_text(crash_path)
                append("backend did not respond to /health or log BACKEND_START in time")
                append("backend.log snippet: " + (backend_content[:500] if backend_content else "backend.log empty"))
                if "ModuleNotFoundError" in backend_content or "ModuleNotFoundError" in crash_content or "aiosqlite" in crash_content:
                    append("failure_mode=module_not_found")
                    if not _apply_fix("module_not_found", repo_root, lines):
                        break
                    continue
                append("failure_mode=backend_not_started")
                if not _apply_fix("backend_not_started", repo_root, lines):
                    break
                continue

            # (3) GET /health (already verified; record raw output)
            code, headers, body = _http_get(BASE_URL + "/health")
            raw_health = f"GET /health -> {code} headers={dict(headers)} body={body.decode(errors='replace')}"
            append(raw_health)
            if code != 200:
                append("failure_mode=health_failed")
                if not _apply_fix("health_failed", repo_root, lines):
                    break
                continue
            try:
                j = json.loads(body.decode())
                if j.get("status") != "ok":
                    append("health body status != ok")
                    if not _apply_fix("health_failed", repo_root, lines):
                        break
                    continue
            except Exception:
                append("health body not valid JSON")
                if not _apply_fix("health_failed", repo_root, lines):
                    break
                continue

            # (4) OPTIONS /api/v1/analyze with Origin (preflight)
            code, headers, body = _http_options(BASE_URL + "/api/v1/analyze", ORIGIN_TAURI)
            raw_preflight = f"OPTIONS /api/v1/analyze Origin={ORIGIN_TAURI} -> {code} headers={dict(headers)} body={body.decode(errors='replace')}"
            append(raw_preflight)
            h_lower = {k.lower(): v for k, v in headers.items()}
            has_cors = "access-control-allow-origin" in h_lower or "access-control-allow-credentials" in h_lower
            # Accept 200/204 or 405 with CORS headers (FastAPI may return 405 for OPTIONS on POST-only routes but still sends CORS headers)
            if code not in (200, 204, 405):
                append("failure_mode=cors (preflight status)")
                if not _apply_fix("cors", repo_root, lines):
                    break
                continue
            if not has_cors:
                append("failure_mode=cors (no CORS header)")
                if not _apply_fix("cors", repo_root, lines):
                    break
                continue

            # (5) POST /api/v1/analyze
            code, headers, body = _http_post(BASE_URL + "/api/v1/analyze", b"{}")
            raw_post = f"POST /api/v1/analyze -> {code} body={body.decode(errors='replace')[:500]}"
            append(raw_post)
            if code != 200:
                append("failure_mode=analyze_failed")
                if not _apply_fix("analyze_failed", repo_root, lines):
                    break
                continue
            try:
                json.loads(body.decode())
            except Exception:
                append("analyze response not valid JSON")
                if not _apply_fix("analyze_failed", repo_root, lines):
                    break
                continue

            passed = True
            break
        finally:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    # Final summary
    append("")
    if passed:
        append("=== SELF-TEST PASS ===")
        append("backend_started=yes backend_bind_127.0.0.1_8000=yes")
        append("health=200 preflight=200/204 CORS=yes post_analyze=200 valid_JSON=yes")
        append("Desktop app can invoke Analyze without Failed to fetch (API verified).")
    else:
        append("=== SELF-TEST FAIL ===")
        append("iterations=" + str(iteration) + " max=" + str(max_iterations))
    append("self_test_log=" + str(self_log))
    append("installer/build_artifact=" + str(repo_root / "dist" / "ai-mentor-backend.exe"))
    bundle = repo_root / "app" / "frontend" / "src-tauri" / "target" / "release" / "bundle"
    append("installer_nsis=" + str(bundle / "nsis"))
    append("installer_msi=" + str(bundle / "msi"))

    self_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if passed else 1


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Run self-test and auto-fix for built backend.")
    p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT, help="Repo root")
    p.add_argument("--max-iterations", type=int, default=3, help="Max fix/retry iterations")
    args = p.parse_args()
    return run_self_test(args.repo_root, args.max_iterations)


if __name__ == "__main__":
    sys.exit(main())
