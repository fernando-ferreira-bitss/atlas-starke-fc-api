"""renomear_delinquency_para_inadimplencia

Revision ID: 81f9916bc04f
Revises: dc476d3a51d3
Create Date: 2025-11-07 14:13:00.592786

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81f9916bc04f'
down_revision: Union[str, None] = 'dc476d3a51d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename delinquency table to Portuguese."""

    # Rename table
    op.rename_table('delinquency', 'inadimplencia')

    # Rename indexes
    op.execute('ALTER INDEX idx_delinquency_emp_ref_month RENAME TO idx_inadimplencia_emp_ref_month')
    op.execute('ALTER INDEX ix_delinquency_empreendimento_id RENAME TO ix_inadimplencia_empreendimento_id')
    op.execute('ALTER INDEX ix_delinquency_ref_month RENAME TO ix_inadimplencia_ref_month')

    # Rename constraints
    op.execute('ALTER TABLE inadimplencia RENAME CONSTRAINT delinquency_pkey TO inadimplencia_pkey')
    op.execute('ALTER TABLE inadimplencia RENAME CONSTRAINT uq_delinquency_emp_date TO uq_inadimplencia_emp_date')


def downgrade() -> None:
    """Revert delinquency table name back to English."""

    # Revert constraints
    op.execute('ALTER TABLE inadimplencia RENAME CONSTRAINT uq_inadimplencia_emp_date TO uq_delinquency_emp_date')
    op.execute('ALTER TABLE inadimplencia RENAME CONSTRAINT inadimplencia_pkey TO delinquency_pkey')

    # Revert indexes
    op.execute('ALTER INDEX ix_inadimplencia_ref_month RENAME TO ix_delinquency_ref_month')
    op.execute('ALTER INDEX ix_inadimplencia_empreendimento_id RENAME TO ix_delinquency_empreendimento_id')
    op.execute('ALTER INDEX idx_inadimplencia_emp_ref_month RENAME TO idx_delinquency_emp_ref_month')

    # Revert table name
    op.rename_table('inadimplencia', 'delinquency')
