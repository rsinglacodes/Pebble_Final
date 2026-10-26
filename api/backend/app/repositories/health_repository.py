"""Repository for database connectivity checks."""

import logging
from sqlalchemy import text
from backend.app.db.session import get_engine

logger = logging.getLogger(__name__)


class HealthRepository:
    """Handles raw SQL checks for database health."""

    @staticmethod
    def ping_database() -> bool:
        """Execute SELECT 1 to verify database connectivity.
        
        Returns:
            bool: True if query executes successfully, False otherwise.
        """
        try:
            engine = get_engine()
            if engine is None:
                return False

            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                scalar = result.scalar()
                return scalar == 1
        except Exception as exc:
            logger.warning("Database ping failed: %s", exc)
            return False
