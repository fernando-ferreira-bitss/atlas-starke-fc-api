"""add document status validation fields

Revision ID: 1dbff35f92c0
Revises: a790b9a1721d
Create Date: 2025-12-08 10:40:14.076993

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1dbff35f92c0'
down_revision: Union[str, None] = 'a790b9a1721d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status validation fields to pat_documents
    op.add_column('pat_documents', sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('pat_documents', sa.Column('validated_by', sa.Integer(), nullable=True))
    op.add_column('pat_documents', sa.Column('validated_at', sa.DateTime(), nullable=True))
    op.add_column('pat_documents', sa.Column('validation_notes', sa.Text(), nullable=True))

    # Add foreign key for validated_by
    op.create_foreign_key(
        'pat_documents_validated_by_fkey',
        'pat_documents', 'users',
        ['validated_by'], ['id'],
        ondelete='SET NULL'
    )

    # Add index on status
    op.create_index('idx_pat_documents_status', 'pat_documents', ['status'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_pat_documents_status', table_name='pat_documents')

    # Remove foreign key
    op.drop_constraint('pat_documents_validated_by_fkey', 'pat_documents', type_='foreignkey')

    # Remove columns
    op.drop_column('pat_documents', 'validation_notes')
    op.drop_column('pat_documents', 'validated_at')
    op.drop_column('pat_documents', 'validated_by')
    op.drop_column('pat_documents', 'status')
