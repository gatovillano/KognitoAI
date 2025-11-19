## 19-11-2025 Solución de Error de Caracteres Unicode Inválidos en Chat History

### Descripción general:
Se resolvió un error de base de datos causado por caracteres Unicode inválidos (como \u0000) en los mensajes de chat almacenados en la tabla `langchain_chat_history`. El problema ocurría cuando el contenido de los mensajes contenía caracteres de control que PostgreSQL no puede convertir a texto válido en columnas JSONB.

- **Implementación de función de sanitización**: Se creó la función `sanitize_json_content()` en `core/agent.py` que elimina caracteres de control inválidos del contenido de los mensajes antes de guardarlos en la base de datos.
- **Modificación de puntos de guardado**: Se actualizaron todos los lugares donde se guardan mensajes en el historial de chat (`api/chat.py` y `core/agent.py`) para usar la función de sanitización antes de llamar a `aadd_messages()`.
- **Importación de la función**: Se importó `sanitize_json_content` en `api/chat.py` para su uso en las funciones de manejo de chat.
---
## 19-11-2025 Resolución de Error en Migración Alembic y Adición de Campo Status a Tabla Tasks

### Descripción general:
Se resolvió un error en el comando `alembic upgrade head` que impedía la actualización de la base de datos. El problema se debía a una migración que intentaba eliminar una tabla `langchain_chat_history` que no existía y un índice que ya había sido eliminado en una migración anterior. La solución implicó modificar la migración para eliminar las operaciones problemáticas y aplicar manualmente los cambios necesarios, preservando la tabla `langchain_chat_history` según la solicitud del usuario.

- **Modificación de la migración**: Se eliminaron las líneas que intentaban eliminar la tabla `langchain_chat_history` y el índice `ix_analyzed_pairs_document_ids` de la migración `40a71dbe5a5d_añadir_campo_status_a_la_tabla_task.py`, ya que estas operaciones no eran necesarias y causaban errores.
- **Adición manual del campo status**: Se ejecutó directamente el comando SQL `ALTER TABLE tasks ADD COLUMN status VARCHAR(50)` para añadir el campo status a la tabla tasks.
- **Actualización de la versión de Alembic**: Se actualizó la tabla `alembic_version` para marcar la migración como aplicada, completando el proceso de actualización de la base de datos.
---
## 18-11-2025 Actualización de alineación de botones de citación

### Descripción general:
Se solicitó corregir la alineación vertical de los botones de citación en el chat y asegurar la consistencia del tamaño de fuente. La solución implicó modificar `MarkdownRenderer` para envolver el texto y `SourceButton` en un contenedor `inline-flex` con `align-items: baseline;`, y ajustar las clases de `SourceButton` en `ChatMessage.tsx`.

- **Modificación en MarkdownRenderer.tsx**: Se envolvió la salida de `marked.parseInline` y `SourceButton` en un `<span>` con las clases `inline-flex` y `items-baseline` para mejorar la alineación vertical de los elementos en línea.
- **Modificación en ChatMessage.tsx**: Se eliminaron las clases de alineación redundantes (`align-middle`, `align-text-bottom`) y se aseguró que `SourceButton` tuviera la clase `text-xl` para coincidir con el tamaño de fuente. Se verificó que estos cambios ya estaban aplicados en el archivo.
---
## 18-11-2025 Corrección de Indentación en cognee_integration.py

### Descripción general:
Se identificó y corrigió un `IndentationError` en el archivo `knowledge_graph/cognee_integration.py` en la línea 1272. Este error impedía la correcta ejecución del módulo.

- **Punto 1**: Se ajustó la indentación de los bucles `for node in path_object.nodes:` y `for rel in path_object.relationships:` dentro del método `_format_advanced_search_results` para asegurar la correcta anidación y sintaxis de Python.
---
## 18-11-2025 Reubicación del Acceso al Módulo de Análisis

### Descripción general:
Se modificó la página de Colecciones de Conocimientos (`rag/page.tsx`) para reubicar el acceso al módulo de Análisis. Anteriormente, se accedía a través de un `DropdownMenu` global, pero ahora se ha implementado un botón dedicado de "Análisis" junto al botón "Subir Documento" en la parte superior derecha de la página.

- **Punto 1**: Se añadió un nuevo botón con el texto "Análisis" y el icono `ScanSearch` al lado del botón "Subir Documento".
- **Punto 2**: El nuevo botón de "Análisis" tiene un estilo idéntico al botón "Subir Documento" (azul, mismo tamaño, etc.).
- **Punto 3**: Se configuró el `onClick` del botón de "Análisis" para navegar a la ruta `/analysis`, proporcionando un acceso directo y visible al módulo de análisis global.
---
## 18-11-2025 Actualización de Icono y Estilo del Botón de Análisis

### Descripción general:
Se actualizó el botón de "Análisis" en la página de Colecciones de Conocimientos (`rag/page.tsx`) para que su icono y estilo coincidan con las convenciones del proyecto.

- **Punto 1**: Se cambió el icono del botón de "Análisis" de `ScanSearch` a `BarChart3` para alinearse con el icono utilizado en el `Sidebar.tsx` para la sección de "Análisis".
- **Punto 2**: Se ajustaron las clases CSS del botón de "Análisis" para que su color y apariencia sean idénticos a los del botón "Subir Documento", utilizando `bg-primary hover:bg-primary/90`.
---
## 18-11-2025 Corrección de Importación de Icono en rag/page.tsx

### Descripción general:
Se corrigió un `ReferenceError` (`BarChart3 is not defined`) en `src/app/(dashboard)/rag/page.tsx` añadiendo la importación faltante del componente `BarChart3` de `lucide-react`.

- **Punto 1**: Se añadió `BarChart3` a la lista de importaciones de `lucide-react` en la parte superior del archivo `rag/page.tsx`.
---
## 18-11-2025 Eliminación del Acceso al Módulo de Análisis del Sidebar

### Descripción general:
Se eliminó el enlace directo al módulo de "Análisis" del `Sidebar.tsx`, ya que ahora se accede a esta funcionalidad a través de un botón dedicado en la página de Colecciones de Conocimientos (`rag/page.tsx`).

- **Punto 1**: Se eliminó el componente `Link` y su `Button` asociado que dirigían a la ruta `/analysis` del `Sidebar.tsx`.
---
## 18-11-2025 Configuración de Faster Whisper para GPU con Fallback a CPU

### Descripción general:
Se modificó `utils/audio_transcriber.py` para mejorar la robustez en la carga del modelo Faster Whisper, permitiendo el uso de GPU (`cuda`) si está disponible y configurado correctamente, con un fallback automático a CPU en caso de fallo o indisponibilidad de la GPU.

- **Punto 1**: Se añadió la importación de `torch` para verificar dinámicamente la disponibilidad de CUDA (`torch.cuda.is_available()`).
- **Punto 2**: La función `load_whisper_model` ahora determina el dispositivo (`cuda` o `cpu`) y el `compute_type` (`int8` para GPU, `float32` para CPU) de forma dinámica.
- **Punto 3**: Se implementó un bloque `try-except` para intentar cargar el modelo en el dispositivo determinado y, si falla en GPU, se realiza un segundo intento en CPU con `compute_type="float32"`.
- **Punto 4**: La función `get_whisper_model` ahora utiliza `asyncio.get_running_loop().run_in_executor(None, load_whisper_model)` para ejecutar la carga del modelo en un hilo separado, evitando bloquear el event loop principal de la aplicación asíncrona.
---
## 18-11-2025 Habilitación de Acceso a GPU para el Servicio Core en Docker Compose

### Descripción general:
Se modificó el archivo `docker-compose.yml` para habilitar explícitamente el acceso a la GPU para el servicio `kognito_core`. Esto permitirá que el modelo Faster Whisper y otras operaciones que puedan beneficiarse de la aceleración por hardware utilicen la GPU del sistema host.

- **Punto 1**: Se añadió la sección `deploy.resources.reservations.devices` al servicio `core` en `docker-compose.yml`.
- **Punto 2**: Se configuró el `driver` como `nvidia`, `count` como `all` (para usar todas las GPUs disponibles) y `capabilities` como `[gpu]` para asegurar que Docker asigne los recursos de GPU al contenedor.
---
## 18-11-2025 Ajuste de Tamaño de Fuente en Sidebar.tsx

### Descripción general:
Se ajustó el tamaño de la fuente en el componente `Sidebar.tsx` para mejorar la legibilidad general de los elementos de la barra lateral, manteniendo los nombres de los chats ligeramente más pequeños según la solicitud del usuario.

- **Punto 1**: Se cambiaron todas las ocurrencias de la clase `text-xs` a `text-sm` en los elementos de la barra lateral, como los títulos de las secciones y los nombres de las herramientas.
- **Punto 2**: Se cambiaron la mayoría de las ocurrencias de la clase `text-sm` a `text-base` para los elementos principales de la barra lateral, como los nombres de usuario y los títulos de las secciones.
- **Punto 3**: Se mantuvo el tamaño de la fuente de los nombres de los chats en `text-sm` para que fueran ligeramente más pequeños que el resto de los elementos principales, atendiendo a la solicitud específica del usuario.
---
## 18-11-2025 Corrección de Persistencia de Fuentes en el Agente

### Descripción general:
Se corrigió un problema en `core/agent.py` donde las fuentes de las notas (y otras fuentes RAG) se perdían o eran reemplazadas en el flujo del agente, especialmente después de una llamada a herramienta. La modificación asegura que las fuentes persistan correctamente en el estado del agente a lo largo de las iteraciones y se entreguen al usuario final.

- **Punto 1**: En el nodo `call_model_node`, la variable `final_sources_for_state` ahora se inicializa con las fuentes existentes en el estado (`state.get('sources', [])`) en lugar de una lista vacía.
- **Punto 2**: Se ajustó la lógica dentro de `call_model_node` para que, si el agente regresa de una llamada a herramienta (`is_after_tool_call` es `True`), no se ejecute una nueva búsqueda RAG inicial. En su lugar, se utilizan las `final_sources_for_state` existentes (que ya habrían sido actualizadas por `tool_node` si la herramienta generó fuentes) para construir el `relevant_memories_text` y para adjuntarlas al `final_ai_message`.
- **Punto 3**: Se aseguró que el `final_ai_message` siempre adjunte las `final_sources_for_state` acumuladas, garantizando que todas las fuentes relevantes (tanto RAG iniciales como de herramientas) lleguen al usuario.
---
## 18-11-2025 Añadir Botón de Navegación a Página de Análisis

### Descripción general:
Se añadió un botón de "volver atrás" en la página de análisis (`src/app/(dashboard)/analysis/page.tsx`) para facilitar la navegación del usuario de regreso a la página de colecciones RAG (`src/app/(dashboard)/rag/page.tsx`).

- **Punto 1**: Se insertó un componente `Button` con un icono `ArrowLeft` al inicio de la cabecera de la página de análisis.
- **Punto 2**: El botón utiliza `router.push('/rag')` para redirigir al usuario a la página de colecciones RAG.
- **Punto 3**: Se añadió `ArrowLeft` a la importación de `lucide-react` en el archivo `src/app/(dashboard)/analysis/page.tsx`.
---
## 18-11-2025 Añadir Endpoint para Vincular Nota a Workspace

### Descripción general:
Se añadió un nuevo endpoint en `api/notes.py` (`/notes/{note_id}/link-to-workspace`) para proporcionar una forma explícita y semántica de vincular una nota a un workspace. Esto clarifica la API y ayuda a evitar confusiones con la operación de desvinculación.

- **Punto 1**: Se definió un nuevo modelo Pydantic `LinkNoteToWorkspaceRequest` para recibir el `workspace_id` de destino.
- **Punto 2**: Se creó el endpoint `@router.post("/notes/{note_id}/link-to-workspace")` que recibe el `note_id` y el `workspace_id` en el cuerpo de la solicitud.
- **Punto 3**: Se realizan verificaciones de permisos para asegurar que el usuario tiene autorización para vincular notas al workspace de destino.
- **Punto 4**: El endpoint llama a `notes_manager.update_note` con el `note_id` y el `new_workspace_id` proporcionado para realizar la vinculación.
---
## 19-11-2025 Corrección de Renderizado de Fuentes de Grafo y Notas

### Descripción general:
Se abordó un problema donde las fuentes de tipo 'graph' y 'note' no se renderizaban correctamente en el frontend, especialmente en el componente `SourceButton.tsx`. Las URLs de las fuentes de grafo no eran consistentes, y el componente `SourceButton.tsx` no manejaba el tipo 'graph' en su interfaz ni en la lógica de navegación.

- **Actualización en SourceButton.tsx**:
    - Se añadió `'graph'` al tipo de la propiedad `type` en la interfaz `Source` para asegurar una tipificación correcta.
    - Se implementó la lógica para manejar URLs con el prefijo `graph://` en la sección de `source.url`, similar a cómo se manejan las URLs `note://`, permitiendo la navegación a `/graphs/{id_del_grafo}`.
- **Actualización en agent.py**:
    - Se modificó la creación de fuentes de tipo `graph` en el nodo `call_model_node` para que sus URLs utilicen un prefijo `graph://` consistente (ej. `graph://insight_{id}` o `graph://path_{id}`), facilitando su interpretación y manejo en el frontend.
    - Se ajustó la lógica de manejo de fuentes en el `tool_node` para dar prioridad a las fuentes devueltas por una herramienta. Si una herramienta (como `search_notes_tool`) proporciona fuentes, estas reemplazarán por completo cualquier fuente existente de la búsqueda RAG inicial, evitando así que las fuentes de notas sean sobrescritas por las de grafos.
---
## 19-11-2025 Eliminación de la dependencia 'davpy'

### Descripción general:
Se eliminó la dependencia `davpy` del archivo `requirements.txt` debido a problemas de compatibilidad con la versión de Python utilizada en la imagen Docker `nvcr.io/nvidia/pytorch:23.09-py3`. Tras una investigación, se determinó que `davpy` no es una dependencia crítica y su eliminación no afecta la funcionalidad principal del proyecto.

- **Eliminación de 'davpy'**: Se quitó la línea `davpy` de `requirements.txt`.