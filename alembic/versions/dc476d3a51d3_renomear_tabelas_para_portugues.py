"""renomear_tabelas_para_portugues

Revision ID: dc476d3a51d3
Revises: dedece336096
Create Date: 2025-11-07 13:54:00.788746

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc476d3a51d3'
down_revision: Union[str, None] = 'dedece336096'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename tables from English to Portuguese."""

    # Rename main tables
    op.rename_table('developments', 'empreendimentos')
    op.rename_table('contracts', 'contratos')
    op.rename_table('cash_in', 'entradas_caixa')
    op.rename_table('cash_out', 'saidas_caixa')
    op.rename_table('balance', 'saldos')
    op.rename_table('portfolio_stats', 'estatisticas_portfolio')

    # Update index names to match new table names
    # cash_out (now saidas_caixa) indexes - já renomeados parcialmente
    # Alguns já foram renomeados na migração anterior, outros precisam ser renomeados

    # cash_in (now entradas_caixa) indexes
    op.execute('ALTER INDEX idx_cash_in_emp_ref_month RENAME TO idx_entradas_caixa_emp_mes_ref')
    op.execute('ALTER INDEX idx_cash_in_ref_month_category RENAME TO idx_entradas_caixa_mes_categoria')
    op.execute('ALTER INDEX ix_cash_in_empreendimento_id RENAME TO ix_entradas_caixa_empreendimento_id')
    op.execute('ALTER INDEX ix_cash_in_ref_month RENAME TO ix_entradas_caixa_ref_month')
    op.execute('ALTER INDEX uq_cash_in_emp_month_category RENAME TO uq_entradas_caixa_emp_mes_categoria')

    # developments (now empreendimentos) indexes
    op.execute('ALTER INDEX idx_development_active RENAME TO idx_empreendimento_ativo')
    op.execute('ALTER INDEX idx_development_centro_custo RENAME TO idx_empreendimento_centro_custo')
    op.execute('ALTER INDEX idx_development_filial RENAME TO idx_empreendimento_filial')
    op.execute('ALTER INDEX ix_developments_centro_custo_id RENAME TO ix_empreendimentos_centro_custo_id')
    op.execute('ALTER INDEX ix_developments_filial_id RENAME TO ix_empreendimentos_filial_id')

    # Update constraint names (only primary keys, no foreign keys exist)
    op.execute('ALTER TABLE saidas_caixa RENAME CONSTRAINT cash_out_pkey TO saidas_caixa_pkey')
    op.execute('ALTER TABLE entradas_caixa RENAME CONSTRAINT cash_in_pkey TO entradas_caixa_pkey')
    op.execute('ALTER TABLE contratos RENAME CONSTRAINT contracts_pkey TO contratos_pkey')
    op.execute('ALTER TABLE saldos RENAME CONSTRAINT balance_pkey TO saldos_pkey')
    op.execute('ALTER TABLE estatisticas_portfolio RENAME CONSTRAINT portfolio_stats_pkey TO estatisticas_portfolio_pkey')

    # Note: developments already has empreendimentos_pkey from previous migration, skip rename


def downgrade() -> None:
    """Revert table names back to English."""

    # Revert constraint names (only primary keys)
    op.execute('ALTER TABLE estatisticas_portfolio RENAME CONSTRAINT estatisticas_portfolio_pkey TO portfolio_stats_pkey')
    op.execute('ALTER TABLE saldos RENAME CONSTRAINT saldos_pkey TO balance_pkey')
    op.execute('ALTER TABLE contratos RENAME CONSTRAINT contratos_pkey TO contracts_pkey')
    op.execute('ALTER TABLE entradas_caixa RENAME CONSTRAINT entradas_caixa_pkey TO cash_in_pkey')
    op.execute('ALTER TABLE saidas_caixa RENAME CONSTRAINT saidas_caixa_pkey TO cash_out_pkey')

    # Note: empreendimentos already had empreendimentos_pkey, will need to rename to developments_pkey
    op.execute('ALTER TABLE empreendimentos RENAME CONSTRAINT empreendimentos_pkey TO developments_pkey')

    # Revert index names
    op.execute('ALTER INDEX ix_empreendimentos_filial_id RENAME TO ix_developments_filial_id')
    op.execute('ALTER INDEX ix_empreendimentos_centro_custo_id RENAME TO ix_developments_centro_custo_id')
    op.execute('ALTER INDEX idx_empreendimento_filial RENAME TO idx_development_filial')
    op.execute('ALTER INDEX idx_empreendimento_centro_custo RENAME TO idx_development_centro_custo')
    op.execute('ALTER INDEX idx_empreendimento_ativo RENAME TO idx_development_active')

    op.execute('ALTER INDEX uq_entradas_caixa_emp_mes_categoria RENAME TO uq_cash_in_emp_month_category')
    op.execute('ALTER INDEX ix_entradas_caixa_ref_month RENAME TO ix_cash_in_ref_month')
    op.execute('ALTER INDEX ix_entradas_caixa_empreendimento_id RENAME TO ix_cash_in_empreendimento_id')
    op.execute('ALTER INDEX idx_entradas_caixa_mes_categoria RENAME TO idx_cash_in_ref_month_category')
    op.execute('ALTER INDEX idx_entradas_caixa_emp_mes_ref RENAME TO idx_cash_in_emp_ref_month')

    # Revert table names
    op.rename_table('estatisticas_portfolio', 'portfolio_stats')
    op.rename_table('saldos', 'balance')
    op.rename_table('saidas_caixa', 'cash_out')
    op.rename_table('entradas_caixa', 'cash_in')
    op.rename_table('contratos', 'contracts')
    op.rename_table('empreendimentos', 'developments')
