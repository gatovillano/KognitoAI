
import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from core.config import settings

async def count_docs():
    db_url = settings.database_url
    if "@db:" in db_url:
        db_url = db_url.replace("@db:", "@localhost:")
    
    async_url = db_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Filter like _fetch_documents_from_db
        query = text("""
            SELECT account_id, workspace_id, COUNT(DISTINCT cmetadata->>'document_id') 
            FROM langchain_pg_embedding 
            WHERE (cmetadata->>'type' = 'document_chunk' OR cmetadata->>'type' = 'document' OR cmetadata->>'type' IS NULL)
            GROUP BY account_id, workspace_id;
        """)
        result = await session.execute(query)
        rows = result.all()
        if not rows:
            print("No documents found with current filters.")
        for row in rows:
            print(f"Account: {row[0]}, Workspace: {row[1]}, Count: {row[2]}")

if __name__ == "__main__":
    asyncio.run(count_docs())
