"""add_external_id_to_empreendimentos_and_filiais

Revision ID: add_external_id_empreendimentos
Revises: 0a38e7b8a521
Create Date: 2026-01-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_external_id_empreendimentos'
down_revision: Union[str, None] = '0a38e7b8a521'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== EMPREENDIMENTOS ==========
    # 1. Add external_id column (nullable initially)
    op.add_column('empreendimentos', sa.Column('external_id', sa.Integer(), nullable=True))

    # 2. Copy current id to external_id for existing records
    op.execute("UPDATE empreendimentos SET external_id = id")

    # 3. Make external_id NOT NULL after populating
    op.alter_column('empreendimentos', 'external_id', nullable=False)

    # 4. Create unique index on (external_id, origem) to prevent duplicates
    op.create_index(
        'idx_empreendimentos_external_origem',
        'empreendimentos',
        ['external_id', 'origem'],
        unique=True
    )

    # ========== FILIAIS ==========
    # 1. Add external_id column (nullable initially)
    op.add_column('filiais', sa.Column('external_id', sa.Integer(), nullable=True))

    # 2. Copy current id to external_id for existing records
    # For UAU filiais, remove the offset (1000000) to get the original empresa ID
    op.execute("""
        UPDATE filiais
        SET external_id = CASE
            WHEN origem = 'uau' THEN id - 1000000
            ELSE id
        END
    """)

    # 3. Make external_id NOT NULL after populating
    op.alter_column('filiais', 'external_id', nullable=False)

    # 4. Create unique index on (external_id, origem) to prevent duplicates
    op.create_index(
        'idx_filiais_external_origem',
        'filiais',
        ['external_id', 'origem'],
        unique=True
    )


def downgrade() -> None:
    # ========== FILIAIS ==========
    op.drop_index('idx_filiais_external_origem', table_name='filiais')
    op.drop_column('filiais', 'external_id')

    # ========== EMPREENDIMENTOS ==========
    op.drop_index('idx_empreendimentos_external_origem', table_name='empreendimentos')
    op.drop_column('empreendimentos', 'external_id')
