"""Permission service for role-based access control.

This service handles:
- Checking user permissions for screens
- Managing RM-Client assignments
- Caching permissions for performance
"""

from typing import Optional

from sqlalchemy.orm import Session

from starke.domain.permissions.screens import Screen, DEFAULT_ROLE_PERMISSIONS, get_parent_screen
from starke.infrastructure.database.models import User, RolePermission


class PermissionService:
    """Service for managing user permissions.

    Usage:
        permission_service = PermissionService(db)

        # Check if user has permission
        if permission_service.has_permission(user, Screen.CLIENTS):
            # User can access clients

        # Get all user permissions
        permissions = permission_service.get_user_permissions(user)
    """

    def __init__(self, db: Session):
        """Initialize permission service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self._permission_cache: dict[str, set[str]] = {}

    def get_user_permissions(self, user: User) -> set[str]:
        """Get all screen codes the user has access to.

        Args:
            user: User to check permissions for

        Returns:
            Set of screen codes the user can access
        """
        # Admin (via role or is_superuser) has access to everything
        if user.is_admin:
            return {screen.value for screen in Screen}

        # Check cache
        cache_key = f"{user.role}_{user.id}"
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]

        # Try to get permissions from database
        db_permissions = (
            self.db.query(RolePermission.screen_code)
            .filter(RolePermission.role == user.role)
            .all()
        )

        if db_permissions:
            # Use database permissions
            permissions = {p.screen_code for p in db_permissions}
        else:
            # Fall back to default permissions
            default_screens = DEFAULT_ROLE_PERMISSIONS.get(user.role, [])
            permissions = {screen.value for screen in default_screens}

        # Cache permissions
        self._permission_cache[cache_key] = permissions
        return permissions

    def has_permission(self, user: User, screen: Screen) -> bool:
        """Check if user has access to a specific screen.

        Permission is granted if:
        1. User is admin (is_admin property)
        2. User has exact permission for the screen
        3. User has permission for parent screen (e.g., 'users' grants 'users.create')

        Args:
            user: User to check
            screen: Screen to check access for

        Returns:
            True if user has access, False otherwise
        """
        # Admin always has access
        if user.is_admin:
            return True

        permissions = self.get_user_permissions(user)

        # Check exact permission
        if screen.value in permissions:
            return True

        # Check parent permission (e.g., 'users' grants 'users.create')
        parent = get_parent_screen(screen)
        if parent and parent.value in permissions:
            return True

        return False

    def has_any_permission(self, user: User, screens: list[Screen]) -> bool:
        """Check if user has access to any of the given screens.

        Args:
            user: User to check
            screens: List of screens to check

        Returns:
            True if user has access to at least one screen
        """
        return any(self.has_permission(user, screen) for screen in screens)

    def has_all_permissions(self, user: User, screens: list[Screen]) -> bool:
        """Check if user has access to all of the given screens.

        Args:
            user: User to check
            screens: List of screens to check

        Returns:
            True if user has access to all screens
        """
        return all(self.has_permission(user, screen) for screen in screens)

    def clear_cache(self) -> None:
        """Clear the permission cache."""
        self._permission_cache = {}

    # =========================================================================
    # Role Permission Management
    # =========================================================================

    def set_role_permissions(self, role: str, screens: list[Screen]) -> None:
        """Set permissions for a role (replaces existing).

        Args:
            role: Role name (admin, rm, analyst, client)
            screens: List of screens to grant access to
        """
        # Remove existing permissions
        self.db.query(RolePermission).filter(RolePermission.role == role).delete()

        # Add new permissions
        for screen in screens:
            permission = RolePermission(role=role, screen_code=screen.value)
            self.db.add(permission)

        self.db.commit()

        # Clear cache
        self.clear_cache()

    def add_permission_to_role(self, role: str, screen: Screen) -> bool:
        """Add a single permission to a role.

        Args:
            role: Role name
            screen: Screen to grant access to

        Returns:
            True if added, False if already exists
        """
        existing = (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role == role,
                RolePermission.screen_code == screen.value,
            )
            .first()
        )

        if existing:
            return False

        permission = RolePermission(role=role, screen_code=screen.value)
        self.db.add(permission)
        self.db.commit()
        self.clear_cache()
        return True

    def remove_permission_from_role(self, role: str, screen: Screen) -> bool:
        """Remove a permission from a role.

        Args:
            role: Role name
            screen: Screen to remove access from

        Returns:
            True if removed, False if not found
        """
        result = (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role == role,
                RolePermission.screen_code == screen.value,
            )
            .delete()
        )
        self.db.commit()
        self.clear_cache()
        return result > 0
