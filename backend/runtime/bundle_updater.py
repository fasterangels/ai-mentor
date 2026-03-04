from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import hashlib
import json
from urllib.request import Request, urlopen


@dataclass
class UpdateConfig:
    version: str = "v0"
    timeout_seconds: int = 10
    # URL pointing to a JSON manifest that declares bundle + artifact URLs
    manifest_url: str = ""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_bytes(url: str, timeout: int = 10) -> bytes:
    """
    Download raw bytes from a URL using stdlib urllib.
    """
    req = Request(url, headers={"User-Agent": "ai-mentor-bundle-updater"})
    with urlopen(req, timeout=timeout) as resp:  # type: ignore[arg-type]
        return resp.read()


def verify_sha256(data: bytes, expected_hex: str) -> bool:
    if not expected_hex:
        return False
    actual = sha256_bytes(data)
    return actual.lower() == expected_hex.lower()


def apply_update(manifest: Dict[str, Any], install_dir: str = "backend/runtime", timeout_seconds: int = 10) -> Dict[str, Any]:
    """
    Apply a bundle update based on a manifest.

    Rules:
      - Download each file
      - Verify sha256
      - Write into a staging directory: install_dir/.staging_<bundle_version>/
      - If all succeed, atomically replace:
          backend/runtime/decision_bundle.json
          backend/policies/decision_engine_policy.json
          backend/calibration/confidence_calibrator.json
    """
    bundle_version = str(manifest.get("bundle_version", "unknown"))
    files = manifest.get("files") or []
    if not isinstance(files, list):
        return {"updated": False, "bundle_version": bundle_version, "files": []}

    base = Path(install_dir)
    root = base.parent
    stage_dir = base / f".staging_{bundle_version}"
    stage_dir.mkdir(parents=True, exist_ok=True)

    staged_paths: Dict[str, Path] = {}

    # Stage each file
    for entry in files:
        if not isinstance(entry, dict):
            return {"updated": False, "bundle_version": bundle_version, "files": []}
        name = entry.get("name")
        url = entry.get("url")
        expected_sha = entry.get("sha256") or ""
        if not name or not url:
            return {"updated": False, "bundle_version": bundle_version, "files": []}

        data = download_bytes(str(url), timeout=timeout_seconds)
        if not verify_sha256(data, str(expected_sha)):
            # Abort on first verification failure; do not replace any files.
            return {"updated": False, "bundle_version": bundle_version, "files": []}

        stage_path = stage_dir / str(name)
        stage_path.write_bytes(data)
        staged_paths[str(name)] = stage_path

    # Map logical names to final destinations, rooted at install_dir/backend.
    updated_files: List[str] = []
    for name, stage_path in staged_paths.items():
        if name == "decision_bundle.json":
            dest = base / "decision_bundle.json"
        elif name == "decision_engine_policy.json":
            dest = root / "policies" / "decision_engine_policy.json"
        elif name == "confidence_calibrator.json":
            dest = root / "calibration" / "confidence_calibrator.json"
        else:
            # Unknown artifact: place it under the runtime dir by default.
            dest = base / name

        dest.parent.mkdir(parents=True, exist_ok=True)
        stage_path.replace(dest)
        updated_files.append(str(name))

    return {
        "updated": True,
        "bundle_version": bundle_version,
        "files": updated_files,
    }


def check_and_update(cfg: UpdateConfig) -> Dict[str, Any]:
    """
    Check the remote manifest and apply bundle update.
    """
    if not cfg.manifest_url:
        return {"updated": False, "bundle_version": None, "files": [], "updater_version": cfg.version}

    req = Request(cfg.manifest_url, headers={"User-Agent": "ai-mentor-bundle-updater"})
    with urlopen(req, timeout=cfg.timeout_seconds) as resp:  # type: ignore[arg-type]
        manifest_bytes = resp.read()

    manifest = json.loads(manifest_bytes.decode("utf-8"))
    result = apply_update(manifest, install_dir="backend/runtime", timeout_seconds=cfg.timeout_seconds)
    result["updater_version"] = cfg.version
    return result

