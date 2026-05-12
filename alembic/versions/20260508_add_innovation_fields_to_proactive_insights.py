"""add innovation fields to proactive_insights

Revision ID: 20260508_001
Revises: 145a54ee1fdd
Create Date: 2026-05-08 21:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260508_001'
down_revision = 'fdc15411c20d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar columna 'title' a proactive_insights
    op.add_column('proactive_insights', sa.Column('title', sa.String(255), nullable=True))
    
    # Agregar columna 'innovation_potential' a proactive_insights
    op.add_column('proactive_insights', sa.Column('innovation_potential', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remover columnas en caso de rollback
    op.drop_column('proactive_insights', 'innovation_potential')
    op.drop_column('proactive_insights', 'title')
