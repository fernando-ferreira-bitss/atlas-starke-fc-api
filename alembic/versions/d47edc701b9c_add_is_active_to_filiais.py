"""add_is_active_to_filiais

Revision ID: d47edc701b9c
Revises: 10e24d47b737
Create Date: 2025-11-07 16:43:44.982663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd47edc701b9c'
down_revision: Union[str, None] = '10e24d47b737'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active column to filiais table."""
    # Add is_active column with default True for existing records
    op.add_column('filiais', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Create index on is_active for better query performance
    op.create_index('idx_filiais_is_active', 'filiais', ['is_active'])


def downgrade() -> None:
    """Remove is_active column from filiais table."""
    op.drop_index('idx_filiais_is_active', 'filiais')
    op.drop_column('filiais', 'is_active')
