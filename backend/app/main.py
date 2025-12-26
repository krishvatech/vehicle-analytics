"""FastAPI application entrypoint.

This module constructs the FastAPI app, includes API routers, and
configures CORS to allow the frontend to communicate with the API.

The application mounts a health check endpoint at ``/health`` and
provides automatic OpenAPI documentation at ``/docs``.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import auth, cameras, rois, events, notifications, metrics, videos
from app.db import models
from app.db.session import engine
from app.core.config import get_settings
from app.services.storage.minio_client import MinioService
import redis


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    app = FastAPI(title="CCTV Vehicle Analytics API")
    settings = get_settings()

    # Create database tables if they do not exist
    models.Base.metadata.create_all(bind=engine)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Return a basic health status with dependencies."""
        status = {"db": "ok", "redis": "ok", "minio": "ok"}
        try:
            # DB check
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            status["db"] = f"error: {exc}"
        try:
            cfg = get_settings()
            r = redis.Redis.from_url(cfg.redis_url)
            r.ping()
        except Exception as exc:
            status["redis"] = f"error: {exc}"
        try:
            m = MinioService()
            m.client.bucket_exists(m.bucket)
        except Exception as exc:
            status["minio"] = f"error: {exc}"
        overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
        return {"status": overall, "components": status}

    # Include routers
    app.include_router(auth.router)
    app.include_router(cameras.router)
    app.include_router(videos.router)
    app.include_router(rois.router)
    app.include_router(events.router)
    app.include_router(notifications.router)
    app.include_router(metrics.router)
    return app


app = create_app()
