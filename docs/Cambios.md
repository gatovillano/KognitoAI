## 26-09-25 Corrección de Límite de Hilos en Sidebar.tsx

Se corrigió un error de validación en la API de `/api/threads` donde el límite de resultados era 100, pero la solicitud desde el frontend intentaba usar 1000.

- **Punto 1**: Se identificó que la llamada a la API con `limit=1000` se realizaba en el archivo `src/components/Sidebar.tsx`.
- **Punto 2**: Se modificó la línea `let apiUrl = '/api/threads?limit=100';` a `let apiUrl = '/api/threads?limit=100';` en `src/components/Sidebar.tsx` para ajustar el límite al valor permitido por la API.

---

## 26-09-25 Corrección de URL de API en entorno de producción

El usuario reportó un error de conexión en la aplicación debido a que la URL de la API apuntaba a un entorno local (`localhost:8000`) en lugar del de producción. Se procedió a actualizar la configuración del proxy en `next.config.mjs` para que apunte a la URL de producción correcta.

- **Punto 1**: Se identificó que el archivo `next.config.mjs` contenía una regla de reescritura que dirigía las llamadas a `/api` hacia `http://localhost:8000/api`.
- **Punto 2**: Se modificó la regla de reescritura para que apunte a la URL de producción `https://apibase.gatoslibres.art/api`.
- **Punto 3**: Se confirmó con el usuario que la URL `https://apibase.gatoslibres.art` era la correcta antes de aplicar el cambio.

---

## 27-09-25 Añadido de Logging Detallado en `api/chat.py`
Se añadió logging detallado en las funciones `create_and_run_agent_streaming` y `handle_chat_stream` en `api/chat.py` para mejorar la depuración del flujo de streaming y la generación de respuestas.

- **Logging en `create_and_run_agent_streaming`**: Se añadió un log antes de la línea 738 para mostrar el contenido completo de `full_response_content`, incluyendo `thread_id` y `task_id`.
- **Logging en `handle_chat_stream`**: Se añadió un log antes de la línea 983 para mostrar el contenido completo de `full_response_content`, incluyendo `thread_id` y `task_id`.

---

## 28-09-25 Añadido de Logging en Frontend para Depuración de Streaming
Se añadieron `console.log` en el archivo `src/components/CommonChat.tsx` para depurar el problema de streaming en el frontend, específicamente en los eventos `llm_chunk` y `llm_end`.

- **Logging en `llm_chunk`**: Se añadió un `console.log` dentro del `case 'llm_chunk'` para mostrar el `data.chunk` recibido, incluyendo `thread_id` y `task_id`.
- **Logging en `llm_end`**: Se añadió un `console.log` en el `case 'llm_end'` para verificar la llegada del evento de finalización del streaming, incluyendo `thread_id` y `task_id`.
- **Corrección de error de TypeScript**: Se corrigió un error de tipo en la función `setBackgroundTasks` donde `message.task_id` podía ser `undefined`, asegurando que siempre sea un `string`.

---

## 28-09-25 Añadido de Logging de Chunks en `api/chat.py`

Se añadió logging detallado por cada chunk enviado en las funciones `create_and_run_agent_streaming` y `handle_chat_stream` en `api/chat.py` para depurar problemas de conexión WebSocket y envío de chunks.

- **Logging en `create_and_run_agent_streaming`**: Se añadió un log antes de `await send_personal_message(...)` (línea 684) para mostrar el `char` que se está enviando, incluyendo `thread_id` y `task_id`.
- **Logging en `handle_chat_stream`**: Se añadió un log antes de `yield json.dumps(...)` (línea 944) para mostrar el `char` que se está enviando, incluyendo `thread_id` y `task_id`.

---
## 28-09-2025 Corrección de Desconexiones Prematuras de WebSocket

Se solucionó un problema donde las conexiones WebSocket se cerraban prematuramente (código 1001) debido a timeouts de inactividad en el túnel de Cloudflare.

- **Diagnóstico**: Se identificó que la falta de un mecanismo de "keep-alive" (heartbeat) provocaba que Cloudflare terminara las conexiones que consideraba inactivas.
- **Solución Backend**: Se implementó una tarea en `core/websocket_manager.py` que envía un mensaje "ping" a todos los clientes conectados cada 20 segundos para mantener la conexión activa.
- **Solución Frontend**: Se añadió un `setInterval` en `src/hooks/useWebSocket.ts` que envía un "ping" al servidor cada 20 segundos, asegurando que la conexión se mantenga viva desde ambos extremos.
---

## 27-09-25 Implementación de Eliminación de Respuestas de Formularios

Se añadió la funcionalidad para permitir a los usuarios eliminar respuestas de los formularios que han creado.

- **Punto 1 (Backend)**: Se creó un nuevo endpoint `DELETE /api/form-responses/{response_id}` en `api/forms.py`. Este endpoint verifica que el usuario que realiza la solicitud sea el propietario del formulario antes de eliminar la respuesta.
- **Punto 2 (Frontend)**: Se añadió un botón de eliminar (con un ícono de papelera) en el componente `ResponseCard.tsx`, que se muestra en la página de detalles del formulario. Este botón abre un diálogo de confirmación antes de proceder con la eliminación.
- **Punto 3 (Frontend)**: Se añadió también un botón de eliminar en cada fila de la tabla de respuestas, en la página `.../forms/[formId]/responses/page.tsx`, para mantener la consistencia en la interfaz.
- **Punto 4 (Frontend)**: Se implementó la lógica en ambos componentes del frontend para llamar al nuevo endpoint de la API y actualizar la interfaz de usuario eliminando la respuesta de la lista una vez que se ha borrado con éxito.

---

## 28-09-25 Refactorización de la Arquitectura de Streaming de Mensajes

Se refactorizó la lógica de streaming en el backend de FastAPI para usar una arquitectura basada en WebSockets, eliminando el endpoint HTTP de streaming y unificando el flujo de comunicación.

- **Refactorización de `api/chat.py` - Endpoint `POST /api/chat`**:
    - El endpoint `POST /api/chat` ahora acepta la solicitud, inicia la función `create_and_run_agent_streaming` como una tarea en segundo plano (`background_tasks.add_task`), y devuelve inmediatamente una respuesta `HTTP 202 Accepted` con un cuerpo JSON que incluye el `thread_id` y un `taskId` único.
- **Eliminación de Endpoint Obsoleto**:
    - Se eliminó por completo el endpoint `POST /api/chat/stream` y su lógica asociada, ya que es obsoleto y generaba redundancia.
- **Actualización de `create_and_run_agent_streaming` en `api/chat.py`**:
    - La función `create_and_run_agent_streaming` ahora acepta el nuevo `taskId`.
    - Los tipos de eventos WebSocket (`llm_start`, `llm_chunk`, `llm_end`, `llm_error`) fueron reemplazados por los nuevos definidos en la arquitectura (`stream_start`, `stream_chunk`, `stream_end`, `error`).
    - Todos los mensajes de WebSocket enviados al frontend ahora incluyen el `taskId` para que el cliente pueda identificar a qué petición pertenece cada evento.
    - El `stream_chunk` envía el contenido incremental directamente como lo provee LangGraph, sin cálculos manuales de deltas.
- **Verificación de `core/agent.py` - `tool_node`**:
    - Se modificó el `tool_node` en `core/agent.py` para asegurar que los eventos de inicio y fin de herramienta (`tool_start`, `tool_end`) también se envíen a través del WebSocket, incluyendo el `taskId` correspondiente.

---

## 28-09-25 Refactorización de la Gestión de Estado de Streaming en Frontend

Se refactorizó `src/components/CommonChat.tsx` para implementar la nueva lógica de gestión de estado de streaming, utilizando `taskId` para la acumulación de chunks y la gestión del ciclo de vida de los mensajes de streaming. Se eliminó la dependencia de `accumulatedChunks` del contexto de WebSocket.

- **Eliminación de `accumulatedChunks`**: Se eliminó la variable `accumulatedChunks` y su lógica asociada de `src/hooks/useWebSocket.ts`, ya que la acumulación de chunks ahora se maneja directamente en `CommonChat.tsx`.
- **Gestión de Estado de Mensajes de Streaming en `CommonChat.tsx`**:
   - Se introdujo un nuevo estado local `streamingMessages` (`Record<string, ChatMessageType>`) en `CommonChat.tsx` para manejar los mensajes en curso, utilizando el `taskId` como clave.
   - Se modificó el `useEffect` que reacciona a `latestMessage` para procesar los eventos de streaming (`stream_start`, `stream_chunk`, `stream_end`) y de herramientas (`tool_start`, `tool_end`, `tool_code`) utilizando el `taskId` para asociar los eventos con los mensajes correctos.
   - Los eventos `llm_start`, `llm_chunk`, `llm_end` fueron renombrados a `stream_start`, `stream_chunk`, `stream_end` respectivamente.
   - Se aseguró que `isResponding` y `isThinking` se actualicen correctamente con los eventos de streaming.
   - Se reseteó `toolName` y `reactState` al recibir un `stream_chunk`.
   - Se añadió el mensaje final de streaming al estado `messages` principal y se eliminó de `streamingMessages` al recibir `stream_end`.
   - Se adaptó la lógica de `tool_start` y `tool_end` para usar `taskId` y actualizar `backgroundTasks`, `toolName` y `reactState`.
- **Actualización de `handleSendMessage`**:
   - Se modificó `handleSendMessage` en `src/components/CommonChat.tsx` para capturar el `taskId` de la respuesta `HTTP 202 Accepted` del backend y usarlo para inicializar el estado de `streamingMessages` si es necesario.
- **Renderizado de Mensajes**:
   - Se modificó la sección de renderizado en `CommonChat.tsx` para incluir los mensajes de `streamingMessages` junto con los mensajes completados del estado `messages`.
   - Se ajustó la `LoadingIndicator` para que solo se muestre si no hay mensajes de streaming activos.

---

## 28-09-2025 Activación del Botón de Micrófono en CommonChat.tsx

Se corrigió el problema por el cual el botón del micrófono en la barra de entrada del chat no funcionaba. La causa era que las funciones `onStartRecording` y `onStopRecording` se pasaban como funciones vacías desde el componente padre `CommonChat.tsx`.

-   **Punto 1**: Se definieron las funciones `handleStartRecording` y `handleStopRecording` en `src/components/CommonChat.tsx`. Estas funciones actualizan el estado `isRecording` y `isProcessingAudio` del componente y muestran notificaciones al usuario.
-   **Punto 2**: Se modificó la forma en que se pasan las props `onStartRecording` y `onStopRecording` al componente `ChatInputBar` en `src/components/CommonChat.tsx`, reemplazando las funciones vacías por las recién definidas `handleStartRecording` y `handleStopRecording`.
-   **Punto 3**: Se eliminaron las props `onStartRecording` y `onStopRecording` del componente `MoreActionsMenu` en `src/components/ChatInputBar.tsx` para evitar posibles conflictos y redundancias, asegurando que el control de grabación se gestione desde el botón principal.

---

## 28-09-2025 Implementación de Transcripción de Audio Real en CommonChat.tsx

Se actualizó la funcionalidad del botón de micrófono para realizar una transcripción de audio real en lugar de una simulación.

-   **Punto 1**: Se modificó la función `handleStopRecording` en `src/components/CommonChat.tsx` para enviar el `audioBlob` grabado al endpoint `/transcribe-audio` del backend.
-   **Punto 2**: Se procesó la respuesta del backend para obtener el texto transcrito y se actualizó el estado `newMessage` con este texto.
-   **Punto 3**: Se añadió manejo de errores para el proceso de transcripción.

---

## 28-09-2025 Corrección de Mensajes de WebSocket no Visualizados en Frontend

Se solucionó el problema donde los mensajes de WebSocket no se visualizaban en el frontend, a pesar de aparecer en los logs, debido a un desajuste en el `thread_id`.

-   **Actualización de `threadIdRef.current`**: Se modificó la función `handleSendMessage` en `src/components/CommonChat.tsx` para actualizar `threadIdRef.current` con el nuevo `threadId` inmediatamente después de crear un nuevo hilo. Esto asegura que el componente siempre tenga la referencia correcta al hilo actual.
-   **Mejora de Logs de Depuración**: Se añadió más información al mensaje de log de "Thread ID mismatch" en `src/components/CommonChat.tsx` para mostrar los valores esperados y recibidos, facilitando la depuración.
-   **Sincronización de Estado de Mensajes**: Se añadió `messages` a las dependencias del `useEffect` que procesa los mensajes de WebSocket en `src/components/CommonChat.tsx`. Esto asegura que el efecto siempre opere con la versión más reciente del estado `messages`, evitando problemas de mensajes obsoletos al añadir el mensaje final del streaming.
-   **Sincronización de `threadIdRef.current` y Logs de Depuración en `useMemo`**: Se añadió un `console.log` en el `useEffect` que actualiza `threadIdRef.current` para verificar su valor. Además, se añadió un `console.log` en el `useMemo` de `allMessages` para confirmar su re-evaluación cuando `streamingMessages` cambia, ayudando a diagnosticar problemas de reactividad.
-   **Clave de Mensajes de Streaming y Eliminación de `memo`**: Se modificó la renderización de los mensajes de streaming en `src/components/CommonChat.tsx` para usar el `taskId` como clave, asegurando una identificación única y estable. Además, se eliminó temporalmente `memo` del componente `ChatMessage` en `src/components/ChatMessage.tsx` para descartar que estuviera impidiendo las re-renderizaciones.
-   **Forzar Re-renderización del Contenedor de Mensajes**: Se añadió una `key` dinámica al `div` que contiene todos los mensajes (`messages` y `streamingMessages`) en `src/components/CommonChat.tsx`. Esta `key` se actualiza con la longitud de `messages` y `streamingMessages`, forzando a React a re-renderizar el contenedor completo cuando el número de mensajes cambia.