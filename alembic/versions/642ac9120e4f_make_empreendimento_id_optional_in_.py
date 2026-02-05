"""make_empreendimento_id_optional_in_tokens

Revision ID: 642ac9120e4f
Revises: c95c4bb14c77
Create Date: 2025-10-22 18:46:47.422171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '642ac9120e4f'
down_revision: Union[str, None] = 'c95c4bb14c77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make empreendimento_id nullable to allow tokens for all empreendimentos
    op.alter_column('report_access_tokens', 'empreendimento_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)


def downgrade() -> None:
    # Make empreendimento_id required again
    op.alter_column('report_access_tokens', 'empreendimento_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
