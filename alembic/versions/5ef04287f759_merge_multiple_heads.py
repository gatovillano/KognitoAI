"""Merge multiple heads

Revision ID: 5ef04287f759
Revises: 145a54ee1fdd, 20260508_001
Create Date: 2026-05-08 23:51:47.892950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ef04287f759'
down_revision: Union[str, Sequence[str], None] = ('145a54ee1fdd', '20260508_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
