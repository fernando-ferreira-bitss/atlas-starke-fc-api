"""Add last_financial_sync_at to empreendimentos table.

Revision ID: add_last_financial_sync_at
Revises: add_origem_to_contratos
Create Date: 2026-02-04

This migration adds a timestamp field to track when each development
was last fully synchronized (CashIn/CashOut). This enables checkpoint/resume
functionality for long-running sync operations.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_last_financial_sync_at'
down_revision = 'add_origem_to_contratos'
branch_labels = None
depends_on = None


def upgrade():
    # Add last_financial_sync_at column to empreendimentos table
    # This tracks when the last full financial sync was completed for each development
    op.add_column(
        'empreendimentos',
        sa.Column('last_financial_sync_at', sa.DateTime(), nullable=True)
    )


def downgrade():
    # Remove the column
    op.drop_column('empreendimentos', 'last_financial_sync_at')
