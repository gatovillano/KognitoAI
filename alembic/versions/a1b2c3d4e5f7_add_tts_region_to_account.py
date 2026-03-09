"""Add tts_region column to Account model

Revision ID: a1b2c3d4e5f7
Revises: eeedefc8932c
Create Date: 2026-02-16 03:17:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'eeedefc8932c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('accounts', sa.Column('tts_region', sa.String(length=50), nullable=True, comment="Región del servicio de TTS (e.g., 'eastus' para Azure)."))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('accounts', 'tts_region')
