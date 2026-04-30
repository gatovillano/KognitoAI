"""merge heads

Revision ID: 58c0aabd5348
Revises: 20250124_missing_providers, 20250124_add_missing_llm_provider_columns, a1b2c3d4e5f7
Create Date: 2026-03-11 19:49:36.041451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58c0aabd5348'
down_revision: Union[str, Sequence[str], None] = ('20250124_missing_providers', '20250124_add_missing_llm_provider_columns', 'a1b2c3d4e5f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
