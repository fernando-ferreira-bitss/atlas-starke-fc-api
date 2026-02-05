"""add_triggered_by_user_id_to_runs

Revision ID: 8f0414affd51
Revises: a1b2c3d4e5f6
Create Date: 2025-12-31 11:20:24.819328

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f0414affd51'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add triggered_by_user_id column to runs table
    op.add_column('runs', sa.Column('triggered_by_user_id', sa.Integer(), nullable=True))
    op.create_index('idx_runs_triggered_by', 'runs', ['triggered_by_user_id'], unique=False)
    op.create_foreign_key(
        'fk_runs_triggered_by_user_id',
        'runs', 'users',
        ['triggered_by_user_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_runs_triggered_by_user_id', 'runs', type_='foreignkey')
    op.drop_index('idx_runs_triggered_by', table_name='runs')
    op.drop_column('runs', 'triggered_by_user_id')
