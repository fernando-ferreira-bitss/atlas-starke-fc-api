"""add_impersonation_logs

Adiciona tabela para log de sessões de impersonation.
Registra quando um admin/rm visualiza o portal como um cliente.

Revision ID: add_impersonation_logs
Revises: add_external_id_empreendimentos
Create Date: 2026-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_impersonation_logs"
down_revision: Union[str, None] = "add_external_id_empreendimentos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabela impersonation_logs."""
    op.create_table(
        "impersonation_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("target_client_id", sa.String(36), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_impersonation_actor_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name="fk_impersonation_target_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_impersonation_actor", "impersonation_logs", ["actor_user_id"])
    op.create_index("idx_impersonation_target", "impersonation_logs", ["target_client_id"])
    op.create_index("idx_impersonation_started", "impersonation_logs", ["started_at"])


def downgrade() -> None:
    """Remove tabela impersonation_logs."""
    op.drop_index("idx_impersonation_started", table_name="impersonation_logs")
    op.drop_index("idx_impersonation_target", table_name="impersonation_logs")
    op.drop_index("idx_impersonation_actor", table_name="impersonation_logs")
    op.drop_table("impersonation_logs")
