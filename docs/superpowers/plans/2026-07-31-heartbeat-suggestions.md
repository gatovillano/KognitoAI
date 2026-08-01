# Heartbeat Autónomo (Acciones Sugeridas en Insights) Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar la creación automática e inserción directa de tareas (`Task`) y eventos (`AgendaEvent`) en la BD desde el Heartbeat Autónomo, transformándolos en sugerencias dentro de los insights.

**Architecture:** Modificar `core/autonomous_heartbeat.py` actualizando el prompt del LLM, el esquema JSON de respuesta y la persistencia de insights sin tocar las tablas de tareas ni agenda.

**Tech Stack:** Python 3.11+, SQLAlchemy Async, Pydantic, LiteLLM/OpenRouter.

## Global Constraints

- Preservar la compatibilidad de `ProactiveInsight` usando el campo `related_items` para almacenar sugerencias de tareas y eventos.
- No alterar otros comportamientos del heartbeat (herramientas de lectura, notificaciones WS, logs de hilo).

---

### Task 1: Modificar `_save_autonomous_heartbeat_insights` en `core/autonomous_heartbeat.py`

**Files:**
- Modify: `core/autonomous_heartbeat.py:507-640`

**Interfaces:**
- Consumes: List of insight dicts from LLM response parser.
- Produces: Saved `ProactiveInsight` records in DB with `related_items` containing `suggested_actions`.

- [ ] **Step 1: Modificar `_save_autonomous_heartbeat_insights` para remover la creación de `Task` por recurrencia**
  Remover la instanciación e inserción de `Task` en BD cuando `similar_count >= 3`.

- [ ] **Step 2: Mapear `suggested_actions` a `related_items`**
  Para cada elemento en `suggested_actions`, añadirlo a `related_items` como dict con `kind: "suggested_task"` o `kind: "suggested_event"`.

- [ ] **Step 3: Verificar sintaxis**
  Ejecutar `python3 -m py_compile core/autonomous_heartbeat.py`.

---

### Task 2: Modificar el Prompt y Parser en `run_autonomous_agent_heartbeat`

**Files:**
- Modify: `core/autonomous_heartbeat.py:1046-1205`

- [ ] **Step 1: Actualizar guardarraíles del prompt**
  Reemplazar la regla de creación autónoma por una regla estricta de prohibición de creación directa y exigencia de uso de `suggested_actions`.

- [ ] **Step 2: Actualizar el esquema JSON del prompt**
  Remover `auto_created_tasks` y `auto_created_events` del esquema JSON del prompt. Añadir `suggested_actions` en los elementos de `insights`.

- [ ] **Step 3: Eliminar inserción DB en `run_autonomous_agent_heartbeat`**
  Remover el bloque de código que iteraba sobre `auto_tasks` y `auto_events` creando e insertando instancias de `Task` y `AgendaEvent`.

- [ ] **Step 4: Normalizar `suggested_actions` en los insights**
  Extraer `suggested_actions` del JSON parsed de cada insight y asegurar que se pase a `_save_autonomous_heartbeat_insights`.

- [ ] **Step 5: Verificar compilación y sintaxis**
  Ejecutar `python3 -m py_compile core/autonomous_heartbeat.py`.
