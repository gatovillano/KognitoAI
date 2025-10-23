---
## 22-10-25 Corrección: Rutas de Notas en Frontend (src y Telegram Panel)

Se corrigió la inconsistencia en las rutas de la API para las notas en el frontend, tanto en la aplicación principal (`src/app/(dashboard)/notes/edit/[id]/page.tsx`) como en el panel de Telegram (`telegram_panel/script.js`). Esto resuelve el problema de que las notas no cargaban después de la reversión en el backend.

- **Punto 1**: En `telegram_panel/script.js`, se modificaron las llamadas a la API para añadir, actualizar y eliminar notas para que incluyan el prefijo `/notes`. Específicamente, se cambió `'/api/add-note'` a `'/api/notes/add-note'`, `'/api/update-note'` a `'/api/notes/update-note'`, y `'/api/delete-note'` a `'/api/notes/delete-note'`.
- **Punto 2**: En `src/app/(dashboard)/notes/edit/[id]/page.tsx`, se modificaron las llamadas a la API para añadir, actualizar y auto-guardar notas para que incluyan el prefijo `/notes`. Específicamente, se cambió `'/api/update-note'` a `'/api/notes/update-note'` en la función `autoSaveNote`, y `'/api/add-note'` a `'/api/notes/add-note'` y `'/api/update-note'` a `'/api/notes/update-note'` en la función `handleSave`.
---
## 22-10-25 Corrección: Carga de Notas Vacías en el Editor

Se corrigió un problema en `src/app/(dashboard)/notes/edit/[id]/page.tsx` donde las notas se cargaban vacías, lo que provocaba la pérdida de contenido debido al autoguardado.

- **Punto 1**: Se ajustó la lógica de carga de notas personales para asegurar que la respuesta de la API se maneje correctamente. Ahora, cuando se intenta obtener una nota directamente por ID, se asigna el `data` de la respuesta a una variable y se verifica su contenido antes de establecer el estado de la nota.
- **Punto 2**: Se corrigió un `console.log` en la sección de fallback para que muestre los datos correctos (`fallbackResponse.data`) en lugar de una variable incorrecta (`response.data`).
---
## 22-10-25 Corrección: Error 500 al Cargar Nota por ID en Backend

Se corrigió un error 500 en el backend al intentar cargar una nota por su ID. El problema se debía a que el método `get_note_by_id` en `core/notes_manager.py` no devolvía los campos `workspace_name` y `workspace_color`, que eran esperados por el modelo `NoteResponse` en `api/notes.py`.

- **Punto 1**: Se modificó el método `get_note_by_id` en `core/notes_manager.py` para incluir `workspace_name` y `workspace_color` en el diccionario que devuelve, asegurando que la estructura de datos coincida con la esperada por el frontend y el modelo Pydantic.
---
## 22-10-25 Corrección: Notificación "Contenido no disponible" en el Editor de Notas

Se abordó la aparición de la notificación "El contenido de la nota no está disponible" en el frontend, que ocurría incluso después de corregir el error 500 del backend. Se determinó que la lógica del frontend realizaba una llamada redundante a la API para obtener el contenido de la nota.

- **Punto 1**: Se eliminó la segunda llamada a la API en `src/app/(dashboard)/notes/edit/[id]/page.tsx` que intentaba cargar el contenido completo de la nota. Ahora, si el `content` de la nota está vacío después de la carga inicial, se asume que la nota no tiene contenido y se muestra el mensaje de error correspondiente, evitando llamadas innecesarias al backend.
---
## 22-10-2025 Mejora: Integración de Vista Semanal de Agenda en Workspace

Se ha integrado la vista semanal de la agenda (`WeeklyScheduleView`) en la página de detalles del workspace (`src/app/(dashboard)/workspaces/[id]/page.tsx`). Esto permite visualizar y gestionar eventos y tareas de calendario directamente desde el dashboard del workspace, ofreciendo una experiencia de usuario más completa y organizada.

- **Punto 1**: Se importó el componente `WeeklyScheduleView` de `src/app/(dashboard)/agenda/WeeklyScheduleView.tsx` en `src/app/(dashboard)/workspaces/[id]/page.tsx`.
- **Punto 2**: Se añadió el estado `currentDate` y las funciones de manejo (`handleEditEvent`, `handleDeleteEvent`, `handleEditTask`, `handleDeleteTask`, `handleToggleTaskCompleted`) en `src/app/(dashboard)/workspaces/[id]/page.tsx` para gestionar la interacción con el calendario y los elementos de la agenda.

- **Punto 3**: Se reemplazó la sección anterior de "Agenda del Workspace" con el componente `WeeklyScheduleView`, pasándole los eventos y tareas existentes, así como las funciones de manejo correspondientes.
- **Punto 4**: Se modificaron los componentes `EventDialog` y `TaskDialog` para que reciban el evento o tarea seleccionada como prop, permitiendo la edición de elementos existentes.
---
## 22-10-2025 Corrección: TypeError en GetDocumentListTool por argumento 'team_id' inesperado

Se corrigió un `TypeError` en `GetDocumentListTool` que ocurría porque la función `list_user_documents()` estaba recibiendo un argumento `team_id` inesperado. La función `list_user_documents()` no tiene `team_id` en su firma, lo que provocaba el error.

- **Punto 1**: Se eliminó el argumento `team_id` de la llamada a `list_user_documents()` en `tools/get_document_list_tool.py` para que solo se pasen los parámetros esperados por la función.
---
## 22-10-2025 Corrección: TypeError en comprehensive_web_analyzer por argumento 'team_id' inesperado

Se corrigió un `TypeError` en la herramienta `comprehensive_web_analyzer` que ocurría porque la función `get_relevant_memories()` estaba recibiendo un argumento `team_id` inesperado. La función `get_relevant_memories()` no tiene `team_id` en su firma, lo que provocaba el error.

- **Punto 1**: Se eliminó el argumento `team_id` de la llamada a `get_relevant_memories()` en `utils/multi_query_retriever.py` para que solo se pasen los parámetros esperados por la función.
---
## 22-10-2025 Corrección: AttributeError en MultiQueryRetriever por atributo 'k' faltante

Se corrigió un `AttributeError` en la clase `MultiQueryRetriever` que ocurría porque se intentaba acceder al atributo `self.k` sin que este hubiera sido inicializado en el constructor de la clase.

- **Punto 1**: Se añadió el parámetro `k` al constructor de `MultiQueryRetriever` (`__init__`) en `utils/multi_query_retriever.py` y se asignó a `self.k`.
- **Punto 2**: Se modificó la función `multi_query_search` en `utils/multi_query_retriever.py` para que pase el argumento `k` al constructor de `MultiQueryRetriever`.
---
## 22-10-2025 Corrección: TypeError en comprehensive_web_analyzer por argumento 'document_ids' inesperado

Se corrigió un `TypeError` en la herramienta `comprehensive_web_analyzer` que ocurría porque la función `get_relevant_memories()` estaba recibiendo un argumento `document_ids` cuando esperaba `filter_document_ids`.

- **Punto 1**: Se cambió el argumento `document_ids` a `filter_document_ids` en la llamada a `get_relevant_memories()` en `utils/multi_query_retriever.py` para que coincida con la firma de la función.
---
## 22-10-2025 Corrección: TypeError en comprehensive_web_analyzer por argumento 'visibility_teams' inesperado

Se corrigió un `TypeError` en la herramienta `comprehensive_web_analyzer` que ocurría porque la función `get_relevant_memories()` estaba recibiendo un argumento `visibility_teams` inesperado. La función `get_relevant_memories()` no tiene `visibility_teams` en su firma, lo que provocaba el error.

- **Punto 1**: Se eliminó el argumento `visibility_teams` de la llamada a `get_relevant_memories()` en `utils/multi_query_retriever.py` para que solo se pasen los parámetros esperados por la función.
---
## 22-10-25 Corrección: Carga de Notas Vacías en el Editor y Autoguardado
Se corrigió un problema en `src/app/(dashboard)/notes/edit/[id]/page.tsx` donde las notas se cargaban vacías, lo que provocaba la pérdida de contenido debido al autoguardado.

- **Punto 1**: Se refactorizó el `useEffect` principal para manejar de forma unificada la carga de notas existentes y la inicialización de notas nuevas. Ahora, el contenido se establece correctamente (ya sea cargado de la API o vacío para notas nuevas) antes de que el editor se renderice.
- **Punto 2**: Se eliminó un `useEffect` redundante que reseteaba el contenido para notas nuevas, ya que esta lógica se integró en el `useEffect` principal.
- **Punto 3**: Se añadió una condición de renderizado al `TiptapEditor` para que solo se muestre cuando `isLoading` sea `false`. Esto asegura que el editor no se inicialice con un contenido vacío y evita problemas de autoguardado prematuro.
---
## 22-10-25 Mejora: Streaming de Respuestas del LLM en Tiempo Real

Se implementó el streaming de las respuestas del LLM en tiempo real para que los mensajes se muestren en el frontend en fragmentos, en lugar de aparecer completos de una vez. Esto mejora la experiencia del usuario al interactuar con el asistente.

- **Punto 1**: En `core/agent.py`, se modificó el `call_model_node` para utilizar `chain.astream` en lugar de `chain.ainvoke`. Esto permite procesar la respuesta del LLM en chunks.
- **Punto 2**: Dentro del `call_model_node` en `core/agent.py`, se añadió la lógica para enviar cada chunk de la respuesta del LLM directamente al frontend a través de `send_personal_message` (WebSocket) con el tipo `stream_chunk`.
- **Punto 3**: En `api/chat.py`, se ajustó la función `create_and_run_agent_streaming` para que, en lugar de calcular deltas y enviar chunks, simplemente acumule la respuesta completa del LLM (que ya ha sido transmitida por `core/agent.py`) y la guarde en el historial de mensajes una vez que el proceso del agente ha finalizado.
- **Punto 4**: Se aseguró que el LLM principal en `core/llm_manager.py` esté configurado con `streaming=True`.
---
## 22-10-25 Corrección: Visualización de Mensajes de Streaming en Frontend

Se corrigió el problema por el cual los mensajes de streaming del LLM no se mostraban en tiempo real en el frontend, sino que solo aparecían al recargar la página. Esto se debía a que el hook `useWebSocket` no estaba acumulando los chunks de los mensajes de streaming, sino que sobrescribía el mensaje anterior con cada nuevo chunk.

- **Punto 1**: En `src/hooks/useWebSocket.ts`, se añadió un nuevo estado `streamingMessage` para acumular el contenido de los chunks de un mensaje de streaming.
- **Punto 2**: Se modificó el `onmessage` handler en `src/hooks/useWebSocket.ts` para:
    - Inicializar `streamingMessage` cuando se recibe un mensaje de tipo `stream_start`.
    - Acumular el `chunk` al `content` de `streamingMessage` cuando se recibe un mensaje de tipo `stream_chunk`.
    - Finalizar el streaming y transferir el mensaje completo a `latestMessage` (y limpiar `streamingMessage`) cuando se recibe un mensaje de tipo `stream_end`.
- **Punto 3**: Se expuso el nuevo estado `streamingMessage` en el retorno del hook `useWebSocket`.
- **Punto 4**: En `src/contexts/WebSocketContext.tsx`, se actualizó `WebSocketContextType` y el `contextValue` en `WebSocketProvider` para incluir y exponer `streamingMessage` a los componentes que consumen el contexto.