#!/usr/bin/env python3
"""
Script to check and fix team sharing issues in the KognitoAI database.
This script verifies if documents are correctly associated with a team and can update the team_id if necessary.
"""

import argparse
import logging
import sys
import uuid
from sqlalchemy import create_engine, update, select
from sqlalchemy.orm import sessionmaker
from core.config import settings
from core.database import Memory, Team

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_and_fix_team_sharing(team_id, file_name=None, account_id=None, fix=False):
    """
    Check if documents are correctly shared with a team and optionally fix the association.
    
    Args:
        team_id (str): The UUID of the team to check.
        file_name (str, optional): Specific file name to check. If None, checks all documents for the team.
        account_id (str, optional): UUID of the account to filter documents. Required if fix=True.
        fix (bool): If True, update the team_id for matching documents.
    """
    try:
        # Check if database URL is set
        if not settings.database_url:
            logger.error("Database URL is not set in the configuration.")
            return
        
        # Create database connection
        engine = create_engine(settings.database_url.replace('+psycopg', ''))
        Session = sessionmaker(bind=engine)
        session = Session()
        
        team_uuid = uuid.UUID(team_id)
        team = session.get(Team, team_uuid)
        if not team:
            logger.error(f"Team with ID {team_id} not found.")
            return
        
        logger.info(f"Checking sharing for team: {team.name} (ID: {team_id})")
        
        # Query for documents associated with the team
        query = select(Memory).where(
            Memory.team_id == team_uuid,
            Memory.type == "document_chunk"
        )
        if file_name:
            query = query.where(Memory.content.like(f"%{file_name}%"))
        
        shared_documents = session.execute(query).scalars().all()
        logger.info(f"Found {len(shared_documents)} documents shared with this team matching the criteria.")
        
        for doc in shared_documents:
            logger.info(f"Document: {doc.content} (Account ID: {doc.account_id})")
        
        if fix:
            if not account_id:
                logger.error("Account ID is required to fix sharing issues.")
                return
            
            account_uuid = uuid.UUID(account_id)
            # Query for documents that match the file_name but are not associated with the team
            fix_query = select(Memory).where(
                Memory.account_id == account_uuid,
                Memory.type == "document_chunk",
                Memory.team_id.is_(None)
            )
            if file_name:
                fix_query = fix_query.where(Memory.content.like(f"%{file_name}%"))
            
            unshared_documents = session.execute(fix_query).scalars().all()
            logger.info(f"Found {len(unshared_documents)} unshared documents for account {account_id} matching the criteria.")
            
            if unshared_documents and fix:
                for doc in unshared_documents:
                    logger.info(f"Fixing sharing for document: {doc.content}")
                    session.execute(
                        update(Memory)
                        .where(Memory.id == doc.id)
                        .values(team_id=team_uuid)
                    )
                session.commit()
                logger.info(f"Updated team_id for {len(unshared_documents)} documents to associate with team {team_id}.")
            elif not unshared_documents:
                logger.warning("No unshared documents found to fix.")
        else:
            logger.info("Run with --fix to update team sharing for unshared documents.")
            
    except Exception as e:
        logger.error(f"Error checking team sharing: {e}", exc_info=True)
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check and fix team sharing issues in KognitoAI database.")
    parser.add_argument("--team-id", required=True, help="UUID of the team to check.")
    parser.add_argument("--file-name", help="Specific file name to check (partial match).")
    parser.add_argument("--account-id", help="UUID of the account owning the documents (required for fixing).")
    parser.add_argument("--fix", action="store_true", help="Fix sharing by updating team_id for matching documents.")
    
    args = parser.parse_args()
    
    if args.fix and not args.account_id:
        logger.error("Error: --account-id is required when using --fix.")
        sys.exit(1)
    
    check_and_fix_team_sharing(args.team_id, args.file_name, args.account_id, args.fix)
