"""remove_saldos_table

Revision ID: 10e24d47b737
Revises: 2aca30aa7d52
Create Date: 2025-11-07 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10e24d47b737'
down_revision: Union[str, None] = '2aca30aa7d52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop saldos table - no longer needed with different granularities"""
    op.drop_table('saldos')


def downgrade() -> None:
    """Recreate saldos table"""
    op.create_table(
        'saldos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empreendimento_id', sa.Integer(), nullable=False),
        sa.Column('mes_referencia', sa.String(length=7), nullable=False),
        sa.Column('saldo_inicial', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('entradas_orcamento', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('entradas_realizado', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('saidas_orcamento', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('saidas_realizado', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('saldo_final_orcamento', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('saldo_final_realizado', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['empreendimento_id'], ['empreendimentos.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empreendimento_id', 'mes_referencia', name='uq_saldo_emp_mes')
    )
    op.create_index('idx_saldo_emp_mes', 'saldos', ['empreendimento_id', 'mes_referencia'])
