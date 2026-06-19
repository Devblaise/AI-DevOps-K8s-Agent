"""FastAPI application entrypoint.

Phase 1 scaffold: CORS, logging, settings, and a health endpoint. No Kubernetes or
AI logic yet — those layers exist only as placeholders.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.health import router as health_router
from app.api.investigate import router as investigate_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("{} backend started", settings.service_name)
    yield


app = FastAPI(title="AI Kubernetes Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(investigate_router)
