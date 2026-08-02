# User Activity & Feature Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide system administrators with real-time statistics on user connections (last login, last activity) and feature usage breakdown across the system.

**Architecture:** Extend `Account` ORM model with `last_login_at` and `last_active_at` fields, update them automatically on authentication and tracking requests, provide new admin REST endpoints for user-by-user and platform-wide feature usage, and build interactive UI components in the Admin Analytics page.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, PostgreSQL, Next.js (React), TypeScript, Tailwind CSS, Lucide Icons, Recharts.

## Global Constraints
- Naming: `last_login_at` and `last_active_at` for database columns.
- Endpoint naming: `/api/admin/analytics/users` and `/api/admin/analytics/features`.
- Admin Protection: All admin endpoints must enforce `Depends(get_current_admin_account)`.
- UI: Next.js app router component in `src/app/(dashboard)/admin/analytics/page.tsx`.

---

### Task 1: Database Schema & Migration for User Activity Columns

**Files:**
- Modify: `core/database.py:150-165`
- Create: `add_user_activity_columns.py`
- Test: `tests/test_user_activity_db.py`

**Interfaces:**
- Consumes: SQLAlchemy engine settings from `core.database`
- Produces: `Account.last_login_at` and `Account.last_active_at` fields in database

- [ ] **Step 1: Write the failing test**

```python
import pytest
from datetime import datetime
from sqlalchemy import select
from core.database import Account

@pytest.mark.asyncio
async def test_account_has_activity_fields(db_session):
    account = Account(
        name="Test User",
        email="test_activity@example.com",
        last_login_at=datetime.now(),
        last_active_at=datetime.now()
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    
    assert account.last_login_at is not None
    assert account.last_active_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_user_activity_db.py -v`
Expected: FAIL with AttributeError or unknown column error before implementation.

- [ ] **Step 3: Modify Account model and write migration script**

In `core/database.py`:
```python
    last_login_at = Column(DateTime(timezone=True), nullable=True, comment="Fecha y hora de inicio de sesión")
    last_active_at = Column(DateTime(timezone=True), nullable=True, comment="Fecha y hora de última actividad")
```

Create `add_user_activity_columns.py`:
```python
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
```

- [ ] **Step 4: Run migration and test to verify it passes**

Run: `.venv/bin/python add_user_activity_columns.py && .venv/bin/pytest tests/test_user_activity_db.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/database.py add_user_activity_columns.py tests/test_user_activity_db.py
git commit -m "feat(db): add last_login_at and last_active_at columns to Account model"
```

---

### Task 2: Update Activity Timestamps on Auth and Analytics Track

**Files:**
- Modify: `api/users.py:50-85`
- Modify: `api/analytics.py:80-130`
- Test: `tests/test_user_activity_tracking.py`

**Interfaces:**
- Consumes: JWT tokens, `AnalyticsEvent` requests
- Produces: Updated `last_login_at` and `last_active_at` records on `Account`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from api.main import app

@pytest.mark.asyncio
async def test_track_event_updates_last_active_at(client, auth_headers, test_account):
    response = client.post(
        "/api/analytics/track",
        json={"session_id": "test_sess_123", "event_type": "pageview", "path": "/chat"},
        headers=auth_headers
    )
    assert response.status_code == 201 or response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_user_activity_tracking.py -v`
Expected: Test fails or shows `last_active_at` was not updated.

- [ ] **Step 3: Update `api/analytics.py` and `api/users.py`**

In `api/analytics.py` `track_event`:
```python
    if user_id:
        try:
            stmt = update(Account).where(Account.id == user_id).values(last_active_at=datetime.now())
            await db.execute(stmt)
        except Exception as e:
            logger.debug(f"Error actualizando last_active_at para usuario {user_id}: {e}")
```

In `api/users.py` (during login or `/users/me`):
```python
    # Update last_login_at or last_active_at
    await db.execute(update(Account).where(Account.id == uuid.UUID(current_account_id)).values(last_active_at=datetime.now()))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_user_activity_tracking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/analytics.py api/users.py tests/test_user_activity_tracking.py
git commit -m "feat(api): update user activity timestamps on track and login"
```

---

### Task 3: Admin User Activity & Feature Analytics Endpoints

**Files:**
- Modify: `api/analytics.py:300-350`
- Test: `tests/test_admin_user_analytics_api.py`

**Interfaces:**
- Consumes: Admin session, `Account` and `AnalyticsEvent` tables
- Produces: `GET /api/admin/analytics/users` and `GET /api/admin/analytics/features`

- [ ] **Step 1: Write the failing test**

```python
import pytest

def test_admin_analytics_users_endpoint(admin_client):
    response = admin_client.get("/api/admin/analytics/users")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert isinstance(data["users"], list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_admin_user_analytics_api.py -v`
Expected: FAIL 404 (endpoint does not exist yet)

- [ ] **Step 3: Implement `GET /api/admin/analytics/users` in `api/analytics.py`**

```python
def map_path_to_feature(path: str) -> str:
    if not path:
        return "Desconocido"
    if path.startswith("/chat") or path.startswith("/c/"):
        return "Asistente de Chat"
    elif path.startswith("/notes") or path.startswith("/notas"):
        return "Gestor de Notas"
    elif path.startswith("/forms") or path.startswith("/formularios"):
        return "Formularios Dinámicos"
    elif path.startswith("/mindmap"):
        return "Mapas Mentales"
    elif path.startswith("/knowledge-graph") or path.startswith("/grafo"):
        return "Grafo de Conocimiento"
    elif path.startswith("/settings") or path.startswith("/perfil"):
        return "Configuración y Perfil"
    elif path.startswith("/presentacion"):
        return "Web de Presentación"
    return "Navegación General"

@router.get("/admin/analytics/users", summary="Obtener analíticas de uso por usuario (solo admin)")
async def get_admin_user_analytics(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(select(Account))
    accounts = result.scalars().all()
    
    now = datetime.now()
    user_stats = []
    for acc in accounts:
        # Fetch events count and top paths for this account
        events_stmt = select(
            AnalyticsEvent.path,
            func.count(AnalyticsEvent.id).label("count")
        ).where(
            AnalyticsEvent.account_id == acc.id
        ).group_by(
            AnalyticsEvent.path
        ).order_by(
            desc("count")
        )
        
        events_res = await db.execute(events_stmt)
        rows = events_res.all()
        
        total_events = sum(r.count for r in rows)
        feature_counts = {}
        for r in rows:
            feat = map_path_to_feature(r.path)
            feature_counts[feat] = feature_counts.get(feat, 0) + r.count
            
        top_features = [
            {
                "name": feat,
                "count": count,
                "percentage": round((count / total_events) * 100) if total_events > 0 else 0
            }
            for feat, count in sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:4]
        ]
        
        # Calculate online/active status
        status_label = "never"
        if acc.last_active_at:
            delta = now - acc.last_active_at.replace(tzinfo=None)
            if delta.total_seconds() < 900: # 15 min
                status_label = "online"
            elif delta.total_seconds() < 86400: # 24h
                status_label = "active"
            else:
                status_label = "inactive"
                
        user_stats.append({
            "account_id": str(acc.id),
            "name": acc.name or acc.username or "Usuario",
            "email": acc.email,
            "username": acc.username,
            "is_admin": bool(acc.is_admin),
            "last_login_at": acc.last_login_at.isoformat() if acc.last_login_at else None,
            "last_active_at": acc.last_active_at.isoformat() if acc.last_active_at else None,
            "total_events": total_events,
            "status": status_label,
            "top_features": top_features
        })
        
    return {"users": user_stats}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_admin_user_analytics_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/analytics.py tests/test_admin_user_analytics_api.py
git commit -m "feat(api): add admin user activity and feature usage analytics endpoint"
```

---

### Task 4: Frontend UI for User Activity & Feature Usage Dashboard

**Files:**
- Modify: `src/app/(dashboard)/admin/analytics/page.tsx`
- Test: Build frontend using `npm run build` or visual verification

**Interfaces:**
- Consumes: `/api/admin/analytics/summary` & `/api/admin/analytics/users`
- Produces: Interactive "Usuarios y Funciones" tab in `/admin/analytics` UI

- [ ] **Step 1: Add state and fetch logic for user analytics in `page.tsx`**

Add interfaces:
```typescript
interface UserActivityStat {
  account_id: string;
  name: string;
  email: string;
  username: string;
  is_admin: boolean;
  last_login_at: string | null;
  last_active_at: string | null;
  total_events: number;
  status: 'online' | 'active' | 'inactive' | 'never';
  top_features: Array<{
    name: string;
    count: number;
    percentage: number;
  }>;
}
```

- [ ] **Step 2: Create UI Tabs for "Tráfico General" and "Usuarios y Funciones"**

In `src/app/(dashboard)/admin/analytics/page.tsx`:
Add tab selector buttons (`activeTab === 'traffic'` vs `activeTab === 'users'`).

- [ ] **Step 3: Implement User Activity Table & Feature Badges**

Render table with:
- User details & admin badge
- Last connection date formatted with relative time (`formatDistanceToNow` or custom parser)
- Status badge (Green dot for online, Yellow for active today, Gray for inactive)
- Top 3 feature badges with percentage pill bars
- Search input filter for user name/email.

- [ ] **Step 4: Build project to ensure no Next.js build or type errors**

Run: `npm run build`
Expected: Successful Next.js compilation with zero errors.

- [ ] **Step 5: Commit**

```bash
git add src/app/\(dashboard\)/admin/analytics/page.tsx
git commit -m "feat(ui): add Users & Feature Usage tab to admin analytics page"
```
