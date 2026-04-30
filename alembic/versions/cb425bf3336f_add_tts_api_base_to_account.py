"""Add tts_api_base to Account

Revision ID: cb425bf3336f
Revises: fc0c81ed56cb
Create Date: 2026-03-27 02:06:37.175231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb425bf3336f'
down_revision: Union[str, Sequence[str], None] = 'fc0c81ed56cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('accounts', sa.Column('tts_api_base', sa.String(length=255), nullable=True, comment='URL base opcional para un servicio de TTS local o custom.'))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('accounts', 'tts_api_base')
