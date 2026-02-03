"""API v1: analyze and evaluation endpoints."""

from fastapi import APIRouter

from .analyze import router as analyze_router
from .evaluation import router as evaluation_router
from .ingestion import router as ingestion_router
from .results import router as results_router

router = APIRouter(prefix="/api/v1", tags=["api_v1"])
router.include_router(analyze_router)
router.include_router(evaluation_router)
router.include_router(ingestion_router)
router.include_router(results_router)

api_v1_router = router