"""add is_agent_message to notas

Revision ID: 20260605_add_is_agent_message_to_notas
Revises: 464a9aac6c0a
Create Date: 2026-06-05 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260605_add_is_agent_message_to_notas"
down_revision: Union[str, Sequence[str], None] = "464a9aac6c0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notas",
        sa.Column(
            "is_agent_message",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_notas_is_agent_message"),
        "notas",
        ["is_agent_message"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notas_is_agent_message"), table_name="notas")
    op.drop_column("notas", "is_agent_message")
