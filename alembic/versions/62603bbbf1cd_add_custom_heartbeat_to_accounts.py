"""Add custom heartbeat to accounts

Revision ID: 62603bbbf1cd
Revises: 5ef04287f759
Create Date: 2026-05-08 23:52:05.628969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '62603bbbf1cd'
down_revision: Union[str, Sequence[str], None] = '5ef04287f759'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('accounts', sa.Column('custom_heartbeat_instructions', sa.Text(), nullable=True, comment='Instrucciones personalizadas para el heartbeat autónomo de este usuario.'))
    op.add_column('accounts', sa.Column('custom_heartbeat_interval_minutes', sa.Integer(), nullable=True, comment='Frecuencia en minutos para el heartbeat personalizado.'))
    op.add_column('accounts', sa.Column('custom_heartbeat_allowed_tools', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=True, comment='Lista de IDs/nombres de herramientas permitidas para el heartbeat personalizado.'))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('accounts', 'custom_heartbeat_allowed_tools')
    op.drop_column('accounts', 'custom_heartbeat_interval_minutes')
    op.drop_column('accounts', 'custom_heartbeat_instructions')
