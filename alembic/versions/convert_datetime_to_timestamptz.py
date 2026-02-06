"""Convert datetime columns to TIMESTAMP WITH TIME ZONE.

Altera todas as colunas TIMESTAMP para TIMESTAMP WITH TIME ZONE,
interpretando valores existentes como UTC.

Revision ID: convert_datetime_to_timestamptz
Revises: create_default_admin_user
Create Date: 2026-02-06

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'convert_datetime_to_timestamptz'
down_revision = 'create_default_admin_user'
branch_labels = None
depends_on = None

# Mapeamento: tabela -> lista de colunas datetime
TABLES_COLUMNS = {
    "runs": ["started_at", "finished_at"],
    "raw_payloads": ["created_at"],
    "entradas_caixa": ["created_at"],
    "saidas_caixa": ["criado_em"],
    "estatisticas_portfolio": ["created_at"],
    "inadimplencia": ["created_at"],
    "users": ["created_at", "updated_at"],
    "filiais": ["criado_em", "atualizado_em"],
    "empreendimentos": ["created_at", "updated_at", "last_synced_at", "last_financial_sync_at"],
    "contratos": ["last_synced_at"],
    "faturas_pagar": ["criado_em", "atualizado_em"],
    "role_permissions": ["created_at"],
    "impersonation_logs": ["started_at", "ended_at"],
}


def upgrade():
    """Convert all datetime columns to TIMESTAMP WITH TIME ZONE."""
    for table, columns in TABLES_COLUMNS.items():
        for col in columns:
            op.execute(
                sa.text(
                    f'ALTER TABLE {table} ALTER COLUMN "{col}" '
                    f"TYPE TIMESTAMP WITH TIME ZONE USING \"{col}\" AT TIME ZONE 'UTC'"
                )
            )


def downgrade():
    """Revert TIMESTAMP WITH TIME ZONE back to TIMESTAMP (without timezone)."""
    for table, columns in TABLES_COLUMNS.items():
        for col in columns:
            op.execute(
                sa.text(
                    f'ALTER TABLE {table} ALTER COLUMN "{col}" '
                    f"TYPE TIMESTAMP WITHOUT TIME ZONE"
                )
            )
