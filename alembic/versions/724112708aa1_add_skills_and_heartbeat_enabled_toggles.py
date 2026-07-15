"""add skills and heartbeat enabled toggles

Revision ID: 724112708aa1
Revises: c728b4679576
Create Date: 2026-07-15 09:05:31.145984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '724112708aa1'
down_revision: Union[str, Sequence[str], None] = 'c728b4679576'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('accounts', sa.Column('skills_enabled', sa.Boolean(), nullable=False, server_default=sa.text('TRUE'), comment='Indica si el módulo de skills está habilitado para la cuenta.'))
    op.add_column('accounts', sa.Column('heartbeat_enabled', sa.Boolean(), nullable=False, server_default=sa.text('TRUE'), comment='Indica si el módulo de heartbeat está habilitado para la cuenta.'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('accounts', 'heartbeat_enabled')
    op.drop_column('accounts', 'skills_enabled')
