"""Patrimony management database models.

This module contains all models for the patrimony management system:
- PatInstitution: Financial institutions (banks, brokers)
- PatClient: Clients (PF, PJ, Family, Company)
- PatAccount: Bank/brokerage accounts
- PatAsset: Assets (investments, real estate, etc.)
- PatLiability: Liabilities (loans, mortgages, etc.)
- PatMonthlyPosition: Monthly asset positions
- PatDocument: Documents stored in S3
- PatAuditLog: LGPD audit trail
- PatImportHistory: Import history for position uploads
"""

from starke.infrastructure.database.patrimony.institution import PatInstitution
from starke.infrastructure.database.patrimony.client import PatClient
from starke.infrastructure.database.patrimony.account import PatAccount
from starke.infrastructure.database.patrimony.asset import PatAsset
from starke.infrastructure.database.patrimony.liability import PatLiability
from starke.infrastructure.database.patrimony.monthly_position import PatMonthlyPosition
from starke.infrastructure.database.patrimony.document import PatDocument
from starke.infrastructure.database.patrimony.audit_log import PatAuditLog
from starke.infrastructure.database.patrimony.import_history import PatImportHistory

__all__ = [
    "PatInstitution",
    "PatClient",
    "PatAccount",
    "PatAsset",
    "PatLiability",
    "PatMonthlyPosition",
    "PatDocument",
    "PatAuditLog",
    "PatImportHistory",
]
