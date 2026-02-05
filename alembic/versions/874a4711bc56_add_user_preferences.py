"""add_user_preferences

Revision ID: 874a4711bc56
Revises: 75e4bcb4f7fb
Create Date: 2025-12-09 17:55:09.838342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '874a4711bc56'
down_revision: Union[str, None] = '75e4bcb4f7fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add preferences column to users table
    op.add_column('users', sa.Column('preferences', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove preferences column from users table
    op.drop_column('users', 'preferences')
