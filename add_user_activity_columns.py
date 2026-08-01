import asyncio
from sqlalchemy import text
from core.database import engine

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;"))
        await conn.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ;"))
    print("Migration finished successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
