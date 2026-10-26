"""Health service orchestrating application health verification."""

from backend.app.repositories.health_repository import HealthRepository
from backend.app.schemas.contracts import HealthResponse


class HealthService:
    """Service to coordinate application health status."""

    def __init__(self, repository: HealthRepository = None):
        self.repository = repository or HealthRepository()

    def check_health(self) -> HealthResponse:
        """Verify services and database status.
        
        Returns:
            HealthResponse: Structured status with db boolean.
        """
        db_alive = self.repository.ping_database()
        return HealthResponse(status="ok", db=db_alive)
