"""add_is_graph_processed_to_langchain_pg_embedding

Revision ID: 919e3d484188
Revises: 356dfcd81d0b
Create Date: 2026-09-12 19:43:44.531940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '919e3d484188'
down_revision: Union[str, Sequence[str], None] = '356dfcd81d0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE langchain_pg_embedding ADD COLUMN IF NOT EXISTS is_graph_processed BOOLEAN NOT NULL DEFAULT false"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_langchain_pg_embedding_is_graph_proc ON langchain_pg_embedding (account_id, is_graph_processed)"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_langchain_pg_embedding_is_graph_proc', table_name='langchain_pg_embedding')
    op.drop_column('langchain_pg_embedding', 'is_graph_processed')
