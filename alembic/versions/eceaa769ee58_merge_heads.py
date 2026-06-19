"""merge heads

Revision ID: eceaa769ee58
Revises: 0fd9fd0e16e2, 20260605_add_is_agent_message_to_notas
Create Date: 2026-06-05 23:49:40.296325

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eceaa769ee58'
down_revision: Union[str, Sequence[str], None] = ('0fd9fd0e16e2', '20260605_add_is_agent_message_to_notas')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
