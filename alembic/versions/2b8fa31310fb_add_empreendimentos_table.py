"""add_empreendimentos_table

Revision ID: 2b8fa31310fb
Revises: 6c52ad66450a
Create Date: 2025-10-22 16:51:30.154283

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b8fa31310fb'
down_revision: Union[str, None] = '6c52ad66450a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'empreendimentos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_empreendimento_active', 'empreendimentos', ['is_active'])


def downgrade() -> None:
    op.drop_index('idx_empreendimento_active', table_name='empreendimentos')
    op.drop_table('empreendimentos')
