"""fix_fatura_unique_constraint_add_filial

Revision ID: 2aca30aa7d52
Revises: 81f9916bc04f
Create Date: 2025-11-07 15:22:57.387890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2aca30aa7d52'
down_revision: Union[str, None] = '81f9916bc04f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop old constraint and add new one with filial_id"""
    # First, clear the table to avoid duplicate issues
    op.execute("TRUNCATE TABLE faturas_pagar CASCADE")

    # Drop the old constraint
    op.drop_constraint('uq_fatura_ap_parcela', 'faturas_pagar', type_='unique')

    # Create new constraint with filial_id
    op.create_unique_constraint(
        'uq_fatura_filial_ap_parcela',
        'faturas_pagar',
        ['filial_id', 'numero_ap', 'numero_parcela']
    )


def downgrade() -> None:
    """Restore old constraint"""
    # Drop new constraint
    op.drop_constraint('uq_fatura_filial_ap_parcela', 'faturas_pagar', type_='unique')

    # Restore old constraint
    op.create_unique_constraint(
        'uq_fatura_ap_parcela',
        'faturas_pagar',
        ['numero_ap', 'numero_parcela']
    )
