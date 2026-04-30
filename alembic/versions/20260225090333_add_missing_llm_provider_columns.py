"""Add missing LLM provider columns to Account model

Revision ID: 20250124_add_missing_llm_provider_columns
Revises: 4511159c8ca0
Create Date: 2025-01-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250124_add_missing_llm_provider_columns'
down_revision: Union[str, Sequence[str], None] = '4511159c8ca0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if columns exist before adding
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('accounts')]
    
    if 'fast_llm_provider' not in columns:
        op.add_column('accounts', sa.Column('fast_llm_provider', sa.String(50), nullable=True, comment='Proveedor de LLM para tareas rápidas.'))
    if 'vision_llm_provider' not in columns:
        op.add_column('accounts', sa.Column('vision_llm_provider', sa.String(50), nullable=True, comment='Proveedor de LLM para tareas de visión.'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('accounts', 'vision_llm_provider')
    op.drop_column('accounts', 'fast_llm_provider')
