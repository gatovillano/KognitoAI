# Rediseño de la Arquitectura de Streaming de Mensajes

**Fecha:** 28 de Septiembre de 2025

**Autor:** Kilo Code

## 1. Resumen Ejecutivo

Este documento propone un rediseño completo de la arquitectura de streaming de mensajes entre el backend de FastAPI y el frontend de React/Next.js. La implementación actual presenta problemas de fiabilidad, complejidad y mantenibilidad debido a flujos de datos redundantes y una gestión de estado frágil en el cliente.

La nueva arquitectura se centrará en **unificar la lógica del backend** en un único flujo basado en WebSockets, **simplificar drásticamente la gestión de estado en el frontend** y establecer un **protocolo de mensajes WebSocket estricto** para garantizar una comunicación robusta y predecible.

## 2. Análisis del Sistema Actual

### 2.1. Flujo de Datos Actual

El sistema presenta dos flujos de streaming paralelos y conflictivos:

1.  **Flujo Principal (WebSocket):** Un endpoint `POST /api/chat` inicia una tarea en segundo plano que envía `chunks` de mensajes a través de un `WebSocketManager`.
2.  **Flujo Alternativo (HTTP):** Un endpoint `POST /api/chat/stream` intenta devolver los `chunks` directamente en una `StreamingResponse` HTTP.

Esta dualidad es una fuente importante de errores y complejidad.

```mermaid
graph TD
    subgraph Frontend (React)
        A[Usuario envía mensaje en CommonChat.tsx] --> B{POST /api/chat};
    end

    subgraph Backend (FastAPI)
        B --> C[api/chat.py: handle_chat];
        C --> D[create_and_run_agent_streaming];
        D --> E[core/agent.py: Agente LangGraph];
        E -- Chunks de respuesta --> F[core/websocket_manager.py];
        F -- Envía mensaje WebSocket --> G[Canal WebSocket del Usuario];

        subgraph "Flujo HTTP Alternativo (Problemático)"
            H[POST /api/chat/stream] --> I[api/chat.py: handle_chat_stream];
            I --> J[Agente LangGraph];
            J -- Chunks --> K[StreamingResponse HTTP];
        end
    end

    subgraph "Frontend (Recepción)"
        G --> L[useWebSocket.ts];
        L --> M[WebSocketContext.tsx];
        M --> N[CommonChat.tsx: Procesa mensajes];
    end

    style H fill:#f9f,stroke:#333,stroke-width:2px
    style I fill:#f9f,stroke:#333,stroke-width:2px
    style J fill:#f9f,stroke:#333,stroke-width:2px
    style K fill:#f9f,stroke:#333,stroke-width:2px
```

### 2.2. Puntos de Fallo Identificados

*   **Gestión de Estado Compleja en Frontend:** La lógica en `CommonChat.tsx` para reconstruir mensajes a partir de `accumulatedChunks` es propensa a errores de sincronización, causando mensajes duplicados o pérdida de datos.
*   **Cálculo Ineficiente de Chunks en Backend:** El backend calcula los `chunks` incrementales comparando strings, un método ineficiente y frágil.
*   **Endpoints Redundantes:** La existencia de `/api/chat` y `/api/chat/stream` viola el principio de una única fuente de verdad.
*   **Protocolo de Mensajes Débil:** La comunicación entre cliente y servidor carece de un protocolo estricto, lo que lleva a una gestión de estado inconsistente.

## 3. Propuesta de Nueva Arquitectura

### 3.1. Protocolo de Mensajes WebSocket

Se establece un protocolo de eventos claro y tipado para toda la comunicación.

| Tipo de Mensaje | `payload` | Descripción |
| :--- | :--- | :--- |
| `stream_start` | `{ taskId: string }` | Inicio de una nueva respuesta. El `taskId` agrupa todos los mensajes relacionados. |
| `stream_chunk` | `{ taskId: string, chunk: string }` | Fragmento de texto incremental de la respuesta del LLM. |
| `stream_end` | `{ taskId: string }` | Final de la respuesta del LLM. |
| `tool_start` | `{ taskId: string, toolName: string }` | El agente ha comenzado a ejecutar una herramienta. |
| `tool_end` | `{ taskId: string, toolName: string, result: any, sources?: Source[] }` | La herramienta ha finalizado. Incluye resultado y fuentes. |
| `error` | `{ taskId: string, message: string }` | Notifica un error durante el proceso. |

### 3.2. Arquitectura del Backend (FastAPI)

*   **Endpoint Único:** `POST /api/chat` será el único punto de entrada. Iniciará una tarea en segundo plano y devolverá `HTTP 202 Accepted` de inmediato.
*   **Lógica de Streaming Aislada:** La función de streaming se refactorizará para generar un `taskId`, emitir los eventos WebSocket definidos en el protocolo y obtener los `chunks` de forma nativa desde LangGraph, sin cálculos manuales.

```mermaid
graph TD
    subgraph Frontend
        A[Usuario envía mensaje] --> B[POST /api/chat];
        B -- HTTP 202 Accepted --> C[UI se pone en modo 'esperando respuesta'];
    end

    subgraph Backend
        B --> D[api/chat.py: handle_chat];
        D -- Inicia tarea en background --> E[run_agent_task];
        E -- taskId --> F[Agente LangGraph];
        F -- Emite eventos (chunks, tools) --> G[websocket_manager];
        G -- Envía mensajes WebSocket --> H[Canal del Usuario];
    end

    subgraph Frontend (Recepción)
        H --> I[useWebSocket.ts];
        I --> J[CommonChat.tsx];
    end
```

### 3.3. Arquitectura del Frontend (React)

*   **Receptor Pasivo:** El frontend se convierte en un receptor pasivo que renderiza los eventos a medida que llegan.
*   **Estado de Streaming Local:** `CommonChat.tsx` gestionará un estado local (`streamingMessage`) que se crea al recibir `stream_start`, se actualiza con cada `stream_chunk` y se consolida en la lista de mensajes al recibir `stream_end`. Esto aísla el estado de cada respuesta y elimina la acumulación global de `chunks`.

## 4. Plan de Implementación

### Parte 1: Backend (FastAPI)

1.  **Refactorizar `api/chat.py` - Endpoint `handle_chat`:**
    *   Modificar `handle_chat` para que use `background_tasks.add_task`.
    *   Hacer que devuelva `HTTP 202 Accepted` inmediatamente.
    *   Eliminar el endpoint `POST /api/chat/stream` y su lógica asociada.
2.  **Refactorizar `api/chat.py` - Lógica de Streaming:**
    *   Modificar `create_and_run_agent_streaming` para implementar el nuevo protocolo de mensajes con `taskId`.
    *   Cambiar la obtención de `chunks` para usar un método nativo de LangGraph.
    *   Asegurar que se emitan los eventos `stream_start`, `stream_chunk`, `tool_start`, `tool_end`, y `stream_end`/`error` correctamente.

### Parte 2: Frontend (React)

1.  **Simplificar `useWebSocket.ts`:**
    *   Eliminar el estado `accumulatedChunks` y toda la lógica de acumulación. El hook solo debe pasar los mensajes recibidos al contexto.
2.  **Refactorizar `CommonChat.tsx`:**
    *   Añadir un nuevo estado local: `const [streamingMessage, setStreamingMessage] = useState<... | null>(null);`.
    *   Reescribir el `useEffect` que maneja los mensajes del WebSocket para que siga la lógica del nuevo protocolo:
        *   `stream_start`: Crea el objeto `streamingMessage`.
        *   `stream_chunk`: Concatena el `chunk` al `content` de `streamingMessage`.
        *   `stream_end`: Mueve `streamingMessage` a la lista de mensajes permanentes y resetea el estado a `null`.
    *   Actualizar la lógica de renderizado para mostrar el `streamingMessage` mientras se está construyendo.
