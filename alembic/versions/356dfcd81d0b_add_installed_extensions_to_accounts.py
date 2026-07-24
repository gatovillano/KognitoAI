"""add_installed_extensions_to_accounts

Revision ID: 356dfcd81d0b
Revises: 724112708aa1
Create Date: 2026-07-24 05:22:33.228678

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '356dfcd81d0b'
down_revision: Union[str, Sequence[str], None] = '724112708aa1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'accounts',
        sa.Column(
            'installed_extensions',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment="Lista de IDs de extensiones instaladas y activas."
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('accounts', 'installed_extensions')

