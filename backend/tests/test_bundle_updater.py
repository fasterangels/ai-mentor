"""
Unit tests for the decision bundle updater.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.runtime.bundle_updater import (  # type: ignore[import-error]
    apply_update,
    sha256_bytes,
    verify_sha256,
)


def test_verify_sha256_round_trip() -> None:
    data = b"hello world"
    digest = sha256_bytes(data)
    assert verify_sha256(data, digest)
    assert not verify_sha256(data, "deadbeef")


def test_apply_update_success_with_mocked_download(tmp_path: Path, monkeypatch) -> None:
    # Prepare fake file contents
    files_content = {
        "decision_bundle.json": b'{"version":"v3"}',
        "decision_engine_policy.json": b'{"version":"v3","thresholds":{"default":0.6}}',
        "confidence_calibrator.json": b'{"version":"v3","n_bins":10}',
    }

    # Build manifest with correct sha256 for each file
    manifest_files = []
    for name, content in files_content.items():
        manifest_files.append(
            {
                "name": name,
                "url": f"https://example.com/{name}",
                "sha256": sha256_bytes(content),
            }
        )
    manifest = {
        "bundle_version": "v3",
        "files": manifest_files,
    }

    # Monkeypatch download_bytes to return our fake contents based on URL.
    def _fake_download_bytes(url: str, timeout: int = 10) -> bytes:
        for name, content in files_content.items():
            if url.endswith(name):
                return content
        raise RuntimeError(f"Unexpected URL {url}")

    monkeypatch.setattr("backend.runtime.bundle_updater.download_bytes", _fake_download_bytes)

    install_dir = tmp_path / "backend" / "runtime"
    result = apply_update(manifest, install_dir=str(install_dir), timeout_seconds=5)

    assert result["updated"] is True
    assert result["bundle_version"] == "v3"
    assert sorted(result["files"]) == sorted(list(files_content.keys()))

    # Check destinations relative to the temp backend structure.
    backend_root = tmp_path / "backend"
    assert (backend_root / "runtime" / "decision_bundle.json").is_file()
    assert (backend_root / "policies" / "decision_engine_policy.json").is_file()
    assert (backend_root / "calibration" / "confidence_calibrator.json").is_file()


def test_apply_update_sha_mismatch_does_not_replace(tmp_path: Path, monkeypatch) -> None:
    content = b'{"version":"v3"}'
    manifest = {
        "bundle_version": "v3",
        "files": [
            {
                "name": "decision_bundle.json",
                "url": "https://example.com/decision_bundle.json",
                "sha256": "deadbeef",  # incorrect
            }
        ],
    }

    def _fake_download_bytes(url: str, timeout: int = 10) -> bytes:
        return content

    monkeypatch.setattr("backend.runtime.bundle_updater.download_bytes", _fake_download_bytes)

    install_dir = tmp_path / "backend" / "runtime"
    result = apply_update(manifest, install_dir=str(install_dir), timeout_seconds=5)

    assert result["updated"] is False
    backend_root = tmp_path / "backend"
    # No files should have been written to final locations.
    assert not (backend_root / "runtime" / "decision_bundle.json").exists()

