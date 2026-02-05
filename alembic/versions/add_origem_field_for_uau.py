"""add_origem_field_for_uau

Revision ID: a1b2c3d4e5f6
Revises: 874a4711bc56
Create Date: 2025-12-29

Adiciona campo 'origem' nas tabelas de dados financeiros para suportar
múltiplas fontes de dados (Mega e UAU).

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '874a4711bc56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add origem column to financial tables."""
    # Add origem column to entradas_caixa (CashIn)
    op.add_column(
        'entradas_caixa',
        sa.Column('origem', sa.String(20), nullable=False, server_default='mega')
    )
    op.create_index('idx_entradas_caixa_origem', 'entradas_caixa', ['origem'])

    # Add origem column to saidas_caixa (CashOut)
    op.add_column(
        'saidas_caixa',
        sa.Column('origem', sa.String(20), nullable=False, server_default='mega')
    )
    op.create_index('idx_saidas_caixa_origem', 'saidas_caixa', ['origem'])

    # Add origem column to estatisticas_portfolio (PortfolioStats)
    op.add_column(
        'estatisticas_portfolio',
        sa.Column('origem', sa.String(20), nullable=False, server_default='mega')
    )
    op.create_index('idx_estatisticas_portfolio_origem', 'estatisticas_portfolio', ['origem'])

    # Add origem column to inadimplencia (Delinquency)
    op.add_column(
        'inadimplencia',
        sa.Column('origem', sa.String(20), nullable=False, server_default='mega')
    )
    op.create_index('idx_inadimplencia_origem', 'inadimplencia', ['origem'])

    # Add origem column to empreendimentos (Development)
    op.add_column(
        'empreendimentos',
        sa.Column('origem', sa.String(20), nullable=False, server_default='mega')
    )
    op.create_index('idx_empreendimentos_origem', 'empreendimentos', ['origem'])


def downgrade() -> None:
    """Remove origem column from financial tables."""
    # Remove from empreendimentos
    op.drop_index('idx_empreendimentos_origem', 'empreendimentos')
    op.drop_column('empreendimentos', 'origem')

    # Remove from inadimplencia
    op.drop_index('idx_inadimplencia_origem', 'inadimplencia')
    op.drop_column('inadimplencia', 'origem')

    # Remove from estatisticas_portfolio
    op.drop_index('idx_estatisticas_portfolio_origem', 'estatisticas_portfolio')
    op.drop_column('estatisticas_portfolio', 'origem')

    # Remove from saidas_caixa
    op.drop_index('idx_saidas_caixa_origem', 'saidas_caixa')
    op.drop_column('saidas_caixa', 'origem')

    # Remove from entradas_caixa
    op.drop_index('idx_entradas_caixa_origem', 'entradas_caixa')
    op.drop_column('entradas_caixa', 'origem')
