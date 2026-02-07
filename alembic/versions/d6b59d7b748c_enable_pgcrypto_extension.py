"""enable pgcrypto extension

Revision ID: d6b59d7b748c
Revises: 0861f9344778
Create Date: 2026-01-07 22:48:13.194577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6b59d7b748c'
down_revision: Union[str, Sequence[str], None] = '0861f9344778'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP EXTENSION IF EXISTS pgcrypto')