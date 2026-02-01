"""API v1: analyze and evaluation endpoints."""

from fastapi import APIRouter

from .analyze import router as analyze_router
from .evaluation import router as evaluation_router

router = APIRouter(prefix="/api/v1", tags=["api_v1"])
router.include_router(analyze_router)
router.include_router(evaluation_router)

api_v1_router = router