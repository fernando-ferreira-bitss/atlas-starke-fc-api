"""Add origem to unique constraints.

Revision ID: add_origem_to_constraints
Revises: add_origem_field_for_uau
Create Date: 2026-01-06 12:00:00

This migration:
1. Updates unique constraints to include 'origem' field
2. Allows same empreendimento/ref_month/category for different origins (mega, uau)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_origem_to_constraints'
down_revision = ('a1b2c3d4e5f6', 'add_origem_faturas')  # Merge multiple heads
branch_labels = None
depends_on = None


def upgrade():
    # 1. CashIn (entradas_caixa)
    # Drop old constraint (actual name in DB)
    op.drop_constraint('uq_entradas_caixa_emp_mes_categoria', 'entradas_caixa', type_='unique')
    # Create new constraint with origem
    op.create_unique_constraint(
        'uq_cash_in_emp_month_category_origem',
        'entradas_caixa',
        ['empreendimento_id', 'ref_month', 'category', 'origem']
    )

    # 2. CashOut (saidas_caixa)
    # Drop old constraint
    op.drop_constraint('uq_cash_out_filial_mes_categoria', 'saidas_caixa', type_='unique')
    # Create new constraint with origem
    op.create_unique_constraint(
        'uq_cash_out_filial_mes_categoria_origem',
        'saidas_caixa',
        ['filial_id', 'mes_referencia', 'categoria', 'origem']
    )

    # 3. PortfolioStats (estatisticas_portfolio)
    # Drop old constraint
    op.drop_constraint('uq_portfolio_emp_month', 'estatisticas_portfolio', type_='unique')
    # Create new constraint with origem
    op.create_unique_constraint(
        'uq_portfolio_emp_month_origem',
        'estatisticas_portfolio',
        ['empreendimento_id', 'ref_month', 'origem']
    )

    # 4. Delinquency (inadimplencia)
    # Drop old constraint (actual name in DB)
    op.drop_constraint('uq_inadimplencia_emp_date', 'inadimplencia', type_='unique')
    # Create new constraint with origem
    op.create_unique_constraint(
        'uq_delinquency_emp_date_origem',
        'inadimplencia',
        ['empreendimento_id', 'ref_month', 'origem']
    )


def downgrade():
    # 1. CashIn (entradas_caixa)
    op.drop_constraint('uq_cash_in_emp_month_category_origem', 'entradas_caixa', type_='unique')
    op.create_unique_constraint(
        'uq_entradas_caixa_emp_mes_categoria',
        'entradas_caixa',
        ['empreendimento_id', 'ref_month', 'category']
    )

    # 2. CashOut (saidas_caixa)
    op.drop_constraint('uq_cash_out_filial_mes_categoria_origem', 'saidas_caixa', type_='unique')
    op.create_unique_constraint(
        'uq_cash_out_filial_mes_categoria',
        'saidas_caixa',
        ['filial_id', 'mes_referencia', 'categoria']
    )

    # 3. PortfolioStats (estatisticas_portfolio)
    op.drop_constraint('uq_portfolio_emp_month_origem', 'estatisticas_portfolio', type_='unique')
    op.create_unique_constraint(
        'uq_portfolio_emp_month',
        'estatisticas_portfolio',
        ['empreendimento_id', 'ref_month']
    )

    # 4. Delinquency (inadimplencia)
    op.drop_constraint('uq_delinquency_emp_date_origem', 'inadimplencia', type_='unique')
    op.create_unique_constraint(
        'uq_inadimplencia_emp_date',
        'inadimplencia',
        ['empreendimento_id', 'ref_month']
    )
