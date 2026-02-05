"""FastAPI application for Starke."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from starke.api.middleware.audit import AuditMiddleware
from starke.api.v1.router import api_router as v1_router
from starke.infrastructure.database.base import SessionLocal
from starke.core.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    logger.info("Starting application...")

    # Start scheduler (uncomment condition below to restrict to production only)
    environment = os.getenv("ENVIRONMENT", "development").lower()
    # if environment == "production":
    logger.info("Starting scheduler for daily Mega + UAU sync...")
    start_scheduler()
    logger.info("Scheduler started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    # if environment == "production":
    logger.info("Stopping scheduler...")
    stop_scheduler()
    logger.info("Scheduler stopped")

# Middleware to strip trailing slashes (avoid 307 redirects)
class TrailingSlashMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Remove trailing slash from path (except for root "/")
        if request.url.path != "/" and request.url.path.endswith("/"):
            # Modify the scope to remove trailing slash
            scope = request.scope
            scope["path"] = request.url.path.rstrip("/")
        return await call_next(request)


# Create FastAPI app
app = FastAPI(
    title="Starke API",
    description="API for Starke - Cash Flow and Patrimony Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    redirect_slashes=False,  # Disable automatic trailing slash redirects
)

# Add audit middleware for logging all requests
app.add_middleware(
    AuditMiddleware,
    db_session_factory=SessionLocal,
)

# Add trailing slash middleware
app.add_middleware(TrailingSlashMiddleware)

# Configure CORS - MUST be added last to be processed first
# Origins from environment variable (comma-separated) or defaults for local dev
cors_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (if any)
# app.mount("/static", StaticFiles(directory="src/starke/presentation/web/static"), name="static")

# Include API v1 router
app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/debug/storage")
def debug_storage() -> dict:
    """Debug endpoint to check storage configuration."""
    from starke.core.storage import get_storage

    storage = get_storage()
    return {
        "storage_type": storage.storage_type,
        "is_s3": storage.is_s3,
        "is_local": storage.is_local,
        "env_storage_type": os.getenv("STORAGE_TYPE", "not_set"),
        "env_bucket": os.getenv("S3_BUCKET_NAME", "not_set"),
        "env_region": os.getenv("AWS_REGION", "not_set"),
        "env_access_key": os.getenv("AWS_ACCESS_KEY_ID", "not_set")[:8] + "..." if os.getenv("AWS_ACCESS_KEY_ID") else "not_set",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
