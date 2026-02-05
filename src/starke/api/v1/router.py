"""Main router for API v1.

This router combines all v1 endpoints under /api/v1 prefix.
"""

from fastapi import APIRouter

from starke.api.v1.auth.routes import router as auth_router
from starke.api.v1.users.routes import router as users_router
from starke.api.v1.me.routes import router as me_router
from starke.api.v1.reports.routes import router as reports_router
from starke.api.v1.scheduler.routes import router as scheduler_router
from starke.api.v1.developments.routes import router as developments_router

# Create main v1 router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Users"],
)

api_router.include_router(
    me_router,
    prefix="/me",
    tags=["My Profile"],
)

# Reports endpoints
api_router.include_router(reports_router)

# Scheduler endpoints
api_router.include_router(scheduler_router)

# Developments endpoints (empreendimentos)
api_router.include_router(developments_router)
