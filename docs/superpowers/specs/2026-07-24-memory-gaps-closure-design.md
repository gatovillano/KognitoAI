# Design Specification: Propuesta de Cierre de Brechas de Memoria y Razonamiento KAI (2026)

**Fecha:** 2026-07-24  
**Autor:** Antigravity / KAI OS Architecture  
**Estado:** Aprobado  

---

## 1. Resumen y Contexto

Tras la refactorización base de KAI (que introdujo procedencia de datos, soporte bi-temporal en Neo4j, memoria episódica, olvido activo y resolución de conflictos), se han identificado 5 brechas operativas y estructurales emergentes en el código local:

1. **Ausencia de Memoria Procedural:** El agente recombina herramientas desde cero en tareas repetitivas sin recordar playbooks óptimos.
2. **Trust Score Estático:** Hechos antiguos no re-confirmados mantienen la misma relevancia que datos recién verificados.
3. **Falta de Aislamiento Multi-Tenant Estricto y Auditoría:** Necesidad de enforcer unificado y log inmutable de accesos a la memoria.
4. **Falta de Explicabilidad ("Why" Log):** El filtrado por confianza/temporalidad ocurre como "caja negra" sin traza clara para inspección.
5. **Evaluación Discontinua:** Ausencia de telemetría continua en tiempo real sobre la salud y degradación de la memoria en producción.

---

## 2. Decisiones Arquitectónicas

### 2.1 Fase 1: Memoria Procedural (Procedural Memory)

- **Tabla SQL (`procedural_memory`)**: Definida en `core/database.py` con SQLAlchemy.
  - Campos: `id` (UUID), `account_id` (UUID), `workspace_id` (UUID), `task_category` (String(100)), `procedure_name` (String(150)), `steps_json` (JSONB), `success_rate` (Float), `usage_count` (Int), `last_executed_at` (TIMESTAMPTZ), `created_at` (TIMESTAMPTZ).
- **Manager (`core/procedural_memory_manager.py`)**: Clase `ProceduralMemoryManager` encargada de:
  - Guardar/actualizar patrones de herramientas tras ejecuciones exitosas.
  - Actualizar tasas de éxito e incrementar conteos de uso.
  - Recuperar playbooks procedimentales por categoría e inyectar sugerencias.
- **Inyección en `unified_context_node` (`core/agent.py`)**: Cuando la intención del usuario coincida con una categoría registrada para su `account_id` y `workspace_id`, se inyecta la guía de pasos en el contexto.

### 2.2 Fase 2: Dynamic Trust Decay (Decaimiento Temporal de Confianza)

- **Modelo Matemático**:
  $$T_{\text{dinámico}} = T_{\text{base}} \times e^{-\lambda \times \Delta t_{\text{días}}}$$
  donde $\lambda = 0.01$ (corresponde a una vida media de $\sim 70$ días).
- **Consultas Cypher Adaptadas en `knowledge_graph/neo4j_adapter.py`**:
  - En la búsqueda y recuperación de nodos/relaciones en Neo4j, se calcula `dynamic_trust` en tiempo real basándose en la diferencia de días entre `updated_at` (o `created_at`) y el momento actual.
  - Filtrado estricto por `$min_trust` usando `dynamic_trust`.

### 2.3 Fase 3: Aislamiento Multi-Tenant Estricto y Auditoría de Memoria

- **Aislamiento Multi-Tenant Estricto Absoluto**:
  - Definición de `TenantIsolationException` en `knowledge_graph/neo4j_adapter.py`.
  - Definición del wrapper `TenantEnforcerGraphDBWrapper` que envuelve `GraphDB`.
  - Toda llamada a `execute_query` verifica que `parameters` contenga obligatoriamente llaves válidas y no nulas para `account_id` y `workspace_id`. Si falta cualquiera de las dos o es nula, se arroja `TenantIsolationException`.
- **Tabla de Auditoría SQL (`memory_access_audit`)**:
  - Definida en `core/database.py`.
  - Campos: `id` (UUID), `timestamp` (TIMESTAMPTZ), `account_id` (UUID), `workspace_id` (UUID), `action` (String: `READ`, `WRITE`, `DELETE`, `RESOLVE`), `component` (String), `query_summary` (Text).

### 2.4 Fase 4: Observabilidad de Traza y Explicabilidad ("Why Log")

- **Modelo `ReasoningTrajectory`**:
  - Definido con Pydantic en `core/models.py` / `knowledge_graph/graph_reasoning_node.py`.
  - Contiene: `query`, `candidates_retrieved`, `filtered_out` (lista de nodos excluidos con razón como `low_dynamic_trust`, `outdated_bitemporal`, `tenant_mismatch` y score/fecha), e `included_in_context`.
- **Exposición**:
  - Se adjunta al `AgentState` de LangGraph.
  - Se transmite en la respuesta de la API/Streaming para consumo en UI.
  - Se persiste en la tabla `memory_access_audit`.

### 2.5 Fase 5: Telemetría de Memoria Continua y Worker de Salud

- **Servicio `MemoryHealthWorker` (`services/memory_health_worker.py`)**:
  - Tarea en segundo plano con ejecuciones periódicas/diarias.
  - Chequeos: detección de nodos huérfanos en Neo4j, índice de frescura temporal, cálculo del score de resistencia a poisoning.
  - Reporte continuo hacia el pipeline de medición.

---

## 3. Esquemas de Datos y Contratos

### 3.1 Modelos SQLAlchemy (`core/database.py`)

```python
class ProceduralMemory(Base):
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


class MemoryAccessAudit(Base):
    __tablename__ = "memory_access_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    component = Column(String(100), nullable=False)
    query_summary = Column(Text, nullable=False)
```

---

## 4. Plan de Verificación

1. **Suites de Pruebas Unitarias e Integración**:
   - `tests/test_procedural_memory.py`: Pruebas de inserción, recuperación e inyección en `unified_context_node`.
   - `tests/test_dynamic_trust_decay.py`: Validación de decaimiento temporal en escenarios de más de 90 días.
   - `tests/test_strict_tenant_isolation.py`: Validación de `TenantIsolationException` cuando falta `account_id` o `workspace_id`.
   - `tests/test_why_log_observability.py`: Validación del objeto `ReasoningTrajectory` y su persitencia.
   - `tests/test_memory_health_worker.py`: Verificación de tareas en segundo plano y detección de nodos huérfanos.
2. **Ejecución del Test Suite Completo**:
   - Ejecución de `pytest` asegurando 100% de éxito en componentes nuevos y cero regresiones.
