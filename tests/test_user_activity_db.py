import pytest
import uuid
from datetime import datetime
from sqlalchemy import select
from core.database import Account, SessionLocal

@pytest.mark.asyncio
async def test_account_has_activity_fields():
    async with SessionLocal() as db:
        acc_id = uuid.uuid4()
        account = Account(
            id=acc_id,
            name="Test Activity User",
            email=f"test_act_{acc_id.hex[:6]}@example.com",
            last_login_at=datetime.now(),
            last_active_at=datetime.now()
        )
        db.add(account)
        await db.commit()
        
        stmt = select(Account).where(Account.id == acc_id)
        res = await db.execute(stmt)
        fetched = res.scalar_one_or_none()
        assert fetched is not None
        assert fetched.last_login_at is not None
        assert fetched.last_active_at is not None
        
        # Cleanup
        await db.delete(fetched)
        await db.commit()
