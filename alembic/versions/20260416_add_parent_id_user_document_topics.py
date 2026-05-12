"""add parent_id to user_document_topics

Revision ID: 20260416_add_parent_id_user_document_topics
Revises: 22fe389484a9
Create Date: 2026-04-16 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260416_add_parent_id_user_document_topics'
down_revision = '22fe389484a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add parent_id, position and item_type to support hierarchical collections
    op.add_column('user_document_topics', sa.Column('parent_id', sa.UUID(), nullable=True))
    op.add_column('user_document_topics', sa.Column('position', sa.Integer(), nullable=True))
    op.add_column('user_document_topics', sa.Column('item_type', sa.String(length=50), nullable=True, server_default=sa.text("'collection'")))
    # Optional index to speed up parent lookups
    op.create_index('ix_user_document_topics_parent_id', 'user_document_topics', ['parent_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_document_topics_parent_id', table_name='user_document_topics')
    op.drop_column('user_document_topics', 'item_type')
    op.drop_column('user_document_topics', 'position')
    op.drop_column('user_document_topics', 'parent_id')
