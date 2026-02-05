"""rename_cod_empreendimento_to_empreendimento_id_in_contracts

Revision ID: khwjs8704vij
Revises: d43246ea9abe
Create Date: 2025-10-30 15:40:00.000000

This migration standardizes the column name in the contracts table
to match the naming convention used in all other tables:
- Before: cod_empreendimento
- After: empreendimento_id

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'khwjs8704vij'
down_revision: Union[str, None] = 'd43246ea9abe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Rename cod_empreendimento to empreendimento_id in contracts table.

    This standardizes the column naming across all financial tables:
    - cash_in: empreendimento_id
    - cash_out: empreendimento_id
    - balance: empreendimento_id
    - portfolio_stats: empreendimento_id
    - monthly_cash_flow: empreendimento_id
    - contracts: cod_empreendimento → empreendimento_id ✅
    """

    print("\n" + "="*80)
    print("MIGRATION: Rename cod_empreendimento to empreendimento_id")
    print("="*80)

    # Rename the column
    print("\n📝 Renaming column contracts.cod_empreendimento → empreendimento_id")
    op.alter_column(
        'contracts',
        'cod_empreendimento',
        new_column_name='empreendimento_id',
        existing_type=sa.Integer(),
        existing_nullable=False
    )

    print("✅ Column renamed successfully!")
    print("\n💡 Benefits:")
    print("  • Consistent naming across all tables")
    print("  • Easier to understand relationships")
    print("  • Simpler to write queries with JOINs")
    print("  • Ready for Foreign Key constraints")
    print()


def downgrade() -> None:
    """
    Revert empreendimento_id back to cod_empreendimento.
    """

    print("\n" + "="*80)
    print("MIGRATION ROLLBACK: Rename empreendimento_id to cod_empreendimento")
    print("="*80)

    # Rename back
    print("\n📝 Renaming column contracts.empreendimento_id → cod_empreendimento")
    op.alter_column(
        'contracts',
        'empreendimento_id',
        new_column_name='cod_empreendimento',
        existing_type=sa.Integer(),
        existing_nullable=False
    )

    print("✅ Rollback completed!")
    print()
