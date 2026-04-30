"""merge shared_conversation_links and tts_api_base heads

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9, cb425bf3336f
Create Date: 2026-03-28

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = ('d4e5f6a7b8c9', 'cb425bf3336f')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
