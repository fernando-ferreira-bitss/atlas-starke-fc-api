"""Tests for permission system."""

import pytest

from starke.domain.permissions.screens import (
    Screen,
    DEFAULT_ROLE_PERMISSIONS,
    get_all_screens,
)
from starke.infrastructure.database.models import UserRole


class TestScreenEnum:
    """Tests for Screen enum."""

    def test_screen_enum_has_values(self):
        """Test that Screen enum has values defined."""
        screens = list(Screen)
        assert len(screens) > 0

    def test_screen_enum_unique_values(self):
        """Test that all Screen enum values are unique."""
        values = [s.value for s in Screen]
        assert len(values) == len(set(values))

    def test_get_all_screens_returns_list(self):
        """Test that get_all_screens returns a list of screen values (strings)."""
        screens = get_all_screens()
        assert isinstance(screens, list)
        assert len(screens) > 0
        # get_all_screens returns string values, not Screen instances
        assert all(isinstance(s, str) for s in screens)

    def test_common_screens_exist(self):
        """Test that common screens exist in enum."""
        assert Screen.DASHBOARD is not None
        assert Screen.CLIENTS is not None
        assert Screen.ASSETS is not None
        assert Screen.LIABILITIES is not None
        assert Screen.ACCOUNTS is not None
        assert Screen.INSTITUTIONS is not None


class TestDefaultRolePermissions:
    """Tests for DEFAULT_ROLE_PERMISSIONS mapping."""

    def test_admin_has_all_admin_permissions(self):
        """Test that admin role has access to all admin screens (excluding client-only MY_* screens)."""
        admin_permissions = DEFAULT_ROLE_PERMISSIONS.get(UserRole.ADMIN.value, [])

        # Client-only screens that admin doesn't have (and shouldn't have)
        client_only_screens = {Screen.MY_PORTFOLIO, Screen.MY_ASSETS, Screen.MY_LIABILITIES,
                              Screen.MY_DOCUMENTS, Screen.MY_EVOLUTION}

        # Admin should have all screens except client-only MY_* screens
        for screen in Screen:
            if screen in client_only_screens:
                assert screen not in admin_permissions, f"Admin should NOT have client screen: {screen}"
            else:
                assert screen in admin_permissions, f"Admin missing permission for {screen}"

    def test_client_has_limited_permissions(self):
        """Test that client role has only MY_* screens."""
        client_permissions = DEFAULT_ROLE_PERMISSIONS.get(UserRole.CLIENT.value, [])

        # Client should only have access to MY_* screens
        for screen in client_permissions:
            assert screen.value.startswith("my_"), f"Client has non-MY screen: {screen}"

    def test_client_has_my_portfolio(self):
        """Test that client has MY_PORTFOLIO permission."""
        client_permissions = DEFAULT_ROLE_PERMISSIONS.get(UserRole.CLIENT.value, [])
        assert Screen.MY_PORTFOLIO in client_permissions

    def test_rm_has_client_permissions(self):
        """Test that RM has permissions for managing clients."""
        rm_permissions = DEFAULT_ROLE_PERMISSIONS.get(UserRole.RM.value, [])

        # RM should have client-related permissions
        assert Screen.CLIENTS in rm_permissions
        assert Screen.ASSETS in rm_permissions
        assert Screen.LIABILITIES in rm_permissions
        assert Screen.ACCOUNTS in rm_permissions

    def test_rm_has_dashboard(self):
        """Test that RM has dashboard access."""
        rm_permissions = DEFAULT_ROLE_PERMISSIONS.get(UserRole.RM.value, [])
        assert Screen.DASHBOARD in rm_permissions

    def test_analyst_has_read_permissions(self):
        """Test that analyst has read permissions."""
        analyst_permissions = DEFAULT_ROLE_PERMISSIONS.get(UserRole.ANALYST.value, [])

        # Analyst should have viewing permissions
        assert Screen.DASHBOARD in analyst_permissions
        assert Screen.CLIENTS in analyst_permissions
        assert Screen.ASSETS in analyst_permissions

    def test_all_roles_defined(self):
        """Test that all user roles have permissions defined."""
        for role in UserRole:
            assert role.value in DEFAULT_ROLE_PERMISSIONS, f"Missing permissions for role: {role}"

    def test_permissions_are_screen_instances(self):
        """Test that all permissions are Screen instances."""
        for role, permissions in DEFAULT_ROLE_PERMISSIONS.items():
            for permission in permissions:
                assert isinstance(permission, Screen), f"Invalid permission {permission} for role {role}"


class TestPermissionInheritance:
    """Tests for permission inheritance patterns."""

    def test_admin_superset_of_rm(self):
        """Test that admin permissions include all RM permissions."""
        admin_perms = set(DEFAULT_ROLE_PERMISSIONS.get(UserRole.ADMIN.value, []))
        rm_perms = set(DEFAULT_ROLE_PERMISSIONS.get(UserRole.RM.value, []))

        assert rm_perms.issubset(admin_perms)

    def test_admin_superset_of_analyst(self):
        """Test that admin permissions include all analyst permissions."""
        admin_perms = set(DEFAULT_ROLE_PERMISSIONS.get(UserRole.ADMIN.value, []))
        analyst_perms = set(DEFAULT_ROLE_PERMISSIONS.get(UserRole.ANALYST.value, []))

        assert analyst_perms.issubset(admin_perms)

    def test_client_no_admin_screens(self):
        """Test that client has no admin screens."""
        client_permissions = DEFAULT_ROLE_PERMISSIONS.get(UserRole.CLIENT.value, [])

        admin_only_screens = [Screen.USERS, Screen.SETTINGS]
        for screen in admin_only_screens:
            assert screen not in client_permissions
