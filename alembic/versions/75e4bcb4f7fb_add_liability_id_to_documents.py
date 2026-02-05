"""add_liability_id_to_documents

Revision ID: 75e4bcb4f7fb
Revises: 1dbff35f92c0
Create Date: 2025-12-09 12:44:20.376911

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '75e4bcb4f7fb'
down_revision: Union[str, None] = '1dbff35f92c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add liability_id column to pat_documents
    op.add_column(
        'pat_documents',
        sa.Column('liability_id', postgresql.UUID(as_uuid=False), nullable=True)
    )
    # Add foreign key constraint
    op.create_foreign_key(
        'pat_documents_liability_id_fkey',
        'pat_documents',
        'pat_liabilities',
        ['liability_id'],
        ['id'],
        ondelete='SET NULL'
    )
    # Add index
    op.create_index('idx_pat_documents_liability', 'pat_documents', ['liability_id'])


def downgrade() -> None:
    op.drop_index('idx_pat_documents_liability', table_name='pat_documents')
    op.drop_constraint('pat_documents_liability_id_fkey', 'pat_documents', type_='foreignkey')
    op.drop_column('pat_documents', 'liability_id')
