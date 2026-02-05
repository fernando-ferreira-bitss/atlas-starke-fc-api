"""add_role_permission_system

Add role-based permission system:
- Add 'role' column to users table
- Create role_permissions table
- Create rm_client_assignments table
- Migrate existing users (is_superuser=True -> role='admin')

Revision ID: add_role_permission_system
Revises: d47edc701b9c
Create Date: 2025-12-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_role_permission_system"
down_revision: Union[str, None] = "d47edc701b9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role-based permission system."""

    # 1. Add 'role' column to users table (nullable first for migration)
    op.add_column(
        "users",
        sa.Column("role", sa.String(50), nullable=True),
    )

    # 2. Migrate existing users:
    #    - is_superuser=True -> role='admin'
    #    - is_superuser=False -> role='analyst' (safe default)
    op.execute(
        """
        UPDATE users
        SET role = CASE
            WHEN is_superuser = true THEN 'admin'
            ELSE 'analyst'
        END
        """
    )

    # 3. Make role NOT NULL with default 'analyst'
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(50),
        nullable=False,
        server_default="analyst",
    )

    # 4. Add index on role column
    op.create_index("idx_users_role", "users", ["role"])

    # 5. Create role_permissions table
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("screen_code", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role", "screen_code", name="uq_role_screen"),
        sa.CheckConstraint(
            "role IN ('admin', 'rm', 'analyst', 'client')",
            name="check_role_permissions_role",
        ),
    )
    op.create_index("idx_role_permissions_role", "role_permissions", ["role"])
    op.create_index("idx_role_permissions_screen", "role_permissions", ["screen_code"])

    # 6. Create rm_client_assignments table
    op.create_table(
        "rm_client_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rm_user_id", sa.Integer(), nullable=False),
        sa.Column("client_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["rm_user_id"],
            ["users.id"],
            name="fk_rm_assignments_rm_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["client_user_id"],
            ["users.id"],
            name="fk_rm_assignments_client_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_rm_assignments_created_by",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rm_user_id", "client_user_id", name="uq_rm_client"),
    )
    op.create_index("idx_rm_assignments_rm", "rm_client_assignments", ["rm_user_id"])
    op.create_index(
        "idx_rm_assignments_client", "rm_client_assignments", ["client_user_id"]
    )


def downgrade() -> None:
    """Remove role-based permission system."""

    # Drop rm_client_assignments table
    op.drop_index("idx_rm_assignments_client", table_name="rm_client_assignments")
    op.drop_index("idx_rm_assignments_rm", table_name="rm_client_assignments")
    op.drop_table("rm_client_assignments")

    # Drop role_permissions table
    op.drop_index("idx_role_permissions_screen", table_name="role_permissions")
    op.drop_index("idx_role_permissions_role", table_name="role_permissions")
    op.drop_table("role_permissions")

    # Remove role column from users
    op.drop_index("idx_users_role", table_name="users")
    op.drop_column("users", "role")
