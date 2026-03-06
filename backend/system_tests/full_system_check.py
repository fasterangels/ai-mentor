from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests as _requests
except ImportError:  # Fallback to stdlib HTTP client if requests is unavailable.
    _requests = None
    import urllib.error as _urllib_error
    import urllib.request as _urllib_request


BACKEND_URL = "http://127.0.0.1:8000/health"


class _Resp:
    """Minimal response shim providing status_code and json()."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self._body = body

    def json(self):
        return json.loads(self._body)


def _http_get(url: str, timeout: float = 2):
    if _requests is not None:
        return _requests.get(url, timeout=timeout)
    req = _urllib_request.Request(url, method="GET")
    with _urllib_request.urlopen(req, timeout=timeout) as resp:  # type: ignore[attr-defined]
        body = resp.read().decode("utf-8")
        return _Resp(resp.getcode(), body)


def _http_post(url: str, json_body: dict | None = None, timeout: float = 10):
    if _requests is not None:
        return _requests.post(url, json=json_body, timeout=timeout)
    data = json.dumps(json_body or {}).encode("utf-8")
    req = _urllib_request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with _urllib_request.urlopen(req, timeout=timeout) as resp:  # type: ignore[attr-defined]
        body = resp.read().decode("utf-8")
        return _Resp(resp.getcode(), body)


class _NoopProcess:
    """Placeholder when backend is already running."""

    def terminate(self) -> None:  # pragma: no cover - trivial
        pass


def start_backend() -> subprocess.Popen:
    """Start the backend process via runner script, unless already running."""
    # If a backend is already listening, reuse it.
    try:
        r = _http_get(BACKEND_URL, timeout=1)
        if r.status_code == 200:
            print("Backend already running")
            return _NoopProcess()
    except Exception:
        pass

    print("Starting backend...")
    repo_root = Path(__file__).resolve().parents[2]
    runner = repo_root / "backend" / "runner" / "start_backend.py"
    process = subprocess.Popen(
        [sys.executable, str(runner)],
        cwd=str(repo_root),
    )
    return process


def wait_for_backend() -> None:
    """Poll the health endpoint until backend is ready or timeout."""
    for _ in range(40):
        try:
            r = _http_get(BACKEND_URL, timeout=2)
            if r.status_code == 200:
                print("Backend ready")
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Backend failed to start")


def test_analysis() -> None:
    """Call a representative analysis endpoint to validate end-to-end flow."""
    print("Testing analysis endpoint...")
    payload = {"query": "Arsenal Chelsea"}
    r = _http_post(
        "http://127.0.0.1:8000/football/analyze_match",
        json_body=payload,
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Analysis endpoint failed with status {r.status_code}")
    data = r.json()
    if "analysis" not in data:
        raise RuntimeError("Invalid analysis response: missing 'analysis' key")
    print("Analysis test passed")


def main() -> None:
    backend = start_backend()
    try:
        wait_for_backend()
        test_analysis()
        print("SYSTEM CHECK PASSED")
    finally:
        backend.terminate()


if __name__ == "__main__":
    main()

