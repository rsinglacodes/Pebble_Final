"""Health check API router."""

from fastapi import APIRouter, Depends
from backend.app.schemas.contracts import HealthResponse
from backend.app.services.health_service import HealthService

router = APIRouter(tags=["Health"])


def get_health_service() -> HealthService:
    """Dependency injector for HealthService."""
    return HealthService()


@router.get("/health", response_model=HealthResponse)
def get_health(service: HealthService = Depends(get_health_service)) -> HealthResponse:
    """Check system and database health status."""
    return service.check_health()
