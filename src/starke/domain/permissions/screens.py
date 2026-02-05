"""Screen codes and default permissions for the Starke system.

This module defines:
- Screen enum: All available screens/modules in the system
- DEFAULT_ROLE_PERMISSIONS: Default permissions for each role

Usage:
    from starke.domain.permissions import Screen, DEFAULT_ROLE_PERMISSIONS

    # Check if a screen code is valid
    if Screen.DASHBOARD in DEFAULT_ROLE_PERMISSIONS["admin"]:
        print("Admin has access to dashboard")
"""

from enum import Enum
from typing import Optional


class Screen(str, Enum):
    """Screen codes for permission management.

    Each screen represents a module or page in the system.
    Sub-screens use dot notation (e.g., 'users.create').
    Having permission to a parent screen grants access to all sub-screens.
    """

    # ==========================================================================
    # Core Screens (existing system)
    # ==========================================================================

    # Dashboard
    DASHBOARD = "dashboard"

    # Reports
    REPORTS = "reports"
    REPORTS_CASH_FLOW = "reports.cash_flow"
    REPORTS_PORTFOLIO = "reports.portfolio"

    # User Management
    USERS = "users"
    USERS_CREATE = "users.create"
    USERS_EDIT = "users.edit"
    USERS_DELETE = "users.delete"

    # Scheduler
    SCHEDULER = "scheduler"
    SCHEDULER_TRIGGER = "scheduler.trigger"

    # Developments (Empreendimentos)
    DEVELOPMENTS = "developments"

    # Contracts (Contratos)
    CONTRACTS = "contracts"

    # ==========================================================================
    # Patrimony Module (new v2 screens)
    # ==========================================================================

    # Clients Management (Admin/RM view)
    CLIENTS = "clients"
    CLIENTS_CREATE = "clients.create"
    CLIENTS_EDIT = "clients.edit"
    CLIENTS_DELETE = "clients.delete"

    # Assets (Ativos)
    ASSETS = "assets"
    ASSETS_CREATE = "assets.create"
    ASSETS_EDIT = "assets.edit"
    ASSETS_DELETE = "assets.delete"

    # Liabilities (Passivos)
    LIABILITIES = "liabilities"
    LIABILITIES_CREATE = "liabilities.create"
    LIABILITIES_EDIT = "liabilities.edit"
    LIABILITIES_DELETE = "liabilities.delete"

    # Accounts (Contas)
    ACCOUNTS = "accounts"
    ACCOUNTS_CREATE = "accounts.create"
    ACCOUNTS_EDIT = "accounts.edit"

    # Institutions (Instituições)
    INSTITUTIONS = "institutions"

    # Positions (Posições mensais)
    POSITIONS = "positions"
    POSITIONS_IMPORT = "positions.import"

    # Documents
    DOCUMENTS = "documents"
    DOCUMENTS_UPLOAD = "documents.upload"
    DOCUMENTS_DELETE = "documents.delete"

    # ==========================================================================
    # Client Self-Service Screens (for role='client')
    # ==========================================================================

    # Client's own portfolio view
    MY_PORTFOLIO = "my_portfolio"
    MY_ASSETS = "my_assets"
    MY_LIABILITIES = "my_liabilities"
    MY_DOCUMENTS = "my_documents"
    MY_EVOLUTION = "my_evolution"

    # ==========================================================================
    # RM-specific Screens
    # ==========================================================================

    # RM's client list
    MY_CLIENTS = "my_clients"

    # ==========================================================================
    # Admin-only Screens
    # ==========================================================================

    # Audit logs (LGPD)
    AUDIT = "audit"

    # System settings
    SETTINGS = "settings"

    # Impersonation (visualizar como cliente)
    IMPERSONATION = "impersonation"


# Default permissions for each role
# Admin has access to everything
# Other roles have specific permissions
DEFAULT_ROLE_PERMISSIONS: dict[str, list[Screen]] = {
    "admin": [
        # Admin has access to ALL screens
        Screen.DASHBOARD,
        Screen.REPORTS,
        Screen.REPORTS_CASH_FLOW,
        Screen.REPORTS_PORTFOLIO,
        Screen.USERS,
        Screen.USERS_CREATE,
        Screen.USERS_EDIT,
        Screen.USERS_DELETE,
        Screen.SCHEDULER,
        Screen.SCHEDULER_TRIGGER,
        Screen.DEVELOPMENTS,
        Screen.CONTRACTS,
        Screen.CLIENTS,
        Screen.CLIENTS_CREATE,
        Screen.CLIENTS_EDIT,
        Screen.CLIENTS_DELETE,
        Screen.ASSETS,
        Screen.ASSETS_CREATE,
        Screen.ASSETS_EDIT,
        Screen.ASSETS_DELETE,
        Screen.LIABILITIES,
        Screen.LIABILITIES_CREATE,
        Screen.LIABILITIES_EDIT,
        Screen.LIABILITIES_DELETE,
        Screen.ACCOUNTS,
        Screen.ACCOUNTS_CREATE,
        Screen.ACCOUNTS_EDIT,
        Screen.INSTITUTIONS,
        Screen.POSITIONS,
        Screen.POSITIONS_IMPORT,
        Screen.DOCUMENTS,
        Screen.DOCUMENTS_UPLOAD,
        Screen.DOCUMENTS_DELETE,
        Screen.MY_CLIENTS,
        Screen.AUDIT,
        Screen.SETTINGS,
        Screen.IMPERSONATION,
    ],
    "rm": [
        # RM: Manage assigned clients, full CRUD on patrimony
        Screen.DASHBOARD,
        Screen.REPORTS,
        Screen.REPORTS_CASH_FLOW,
        Screen.REPORTS_PORTFOLIO,
        Screen.DEVELOPMENTS,
        Screen.CONTRACTS,
        Screen.MY_CLIENTS,
        Screen.CLIENTS,
        Screen.CLIENTS_CREATE,
        Screen.CLIENTS_EDIT,
        Screen.ASSETS,
        Screen.ASSETS_CREATE,
        Screen.ASSETS_EDIT,
        Screen.LIABILITIES,
        Screen.LIABILITIES_CREATE,
        Screen.LIABILITIES_EDIT,
        Screen.ACCOUNTS,
        Screen.ACCOUNTS_CREATE,
        Screen.ACCOUNTS_EDIT,
        Screen.INSTITUTIONS,
        Screen.POSITIONS,
        Screen.POSITIONS_IMPORT,
        Screen.DOCUMENTS,
        Screen.DOCUMENTS_UPLOAD,
        Screen.IMPERSONATION,
    ],
    "analyst": [
        # Analyst: Read-only access to reports and data
        Screen.DASHBOARD,
        Screen.REPORTS,
        Screen.REPORTS_CASH_FLOW,
        Screen.REPORTS_PORTFOLIO,
        Screen.DEVELOPMENTS,
        Screen.CONTRACTS,
        Screen.CLIENTS,
        Screen.ASSETS,
        Screen.LIABILITIES,
        Screen.ACCOUNTS,
        Screen.INSTITUTIONS,
        Screen.POSITIONS,
        Screen.DOCUMENTS,
    ],
    "client": [
        # Client: View own portfolio only
        Screen.MY_PORTFOLIO,
        Screen.MY_ASSETS,
        Screen.MY_LIABILITIES,
        Screen.MY_DOCUMENTS,
        Screen.MY_EVOLUTION,
    ],
}


def get_all_screens() -> list[str]:
    """Get all screen codes as strings."""
    return [screen.value for screen in Screen]


def get_parent_screen(screen: Screen) -> Optional[Screen]:
    """Get the parent screen for a sub-screen.

    Example: 'users.create' -> 'users'
    """
    if "." in screen.value:
        parent_code = screen.value.rsplit(".", 1)[0]
        try:
            return Screen(parent_code)
        except ValueError:
            return None
    return None
