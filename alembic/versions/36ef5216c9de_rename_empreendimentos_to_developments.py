"""rename_empreendimentos_to_developments

Revision ID: 36ef5216c9de
Revises: 2b8fa31310fb
Create Date: 2025-10-22 16:59:00.879924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36ef5216c9de'
down_revision: Union[str, None] = '2b8fa31310fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename table
    op.rename_table('empreendimentos', 'developments')

    # Drop old index
    op.drop_index('idx_empreendimento_active', table_name='developments')

    # Rename column
    op.alter_column('developments', 'nome', new_column_name='name')

    # Create new index with new name
    op.create_index('idx_development_active', 'developments', ['is_active'])


def downgrade() -> None:
    # Drop new index
    op.drop_index('idx_development_active', table_name='developments')

    # Rename column back
    op.alter_column('developments', 'name', new_column_name='nome')

    # Create old index
    op.create_index('idx_empreendimento_active', 'developments', ['is_active'])

    # Rename table back
    op.rename_table('developments', 'empreendimentos')
