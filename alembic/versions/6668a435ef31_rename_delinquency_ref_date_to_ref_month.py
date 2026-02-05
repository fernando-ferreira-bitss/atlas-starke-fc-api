"""rename_delinquency_ref_date_to_ref_month

Revision ID: 6668a435ef31
Revises: tyxqab2i1q6j
Create Date: 2025-10-30 15:47:53.466275

This migration renames the ref_date column to ref_month in the delinquency table
to maintain consistency with other models (CashIn, CashOut, PortfolioStats).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6668a435ef31'
down_revision: Union[str, None] = 'tyxqab2i1q6j'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename ref_date to ref_month in delinquency table."""

    print("\n" + "="*80)
    print("MIGRATION: Rename ref_date to ref_month in delinquency table")
    print("="*80)

    # Drop old constraints and indexes that reference ref_date
    print("\n📋 Step 1: Dropping old constraints and indexes...")
    op.drop_index('idx_delinquency_emp_ref_date', table_name='delinquency')
    op.drop_constraint('uq_delinquency_emp_date', 'delinquency', type_='unique')

    # Rename column
    print("\n✏️  Step 2: Renaming column ref_date to ref_month...")
    op.alter_column(
        'delinquency',
        'ref_date',
        new_column_name='ref_month',
        existing_type=sa.String(10),
        existing_nullable=False
    )

    # Recreate constraints and indexes with new column name
    print("\n🔗 Step 3: Recreating constraints and indexes...")
    op.create_unique_constraint('uq_delinquency_emp_date', 'delinquency', ['empreendimento_id', 'ref_month'])
    op.create_index('idx_delinquency_emp_ref_month', 'delinquency', ['empreendimento_id', 'ref_month'])

    print("\n" + "="*80)
    print("✅ Migration completed successfully!")
    print("   - Column renamed: ref_date → ref_month")
    print("   - Constraints updated")
    print("   - Indexes recreated")
    print("="*80 + "\n")


def downgrade() -> None:
    """Rollback: rename ref_month back to ref_date."""

    print("\n" + "="*80)
    print("MIGRATION ROLLBACK: Rename ref_month back to ref_date")
    print("="*80)

    # Drop new constraints and indexes
    op.drop_index('idx_delinquency_emp_ref_month', table_name='delinquency')
    op.drop_constraint('uq_delinquency_emp_date', 'delinquency', type_='unique')

    # Rename column back
    op.alter_column(
        'delinquency',
        'ref_month',
        new_column_name='ref_date',
        existing_type=sa.String(10),
        existing_nullable=False
    )

    # Recreate old constraints and indexes
    op.create_unique_constraint('uq_delinquency_emp_date', 'delinquency', ['empreendimento_id', 'ref_date'])
    op.create_index('idx_delinquency_emp_ref_date', 'delinquency', ['empreendimento_id', 'ref_date'])

    print("\n✅ Rollback completed!")
    print("="*80 + "\n")
