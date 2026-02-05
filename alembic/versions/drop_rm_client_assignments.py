"""Drop rm_client_assignments table

Revision ID: drop_rm_client_assignments
Revises: add_impersonation_logs
Create Date: 2026-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "drop_rm_client_assignments"
down_revision: Union[str, None] = "add_impersonation_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop rm_client_assignments table."""
    op.drop_table("rm_client_assignments")


def downgrade() -> None:
    """Recreate rm_client_assignments table."""
    op.create_table(
        "rm_client_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rm_user_id", sa.Integer(), nullable=False),
        sa.Column("client_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["client_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["rm_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rm_user_id", "client_user_id", name="uq_rm_client"),
    )
    op.create_index("idx_rm_assignments_rm", "rm_client_assignments", ["rm_user_id"])
    op.create_index("idx_rm_assignments_client", "rm_client_assignments", ["client_user_id"])
