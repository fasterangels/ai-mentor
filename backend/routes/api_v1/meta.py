"""GET /api/v1/meta/version — application version from VERSION file."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from version import get_version
from backend.runtime.bundle_updater import UpdateConfig, check_and_update

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/version", summary="Application version")
def meta_version() -> dict:
    """Return version from repo root VERSION file."""
    return {"version": get_version()}


class UpdateRequest(BaseModel):
    manifest_url: str


@router.post("/update", summary="Update decision bundle from manifest")
def update_bundle(body: UpdateRequest) -> dict:
    """
    Fetch and apply a new decision bundle and associated artifacts from a remote manifest URL.
    """
    cfg = UpdateConfig(manifest_url=body.manifest_url)
    return check_and_update(cfg)
