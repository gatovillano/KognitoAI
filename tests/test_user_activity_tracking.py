import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from api.main import app
from core.database import Account, SessionLocal
from utils.security import create_access_token

@pytest.mark.asyncio
async def test_analytics_track_updates_last_active_at():
    async with SessionLocal() as db:
        acc_id = uuid.uuid4()
        acc = Account(
            id=acc_id,
            name="Tracking Test User",
            email=f"track_{acc_id.hex[:6]}@example.com",
            username=f"track_user_{acc_id.hex[:6]}"
        )
        db.add(acc)
        await db.commit()

        token = create_access_token(data={"sub": str(acc_id)})
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/analytics/track",
                json={
                    "session_id": "sess_test_123",
                    "event_type": "pageview",
                    "path": "/chat"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 201
        
        # Verify db was updated
        await db.refresh(acc)
        assert acc.last_active_at is not None
        
        # Cleanup
        await db.delete(acc)
        await db.commit()
