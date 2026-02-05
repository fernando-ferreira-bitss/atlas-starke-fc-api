"""Remove patrimony tables.

Revision ID: remove_patrimony_tables
Revises: add_last_financial_sync_at
Create Date: 2026-02-05

This migration removes all tables related to the patrimony module
that are not needed for the cash flow system.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_patrimony_tables'
down_revision = 'add_last_financial_sync_at'
branch_labels = None
depends_on = None


def upgrade():
    # Drop patrimony tables (in correct order due to foreign keys)

    # First drop tables that may have foreign keys to others
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
    op.execute("DROP TABLE IF EXISTS monthly_positions CASCADE")
    op.execute("DROP TABLE IF EXISTS assets CASCADE")
    op.execute("DROP TABLE IF EXISTS liabilities CASCADE")
    op.execute("DROP TABLE IF EXISTS accounts CASCADE")
    op.execute("DROP TABLE IF EXISTS clients CASCADE")
    op.execute("DROP TABLE IF EXISTS institutions CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS import_history CASCADE")
    op.execute("DROP TABLE IF EXISTS pat_import_history CASCADE")

    # Other tables that may not be needed
    op.execute("DROP TABLE IF EXISTS report_access_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS user_preferences CASCADE")
    op.execute("DROP TABLE IF EXISTS impersonation_logs CASCADE")

    # Role/permission tables if not needed
    op.execute("DROP TABLE IF EXISTS role_permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS roles CASCADE")


def downgrade():
    # We don't provide downgrade as these tables are being permanently removed
    # If needed, restore from backup or recreate from original migrations
    pass
