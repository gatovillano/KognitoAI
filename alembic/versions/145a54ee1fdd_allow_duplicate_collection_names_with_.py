"""allow_duplicate_collection_names_with_parents

Revision ID: 145a54ee1fdd
Revises: b93ca375f016
Create Date: 2026-04-22 22:41:02.778171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '145a54ee1fdd'
down_revision: Union[str, Sequence[str], None] = 'b93ca375f016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = 'b93ca375f016'


def upgrade() -> None:
    # Eliminar restricciones existentes
    op.execute('DROP INDEX IF EXISTS "ix_account_personal_topic"')
    op.execute('DROP INDEX IF EXISTS "ix_account_workspace_topic"')
    
    # Crear nuevas restricciones incluyendo parent_id
    # Nota: Usamos ejecución directa de SQL para manejar el WHERE clause específico de Postgres
    op.execute('''
        CREATE UNIQUE INDEX "uq_account_parent_name_personal" 
        ON user_document_topics (account_id, name) 
        WHERE workspace_id IS NULL AND parent_id IS NULL
    ''')
    op.execute('''
        CREATE UNIQUE INDEX "uq_account_workspace_parent_name" 
        ON user_document_topics (account_id, workspace_id, parent_id, name) 
        WHERE workspace_id IS NOT NULL
    ''')

def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS "uq_account_parent_name_personal"')
    op.execute('DROP INDEX IF EXISTS "uq_account_workspace_parent_name"')
    
    op.execute('''
        CREATE UNIQUE INDEX "ix_account_personal_topic" 
        ON user_document_topics (account_id, name) 
        WHERE workspace_id IS NULL
    ''')
    op.execute('''
        CREATE UNIQUE INDEX "ix_account_workspace_topic" 
        ON user_document_topics (account_id, workspace_id, name) 
        WHERE workspace_id IS NOT NULL
    ''')
