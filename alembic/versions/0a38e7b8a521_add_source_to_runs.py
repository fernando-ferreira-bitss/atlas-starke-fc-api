"""add_source_to_runs

Revision ID: 0a38e7b8a521
Revises: add_origem_to_constraints
Create Date: 2026-01-06 11:12:41.510397

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0a38e7b8a521'
down_revision: Union[str, None] = 'add_origem_to_constraints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source column to runs table
    op.add_column('runs', sa.Column('source', sa.String(length=20), nullable=False, server_default='mega'))

    # Create indexes
    op.create_index('idx_runs_source', 'runs', ['source'], unique=False)
    op.create_index('idx_runs_exec_date_source', 'runs', ['exec_date', 'source'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_runs_exec_date_source', table_name='runs')
    op.drop_index('idx_runs_source', table_name='runs')

    # Drop column
    op.drop_column('runs', 'source')
