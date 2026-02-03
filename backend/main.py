import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.database import init_database, dispose_database
from core.logging import setup_logging
from routes.api_v1 import api_v1_router


# Block 1 skeleton + Block 8.1 API wiring.
# TODO: Re-introduce legacy endpoints and services using the new core
#       configuration, logging, and async database infrastructure.

settings = get_settings()
setup_logging(settings)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

# CORS: single source of truth — defined here only, before any routers. OPTIONS preflight handled by CORSMiddleware.
ALLOWED_ORIGINS = [
    "http://tauri.localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(api_v1_router)


@app.on_event("startup")
async def on_startup() -> None:
    """Application startup hook."""
    await init_database(settings.database_url)
    logger.info("FastAPI app from %s: CORS allow_origins=%s allow_credentials=%s", __file__, ALLOWED_ORIGINS, False)
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Application shutdown hook."""
    await dispose_database()
    logger.info("Application shutdown complete")


@app.get("/health")
async def health() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}

