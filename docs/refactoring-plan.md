# Plan de refactorización — KognitoAI

## Foco y criterios
- Métricas: complejidad ciclomática (CC) e índice de mantenibilidad (MI).
- Principios: SRP, DRY, KISS.
- Orden: mayor impacto/riesgo primero; no se altera lógica de negocio salvo corrección mínima.

---

## Paso 1 — Corregir bloqueo de sintaxis
**Archivo**: `examples/cognee_usage_examples.py`  
**Acción**: corregir la función `_strip_json_code_fences` que quedó incompleta.  
**Criterio**: sin este fix no se puede importar el módulo ni validar pruebas.  
**Prueba unitaria mínima**: `python -m py_compile examples/cognee_usage_examples.py` y test directo de la función con entrada con fences y sin fences.

---

## Paso 2 — Reducir CC alta en módulos núcleo
Objetivo: dividir funciones/métodos con CC > 20 o responsabilidades mezcladas.

### 2.1 `core/agent.py`
**Acciones**:
- Extraer `build_system_prompt(...)` a `core/prompt_builder.py`.
- Extraer sanitización de historial a `core/history_sanitizer.py`.
- Extraer consolidación de fuentes/IDs a `core/source_consolidator.py`.
- Dejar `agent.py` como orquestador del grafo.

### 2.2 `api/analysis.py`
**Acciones**:
- Mover `extract_topics_from_payload` y variantes a `services/topic_extractor.py`.
- Mover progreso/WebSocket a `services/analysis_progress.py`.
- Mover orquestación de análisis a `services/analysis_orchestrator.py`.
- Dejar `api/analysis.py` como capa HTTP/validación.

### 2.3 `core/autonomous_heartbeat.py`
**Acciones**:
- Extraer carga de contexto a `heartbeat/context_builder.py`.
- Extraer ejecución de tools a `heartbeat/tool_runner.py`.
- Extraer generación y deduplicación de insights a `heartbeat/insight_generator.py`.

### 2.4 `core/memory_manager.py`
**Acciones**:
- Extraer búsqueda híbrida a `services/hybrid_search_service.py`.
- Extraer gestión de perfiles a `services/profile_service.py`.
- Extraer procesamiento de documentos a `services/document_processor.py`.
- Mantener `memory_manager.py` como interfaz de alto nivel.

### 2.5 `api/caldav.py`
**Acciones**:
- Mover conversores iCal a `services/ical_service.py`.
- Mover construcción XML CalDAV a `services/caldav_xml_builder.py`.
- Dejar `caldav.py` como routing/HTTP.

---

## Paso 3 — Mejorar MI en archivos con rango C
**Acciones**:
- Aplicar divisiones del Paso 2.
- Eliminar código duplicado de parsing JSON y normalización de imágenes.
- Reemplazar condicionales largas por lookups/estrategias.
- Limitar funciones a < 60 líneas y reducir anidación excesiva.

---

## Paso 4 — Revisar `manage_skills.py` (CC 0.00)
**Acciones**:
- Si es wrapper delgado: mover a `skills/skill_registry.py` y documentar responsabilidad única.
- Si tiene lógica oculta: extraerla a servicios y eliminar ramas muertas.
- Si es script aislado: convertir en módulo importable con tests.

---

## Paso 5 — Pruebas unitarias mínimas por módulo refactorizado
- `tests/test_prompt_builder.py`
- `tests/test_history_sanitizer.py`
- `tests/test_topic_extractor.py`
- `tests/test_analysis_progress.py`
- `tests/test_heartbeat_tool_runner.py`
- `tests/test_search_service.py`
- `tests/test_caldav_xml_builder.py`

---

## Criterios de aceptación
- Ninguna función refactorizada supera CC 15.
- Archivos objetivo pasan de MI rango C a rango B o superior.
- `py_compile` verde en todos los módulos tocados.
- Cobertura mínima del 70% en módulos refactorizados.

---

## Estimación de impacto
- **Alto**: `core/agent.py`, `api/analysis.py`, `core/autonomous_heartbeat.py`.
- **Medio**: `core/memory_manager.py`, `api/caldav.py`.
- **Bajo**: `manage_skills.py`, `examples/cognee_usage_examples.py`.
