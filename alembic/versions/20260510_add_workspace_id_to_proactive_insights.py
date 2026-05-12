"""
Migration to add workspace_id to proactive_insights table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '20260510_add_workspace_id_to_proactive_insights'
down_revision = '20260509_001' # Based on previous check, this is the current head
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Agregar columna 'workspace_id' a proactive_insights
    op.add_column('proactive_insights', sa.Column('workspace_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_proactive_insights_workspace_id',
        'proactive_insights', 'workspaces',
        ['workspace_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index(op.f('ix_proactive_insights_workspace_id'), 'proactive_insights', ['workspace_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_proactive_insights_workspace_id'), table_name='proactive_insights')
    op.drop_constraint('fk_proactive_insights_workspace_id', 'proactive_insights', type_='foreignkey')
    op.drop_column('proactive_insights', 'workspace_id')
