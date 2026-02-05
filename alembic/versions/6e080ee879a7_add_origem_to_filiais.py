"""add_origem_to_filiais

Revision ID: 6e080ee879a7
Revises: 8f0414affd51
Create Date: 2026-01-05 11:15:07.826198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6e080ee879a7'
down_revision: Union[str, None] = '8f0414affd51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add origem column to filiais table
    op.add_column('filiais', sa.Column('origem', sa.String(length=20), nullable=False, server_default='mega'))
    op.create_index('idx_filial_origem', 'filiais', ['origem'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_filial_origem', table_name='filiais')
    op.drop_column('filiais', 'origem')
