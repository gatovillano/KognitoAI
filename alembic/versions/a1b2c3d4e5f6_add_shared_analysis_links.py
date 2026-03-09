"""add_shared_analysis_links

Revision ID: a1b2c3d4e5f6
Revises: f98e11034e20
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f98e11034e20'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create shared_analysis_links table
    op.create_table(
        'shared_analysis_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('token', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('allow_download', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    
    # Create index on analysis_id for faster lookups
    op.create_index('ix_shared_analysis_links_analysis_id', 'shared_analysis_links', ['analysis_id'])
    
    # Create index on token for faster lookups
    op.create_index('ix_shared_analysis_links_token', 'shared_analysis_links', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_shared_analysis_links_token', table_name='shared_analysis_links')
    op.drop_index('ix_shared_analysis_links_analysis_id', table_name='shared_analysis_links')
    op.drop_table('shared_analysis_links')
