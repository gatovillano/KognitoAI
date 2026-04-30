"""Merge heads

Revision ID: c3708875e512
Revises: 20260323_add_account_id_to_profiles, eea50fddc8b9
Create Date: 2026-03-27 02:06:02.397037

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3708875e512'
down_revision: Union[str, Sequence[str], None] = ('20260323_add_account_id_to_profiles', 'eea50fddc8b9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
