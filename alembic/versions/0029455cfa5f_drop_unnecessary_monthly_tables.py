"""drop_unnecessary_monthly_tables

Revision ID: 0029455cfa5f
Revises: 488959abe488
Create Date: 2025-10-23 20:39:02.766435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0029455cfa5f'
down_revision: Union[str, None] = '488959abe488'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop unnecessary monthly aggregation tables.

    Tables being removed:
    - monthly_balance (duplicated with balance table)
    - monthly_cash_flow (duplicated with cash_in/cash_out tables)
    - monthly_delinquency (duplicated with delinquency table)
    - monthly_portfolio_stats (duplicated with portfolio_stats table)

    Keeping:
    - cash_in (with ref_month)
    - cash_out (with ref_month)
    - balance (with ref_month)
    - portfolio_stats (with ref_month)
    - delinquency (will be updated if needed)
    """

    # Drop monthly tables
    op.drop_table('monthly_balance')
    op.drop_table('monthly_cash_flow')
    op.drop_table('monthly_delinquency')
    op.drop_table('monthly_portfolio_stats')


def downgrade() -> None:
    """Recreate monthly tables if needed (not implemented for now)."""
    pass
