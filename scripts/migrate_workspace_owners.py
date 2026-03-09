import asyncio
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import Workspace, WorkspacePermission, database_url as DATABASE_URL

def migrate_workspace_owners():
    """
    Migrates existing workspaces to have an owner in the WorkspacePermission table.
    """
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        workspaces = session.query(Workspace).all()
        for workspace in workspaces:
            # Check if a permission entry already exists for this owner
            existing_permission = session.query(WorkspacePermission).filter_by(
                workspace_id=workspace.id,
                account_id=workspace.account_id,
                role='owner'
            ).first()

            if not existing_permission:
                new_permission = WorkspacePermission(
                    workspace_id=workspace.id,
                    account_id=workspace.account_id,
                    role='owner'
                )
                session.add(new_permission)
                print(f"Creating owner permission for workspace '{workspace.name}' (ID: {workspace.id}) for account ID {workspace.account_id}")

        session.commit()
        print("Migration completed successfully.")

    except Exception as e:
        session.rollback()
        print(f"An error occurred: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    migrate_workspace_owners()