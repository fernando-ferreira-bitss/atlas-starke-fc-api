"""add_origem_field_to_faturas_pagar

Revision ID: add_origem_faturas
Revises: 6e080ee879a7
Create Date: 2026-01-05 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_origem_faturas'
down_revision: Union[str, None] = '6e080ee879a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add origem column with default 'mega' for existing records
    op.add_column('faturas_pagar', sa.Column('origem', sa.String(length=10), nullable=True))

    # Set default value for existing records
    op.execute("UPDATE faturas_pagar SET origem = 'mega' WHERE origem IS NULL")

    # Make column non-nullable
    op.alter_column('faturas_pagar', 'origem', nullable=False)

    # Increase numero_ap size to accommodate UAU composite keys
    op.alter_column('faturas_pagar', 'numero_ap',
                    existing_type=sa.VARCHAR(length=50),
                    type_=sa.String(length=100),
                    existing_nullable=False)

    # Drop old unique constraint (filial_id, numero_ap, numero_parcela)
    op.drop_constraint('uq_fatura_filial_ap_parcela', 'faturas_pagar', type_='unique')

    # Create new unique constraint including origem and filial_id
    op.create_unique_constraint(
        'uq_fatura_origem_filial_ap_parcela',
        'faturas_pagar',
        ['origem', 'filial_id', 'numero_ap', 'numero_parcela']
    )

    # Add index on origem for filtering
    op.create_index('idx_fatura_origem', 'faturas_pagar', ['origem'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_fatura_origem', table_name='faturas_pagar')

    # Drop new constraint
    op.drop_constraint('uq_fatura_origem_filial_ap_parcela', 'faturas_pagar', type_='unique')

    # Recreate old constraint
    op.create_unique_constraint(
        'uq_fatura_filial_ap_parcela',
        'faturas_pagar',
        ['filial_id', 'numero_ap', 'numero_parcela']
    )

    # Revert numero_ap size
    op.alter_column('faturas_pagar', 'numero_ap',
                    existing_type=sa.String(length=100),
                    type_=sa.VARCHAR(length=50),
                    existing_nullable=False)

    # Remove origem column
    op.drop_column('faturas_pagar', 'origem')
