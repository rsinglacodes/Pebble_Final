"""Main FastAPI application entrypoint for Pebble."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.app.api.ask import router as ask_router
from backend.app.api.auth import router as auth_router
from backend.app.api.health import router as health_router
from backend.app.api.history import router as history_router
from backend.app.api.problems import router as problems_router
from backend.app.api.users import router as users_router
from backend.app.api.video import router as video_router
from backend.app.config import get_settings
from backend.app.core.exceptions import setup_exception_handlers
from backend.app.core.logging import setup_secure_logging
from backend.app.core.middleware import BodySizeLimitMiddleware
from backend.app.core.rate_limit import limiter
from backend.app.services.video_service import VideoService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan hook handling startup and shutdown tasks."""
    VideoService.resume_uncompleted_jobs()
    yield


def create_app() -> FastAPI:
    """Create and configure the hardened FastAPI application instance."""
    setup_secure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="Pebble - AI-Based DSA Learning and Video Generation Platform",
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Attach slowapi rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request body size limit (200 KB)
    app.add_middleware(BodySizeLimitMiddleware)

    # Safe error handling
    setup_exception_handlers(app)

    # Include API routes
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(problems_router)
    app.include_router(ask_router)
    app.include_router(history_router)
    app.include_router(video_router)

    return app


app = create_app()
