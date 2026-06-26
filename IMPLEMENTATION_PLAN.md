# Plan de Implementación: Refactorización Core y Estabilización

**Proyecto:** KognitoAI  
**Fecha:** 2025-06-18  
**Responsable:** Equipo de Desarrollo + Arquitectura  
**Alcance:** Reducir complejidad en core/agent.py y core/memory_manager.py, centralizar gestión de sesiones, mitigar hallazgos críticos de seguridad.

---

## Fase 0 — Pre-requisitos y criterios de calidad

- No modificar comportamiento funcional del chat ni del RAG sin tests explícitos.
- Cada paso se valida con `python -m py_compile` y, cuando aplique, con tests existentes.
- Los cambios se documentan en `docs/Cambios.md` y en `llm_context.md`.
- Se evita introducir nuevos archivos de configuración duplicados.

## Fase 1 — Refactor core/agent.py (mayor impacto)

### 1.1. Levantar métricas actuales
- Correr `code_analysis` sobre `core/agent.py` para obtener CC y mantenibilidad base.
- Identificar en `call_model_node` y `rag_node` los bloques > 50 líneas y con anidación > 3 niveles.

### 1.2. Extraer funciones pequeñas desde `call_model_node`
- Separar:
  - `build_llm_context(state)`: arma el prompt y fuentes.
  - `consolidate_sources(state)`: dedup y reindexación de fuentes.
  - `invoke_model_with_fallback(state, context)`: llamada a LLM con manejo de errores.
  - `handle_streaming_response(...)`: lógica de WebSocket/streaming.
- Cada nueva función <= 40 líneas, con tests unitarios o de integración mínimos.

### 1.3. Simplificar ramas condicionales
- Reemplazar condicionales anidadas por estrategias/estados explícitos donde corresponda.
- Mover reglas de negocio (ej. cuándo usar `graph_reasoning_node`) a `core/context_cache.py` o un nuevo `core/agent_rules.py`.

### 1.4. Normalizar logging
- Unificar formato de logs (ya existe `utils/logging_utils.py`).
- Eliminar `print` y `logger.warning` informativo en flujos críticos.

## Fase 2 — Refactor core/memory_manager.py

### 2.1. Mover lógica RAG a un manager dedicado
- Crear `core/rag_manager.py` con métodos:
  - `get_relevant_memories(...)`
  - `get_document_chunks(...)`
  - `consolidate_sources(...)`
- Reducir `memory_manager.py` a coordinación y acceso a datos.

### 2.2. Eliminar acoplamiento a Neo4j en el manager
- Usar `GraphDB` como interfaz única; no construir consultas Cypher en el manager.

### 2.3. Estandarizar retornos
- Definir un `Source` modelo Pydantic compartido (ya existe `core/citation_models.py`).
- Asegurar que todas las fuentes devuelvan `id`, `type`, `url`, `snippet`, `title`.

## Fase 3 — Centralizar sesiones de base de datos

### 3.1. Migrar endpoints a `DBSession`
- Reemplazar `Depends(get_db)` por `async with DBSession(SessionLocal) as db:` en:
  - `api/analysis.py`
  - `api/notes.py`
  - `api/agenda.py`
  - `api/documents.py`
  - `api/workspaces.py`
- Eliminar todas las funciones `get_db()` duplicadas.

### 3.2. Verificar cierres y excepciones
- Asegurar rollback y cierre de sesión en bloques `try/except`.

## Fase 4 — Seguridad: mitigar hallazgos críticos

### 4.1. Neo4j sin autenticación
- Habilitar `NEO4J_dbms_security_auth__enabled=true`.
- Definir `NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}`.
- Eliminar exposición de puertos 7474/7687 en `docker-compose.yml`.

### 4.2. Redis sin autenticación
- Agregar `--requirepass ${REDIS_PASSWORD}` y eliminar puerto expuesto.

### 4.3. PostgreSQL expuesto
- Eliminar mapeo `5432:5432` en compose.
- Usar `scram-sha-256` y contraseña obligatoria.

### 4.4. JWT secret inseguro
- Prohibir defaults en `get_secret` para `jwt_secret_key` y `db_encryption_key` cuando `DEBUG_MODE=false`.

### 4.5. Endpoints de debug
- Eliminar `/auth/debug-token` y `/auth/emergency-token` en `api/auth.py`.

### 4.6. Tokens en query params
- Cambiar WebSocket a `Authorization` header en `api/main.py`.

## Fase 5 — Pruebas y validación

- Correr `pytest` sobre `tests/` relevantes.
- Correr `python -m py_compile` sobre archivos modificados.
- Smoke test: levantar `start_local.sh` y verificar /health, chat y RAG.

## Fase 6 — Documentación y cierre

- Actualizar `docs/Cambios.md` y `llm_context.md`.
- Generar `docs/REFACTOR_CORE_SUMMARY.md` con antes/después de métricas.
- Commit: `refactor(core): reducir complejidad agent y memory manager, centralizar DB sessions, mitigar hallazgos seguridad criticos`.

---

## Criterios de éxito

| Métrica | Antes | Después |
|---------|-------|---------|
| CC de `core/agent.py` | > 150 | < 80 |
| Mantenibilidad `core/agent.py` | ~ 0 | > 40 |
| Archivos con `get_db()` duplicada | > 10 | 0 |
| Vulnerabilidades críticas (auditoría) | 7 | 0 |
| Tiempo de build backend | ~ X min | No aumentar > 10% |
