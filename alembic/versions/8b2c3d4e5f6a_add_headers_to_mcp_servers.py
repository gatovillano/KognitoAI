"""add headers column to mcp_servers

Revision ID: 8b2c3d4e5f6a
Revises: None
Create Date: 2026-10-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '8b2c3d4e5f6a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    res = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='mcp_servers' AND column_name='headers'"
    )).fetchall()
    if not res:
        op.add_column('mcp_servers', sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    res = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='mcp_servers' AND column_name='headers'"
    )).fetchall()
    if res:
        op.drop_column('mcp_servers', 'headers')
