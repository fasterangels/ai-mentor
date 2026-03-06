"""Verify POST /api/v1/pipeline/shadow/run returns valid JSON. Exit 0 if valid."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8000"
DEFAULT_MATCH_ID = "sample_platform_match_001"
BODY_PREVIEW_LEN = 500


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default=DEFAULT_BASE)
    p.add_argument("--match-id", default=DEFAULT_MATCH_ID)
    args = p.parse_args()
    url = f"{args.base_url.rstrip('/')}/api/v1/pipeline/shadow/run"
    payload = {"connector_name": "sample_platform", "match_id": args.match_id, "final_home_goals": 0, "final_away_goals": 0, "status": "FINAL"}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, headers, body = r.status, dict(r.headers), r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        status, headers = e.code, dict(e.headers) if e.headers else {}
        body = (e.read() if e.fp else b"").decode("utf-8", errors="replace")
    except Exception as e:
        print("Request failed:", e, file=sys.stderr)
        return 1
    content_type = headers.get("Content-Type", "").split(";")[0].strip()
    print("status_code:", status)
    print("content_type:", content_type)
    snippet = body[:BODY_PREVIEW_LEN] + ("..." if len(body) > BODY_PREVIEW_LEN else "")
    print("body_preview:", repr(snippet))
    try:
        parsed = json.loads(body)
        print("valid_json: true")
        if isinstance(parsed, dict):
            print("response.status:", repr(parsed.get("status")))
            if parsed.get("error"):
                print("response.error:", repr(parsed.get("error")))
        return 0
    except json.JSONDecodeError as e:
        print("valid_json: false")
        print("parse_error:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
