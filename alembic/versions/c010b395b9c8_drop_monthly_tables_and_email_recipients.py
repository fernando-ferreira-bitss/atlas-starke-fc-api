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
    # Using IF EXISTS to handle cases where tables don't exist (fresh database)
    op.execute("DROP TABLE IF EXISTS monthly_cash_flow CASCADE")
    op.execute("DROP TABLE IF EXISTS monthly_balance CASCADE")
    op.execute("DROP TABLE IF EXISTS monthly_portfolio_stats CASCADE")
    op.execute("DROP TABLE IF EXISTS monthly_delinquency CASCADE")

    # Drop email_recipients table (email functionality removed)
    op.execute("DROP TABLE IF EXISTS email_recipients CASCADE")

    # Drop report_access_tokens table (public report access removed)
    op.execute("DROP TABLE IF EXISTS report_access_tokens CASCADE")


def downgrade() -> None:
    # Note: downgrade recreates tables but they will be empty
    # Not implementing full downgrade as these tables are being permanently removed
    pass
