"""add pat_import_history table

Revision ID: a790b9a1721d
Revises: add_patrimony_tables
Create Date: 2025-12-08 09:49:36.373934

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a790b9a1721d'
down_revision: Union[str, None] = 'add_patrimony_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pat_import_history',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('reference_date', sa.String(10), nullable=False),
        sa.Column('imported_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('errors', sa.Text(), nullable=True),
        sa.Column('uploaded_by', sa.String(255), nullable=True),
        sa.Column('uploaded_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pat_import_history_status', 'pat_import_history', ['status'])
    op.create_index('idx_pat_import_history_reference_date', 'pat_import_history', ['reference_date'])
    op.create_index('idx_pat_import_history_created_at', 'pat_import_history', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_pat_import_history_created_at', table_name='pat_import_history')
    op.drop_index('idx_pat_import_history_reference_date', table_name='pat_import_history')
    op.drop_index('idx_pat_import_history_status', table_name='pat_import_history')
    op.drop_table('pat_import_history')
