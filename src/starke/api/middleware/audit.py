"""Audit middleware for automatic request logging."""

import json
import logging
import re
import time
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import uuid4

from fastapi import Request, Response
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from starke.api.dependencies import get_db
from starke.infrastructure.database.patrimony.audit_log import PatAuditLog

logger = logging.getLogger(__name__)

# Context variable for request ID (for correlation)
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Paths to exclude from audit logging
EXCLUDED_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}

# Paths that contain sensitive data and should always be logged
SENSITIVE_PATHS = {
    "/api/v1/clients",
    "/api/v1/assets",
    "/api/v1/liabilities",
    "/api/v1/accounts",
    "/api/v1/documents",
    "/api/v1/positions",
}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check for forwarded headers (when behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the list is the original client
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct connection
    if request.client:
        return request.client.host
    return "unknown"


def determine_action(method: str, path: str) -> str:
    """Determine the audit action based on HTTP method and path."""
    method = method.upper()

    # Special cases
    if "/login" in path:
        return "login"
    if "/logout" in path:
        return "logout"
    if "/export" in path or "/download" in path:
        return "export"

    # Standard REST mapping
    action_map = {
        "GET": "read",
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }
    return action_map.get(method, "read")


def extract_entity_info(path: str) -> tuple[Optional[str], Optional[str]]:
    """Extract entity type and ID from path.

    Returns:
        Tuple of (entity_type, entity_id)
    """
    # Pattern: /api/v1/{entity}/{id}
    # Examples:
    #   /api/v1/clients/550e8400-... -> (pat_clients, 550e8400-...)
    #   /api/v1/assets/123 -> (pat_assets, 123)

    patterns = [
        (r"/api/v1/clients/([a-f0-9-]+)", "pat_clients"),
        (r"/api/v1/assets/([a-f0-9-]+)", "pat_assets"),
        (r"/api/v1/liabilities/([a-f0-9-]+)", "pat_liabilities"),
        (r"/api/v1/accounts/([a-f0-9-]+)", "pat_accounts"),
        (r"/api/v1/documents/([a-f0-9-]+)", "pat_documents"),
        (r"/api/v1/institutions/([a-f0-9-]+)", "pat_institutions"),
        (r"/api/v1/positions/([a-f0-9-]+)", "pat_monthly_positions"),
        (r"/api/v1/users/(\d+)", "users"),
    ]

    for pattern, entity_type in patterns:
        match = re.search(pattern, path)
        if match:
            return entity_type, match.group(1)

    # Try to extract entity type from path without ID
    entity_patterns = [
        (r"/api/v1/(clients)", "pat_clients"),
        (r"/api/v1/(assets)", "pat_assets"),
        (r"/api/v1/(liabilities)", "pat_liabilities"),
        (r"/api/v1/(accounts)", "pat_accounts"),
        (r"/api/v1/(documents)", "pat_documents"),
        (r"/api/v1/(institutions)", "pat_institutions"),
        (r"/api/v1/(positions)", "pat_monthly_positions"),
        (r"/api/v1/(users)", "users"),
        (r"/api/v1/(auth)", "auth"),
    ]

    for pattern, entity_type in entity_patterns:
        if re.search(pattern, path):
            return entity_type, None

    return None, None


def should_audit(path: str, method: str) -> bool:
    """Determine if request should be audited."""
    # Exclude certain paths
    for excluded in EXCLUDED_PATHS:
        if path.startswith(excluded):
            return False

    # Always audit sensitive paths
    for sensitive in SENSITIVE_PATHS:
        if path.startswith(sensitive):
            return True

    # Audit all mutating operations
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        return True

    # Audit auth operations
    if "/auth/" in path:
        return True

    return False


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic audit logging of requests."""

    def __init__(self, app: ASGIApp, db_session_factory: Callable[[], Session]):
        super().__init__(app)
        self.db_session_factory = db_session_factory

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log audit entry."""
        # Generate request ID for correlation
        request_id = str(uuid4())
        request_id_var.set(request_id)

        # Get basic request info
        path = request.url.path
        method = request.method
        start_time = time.time()

        # Check if should audit
        if not should_audit(path, method):
            return await call_next(request)

        # Extract request context
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")[:500]  # Limit length

        # Try to get user ID from JWT token (if available)
        user_id = None
        try:
            # The user will be set by the auth dependency, we try to extract from token
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                from jose import jwt
                from starke.core.config_loader import get_settings

                settings = get_settings()
                token = auth_header.split(" ")[1]
                try:
                    payload = jwt.decode(
                        token,
                        settings.SECRET_KEY,
                        algorithms=["HS256"]
                    )
                    # Get user email from token and look up user ID
                    user_email = payload.get("sub")
                    if user_email:
                        # Store email for later lookup
                        request.state.audit_user_email = user_email
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Could not extract user from token: {e}")

        # Determine action and entity
        action = determine_action(method, path)
        entity_type, entity_id = extract_entity_info(path)

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Build audit details
        details: dict[str, Any] = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }

        # Add query params for reads (but not sensitive ones)
        if method == "GET" and request.query_params:
            # Filter out sensitive params
            safe_params = {
                k: v for k, v in request.query_params.items()
                if k.lower() not in ("password", "token", "secret", "key")
            }
            if safe_params:
                details["query_params"] = safe_params

        # Log to database
        try:
            db = self.db_session_factory()
            try:
                # Try to get user ID from email stored in request state
                if hasattr(request.state, "audit_user_email"):
                    from starke.infrastructure.database.models import User
                    from sqlalchemy import select

                    user = db.execute(
                        select(User).where(User.email == request.state.audit_user_email)
                    ).scalar_one_or_none()
                    if user:
                        user_id = user.id

                audit_log = PatAuditLog(
                    id=str(uuid4()),
                    user_id=user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details=details,
                    created_at=datetime.utcnow(),
                )
                db.add(audit_log)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to create database session for audit: {e}")

        return response


def get_request_id() -> str:
    """Get the current request ID for correlation."""
    return request_id_var.get()
