"""Add is_graph_processed to langchain_pg_embedding

Revision ID: 0861f9344778
Revises: a1b2c3d4e5f6
Create Date: 2025-12-06 21:12:02.714770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0861f9344778'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('langchain_pg_embedding', sa.Column('is_graph_processed', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('langchain_pg_embedding', 'is_graph_processed')
