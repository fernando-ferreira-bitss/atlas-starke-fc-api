"""change_ref_date_to_ref_month_and_add_unique_constraints

Revision ID: 488959abe488
Revises: 89992e171a45
Create Date: 2025-10-23 20:37:28.530173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '488959abe488'
down_revision: Union[str, None] = '89992e171a45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migration to change ref_date (YYYY-MM-DD) to ref_month (YYYY-MM)
    and add unique constraints for UPSERT functionality.
    """

    # Step 1: Rename columns from ref_date to ref_month in all tables
    # PostgreSQL: Use ALTER TABLE ... RENAME COLUMN

    # CashIn table
    op.alter_column('cash_in', 'ref_date', new_column_name='ref_month')

    # CashOut table
    op.alter_column('cash_out', 'ref_date', new_column_name='ref_month')

    # Balance table - keep unique constraint name
    op.drop_constraint('uq_balance_emp_date', 'balance', type_='unique')
    op.alter_column('balance', 'ref_date', new_column_name='ref_month')
    op.create_unique_constraint('uq_balance_emp_month', 'balance', ['empreendimento_id', 'ref_month'])

    # PortfolioStats table - keep unique constraint name
    op.drop_constraint('uq_portfolio_emp_date', 'portfolio_stats', type_='unique')
    op.alter_column('portfolio_stats', 'ref_date', new_column_name='ref_month')
    op.create_unique_constraint('uq_portfolio_emp_month', 'portfolio_stats', ['empreendimento_id', 'ref_month'])

    # Step 2: Add unique constraints to cash_in and cash_out for UPSERT
    op.create_unique_constraint(
        'uq_cash_in_emp_month_category',
        'cash_in',
        ['empreendimento_id', 'ref_month', 'category']
    )

    op.create_unique_constraint(
        'uq_cash_out_emp_month_category',
        'cash_out',
        ['empreendimento_id', 'ref_month', 'category']
    )

    # Step 3: Drop old indexes and create new ones with correct column name
    op.drop_index('idx_cash_in_emp_ref_date', table_name='cash_in')
    op.drop_index('idx_cash_in_ref_date_category', table_name='cash_in')
    op.create_index('idx_cash_in_emp_ref_month', 'cash_in', ['empreendimento_id', 'ref_month'])
    op.create_index('idx_cash_in_ref_month_category', 'cash_in', ['ref_month', 'category'])

    op.drop_index('idx_cash_out_emp_ref_date', table_name='cash_out')
    op.drop_index('idx_cash_out_ref_date_category', table_name='cash_out')
    op.create_index('idx_cash_out_emp_ref_month', 'cash_out', ['empreendimento_id', 'ref_month'])
    op.create_index('idx_cash_out_ref_month_category', 'cash_out', ['ref_month', 'category'])

    op.drop_index('idx_balance_emp_ref_date', table_name='balance')
    op.create_index('idx_balance_emp_ref_month', 'balance', ['empreendimento_id', 'ref_month'])

    op.drop_index('idx_portfolio_emp_ref_date', table_name='portfolio_stats')
    op.create_index('idx_portfolio_emp_ref_month', 'portfolio_stats', ['empreendimento_id', 'ref_month'])

    # Step 4: Update existing data from YYYY-MM-DD to YYYY-MM format
    # This requires executing raw SQL to convert existing dates
    op.execute("""
        UPDATE cash_in
        SET ref_month = substring(ref_month from 1 for 7)
        WHERE length(ref_month) = 10
    """)

    op.execute("""
        UPDATE cash_out
        SET ref_month = substring(ref_month from 1 for 7)
        WHERE length(ref_month) = 10
    """)

    op.execute("""
        UPDATE balance
        SET ref_month = substring(ref_month from 1 for 7)
        WHERE length(ref_month) = 10
    """)

    op.execute("""
        UPDATE portfolio_stats
        SET ref_month = substring(ref_month from 1 for 7)
        WHERE length(ref_month) = 10
    """)


def downgrade() -> None:
    """Rollback changes."""

    # Drop unique constraints
    op.drop_constraint('uq_cash_in_emp_month_category', 'cash_in', type_='unique')
    op.drop_constraint('uq_cash_out_emp_month_category', 'cash_out', type_='unique')

    # Rename columns back
    op.alter_column('cash_in', 'ref_month', new_column_name='ref_date')
    op.alter_column('cash_out', 'ref_month', new_column_name='ref_date')

    op.drop_constraint('uq_balance_emp_month', 'balance', type_='unique')
    op.alter_column('balance', 'ref_month', new_column_name='ref_date')
    op.create_unique_constraint('uq_balance_emp_date', 'balance', ['empreendimento_id', 'ref_date'])

    op.drop_constraint('uq_portfolio_emp_month', 'portfolio_stats', type_='unique')
    op.alter_column('portfolio_stats', 'ref_month', new_column_name='ref_date')
    op.create_unique_constraint('uq_portfolio_emp_date', 'portfolio_stats', ['empreendimento_id', 'ref_date'])

    # Recreate old indexes
    op.drop_index('idx_cash_in_emp_ref_month', table_name='cash_in')
    op.drop_index('idx_cash_in_ref_month_category', table_name='cash_in')
    op.create_index('idx_cash_in_emp_ref_date', 'cash_in', ['empreendimento_id', 'ref_date'])
    op.create_index('idx_cash_in_ref_date_category', 'cash_in', ['ref_date', 'category'])

    op.drop_index('idx_cash_out_emp_ref_month', table_name='cash_out')
    op.drop_index('idx_cash_out_ref_month_category', table_name='cash_out')
    op.create_index('idx_cash_out_emp_ref_date', 'cash_out', ['empreendimento_id', 'ref_date'])
    op.create_index('idx_cash_out_ref_date_category', 'cash_out', ['ref_date', 'category'])

    op.drop_index('idx_balance_emp_ref_month', table_name='balance')
    op.create_index('idx_balance_emp_ref_date', 'balance', ['empreendimento_id', 'ref_date'])

    op.drop_index('idx_portfolio_emp_ref_month', table_name='portfolio_stats')
    op.create_index('idx_portfolio_emp_ref_date', 'portfolio_stats', ['empreendimento_id', 'ref_date'])
