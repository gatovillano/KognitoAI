"""Merge heads

Revision ID: c085b910f913
Revises: 40a71dbe5a5d, b64d41572ae8
Create Date: 2025-11-18 22:00:02.955793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c085b910f913'
down_revision: Union[str, Sequence[str], None] = ('40a71dbe5a5d', 'b64d41572ae8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
