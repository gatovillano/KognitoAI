"""Add system_settings table for persistent admin config

Revision ID: 20260509_001
Revises: 62603bbbf1cd
Create Date: 2026-05-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260509_001'
down_revision: Union[str, Sequence[str], None] = '62603bbbf1cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create system_settings table (if not exists)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'system_settings' not in inspector.get_table_names():
        op.create_table(
            'system_settings',
            sa.Column('key', sa.String(255), primary_key=True, comment='Clave de la configuración'),
            sa.Column('value', sa.Text(), nullable=True, comment='Valor de la configuración (serializado como texto/JSON)'),
            sa.Column(
                'updated_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('CURRENT_TIMESTAMP'),
                nullable=True,
                comment='Última actualización'
            ),
        )


def downgrade() -> None:
    """Drop system_settings table."""
    op.drop_table('system_settings')
