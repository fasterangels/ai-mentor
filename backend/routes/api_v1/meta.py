"""GET /api/v1/meta/version — application version from VERSION file."""

from __future__ import annotations

from fastapi import APIRouter

from version import get_version

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/version", summary="Application version")
def meta_version() -> dict:
    """Return version from repo root VERSION file."""
    return {"version": get_version()}
