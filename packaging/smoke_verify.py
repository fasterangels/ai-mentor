"""
Post-BLOCK smoke verification: start backend, GET /health, OPTIONS /api/v1/analyze with Origin,
POST /api/v1/analyze with minimal payload → expect 200 JSON.
Used after build, before artifact upload. Exit 1 with clear message if any check fails.
No new deps; reuse stdlib + existing env.

Usage: python packaging/smoke_verify.py [--repo-root PATH] [--wait-sec N]
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
ORIGIN = "http://tauri.localhost"
DEFAULT_WAIT_SEC = 25
POLL_INTERVAL = 0.5
POST_PAYLOAD = b'{"home_team":"PAOK","away_team":"AEK"}'


def _port_file() -> Path:
    localappdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(localappdata) / "AI_Mentor" / "runtime" / "backend_port.json"


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


def _http_post(url: str, data: bytes) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(
        url, data=data, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read() if e.fp else b""
    except Exception as e:
        return -1, {}, str(e).encode()


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Post-BLOCK smoke: backend + health + OPTIONS + POST /analyze.")
    p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT, help="Repo root")
    p.add_argument("--wait-sec", type=int, default=DEFAULT_WAIT_SEC, help="Max seconds to wait for backend")
    args = p.parse_args()
    repo_root = args.repo_root
    wait_sec = args.wait_sec

    exe = repo_root / "dist" / "ai-mentor-backend.exe"
    if not exe.exists():
        print("FAIL: post-block smoke — backend exe not found: " + str(exe), file=sys.stderr)
        return 1

    # Remove stale port file so we know the one we read is from our process
    pf = _port_file()
    if pf.exists():
        try:
            pf.unlink()
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
        # Wait for port file (backend writes it when it binds)
        deadline = time.monotonic() + wait_sec
        base_url = "http://127.0.0.1:8000"
        while time.monotonic() < deadline:
            if pf.exists():
                try:
                    data = json.loads(pf.read_text(encoding="utf-8"))
                    base_url = data.get("base_url") or ("http://127.0.0.1:" + str(data.get("port", 8000)))
                    break
                except Exception:
                    pass
            time.sleep(POLL_INTERVAL)
        else:
            # Fallback: try fixed 8000 (backend may have written port file we didn't see)
            base_url = "http://127.0.0.1:8000"

        # GET /health → 200
        code, _, body = _http_get(base_url + "/health")
        if code != 200:
            print("FAIL: post-block smoke — GET /health returned " + str(code) + " (expected 200)", file=sys.stderr)
            return 1
        try:
            j = json.loads(body.decode())
            if j.get("status") != "ok":
                print("FAIL: post-block smoke — GET /health body status != ok", file=sys.stderr)
                return 1
        except Exception as e:
            print("FAIL: post-block smoke — GET /health body not valid JSON: " + str(e), file=sys.stderr)
            return 1

        # OPTIONS /api/v1/analyze with Origin → 200 or 204
        code, headers, _ = _http_options(base_url + "/api/v1/analyze", ORIGIN)
        if code not in (200, 204):
            print("FAIL: post-block smoke — OPTIONS /api/v1/analyze returned " + str(code) + " (expected 200 or 204)", file=sys.stderr)
            return 1

        # POST /api/v1/analyze with minimal payload → 200 JSON
        code, _, body = _http_post(base_url + "/api/v1/analyze", POST_PAYLOAD)
        if code != 200:
            print("FAIL: post-block smoke — POST /api/v1/analyze returned " + str(code) + " (expected 200)", file=sys.stderr)
            return 1
        try:
            json.loads(body.decode())
        except Exception as e:
            print("FAIL: post-block smoke — POST /api/v1/analyze response not valid JSON: " + str(e), file=sys.stderr)
            return 1

        print("post-block smoke: GET /health 200, OPTIONS 200/204, POST /api/v1/analyze 200 JSON — OK")
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
