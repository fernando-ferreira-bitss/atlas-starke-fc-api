"""add_foreign_keys_to_financial_tables

Revision ID: tyxqab2i1q6j
Revises: d43246ea9abe
Create Date: 2025-10-30 15:32:54.000000

This migration adds Foreign Key constraints to improve:
- Database integrity (prevent orphaned records)
- JOIN performance (especially with large datasets)
- Query optimizer statistics

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'tyxqab2i1q6j'
down_revision: Union[str, None] = 'khwjs8704vij'  # After renaming cod_empreendimento
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add Foreign Key constraints to financial tables.

    Before creating FKs, this migration:
    1. Checks for orphaned records (records with invalid empreendimento_id)
    2. Removes orphaned records if found
    3. Creates FK constraints with CASCADE delete

    This ensures data integrity and improves JOIN performance.
    """

    # Get connection for data cleanup
    connection = op.get_bind()

    # List of tables that need FK constraints
    tables_to_migrate = [
        'cash_in',
        'cash_out',
        'balance',
        'portfolio_stats',
        'monthly_cash_flow',
        'contracts'  # Added contracts table
    ]

    print("\n" + "="*80)
    print("MIGRATION: Adding Foreign Keys to Financial Tables")
    print("="*80)

    # Step 1: Check and clean orphaned records
    print("\n📊 Step 1: Checking for orphaned records...")

    for table_name in tables_to_migrate:
        # Check if table exists
        inspector = sa.inspect(connection)
        if table_name not in inspector.get_table_names():
            print(f"  ⏭️  Skipping {table_name} (table does not exist)")
            continue

        # Count orphaned records
        orphaned_query = sa.text(f"""
            SELECT COUNT(*)
            FROM {table_name} t
            WHERE t.empreendimento_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM developments d
                  WHERE d.id = t.empreendimento_id
              )
        """)

        orphaned_count = connection.execute(orphaned_query).scalar()

        if orphaned_count > 0:
            print(f"  ⚠️  Found {orphaned_count} orphaned records in {table_name}")

            # Delete orphaned records
            delete_query = sa.text(f"""
                DELETE FROM {table_name}
                WHERE empreendimento_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM developments d
                      WHERE d.id = empreendimento_id
                  )
            """)

            connection.execute(delete_query)
            print(f"  ✅ Cleaned {orphaned_count} orphaned records from {table_name}")
        else:
            print(f"  ✅ No orphaned records in {table_name}")

    # Step 2: Add Foreign Key constraints
    print("\n🔗 Step 2: Adding Foreign Key constraints...")

    # FK for cash_in table
    if 'cash_in' in inspector.get_table_names():
        print("  • Creating FK: cash_in.empreendimento_id -> developments.id")
        op.create_foreign_key(
            'fk_cash_in_development',
            'cash_in',
            'developments',
            ['empreendimento_id'],
            ['id'],
            ondelete='CASCADE'
        )

    # FK for cash_out table
    if 'cash_out' in inspector.get_table_names():
        print("  • Creating FK: cash_out.empreendimento_id -> developments.id")
        op.create_foreign_key(
            'fk_cash_out_development',
            'cash_out',
            'developments',
            ['empreendimento_id'],
            ['id'],
            ondelete='CASCADE'
        )

    # FK for balance table
    if 'balance' in inspector.get_table_names():
        print("  • Creating FK: balance.empreendimento_id -> developments.id")
        op.create_foreign_key(
            'fk_balance_development',
            'balance',
            'developments',
            ['empreendimento_id'],
            ['id'],
            ondelete='CASCADE'
        )

    # FK for portfolio_stats table
    if 'portfolio_stats' in inspector.get_table_names():
        print("  • Creating FK: portfolio_stats.empreendimento_id -> developments.id")
        op.create_foreign_key(
            'fk_portfolio_stats_development',
            'portfolio_stats',
            'developments',
            ['empreendimento_id'],
            ['id'],
            ondelete='CASCADE'
        )

    # FK for monthly_cash_flow table
    if 'monthly_cash_flow' in inspector.get_table_names():
        print("  • Creating FK: monthly_cash_flow.empreendimento_id -> developments.id")
        op.create_foreign_key(
            'fk_monthly_cash_flow_development',
            'monthly_cash_flow',
            'developments',
            ['empreendimento_id'],
            ['id'],
            ondelete='CASCADE'
        )

    # FK for contracts table
    if 'contracts' in inspector.get_table_names():
        print("  • Creating FK: contracts.empreendimento_id -> developments.id")
        op.create_foreign_key(
            'fk_contracts_development',
            'contracts',
            'developments',
            ['empreendimento_id'],
            ['id'],
            ondelete='CASCADE'
        )

    print("\n" + "="*80)
    print("✅ Migration completed successfully!")
    print("="*80)
    print("\n📈 Benefits:")
    print("  • Data integrity: Prevents orphaned records")
    print("  • Performance: Better JOIN optimization by PostgreSQL")
    print("  • Statistics: Query planner can use FK statistics")
    print("  • Cascade delete: Automatically clean related records")
    print()


def downgrade() -> None:
    """
    Remove Foreign Key constraints.

    This allows reverting the migration if needed.
    """

    print("\n" + "="*80)
    print("MIGRATION ROLLBACK: Removing Foreign Keys")
    print("="*80)

    connection = op.get_bind()
    inspector = sa.inspect(connection)

    # Remove FK constraints in reverse order
    fk_constraints = [
        ('contracts', 'fk_contracts_development'),
        ('monthly_cash_flow', 'fk_monthly_cash_flow_development'),
        ('portfolio_stats', 'fk_portfolio_stats_development'),
        ('balance', 'fk_balance_development'),
        ('cash_out', 'fk_cash_out_development'),
        ('cash_in', 'fk_cash_in_development'),
    ]

    for table_name, constraint_name in fk_constraints:
        if table_name in inspector.get_table_names():
            print(f"  • Dropping FK: {constraint_name}")
            try:
                op.drop_constraint(constraint_name, table_name, type_='foreignkey')
            except Exception as e:
                print(f"    ⚠️  Warning: Could not drop {constraint_name}: {e}")

    print("\n✅ Rollback completed!")
    print()
