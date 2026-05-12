"""merge_migration_heads

Revision ID: b93ca375f016
Revises: 20260416_add_parent_id_user_document_topics, dc19a5a11cf4
Create Date: 2026-04-22 22:38:51.421404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b93ca375f016'
down_revision: Union[str, Sequence[str], None] = ('20260416_add_parent_id_user_document_topics', 'dc19a5a11cf4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
