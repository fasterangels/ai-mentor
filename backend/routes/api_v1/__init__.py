"""API v1: analyze, evaluation, pipeline, runner, and reports endpoints."""

from fastapi import APIRouter

from .analyze import router as analyze_router
from .evaluation import router as evaluation_router
from .pipeline import router as pipeline_router
from .reports import router as reports_router
from .runner import router as runner_router

router = APIRouter(prefix="/api/v1", tags=["api_v1"])
router.include_router(analyze_router)
router.include_router(evaluation_router)
router.include_router(pipeline_router)
router.include_router(reports_router)
router.include_router(runner_router)

api_v1_router = router