"""Add origem field to contratos table.

Revision ID: add_origem_to_contratos
Revises: drop_rm_client_assignments
Create Date: 2026-01-09

This migration:
1. Adds 'origem' column to contratos table (mega, uau)
2. Updates unique constraint to include origem
3. Adds new fields for UAU data (obra, cliente_cpf, cliente_codigo)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_origem_to_contratos'
down_revision = 'drop_rm_client_assignments'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add origem column with default 'mega' for existing records
    op.add_column('contratos', sa.Column('origem', sa.String(20), nullable=False, server_default='mega'))

    # 2. Add obra column (for UAU: empresa + obra + venda is the unique key)
    op.add_column('contratos', sa.Column('obra', sa.String(50), nullable=True))

    # 3. Add cliente_cpf column
    op.add_column('contratos', sa.Column('cliente_cpf', sa.String(20), nullable=True))

    # 4. Add cliente_codigo column
    op.add_column('contratos', sa.Column('cliente_codigo', sa.Integer(), nullable=True))

    # 5. Drop old unique constraint
    op.drop_constraint('uq_contract_cod_emp', 'contratos', type_='unique')

    # 6. Create new unique constraint with origem
    # For Mega: cod_contrato + empreendimento_id + origem
    # For UAU: cod_contrato (=Venda) + obra + empreendimento_id (=Empresa) + origem
    op.create_unique_constraint(
        'uq_contract_cod_emp_origem',
        'contratos',
        ['cod_contrato', 'empreendimento_id', 'obra', 'origem']
    )

    # 7. Add index on origem
    op.create_index('idx_contract_origem', 'contratos', ['origem'])


def downgrade():
    # Remove index
    op.drop_index('idx_contract_origem', 'contratos')

    # Restore old unique constraint
    op.drop_constraint('uq_contract_cod_emp_origem', 'contratos', type_='unique')
    op.create_unique_constraint(
        'uq_contract_cod_emp',
        'contratos',
        ['cod_contrato', 'empreendimento_id']
    )

    # Remove new columns
    op.drop_column('contratos', 'cliente_codigo')
    op.drop_column('contratos', 'cliente_cpf')
    op.drop_column('contratos', 'obra')
    op.drop_column('contratos', 'origem')
