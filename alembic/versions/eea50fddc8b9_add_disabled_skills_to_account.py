"""add_disabled_skills_to_account

Revision ID: eea50fddc8b9
Revises: 58c0aabd5348
Create Date: 2026-03-11 19:53:09.194225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'eea50fddc8b9'
down_revision: Union[str, Sequence[str], None] = '58c0aabd5348'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('accounts', sa.Column('disabled_skills', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb"), comment="Lista de IDs de skills desactivadas por el usuario."))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('accounts', 'disabled_skills')
