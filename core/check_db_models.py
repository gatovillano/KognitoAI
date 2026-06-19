import asyncio
from core.database import SessionLocal, Account, SystemSettings
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        # Check SystemSettings
        result = await db.execute(select(SystemSettings))
        settings_rows = result.scalars().all()
        print("=== SYSTEM SETTINGS ===")
        for row in settings_rows:
            print(f"Key: {row.key}, Value: {row.value}")
            
        # Check Accounts
        result = await db.execute(select(Account))
        accounts = result.scalars().all()
        print("\n=== ACCOUNTS ===")
        for acc in accounts:
            print(f"ID: {acc.id}")
            print(f"  Name: {acc.name}")
            print(f"  LLM Model: {acc.llm_model}")
            print(f"  LLM Provider: {acc.llm_provider}")
            print(f"  Fast LLM Model: {acc.fast_llm_model}")
            print(f"  Fast LLM Provider: {acc.fast_llm_provider}")
            print(f"  Vision LLM Model: {acc.vision_llm_model}")
            print(f"  Vision LLM Provider: {acc.vision_llm_provider}")

if __name__ == "__main__":
    asyncio.run(main())
