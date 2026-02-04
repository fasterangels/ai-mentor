"""
Integration tests for read-only reports viewer API: GET /index, GET /item/{run_id}, GET /file.
Uses a temp reports directory fixture; no token when REPORTS_READ_TOKEN unset.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

# Import app after path setup; app startup will run when client is used
from main import app


@pytest.fixture
def temp_reports(tmp_path: Path):
    """Create a temp reports dir with index.json and one report file."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    index = {
        "runs": [],
        "latest_run_id": None,
        "burn_in_ops_runs": [
            {"run_id": "burn_in_ops_20250101_120000_abc123", "created_at_utc": "2025-01-01T12:00:00Z", "status": "ok"}
        ],
        "latest_burn_in_ops_run_id": "burn_in_ops_20250101_120000_abc123",
    }
    (reports_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")
    (reports_dir / "burn_in").mkdir(exist_ok=True)
    bundle_dir = reports_dir / "burn_in" / "burn_in_ops_20250101_120000_abc123"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "summary.json").write_text(json.dumps({"run_id": "burn_in_ops_20250101_120000_abc123", "status": "ok"}), encoding="utf-8")
    return reports_dir


def test_reports_index_returns_index_json(temp_reports: Path) -> None:
    """GET /api/v1/reports/index returns reports/index.json from REPORTS_DIR."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REPORTS_DIR", str(temp_reports))
        client = TestClient(app)
        resp = client.get("/api/v1/reports/index")
    assert resp.status_code == 200
    data = resp.json()
    assert "burn_in_ops_runs" in data
    assert len(data["burn_in_ops_runs"]) == 1
    assert data["burn_in_ops_runs"][0]["run_id"] == "burn_in_ops_20250101_120000_abc123"


def test_reports_item_returns_bundle_paths_and_summary(temp_reports: Path) -> None:
    """GET /api/v1/reports/item/{run_id} returns found sources and paths."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REPORTS_DIR", str(temp_reports))
        client = TestClient(app)
        resp = client.get("/api/v1/reports/item/burn_in_ops_20250101_120000_abc123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "burn_in_ops_20250101_120000_abc123"
    assert data["found"] is True
    assert len(data["sources"]) >= 1
    paths = data["sources"][0].get("paths") or []
    assert any("burn_in/" in p and "summary.json" in p for p in paths)


def test_reports_item_not_found(temp_reports: Path) -> None:
    """GET /api/v1/reports/item/{run_id} returns found=False for unknown run_id."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REPORTS_DIR", str(temp_reports))
        client = TestClient(app)
        resp = client.get("/api/v1/reports/item/nonexistent_run_999")
    assert resp.status_code == 200
    assert resp.json()["found"] is False
    assert resp.json()["sources"] == []


def test_reports_file_serves_json_under_reports(temp_reports: Path) -> None:
    """GET /api/v1/reports/file?path=... returns file contents (sandboxed)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REPORTS_DIR", str(temp_reports))
        client = TestClient(app)
        resp = client.get("/api/v1/reports/file", params={"path": "burn_in/burn_in_ops_20250101_120000_abc123/summary.json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("run_id") == "burn_in_ops_20250101_120000_abc123"
    assert data.get("status") == "ok"


def test_reports_file_rejects_traversal(temp_reports: Path) -> None:
    """GET /api/v1/reports/file with path=../... returns 400."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REPORTS_DIR", str(temp_reports))
        client = TestClient(app)
        resp = client.get("/api/v1/reports/file", params={"path": "../index.json"})
    assert resp.status_code == 400


def test_reports_file_404_for_missing_file(temp_reports: Path) -> None:
    """GET /api/v1/reports/file for non-existent path returns 404."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REPORTS_DIR", str(temp_reports))
        client = TestClient(app)
        resp = client.get("/api/v1/reports/file", params={"path": "burn_in/nonexistent/summary.json"})
    assert resp.status_code in (404, 400)


def test_reports_index_401_when_token_required_and_missing(temp_reports: Path) -> None:
    """When REPORTS_READ_TOKEN is set, GET without X-Reports-Token returns 401."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REPORTS_DIR", str(temp_reports))
        m.setenv("REPORTS_READ_TOKEN", "secret")
        client = TestClient(app)
        resp = client.get("/api/v1/reports/index")
    assert resp.status_code == 401


def test_reports_index_200_with_valid_token(temp_reports: Path) -> None:
    """When REPORTS_READ_TOKEN is set, GET with valid X-Reports-Token returns 200."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REPORTS_DIR", str(temp_reports))
        m.setenv("REPORTS_READ_TOKEN", "secret")
        client = TestClient(app)
        resp = client.get("/api/v1/reports/index", headers={"X-Reports-Token": "secret"})
    assert resp.status_code == 200
    assert "burn_in_ops_runs" in resp.json()
