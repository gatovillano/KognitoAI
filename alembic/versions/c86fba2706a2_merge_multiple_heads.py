"""Merge multiple heads

Revision ID: c86fba2706a2
Revises: 20260606_create_custom_heartbeats_table, eceaa769ee58
Create Date: 2026-06-18 15:54:20.955350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c86fba2706a2'
down_revision: Union[str, Sequence[str], None] = ('20260606_create_custom_heartbeats_table', 'eceaa769ee58')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
