"""add status to agenda_events

Revision ID: e927a11231a9
Revises: c085b910f913
Create Date: 2025-11-20 13:07:35.910397

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e927a11231a9'
down_revision: Union[str, Sequence[str], None] = 'c085b910f913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('langchain_chat_history')
    
    # Step 1: Add column to agenda_events as nullable first
    op.add_column('agenda_events', sa.Column('status', sa.String(length=50), nullable=True, comment='Estado del evento para tableros Kanban (ej. Pendiente, En Progreso, Completado).'))
    
    # Step 2: Update existing rows to have default value
    op.execute("UPDATE agenda_events SET status = 'Pendiente' WHERE status IS NULL")
    
    # Step 3: Make column NOT NULL
    op.alter_column('agenda_events', 'status', nullable=False, server_default='Pendiente')
    
    op.drop_index(op.f('ix_analyzed_pairs_document_ids'), table_name='analyzed_pairs')
    
    # Fix tasks table status column
    op.execute("UPDATE tasks SET status = 'Pendiente' WHERE status IS NULL")
    op.alter_column('tasks', 'status',
               existing_type=sa.VARCHAR(length=50),
               nullable=False,
               comment='Estado de la tarea para tableros Kanban (ej. Pendiente, En Progreso, Completado).')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('tasks', 'status',
               existing_type=sa.VARCHAR(length=50),
               nullable=True,
               comment=None,
               existing_comment='Estado de la tarea para tableros Kanban (ej. Pendiente, En Progreso, Completado).')
    op.create_index(op.f('ix_analyzed_pairs_document_ids'), 'analyzed_pairs', ['document_id_a', 'document_id_b'], unique=False)
    op.drop_column('agenda_events', 'status')
    op.create_table('langchain_chat_history',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('session_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('message', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('langchain_chat_history_pkey'))
    )
