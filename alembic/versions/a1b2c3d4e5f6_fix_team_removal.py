"""Fix team removal issues from previous migration

Revision ID: a1b2c3d4e5f6
Revises: f98e11034e20
Create Date: 2025-11-29 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f98e11034e20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # Drop all related objects if they exist, using CASCADE
    conn.execute(text("DROP TABLE IF EXISTS langchain_chat_history CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS team_members CASCADE"))
    
    # Explicitly drop the foreign key from user_document_topics if it exists
    conn.execute(text("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'user_document_topics_team_id_fkey' AND table_name = 'user_document_topics'
            ) THEN
                ALTER TABLE user_document_topics DROP CONSTRAINT user_document_topics_team_id_fkey;
            END IF;
        END $$;
    """))

    # Now, drop the teams table
    conn.execute(text("DROP TABLE IF EXISTS teams CASCADE"))

    # Clean up columns from other tables
    tables_with_team_id = ['user_document_topics', 'langchain_pg_embedding']
    for table in tables_with_team_id:
        conn.execute(text(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = 'team_id'
                ) THEN
                    ALTER TABLE {table} DROP COLUMN team_id;
                END IF;
            END $$;
        """))

    if conn.dialect.name == 'postgresql':
        conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'langchain_pg_embedding' AND column_name = 'visibility_teams'
                ) THEN
                    ALTER TABLE langchain_pg_embedding DROP COLUMN visibility_teams;
                END IF;
            END $$;
        """))

    # Finally, add the 'is_private' column to 'agenda_events' if it doesn't exist
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'agenda_events' AND column_name = 'is_private'
            ) THEN
                ALTER TABLE agenda_events ADD COLUMN is_private BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;
        END $$;
    """))


def downgrade() -> None:
    """Downgrade schema."""
    # This downgrade is complex and might not be fully restorable
    # For now, we will just add back the 'is_private' column if it was removed
    op.drop_column('agenda_events', 'is_private')
