"""add_shared_conversation_links

Revision ID: d4e5f6a7b8c9
Revises: c3708875e512
Create Date: 2026-03-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3708875e512'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'shared_conversation_links' not in inspector.get_table_names():
        op.create_table(
            'shared_conversation_links',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('thread_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_threads.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('token', sa.String(64), nullable=False, unique=True, index=True),
            sa.Column('password_hash', sa.String(255), nullable=True),
            sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('allow_reply', sa.Boolean(), default=False, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        )


def downgrade() -> None:
    op.drop_table('shared_conversation_links')
