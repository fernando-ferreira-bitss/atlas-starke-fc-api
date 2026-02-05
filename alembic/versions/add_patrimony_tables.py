"""add_patrimony_tables

Add all patrimony management tables:
- pat_institutions
- pat_clients
- pat_accounts
- pat_assets
- pat_liabilities
- pat_monthly_positions
- pat_documents
- pat_audit_logs

Revision ID: add_patrimony_tables
Revises: add_role_permission_system
Create Date: 2025-12-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = "add_patrimony_tables"
down_revision: Union[str, None] = "add_role_permission_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all patrimony tables."""

    # 1. pat_institutions
    op.create_table(
        "pat_institutions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("institution_type", sa.String(50), nullable=False, server_default="bank"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_pat_institutions_name", "pat_institutions", ["name"])
    op.create_index("idx_pat_institutions_type", "pat_institutions", ["institution_type"])
    op.create_index("idx_pat_institutions_active", "pat_institutions", ["is_active"])

    # 2. pat_clients
    op.create_table(
        "pat_clients",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("rm_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("client_type", sa.String(50), nullable=False),
        sa.Column("cpf_cnpj_encrypted", sa.String(500), nullable=False),
        sa.Column("cpf_cnpj_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_pat_clients_type", "pat_clients", ["client_type"])
    op.create_index("idx_pat_clients_status", "pat_clients", ["status"])
    op.create_index("idx_pat_clients_rm", "pat_clients", ["rm_user_id"])
    op.create_index("idx_pat_clients_user", "pat_clients", ["user_id"])
    op.create_index("idx_pat_clients_name", "pat_clients", ["name"])

    # 3. pat_accounts
    op.create_table(
        "pat_accounts",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=False), sa.ForeignKey("pat_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=False), sa.ForeignKey("pat_institutions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("account_number", sa.String(50), nullable=True),
        sa.Column("agency", sa.String(20), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("base_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_pat_accounts_client", "pat_accounts", ["client_id"])
    op.create_index("idx_pat_accounts_institution", "pat_accounts", ["institution_id"])
    op.create_index("idx_pat_accounts_type", "pat_accounts", ["account_type"])
    op.create_index("idx_pat_accounts_active", "pat_accounts", ["is_active"])

    # 4. pat_assets
    op.create_table(
        "pat_assets",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=False), sa.ForeignKey("pat_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", UUID(as_uuid=False), sa.ForeignKey("pat_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("subcategory", sa.String(50), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column("base_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("current_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("base_date", sa.Date(), nullable=True),
        sa.Column("base_year", sa.Integer(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_pat_assets_client", "pat_assets", ["client_id"])
    op.create_index("idx_pat_assets_account", "pat_assets", ["account_id"])
    op.create_index("idx_pat_assets_category", "pat_assets", ["category"])
    op.create_index("idx_pat_assets_active", "pat_assets", ["is_active"])
    op.create_index("idx_pat_assets_ticker", "pat_assets", ["ticker"])

    # 5. pat_liabilities
    op.create_table(
        "pat_liabilities",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=False), sa.ForeignKey("pat_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=False), sa.ForeignKey("pat_institutions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("liability_type", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("original_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("monthly_payment", sa.Numeric(18, 2), nullable=True),
        sa.Column("interest_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("last_payment_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_pat_liabilities_client", "pat_liabilities", ["client_id"])
    op.create_index("idx_pat_liabilities_institution", "pat_liabilities", ["institution_id"])
    op.create_index("idx_pat_liabilities_type", "pat_liabilities", ["liability_type"])
    op.create_index("idx_pat_liabilities_active", "pat_liabilities", ["is_active"])

    # 6. pat_monthly_positions
    op.create_table(
        "pat_monthly_positions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=False), sa.ForeignKey("pat_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=False), sa.ForeignKey("pat_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(18, 2), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("import_batch_id", UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("asset_id", "reference_date", name="uq_pat_position_asset_date"),
    )
    op.create_index("idx_pat_positions_client", "pat_monthly_positions", ["client_id"])
    op.create_index("idx_pat_positions_asset", "pat_monthly_positions", ["asset_id"])
    op.create_index("idx_pat_positions_date", "pat_monthly_positions", ["reference_date"])
    op.create_index("idx_pat_positions_source", "pat_monthly_positions", ["source"])

    # 7. pat_documents
    op.create_table(
        "pat_documents",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=False), sa.ForeignKey("pat_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", UUID(as_uuid=False), sa.ForeignKey("pat_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_id", UUID(as_uuid=False), sa.ForeignKey("pat_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("reference_date", sa.DateTime(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_pat_documents_client", "pat_documents", ["client_id"])
    op.create_index("idx_pat_documents_account", "pat_documents", ["account_id"])
    op.create_index("idx_pat_documents_asset", "pat_documents", ["asset_id"])
    op.create_index("idx_pat_documents_type", "pat_documents", ["document_type"])
    op.create_index("idx_pat_documents_uploaded_by", "pat_documents", ["uploaded_by"])

    # 8. pat_audit_logs
    op.create_table(
        "pat_audit_logs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=False), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_pat_audit_user", "pat_audit_logs", ["user_id"])
    op.create_index("idx_pat_audit_action", "pat_audit_logs", ["action"])
    op.create_index("idx_pat_audit_entity_type", "pat_audit_logs", ["entity_type"])
    op.create_index("idx_pat_audit_entity_id", "pat_audit_logs", ["entity_id"])
    op.create_index("idx_pat_audit_created_at", "pat_audit_logs", ["created_at"])
    op.create_index("idx_pat_audit_ip", "pat_audit_logs", ["ip_address"])


def downgrade() -> None:
    """Drop all patrimony tables in reverse order."""

    op.drop_table("pat_audit_logs")
    op.drop_table("pat_documents")
    op.drop_table("pat_monthly_positions")
    op.drop_table("pat_liabilities")
    op.drop_table("pat_assets")
    op.drop_table("pat_accounts")
    op.drop_table("pat_clients")
    op.drop_table("pat_institutions")
