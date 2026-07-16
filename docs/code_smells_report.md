# Reporte de Code Smells, Código Spaghetti y Duplicación — KognitoAI

> **Fecha de auditoría:** 2026-07-15
> **Alcance:** `core/`, `api/`, `knowledge_graph/`, `utils/`
> **Autor:** BashAgent (auditoría estática)
> **Metodología:** `radon` (complejidad ciclomática + mantenibilidad), `grep`/`search_in_file` (duplicación, excepts), `md5sum` (duplicados byte-a-byte).

---

## 1. Resumen Ejecutivo

El codebase de KognitoAI padece de tres problemas sistémicos:

1. **God Objects / Código Spaghetti:** `core/agent.py` tiene **3.963 líneas** y un nodo LangGraph (`call_model_node`) con **Complejidad Ciclomática = 301**. El promedio de CC del archivo es **18.41** (el umbral de mantenibilidad aconsejado es ≤10).
2. **Duplicación de código:** Existe una carpeta `core/agents_langgraph_backup/` con copias idénticas (mismo MD5) de módulos activos en `core/agents/`.
3. **Manejo de errores deficiente y session management inconsistente:** 29 bloques `except` en `agent.py` (4 de ellos *bare `except:`* que tragan errores), y 30 patrones mixtos de sesión DB en `memory_manager.py`.

---

## 2. Código Spaghetti — Complejidad Ciclomática (radon)

### 2.1 `core/agent.py` — Promedio CC: 18.41 | Total líneas: 3.963

| Función / Bloque | CC | Severidad |
|---|---|---|
| `call_model_node` | **301** | 🔴 Crítica (spaghetti extremo) |
| `run_custom_user_heartbeat` | 36 | 🔴 Crítica |
| `sanitize_json_content` | 29 | 🔴 Crítica |
| `rag_node` | 26 | 🟠 Alta |
| `unified_context_node` | 25 | 🟠 Alta |
| `knowledge_extraction_node` | 22 | 🟠 Alta |
| `update_thread_title_if_needed` | 19 | 🟡 Media |
| `tool_node` | 18 | 🟡 Media |
| `graph_router_node` | 12 | 🟡 Media |
| `force_update_thread_title` | 11 | 🟡 Media |
| `get_shared_graph_dependencies` | 9 | 🟢 Baja |
| `proactive_memory_node` | 15 | 🟡 Media |
| `normalize_image_url` | 10 | 🟡 Media |

**Diagnóstico:** `call_model_node` (CC=301) es una función que debería dividirse en al menos 15–20 sub-funciones. Es el principal cuello de mantenibilidad del proyecto.

### 2.2 Otros archivos con alta CC (radon)

| Archivo | Función | CC |
|---|---|---|
| `api/caldav.py` | `propfind_caldav_calendar_collection` | **37** |
| `api/collection_search.py` | `search_in_collection` | **28** |
| `api/scheduled_tools.py` | `_get_schedule_info` | 21 |
| `api/scheduled_tools.py` | `update_custom_heartbeat` | 15 |
| `api/caldav.py` | `put_caldav_resource` | 23 |
| `api/caldav.py` | `get_caldav_resource` | 12 |
| `api/analysis.py` | (chunk_size=15000, límite manual de tokens) | — |

---

## 3. God Objects

| Archivo | Líneas | Problema |
|---|---|---|
| `core/agent.py` | **3.963** | Orquesta prompts, sanitización, historial, grafo LangGraph, RAG, reasoning, heartbeats. Debería dividirse en: `prompt_builder.py`, `history_sanitizer.py`, `source_consolidator.py`, `graph_nodes/`. |
| `core/memory_manager.py` | **2.630** | Mezcla búsquedas SQL crudas, FTS, semántica y gestión de sesiones en un solo módulo. |
| `core/agents/deep_researcher.py` | **2.053** | Lógica de investigación profunda en un solo archivo; debería modularizarse en nodos. |
| `api/chat.py` | ~2.300 | `create_and_run_agent_streaming` maneja streaming, cancelación, OnlyOffice y persistencia en un solo flujo. |

---

## 4. Duplicación de Código

### 4.1 Backup redundante (MD5 idéntico)

La carpeta `core/agents_langgraph_backup/` contiene copias **byte-a-byte idénticas** de módulos activos:

| Archivo activo | MD5 | Archivo en backup | MD5 | Duplicado |
|---|---|---|---|---|
| `core/agents/deep_researcher.py` | `1b3cb350…` | `core/agents_langgraph_backup/deep_researcher_langgraph_backup.py` | `1b3cb350…` | ✅ **Idéntico** |
| `core/agents/deep_researcher.py` | `1b3cb350…` | `core/agents_langgraph_backup/deep_researcher.py` | `1b3cb350…` | ✅ **Idéntico** |

Además, los archivos `deep_researcher_config.py`, `deep_researcher_prompts.py`, `deep_researcher_state.py`, `deep_researcher_utils.py` están presentes tanto en `core/agents/` como en `core/agents_langgraph_backup/` con contenido divergente (distintos MD5), lo que indica **deriva de copias**: los cambios hechos en uno no se reflejan en el otro.

**Riesgo:** Mantener dos versiones de `deep_researcher.py` idénticas es una fuente de bugs (¿cuál es la "verdadera"?). El backup debería eliminarse o moverse fuera del árbol de código (p. ej. a `docs/archive/` o control de versiones).

### 4.2 Imports muertos en `core/agent.py`

Más de 15 imports no utilizados detectados (ej. `RunnablePassthrough`, `BaseLanguageModel`, `AgentAction`, entre otros). Esto infla el archivo y dificulta la lectura. Recomendado: ejecutar `ruff --fix` o `autoflake`.

### 4.3 Líneas extremadamente largas

40+ líneas >100 caracteres en `core/agent.py`, dificultando la revisión en diffs y editores estándar.

---

## 5. Manejo de Errores Deficiente

### 5.1 `core/agent.py` — 29 bloques `except`

Incluye **4 bare `except:`** que tragan errores silenciosamente (anti-patrón):

- Línea **2149**: `except:`
- Línea **2166**: `except:`
- Línea **2410**: `except:`
- Línea **2725**: `except:`

Estos impiden debugging y ocultan fallos en producción. Deben reemplazarse por `except Exception as e:` con logging apropiado, o capturar excepciones específicas.

### 5.2 Swallowing de errores en `temp_open_webui/backend/open_webui/config.py`

Patrón `except Exception: pass` documentado en el análisis previo (código de terceros/vendored, pero presente en el árbol del proyecto).

---

## 6. Session Management Inconsistente

### 6.1 `core/memory_manager.py` — 30 patrones mixtos

El mismo módulo mezcla dos estrategias de sesión DB:

```python
# Patrón A: sesión inyectada por parámetro
results = await db_session.execute(text(sql_query), query_params)   # línea 233

# Patrón B: context manager propio (línea 236, inmediatamente después)
async with DBSession(SessionLocal) as session:
    ...
```

Esto ocurre en pares repetidos en las líneas: 233/236, 278/281, 389/392, 439/442, y 25 ocurrencias más de `async with DBSession(SessionLocal) as ...`.

**Problema:** Falta una abstracción única de acceso a datos. Algunas funciones reciben `db_session` y otras crean el suyo, lo que dificulta el control de transacciones y el rollback consistente.

---

## 7. Recomendaciones de Refactorización (Priorizadas)

| # | Acción | Impacto | Esfuerzo |
|---|---|---|---|
| 1 | **Eliminar `core/agents_langgraph_backup/`** o mover a `archive/` fuera del PATH | Alto (elimina duplicación) | Bajo |
| 2 | **Dividir `call_model_node` (CC=301)** en sub-nodos: `build_messages`, `invoke_llm`, `parse_response`, `handle_tool_calls` | Crítico | Alto |
| 3 | Extraer de `core/agent.py`: `prompt_builder.py`, `history_sanitizer.py`, `source_consolidator.py` | Alto | Medio |
| 4 | Centralizar session DB en un único context manager / dependency (`get_db_session`) en `core/memory_manager.py` | Medio-Alto | Medio |
| 5 | Reemplazar los 4 bare `except:` por logging explícito | Medio (debuggabilidad) | Bajo |
| 6 | Ejecutar `ruff`/`autoflake` para limpiar imports muertos y líneas >100 chars en `agent.py` | Medio | Bajo |
| 7 | Modularizar `deep_researcher.py` (2.053 líneas) en nodos de grafo | Medio | Alto |
| 8 | Reducir CC de `api/caldav.py::propfind_caldav_calendar_collection` (37) y `api/collection_search.py::search_in_collection` (28) | Medio | Medio |

---

## 8. Métricas de Referencia (radon)

- **Umbral CC mantenible:** ≤ 10
- **CC de `call_model_node`:** 301 (30× el umbral)
- **Promedio CC `core/agent.py`:** 18.41
- **Líneas totales de los 4 God Objects:** 3.963 + 2.630 + 2.053 + ~2.300 ≈ **10.946 líneas**

---

*Fin del reporte. Generado automáticamente por BashAgent durante la auditoría de refactorización.*
