# Heartbeat Autónomo - Sugerencia de Tareas y Eventos mediante Insights

**Fecha:** 2026-07-31  
**Estado:** Aprobado por el usuario  
**Módulo principal:** `core/autonomous_heartbeat.py`  

## 1. Resumen y Contexto
El ciclo de Heartbeat Autónomo (`core/autonomous_heartbeat.py`) genera periódicamente un análisis cognitivo proactivo del contexto del usuario. En su versión anterior, el LLM tenía la capacidad de crear e insertar objetos de `Task` y `AgendaEvent` directamente en la base de datos PostgreSQL, llenando la agenda del usuario con eventos y tareas automáticas que en muchos casos resultaban irrelevantes o excesivas.

Este diseño elimina la creación automática e invasiva de tareas y eventos en la base de datos y la sustituye por un modelo de **Acciones Sugeridas** vinculadas a los `ProactiveInsight`.

---

## 2. Cambios de Comportamiento

### 2.1 Eliminación de Inserción Directa en BD
- Se elimina la lectura y procesamiento de los campos raíz `auto_created_tasks` y `auto_created_events` en `run_autonomous_agent_heartbeat`.
- No se insertarán instancias de `Task` ni `AgendaEvent` directamente a la base de datos durante el ciclo de heartbeat.
- Se elimina la lógica de creación automática de tareas de 48 horas en `_save_autonomous_heartbeat_insights` cuando un insight se detecta como recurrente (`similar_count >= 3`). La recurrencia seguirá registrándose en el campo metadata `related_items`.

### 2.2 Reestructuración del Prompt del LLM
- Se actualiza la sección de guardarraíles del prompt de KAI para prohibir explícitamente la creación o agendamiento directo de elementos en la base de datos.
- Se define una nueva lista opcional `suggested_actions` dentro de cada elemento de `insights` en el esquema de respuesta JSON:

```json
{
  "insights": [
    {
      "type": "opportunity|innovation|synthesis|follow_up|deadline|alert|insight",
      "title": "Título del insight",
      "insight_message": "Explicación del patrón cognitivo...",
      "confidence_score": 0.85,
      "action_suggestion": "Texto explicativo de la acción recomendada...",
      "innovation_potential": "...",
      "related_items": [],
      "suggested_actions": [
        {
          "kind": "suggested_task|suggested_event",
          "title": "Título sugerido",
          "description": "Detalles de la tarea o evento propuesto",
          "start_date": "YYYY-MM-DDTHH:MM:SSZ",
          "end_date": "YYYY-MM-DDTHH:MM:SSZ",
          "duration_minutes": 60,
          "workspace_name": "Nombre del workspace o 'Global'"
        }
      ]
    }
  ]
}
```

### 2.3 Persistencia de Sugerencias en `ProactiveInsight`
- Las sugerencias de acciones recibidas en `suggested_actions` se incorporarán al arreglo JSONB `related_items` de la entidad `ProactiveInsight`.
- De este modo, los insights almacenados mantendrán la información de la tarea o evento sugerido para que la API o el cliente web puedan renderizarlos con botones de aceptación manual (p. ej., "Agendar evento" o "Crear tarea") si el usuario lo desea.

---

## 3. Plan de Verificación

1. **Sintaxis y Tipado:** Inspección del código en `core/autonomous_heartbeat.py`.
2. **Pruebas de Invocación:** Comprobar que el parsing de respuesta JSON del LLM procesa correctamente los insights con `suggested_actions` sin intentar escribir en las tablas `tasks` o `agenda_events`.
3. **Persistencia DB:** Verificar que los registros guardados en `proactive_insights` contengan los ítems sugeridos dentro de `related_items` y que no se creen filas adicionales en `tasks` ni en `agenda_events`.
