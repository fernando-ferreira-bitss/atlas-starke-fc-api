"""Authentication dependencies for FastAPI."""

from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from starke.api.dependencies.database import get_db
from starke.domain.services.auth_service import AuthService
from starke.domain.services.permission_service import PermissionService
from starke.domain.permissions.screens import Screen
from starke.infrastructure.database.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class ImpersonationContext:
    """Contexto de impersonation armazenado em request.state."""

    actor_user_id: int
    actor_email: str
    actor_role: str
    target_user_id: int
    target_client_id: str
    impersonation_log_id: int
    is_read_only: bool = True


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    request: Request = None,
) -> User:
    """Get current authenticated user from JWT token.

    Se for um token de impersonation, retorna o usuário TARGET
    e armazena o contexto do ACTOR em request.state.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = AuthService.decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # ===== DETECTAR IMPERSONATION =====
    if payload.get("type") == "impersonation":
        actor_user_id = payload.get("actor_user_id")
        target_user_id = payload.get("target_user_id")
        target_client_id = payload.get("target_client_id")
        impersonation_log_id = payload.get("impersonation_log_id")

        if not all([actor_user_id, target_user_id, target_client_id, impersonation_log_id]):
            raise credentials_exception

        auth_service = AuthService(db)

        # Validar que o actor ainda tem permissão
        actor = auth_service.get_user_by_id(actor_user_id)
        if not actor or not actor.is_active:
            raise credentials_exception

        # Verificar se actor ainda é admin ou rm
        if actor.role not in [UserRole.ADMIN.value, UserRole.RM.value] and not actor.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão de impersonation revogada",
            )

        # Buscar usuário target
        target = auth_service.get_user_by_id(target_user_id)
        if not target or not target.is_active:
            raise credentials_exception

        # Armazenar contexto de impersonation no request
        if request:
            request.state.impersonation_context = ImpersonationContext(
                actor_user_id=actor_user_id,
                actor_email=actor.email,
                actor_role=actor.role,
                target_user_id=target_user_id,
                target_client_id=target_client_id,
                impersonation_log_id=impersonation_log_id,
                is_read_only=payload.get("read_only", True),
            )

        return target  # Retorna o usuário TARGET

    # ===== LOGIN NORMAL =====
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    # Get user from database
    auth_service = AuthService(db)
    user = auth_service.get_user_by_email(email)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Get current superuser (admin).

    Uses is_admin property which checks both:
    - role == 'admin'
    - is_superuser == True (backward compatibility)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def get_permission_service(
    db: Annotated[Session, Depends(get_db)],
) -> PermissionService:
    """Get permission service instance."""
    return PermissionService(db)


# =============================================================================
# Permission-based Dependencies
# =============================================================================


def require_permission(*screens: Screen):
    """Dependency factory that requires user to have access to specified screens.

    User needs access to at least ONE of the specified screens.

    Usage:
        @router.get("/reports")
        def get_reports(
            user: User = Depends(require_permission(Screen.REPORTS))
        ):
            ...

        # Multiple screens (any one grants access)
        @router.get("/data")
        def get_data(
            user: User = Depends(require_permission(Screen.REPORTS, Screen.DASHBOARD))
        ):
            ...
    """

    def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
        permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    ) -> User:
        # Check if user has any of the required permissions
        for screen in screens:
            if permission_service.has_permission(current_user, screen):
                return current_user

        # No permission found
        screen_names = ", ".join(s.value for s in screens)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required permission: {screen_names}",
        )

    return permission_checker


def require_all_permissions(*screens: Screen):
    """Dependency factory that requires user to have access to ALL specified screens.

    Usage:
        @router.delete("/users/{id}")
        def delete_user(
            user: User = Depends(require_all_permissions(Screen.USERS, Screen.USERS_DELETE))
        ):
            ...
    """

    def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
        permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    ) -> User:
        missing = []
        for screen in screens:
            if not permission_service.has_permission(current_user, screen):
                missing.append(screen.value)

        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing permissions: {', '.join(missing)}",
            )

        return current_user

    return permission_checker


def require_role(*roles: UserRole):
    """Dependency factory that requires user to have specific role(s).

    Admin always has access regardless of specified roles.

    Usage:
        @router.post("/assign-client")
        def assign_client(
            user: User = Depends(require_role(UserRole.ADMIN, UserRole.RM))
        ):
            ...
    """

    def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        # Admin always has access
        if current_user.is_admin:
            return current_user

        # Check if user has one of the required roles
        allowed_roles = [r.value for r in roles]
        if current_user.role not in allowed_roles:
            role_names = ", ".join(allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {role_names}",
            )

        return current_user

    return role_checker


def require_admin():
    """Shortcut dependency for requiring admin role.

    Usage:
        @router.delete("/settings")
        def delete_settings(user: User = Depends(require_admin())):
            ...
    """
    return require_role(UserRole.ADMIN)
