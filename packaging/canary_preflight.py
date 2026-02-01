"""
Canary preflight: start built backend exe, GET /health, OPTIONS /api/v1/analyze with Origin.
Fail fast with clear message if any step fails. Used at start of windows-e2e CI.
No CORS/config changes, no POST /analyze — backend + health + preflight only.

Usage: python packaging/canary_preflight.py [--repo-root PATH] [--wait-sec N]
Exit: 0 if all pass, 1 otherwise.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = _THIS_DIR.parent
BASE_URL = "http://127.0.0.1:8000"
ORIGIN = "http://tauri.localhost"
DEFAULT_WAIT_SEC = 25
POLL_INTERVAL = 0.5


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


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Canary preflight: backend + /health + OPTIONS /api/v1/analyze.")
    p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT, help="Repo root")
    p.add_argument("--wait-sec", type=int, default=DEFAULT_WAIT_SEC, help="Max seconds to wait for /health")
    args = p.parse_args()
    repo_root = args.repo_root
    wait_sec = args.wait_sec

    exe = repo_root / "dist" / "ai-mentor-backend.exe"
    if not exe.exists():
        print(f"FAIL: backend exe not found: {exe}", file=sys.stderr)
        return 1

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
        deadline = time.monotonic() + wait_sec
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
        if not health_ok:
            print("FAIL: GET /health did not return 200 with status=ok within timeout", file=sys.stderr)
            return 1

        code, headers, body = _http_options(BASE_URL + "/api/v1/analyze", ORIGIN)
        h_lower = {k.lower(): v for k, v in headers.items()}
        has_cors = "access-control-allow-origin" in h_lower or "access-control-allow-credentials" in h_lower
        if code not in (200, 204, 405):
            print(f"FAIL: OPTIONS /api/v1/analyze returned {code} (expected 200/204/405)", file=sys.stderr)
            return 1
        if not has_cors:
            print("FAIL: OPTIONS /api/v1/analyze response missing CORS header (Origin)", file=sys.stderr)
            return 1

        print("canary-preflight: GET /health 200, OPTIONS /api/v1/analyze OK")
        return 0
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
