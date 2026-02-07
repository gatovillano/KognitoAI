
import asyncio
import uuid
from core.database import SessionLocal, Account

async def check_account():
    async with SessionLocal() as db:
        account_id = "5b8d59b0-69b7-4aa8-9bb0-bf07511222a6"
        account = await db.get(Account, uuid.UUID(account_id))
        if account:
            print(f"Account ID: {account.id}")
            print(f"System Prompt: {account.system_prompt}")
            print(f"LLM Model: {account.llm_model}")
        else:
            print("Account not found")

if __name__ == "__main__":
    asyncio.run(check_account())
