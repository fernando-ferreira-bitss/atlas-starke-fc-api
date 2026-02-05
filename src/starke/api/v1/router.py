"""Main router for API v1.

This router combines all v1 endpoints under /api/v1 prefix.
"""

from fastapi import APIRouter

from starke.api.v1.auth.routes import router as auth_router
from starke.api.v1.users.routes import router as users_router
from starke.api.v1.me.routes import router as me_router
from starke.api.v1.institutions.routes import router as institutions_router
from starke.api.v1.clients.routes import router as clients_router
from starke.api.v1.accounts.routes import router as accounts_router
from starke.api.v1.assets.routes import router as assets_router
from starke.api.v1.liabilities.routes import router as liabilities_router
from starke.api.v1.documents.routes import router as documents_router
from starke.api.v1.positions.routes import router as positions_router
from starke.api.v1.audit.routes import router as audit_router
from starke.api.v1.reports.routes import router as reports_router
from starke.api.v1.scheduler.routes import router as scheduler_router
from starke.api.v1.impersonation.routes import router as impersonation_router
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
    tags=["My Data (Client Self-Service)"],
)

api_router.include_router(
    impersonation_router,
    prefix="/impersonation",
    tags=["Impersonation"],
)

# Patrimony management endpoints
api_router.include_router(institutions_router)
api_router.include_router(clients_router)
api_router.include_router(accounts_router)
api_router.include_router(assets_router)
api_router.include_router(liabilities_router)
api_router.include_router(documents_router)
api_router.include_router(positions_router)

# Audit endpoints (admin only)
api_router.include_router(audit_router)

# Reports endpoints
api_router.include_router(reports_router)

# Scheduler endpoints
api_router.include_router(scheduler_router)

# Developments endpoints (empreendimentos)
api_router.include_router(developments_router)
