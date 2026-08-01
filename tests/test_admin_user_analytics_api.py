import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from api.main import app
from core.database import Account, AnalyticsEvent, SessionLocal
from utils.security import create_access_token

@pytest.mark.asyncio
async def test_get_admin_user_analytics():
    async with SessionLocal() as db:
        # Create Admin Account
        admin_id = uuid.uuid4()
        admin_acc = Account(
            id=admin_id,
            name="Admin Test User",
            email=f"admin_{admin_id.hex[:6]}@example.com",
            username=f"admin_user_{admin_id.hex[:6]}",
            hashed_password="fake_hashed_password",
            is_admin=True,
            last_active_at=datetime.now(timezone.utc)
        )
        
        # Create Regular User Account
        user_id = uuid.uuid4()
        user_acc = Account(
            id=user_id,
            name="Regular Test User",
            email=f"user_{user_id.hex[:6]}@example.com",
            username=f"user_{user_id.hex[:6]}",
            hashed_password="fake_hashed_password",
            is_admin=False,
            last_active_at=datetime.now(timezone.utc)
        )
        
        db.add_all([admin_acc, user_acc])
        await db.commit()

        # Add sample events for regular user
        event1 = AnalyticsEvent(
            session_id="sess_1",
            account_id=user_id,
            event_type="pageview",
            path="/chat/123"
        )
        event2 = AnalyticsEvent(
            session_id="sess_1",
            account_id=user_id,
            event_type="pageview",
            path="/notes"
        )
        db.add_all([event1, event2])
        await db.commit()

        admin_token = create_access_token(data={"sub": str(admin_id)})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/admin/analytics/users",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "users" in data
            users = data["users"]
            
            # Find the regular user in returned stats
            reg_user_stat = next((u for u in users if u["account_id"] == str(user_id)), None)
            assert reg_user_stat is not None
            assert reg_user_stat["total_events"] == 2
            assert reg_user_stat["status"] in ["online", "active"]
            
            # Check top features mapping
            feature_names = [f["name"] for f in reg_user_stat["top_features"]]
            assert "Asistente de Chat" in feature_names
            assert "Gestor de Notas" in feature_names

        # Cleanup
        await db.delete(event1)
        await db.delete(event2)
        await db.delete(admin_acc)
        await db.delete(user_acc)
        await db.commit()
