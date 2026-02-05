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
    # Drop patrimony tables (all have pat_ prefix)
    op.execute("DROP TABLE IF EXISTS pat_documents CASCADE")
    op.execute("DROP TABLE IF EXISTS pat_monthly_positions CASCADE")
    op.execute("DROP TABLE IF EXISTS pat_assets CASCADE")
    op.execute("DROP TABLE IF EXISTS pat_liabilities CASCADE")
    op.execute("DROP TABLE IF EXISTS pat_accounts CASCADE")
    op.execute("DROP TABLE IF EXISTS pat_clients CASCADE")
    op.execute("DROP TABLE IF EXISTS pat_institutions CASCADE")
    op.execute("DROP TABLE IF EXISTS pat_audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS pat_import_history CASCADE")

    # Drop impersonation logs (not needed for cash flow)
    op.execute("DROP TABLE IF EXISTS impersonation_logs CASCADE")


def downgrade():
    # We don't provide downgrade as these tables are being permanently removed
    # If needed, restore from backup or recreate from original migrations
    pass
