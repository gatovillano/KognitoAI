"""Aumentar dimension de embedding en notas a 768

Revision ID: 3552a6d5af7d
Revises: 
Create Date: 2025-11-06 03:50:37.476575

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '3552a6d5af7d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE notas SET embedding = NULL")
    op.alter_column('notas', 'embedding',
               existing_type=Vector(384),
               type_=Vector(768),
               existing_nullable=True,
               postgresql_using='embedding::vector(768)')


def downgrade() -> None:
    op.execute("UPDATE notas SET embedding = NULL")
    op.alter_column('notas', 'embedding',
               existing_type=Vector(768),
               type_=Vector(384),
               existing_nullable=True,
               postgresql_using='embedding::vector(384)')
