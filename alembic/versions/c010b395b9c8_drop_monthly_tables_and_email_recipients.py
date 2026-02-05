"""drop_monthly_tables_and_email_recipients

Revision ID: c010b395b9c8
Revises: 041b7bd54fb9
Create Date: 2025-10-31 14:08:27.736939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c010b395b9c8'
down_revision: Union[str, None] = '041b7bd54fb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop monthly aggregation tables (no longer needed - using main tables grouped by ref_month)
    op.drop_table('monthly_cash_flow')
    op.drop_table('monthly_balance')
    op.drop_table('monthly_portfolio_stats')
    op.drop_table('monthly_delinquency')

    # Drop email_recipients table (email functionality removed)
    op.drop_table('email_recipients')

    # Drop report_access_tokens table (public report access removed)
    op.drop_table('report_access_tokens')


def downgrade() -> None:
    # Note: downgrade recreates tables but they will be empty
    # Not implementing full downgrade as these tables are being permanently removed
    pass
