"""POST /api/v1/analyze — disabled by design (501). Use /pipeline/shadow/run instead."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

ANALYZE_501_PAYLOAD = {
    "error": {
        "code": "ANALYZE_ENDPOINT_NOT_SUPPORTED",
        "message": "This endpoint is intentionally not supported. Use /pipeline/shadow/run.",
        "remediation": {
            "endpoint": "/pipeline/shadow/run",
            "notes": "The analyzer is designed to run inside the pipeline execution model.",
        },
    },
}


@router.post("/analyze", include_in_schema=False)
async def post_analyze() -> JSONResponse:
    """
    Disabled by design. Always returns 501.
    Use /pipeline/shadow/run for analyzer execution inside the pipeline.
    """
    return JSONResponse(status_code=501, content=ANALYZE_501_PAYLOAD)
