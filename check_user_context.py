
import asyncio
import uuid
from core.database import SessionLocal, Account, Perfil

async def check_account():
    async with SessionLocal() as db:
        account_id = "5b8d59b0-69b7-4aa8-9bb0-bf07511222a6"
        account = await db.get(Account, uuid.UUID(account_id))
        if account:
            print(f"Account ID: {account.id}")
            print(f"Custom System Prompt: {account.custom_system_prompt}")
            
            # Check profile
            from sqlalchemy import select
            result = await db.execute(select(Perfil).where(Perfil.account_id == account.id))
            profile = result.scalar_one_or_none()
            if profile:
                print(f"Profile System Prompt: {profile.system_prompt}")
            else:
                print("Profile not found")
        else:
            print("Account not found")

if __name__ == "__main__":
    asyncio.run(check_account())
