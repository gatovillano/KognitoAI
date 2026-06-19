import asyncio
from core.database import SessionLocal, UserSecret
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        result = await db.execute(select(UserSecret))
        secrets = result.scalars().all()
        print("=== DATABASE SECRETS ===")
        for sec in secrets:
            print(f"Account ID: {sec.account_id}, Key Name: {sec.key_name}")

if __name__ == "__main__":
    asyncio.run(main())
