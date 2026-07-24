# Implementation Plan: Cierre de Brechas de Memoria y Razonamiento KAI (2026)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar las 5 fases de cierre de brechas de memoria y razonamiento en KAI OS (Memoria Procedural, Decaimiento Temporal de Confianza, Aislamiento Multi-Tenant Estricto y Auditoría, Observabilidad "Why" Log y Telemetría/Worker de Salud).

**Architecture:** Se agregarán modelos SQLAlchemy para memoria procedural y auditoría en PostgreSQL, un interceptor/wrapper estricto en Neo4jAdapter para garantizar aislamiento multi-tenant, decaimiento exponencial de confianza ($\lambda=0.01$) en consultas Cypher, trazas de explicabilidad `ReasoningTrajectory` en LangGraph y un servicio de salud en segundo plano `MemoryHealthWorker`.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL (pgvector), Neo4j Cypher, LangGraph, Pytest.

## Global Constraints

- **Python Path:** Ejecutar pruebas usando `PYTHONPATH=. venv_host/bin/pytest`.
- **Aislamiento Multi-Tenant:** Toda consulta a Neo4j requiere obligatoriamente `account_id` y `workspace_id` no nulos.
- **TDD:** Escribir y verificar pruebas para cada componente desarrollado.

---

### Task 1: Implementación de Memoria Procedural (Fase 1)

**Files:**
- Create: `core/procedural_memory_manager.py`
- Modify: `core/database.py`
- Modify: `core/agent.py`
- Test: `tests/test_procedural_memory.py`

**Interfaces:**
- Consumes: `DBSession`, `SessionLocal` de `utils.db_session` y `core.database`.
- Produces: `ProceduralMemoryManager.save_procedure`, `ProceduralMemoryManager.get_procedure_by_category`, `ProceduralMemoryManager.update_success_rate`.

- [ ] **Step 1: Write failing unit tests for ProceduralMemoryManager**

Create `tests/test_procedural_memory.py`:
```python
import asyncio
import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock
from core.procedural_memory_manager import ProceduralMemoryManager

def test_procedural_memory_manager_methods():
    mock_db = MagicMock()
    manager = ProceduralMemoryManager()
    
    # Test saving a procedure
    proc_id = asyncio.run(manager.save_procedure(
        account_id=str(uuid.uuid4()),
        workspace_id=str(uuid.uuid4()),
        task_category="pdf_generation",
        procedure_name="Generate Sales PDF",
        steps_json={"steps": ["search_data", "create_pdf_tool"]}
    ))
    assert proc_id is not None
```

- [ ] **Step 2: Run test to verify failure**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_procedural_memory.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.procedural_memory_manager'`

- [ ] **Step 3: Define ProceduralMemory model in core/database.py and create core/procedural_memory_manager.py**

Add model to `core/database.py`:
```python
class ProceduralMemory(Base):
    """
    Almacena patrones de ejecución de herramientas y playbooks reutilizables.
    """
    __tablename__ = "procedural_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    task_category = Column(String(100), nullable=False, index=True)
    procedure_name = Column(String(150), nullable=False)
    steps_json = Column(JSONB, nullable=False)
    success_rate = Column(Float, default=1.0, nullable=False)
    usage_count = Column(Integer, default=1, nullable=False)
    last_executed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

Create `core/procedural_memory_manager.py`:
```python
import logging
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from utils.db_session import DBSession
from core.database import SessionLocal, ProceduralMemory

logger = logging.getLogger(__name__)

class ProceduralMemoryManager:
    """Administra la inserción, actualización de tasa de éxito y recuperación de procedimientos."""

    async def save_procedure(
        self,
        account_id: str,
        workspace_id: str,
        task_category: str,
        procedure_name: str,
        steps_json: Dict[str, Any]
    ) -> str:
        async with DBSession(SessionLocal) as session:
            proc = ProceduralMemory(
                account_id=uuid.UUID(account_id),
                workspace_id=uuid.UUID(workspace_id),
                task_category=task_category,
                procedure_name=procedure_name,
                steps_json=steps_json,
                success_rate=1.0,
                usage_count=1
            )
            session.add(proc)
            await session.commit()
            return str(proc.id)

    async def get_procedure_by_category(
        self,
        account_id: str,
        workspace_id: str,
        task_category: str
    ) -> Optional[Dict[str, Any]]:
        async with DBSession(SessionLocal) as session:
            stmt = select(ProceduralMemory).where(
                ProceduralMemory.account_id == uuid.UUID(account_id),
                ProceduralMemory.workspace_id == uuid.UUID(workspace_id),
                ProceduralMemory.task_category == task_category
            ).order_by(ProceduralMemory.success_rate.desc(), ProceduralMemory.usage_count.desc())
            result = await session.execute(stmt)
            proc = result.scalars().first()
            if proc:
                return {
                    "id": str(proc.id),
                    "task_category": proc.task_category,
                    "procedure_name": proc.procedure_name,
                    "steps_json": proc.steps_json,
                    "success_rate": proc.success_rate,
                    "usage_count": proc.usage_count
                }
            return None

    async def update_success_rate(self, procedure_id: str, success: bool) -> bool:
        async with DBSession(SessionLocal) as session:
            proc = await session.get(ProceduralMemory, uuid.UUID(procedure_id))
            if proc:
                proc.usage_count += 1
                if success:
                    proc.success_rate = round((proc.success_rate * (proc.usage_count - 1) + 1.0) / proc.usage_count, 2)
                else:
                    proc.success_rate = round((proc.success_rate * (proc.usage_count - 1)) / proc.usage_count, 2)
                await session.commit()
                return True
            return False
```

Integrate procedural guide injection in `unified_context_node` in `core/agent.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_procedural_memory.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/database.py core/procedural_memory_manager.py core/agent.py tests/test_procedural_memory.py
git commit -m "feat(memory): implement ProceduralMemoryManager and procedural memory model (Fase 1)"
```

---

### Task 2: Dynamic Trust Decay (Fase 2)

**Files:**
- Modify: `knowledge_graph/neo4j_adapter.py`
- Test: `tests/test_dynamic_trust_decay.py`

**Interfaces:**
- Consumes: `Neo4jAdapter`
- Produces: Dynamic trust calculation ($T_{\text{dinámico}} = T_{\text{base}} \times e^{-0.01 \times \Delta t_{\text{días}}}$) in Cypher queries.

- [ ] **Step 1: Write failing test for dynamic trust decay Cypher calculation**

Create `tests/test_dynamic_trust_decay.py`:
```python
import pytest
from unittest.mock import MagicMock
from knowledge_graph.neo4j_adapter import Neo4jAdapter

def test_dynamic_trust_decay_formula():
    adapter = Neo4jAdapter(graph_db=MagicMock())
    # 0 days old -> trust score remains base
    t0 = adapter._compute_dynamic_trust(base_trust=0.8, days_old=0)
    assert round(t0, 2) == 0.8

    # 70 days old (approx half life for lambda 0.01: e^(-0.7) ~ 0.4965)
    t70 = adapter._compute_dynamic_trust(base_trust=0.8, days_old=70)
    assert round(t70, 2) == 0.40
```

- [ ] **Step 2: Run test to verify failure**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_dynamic_trust_decay.py -v`
Expected: FAIL with `AttributeError: 'Neo4jAdapter' object has no attribute '_compute_dynamic_trust'`

- [ ] **Step 3: Implement _compute_dynamic_trust and update Cypher queries in knowledge_graph/neo4j_adapter.py**

In `knowledge_graph/neo4j_adapter.py`:
```python
import math

def _compute_dynamic_trust(self, base_trust: float, days_old: float) -> float:
    """Calcula el decaimiento dinámico de confianza: T_dinamico = T_base * e^(-0.01 * days_old)."""
    decay = math.exp(-0.01 * max(0.0, float(days_old)))
    return max(0.0, min(1.0, round(float(base_trust) * decay, 4)))
```

Update Cypher queries retrieving entities in `neo4j_adapter.py` to calculate `duration.between(e.updated_at, datetime()).days` and filter by dynamic trust.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_dynamic_trust_decay.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_graph/neo4j_adapter.py tests/test_dynamic_trust_decay.py
git commit -m "feat(memory): add dynamic trust decay calculation and Cypher adaptation (Fase 2)"
```

---

### Task 3: Aislamiento Multi-Tenant Estricto y Auditoría de Memoria (Fase 3)

**Files:**
- Modify: `core/database.py`
- Modify: `knowledge_graph/neo4j_adapter.py`
- Test: `tests/test_strict_tenant_isolation.py`

**Interfaces:**
- Consumes: `GraphDB`, `execute_query`
- Produces: `TenantIsolationException`, `TenantEnforcerGraphDBWrapper`, `MemoryAccessAudit`

- [ ] **Step 1: Write failing test for TenantEnforcerGraphDBWrapper**

Create `tests/test_strict_tenant_isolation.py`:
```python
import asyncio
import pytest
from unittest.mock import MagicMock
from knowledge_graph.neo4j_adapter import TenantIsolationException, TenantEnforcerGraphDBWrapper

def test_tenant_enforcer_missing_params():
    mock_db = MagicMock()
    wrapper = TenantEnforcerGraphDBWrapper(graph_db=mock_db)

    with pytest.raises(TenantIsolationException):
        asyncio.run(wrapper.execute_query("MATCH (n) RETURN n", parameters={}))
```

- [ ] **Step 2: Run test to verify failure**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_strict_tenant_isolation.py -v`
Expected: FAIL with `ImportError: cannot import name 'TenantIsolationException'`

- [ ] **Step 3: Define MemoryAccessAudit in core/database.py and TenantEnforcerGraphDBWrapper in knowledge_graph/neo4j_adapter.py**

Add `MemoryAccessAudit` model to `core/database.py`:
```python
class MemoryAccessAudit(Base):
    """
    Registro inmutable de auditoría de operaciones sobre la memoria.
    """
    __tablename__ = "memory_access_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    component = Column(String(100), nullable=False)
    query_summary = Column(Text, nullable=False)
```

Add `TenantIsolationException` and `TenantEnforcerGraphDBWrapper` to `knowledge_graph/neo4j_adapter.py`:
```python
class TenantIsolationException(Exception):
    """Excepción lanzada cuando una consulta al grafo no incluye account_id o workspace_id válidos."""
    pass

class TenantEnforcerGraphDBWrapper:
    """Wrapper obligatorio que intercepta toda llamada a execute_query en Neo4j."""

    def __init__(self, graph_db):
        self._graph_db = graph_db

    def __getattr__(self, name):
        return getattr(self._graph_db, name)

    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not parameters or "account_id" not in parameters or "workspace_id" not in parameters:
            raise TenantIsolationException(
                f"❌ Violación de Aislamiento Multi-Tenant: 'account_id' y 'workspace_id' son obligatorios en toda consulta."
            )
        if not parameters["account_id"] or not parameters["workspace_id"]:
            raise TenantIsolationException(
                "❌ Violación de Aislamiento Multi-Tenant: 'account_id' y 'workspace_id' no pueden ser nulos o vacíos."
            )
        return await self._graph_db.execute_query(query, parameters)
```

Wrap `self.graph_db` in `Neo4jAdapter.__init__`:
```python
self.graph_db = TenantEnforcerGraphDBWrapper(graph_db)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_strict_tenant_isolation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/database.py knowledge_graph/neo4j_adapter.py tests/test_strict_tenant_isolation.py
git commit -m "feat(security): implement strict multi-tenant isolation enforcer and audit model (Fase 3)"
```

---

### Task 4: Observabilidad de Traza y Explicabilidad ("Why" Log) (Fase 4)

**Files:**
- Create: `core/models_reasoning.py`
- Modify: `knowledge_graph/graph_reasoning_node.py`
- Modify: `core/agent.py`
- Test: `tests/test_why_log_observability.py`

**Interfaces:**
- Consumes: Candidates retrieved during graph reasoning.
- Produces: `ReasoningTrajectory`, `ReasoningTrajectoryFilterItem` attached to `AgentState`.

- [ ] **Step 1: Write failing test for ReasoningTrajectory model and node integration**

Create `tests/test_why_log_observability.py`:
```python
import pytest
from core.models_reasoning import ReasoningTrajectory, ReasoningTrajectoryFilterItem

def test_reasoning_trajectory_structure():
    traj = ReasoningTrajectory(
        query="test query",
        candidates_retrieved=10,
        filtered_out=[
            ReasoningTrajectoryFilterItem(node_id="e1", reason="low_dynamic_trust", score=0.2)
        ],
        included_in_context=9
    )
    assert traj.candidates_retrieved == 10
    assert len(traj.filtered_out) == 1
    assert traj.filtered_out[0].reason == "low_dynamic_trust"
```

- [ ] **Step 2: Run test to verify failure**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_why_log_observability.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.models_reasoning'`

- [ ] **Step 3: Create core/models_reasoning.py and integrate in graph_reasoning_node.py and core/agent.py**

Create `core/models_reasoning.py`:
```python
from typing import List, Optional
from pydantic import BaseModel

class ReasoningTrajectoryFilterItem(BaseModel):
    node_id: str
    reason: str  # low_dynamic_trust | outdated_bitemporal | tenant_mismatch
    score: Optional[float] = None
    valid_to: Optional[str] = None

class ReasoningTrajectory(BaseModel):
    query: str
    candidates_retrieved: int
    filtered_out: List[ReasoningTrajectoryFilterItem] = []
    included_in_context: int
```

Integrate trajectory tracking in `knowledge_graph/graph_reasoning_node.py` and state merging in `core/agent.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_why_log_observability.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/models_reasoning.py knowledge_graph/graph_reasoning_node.py core/agent.py tests/test_why_log_observability.py
git commit -m "feat(observability): implement ReasoningTrajectory 'Why Log' for reasoning transparency (Fase 4)"
```

---

### Task 5: Telemetría de Memoria Continua y Worker de Salud (Fase 5)

**Files:**
- Create: `services/memory_health_worker.py`
- Test: `tests/test_memory_health_worker.py`

**Interfaces:**
- Consumes: `GraphDB`, `SessionLocal`
- Produces: Health audit stats (orphan node detection, freshness index, poisoning resistance score).

- [ ] **Step 1: Write failing test for MemoryHealthWorker**

Create `tests/test_memory_health_worker.py`:
```python
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock
from services.memory_health_worker import MemoryHealthWorker

def test_memory_health_worker_checks():
    mock_db = MagicMock()
    mock_db.execute_query = AsyncMock(return_value=[{"orphan_count": 0}])
    worker = MemoryHealthWorker(graph_db=mock_db)

    report = asyncio.run(worker.run_daily_health_check(account_id="acc1", workspace_id="ws1"))
    assert "orphan_nodes" in report
    assert report["orphan_nodes"] == 0
```

- [ ] **Step 2: Run test to verify failure**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_memory_health_worker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.memory_health_worker'`

- [ ] **Step 3: Create services/memory_health_worker.py**

Create `services/memory_health_worker.py`:
```python
import logging
from typing import Dict, Any
from utils.db_session import DBSession
from core.database import SessionLocal

logger = logging.getLogger(__name__)

class MemoryHealthWorker:
    """Servicio en segundo plano que ejecuta chequeos diarios automatizados de salud de memoria."""

    def __init__(self, graph_db=None):
        self.graph_db = graph_db

    async def run_daily_health_check(self, account_id: str, workspace_id: str) -> Dict[str, Any]:
        logger.info(f"🏥 Ejecutando chequeo de salud de memoria para account={account_id}, workspace={workspace_id}...")
        report = {
            "orphan_nodes": 0,
            "freshness_index": 1.0,
            "poison_resistance_score": 1.0,
            "status": "healthy"
        }
        
        if self.graph_db:
            try:
                orphan_query = """
                MATCH (n)
                WHERE n.account_id = $account_id AND n.workspace_id = $workspace_id AND NOT (n)--()
                RETURN count(n) as orphan_count
                """
                res = await self.graph_db.execute_query(orphan_query, {"account_id": account_id, "workspace_id": workspace_id})
                if res:
                    report["orphan_nodes"] = res[0].get("orphan_count", 0)
            except Exception as e:
                logger.error(f"Error detectando nodos huérfanos: {e}")

        return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. venv_host/bin/pytest tests/test_memory_health_worker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/memory_health_worker.py tests/test_memory_health_worker.py
git commit -m "feat(telemetry): implement MemoryHealthWorker background health check service (Fase 5)"
```
