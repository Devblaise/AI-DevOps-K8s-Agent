"""Health check endpoint."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Definition of done for Phase 1."""
    return {"status": "healthy", "service": settings.service_name}
