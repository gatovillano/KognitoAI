
import asyncio
import uuid
from core.database import SessionLocal, Account
from utils.security import create_access_token
from sqlalchemy import select

from utils.db_session import DBSession

async def generate_admin_token():
    async with DBSession(SessionLocal) as session:
        result = await session.execute(select(Account).where(Account.is_admin == True).limit(1))
        admin_user = result.scalars().first()

        if admin_user:
            account_id = str(admin_user.id)
            token = create_access_token(data={"sub": account_id})
            print(token)
        else:
            print("No admin user found.")

if __name__ == "__main__":
    asyncio.run(generate_admin_token())
