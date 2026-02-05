"""update_contracts_add_valor_fields_remove_nome_empreendimento

Revision ID: 041b7bd54fb9
Revises: 6668a435ef31
Create Date: 2025-10-31 11:08:15.121939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '041b7bd54fb9'
down_revision: Union[str, None] = '6668a435ef31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add contract value fields and remove nome_empreendimento column."""

    print("\n" + "="*80)
    print("MIGRATION: Update contracts table - add valor fields, remove nome_empreendimento")
    print("="*80)

    # Step 1: Add new columns
    print("\n📋 Step 1: Adding new columns...")
    op.add_column('contracts', sa.Column('valor_contrato', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('contracts', sa.Column('valor_atualizado_ipca', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('contracts', sa.Column('data_assinatura', sa.Date(), nullable=True))
    print("   ✅ Added: valor_contrato, valor_atualizado_ipca, data_assinatura")

    # Step 2: Remove nome_empreendimento column
    print("\n📋 Step 2: Removing nome_empreendimento column...")
    op.drop_column('contracts', 'nome_empreendimento')
    print("   ✅ Removed: nome_empreendimento")

    print("\n" + "="*80)
    print("✅ Migration completed successfully!")
    print("   - Added: valor_contrato (Numeric)")
    print("   - Added: valor_atualizado_ipca (Numeric)")
    print("   - Added: data_assinatura (Date)")
    print("   - Removed: nome_empreendimento (String)")
    print("="*80 + "\n")


def downgrade() -> None:
    """Rollback: remove valor fields and restore nome_empreendimento column."""

    print("\n" + "="*80)
    print("MIGRATION ROLLBACK: Restore contracts table structure")
    print("="*80)

    # Step 1: Restore nome_empreendimento column
    print("\n📋 Step 1: Restoring nome_empreendimento column...")
    op.add_column('contracts', sa.Column('nome_empreendimento', sa.String(255), nullable=True))
    print("   ✅ Restored: nome_empreendimento")

    # Step 2: Remove new columns
    print("\n📋 Step 2: Removing valor columns...")
    op.drop_column('contracts', 'data_assinatura')
    op.drop_column('contracts', 'valor_atualizado_ipca')
    op.drop_column('contracts', 'valor_contrato')
    print("   ✅ Removed: valor_contrato, valor_atualizado_ipca, data_assinatura")

    print("\n✅ Rollback completed!")
    print("="*80 + "\n")
