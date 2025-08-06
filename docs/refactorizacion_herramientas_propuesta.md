
# Propuesta de Refactorización y Mejora del Sistema de Herramientas

**Fecha:** 2025-08-03

**Autor:** Gemini

## 1. Resumen Ejecutivo

El sistema de herramientas actual de Kognito AI ha crecido hasta incluir más de 30 herramientas distintas. Aunque potente, esta gran cantidad de opciones en una estructura "plana" presenta desafíos para la selección óptima por parte del LLM y para el mantenimiento del código.

Esta propuesta describe un plan de dos fases para mejorar la arquitectura de las herramientas:

1.  **Reorganización Estructural:** Refactorizar el directorio `tools/` en subdirectorios categóricos para mejorar la claridad, el mantenimiento y sentar las bases para una selección de herramientas más inteligente.
2.  **Implementación de un Selector de Herramientas:** Añadir una funcionalidad en la interfaz de usuario que permita al usuario final activar o desactivar grupos de herramientas, dándole un control preciso sobre las capacidades del agente para una consulta específica.

## 2. Análisis y Motivación

### 2.1. Estructura Actual

-   Todas las herramientas residen en un único directorio `tools/`.
-   La función `core/tools.py` importa y registra todas las herramientas disponibles.
-   El agente recibe la lista completa de más de 30 herramientas para cada consulta.

### 2.2. Desafíos Identificados

-   **Sobrecarga Cognitiva del LLM:** Con tantas herramientas, el LLM puede tener dificultades para diferenciar matices entre herramientas con funcionalidades similares (ej. `web_search_tool` vs. `ddg_search_tool`), lo que puede llevar a una selección subóptima.
-   **Falta de Contexto:** El agente no tiene forma de priorizar un subconjunto de herramientas, incluso si la consulta del usuario se refiere claramente a un dominio (p. ej., "gestión de documentos").
-   **Mantenibilidad:** A medida que se añaden más herramientas, el directorio `tools/` se vuelve más difícil de navegar y mantener.

## 3. Propuesta de Refactorización Estructural

### 3.1. Categorización de Herramientas

Se propone crear subdirectorios dentro de `tools/` para agrupar las herramientas por su dominio funcional.

**Nueva Estructura Sugerida:**

```
tools/
├── __init__.py
├── analysis/      # Herramientas para analizar contenido
├── document/      # Herramientas para la gestión de documentos (CRUD)
├── generation/    # Herramientas para crear contenido nuevo (imágenes, mapas)
├── memory/        # Herramientas para buscar y gestionar la memoria interna
├── personal/      # Herramientas para gestionar notas, agenda, perfil
├── system/        # Herramientas de sistema, programación y grafos
└── web/           # Herramientas para interactuar con la web
```

### 3.2. Fusión de Herramientas Redundantes

Durante la reorganización, se fusionarán herramientas con propósitos muy similares:

-   **`web_search_tool` y `ddg_search_tool`:** Se convertirán en una única `web_search_tool` que podría aceptar un parámetro de `provider`.
-   **Herramientas CRUD:** Se explorará la posibilidad de fusionar herramientas como `add_note_tool`, `get_notes_tool`, etc., en una única `notes_manager_tool` con diferentes acciones (`action="add"`, `action="get"`), simplificando la interfaz para el LLM.

## 4. Propuesta de Implementación del Selector de Herramientas

### 4.1. Backend

1.  **Modificar `core/tools.py`:**
    *   La función `get_all_langchain_tools` se modificará para aceptar un parámetro opcional `enabled_tools: Optional[List[str]] = None`.
    *   Si `enabled_tools` se proporciona, la función solo instanciará las herramientas cuyos nombres estén en esa lista.
    *   Se creará un mapa (`ALL_TOOL_CLASSES`) para facilitar la carga dinámica de las clases de herramientas por su nombre.
    *   Se añadirá una nueva función `get_tool_info_list()` que devolverá una lista de diccionarios `{"name": "...", "description": "..."}` para todas las herramientas disponibles.

2.  **Crear Endpoint en la API:**
    *   Se creará un nuevo endpoint `GET /api/tools/list` que llame a `get_tool_info_list()` para exponer las herramientas disponibles al frontend.

3.  **Actualizar el Endpoint de Chat:**
    *   El endpoint de chat (ej. `/api/chat/stream`) se modificará para aceptar un campo opcional en el cuerpo de la petición: `enabled_tools: Optional[List[str]]`.
    *   Este valor se pasará directamente a `get_all_langchain_tools` para limitar el conjunto de herramientas del agente para esa consulta específica.

### 4.2. Frontend

1.  **Nuevo Componente `ToolSelector.tsx`:**
    *   Se creará un componente de React que renderizará un botón con un icono de herramientas.
    *   Al hacer clic, se abrirá un `Popover` (`shadcn/ui`) que mostrará la lista de herramientas obtenidas del endpoint `/api/tools/list`.
    *   Cada herramienta tendrá un `Checkbox` para que el usuario pueda activarla o desactivarla.

2.  **Integración en `CommonChat.tsx`:**
    *   Se añadirá un estado `selectedTools: string[]` para mantener un registro de las herramientas seleccionadas por el usuario.
    *   Se obtendrá la lista de `availableTools` del nuevo endpoint de la API.
    *   El componente `ToolSelector` se renderizará dentro de `ChatInputBar`, pasándole los estados y los manejadores de eventos necesarios.
    *   Al enviar un mensaje, el estado `selectedTools` se incluirá en la carga útil de la petición a la API de chat.

## 5. Beneficios Esperados

-   **Mejora de la Precisión del Agente:** Al reducir el número de opciones, el LLM cometerá menos errores en la selección de herramientas.
-   **Control del Usuario:** El usuario tendrá un control granular sobre las capacidades del agente, lo que puede ser útil para tareas específicas o para limitar acciones no deseadas.
-   **Código Más Limpio y Mantenible:** La reorganización por categorías hará que la base de código sea más fácil de entender y ampliar.
-   **Rendimiento:** Enviar un conjunto más pequeño de herramientas al LLM podría reducir ligeramente la latencia y el uso de tokens en el prompt del sistema.

## 6. Plan de Implementación Sugerido

1.  **Fase 1 (Backend):**
    *   Implementar la refactorización en `core/tools.py` (carga dinámica).
    *   Crear el endpoint `GET /api/tools/list`.
    *   Actualizar el endpoint de chat para aceptar `enabled_tools`.
2.  **Fase 2 (Frontend):**
    *   Crear el componente `ToolSelector.tsx`.
    *   Integrar el nuevo componente y la lógica de estado en `CommonChat.tsx` y `ChatInputBar.tsx`.
3.  **Fase 3 (Refactorización de Archivos):**
    *   Mover gradualmente los archivos de herramientas a la nueva estructura de directorios propuesta.
    *   Fusionar herramientas redundantes.

Este enfoque incremental asegura que el sistema permanezca funcional en cada paso del proceso.
