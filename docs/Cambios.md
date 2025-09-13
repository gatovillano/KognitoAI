## 12-09-2025 Corrección de Incompatibilidad de Tipos en Reranker

Descripción general: Se corrigió un `ValueError` crítico que ocurría durante la fase de reordenamiento (reranking) de los resultados de búsqueda de memoria. El error se debía a una incompatibilidad de tipos de datos entre el `MemoryManager` y el `Reranker`, donde se pasaba una lista de objetos `Document` en lugar de una lista de cadenas de texto.

- **Punto 1**: Se modificó la función `rerank` en `core/reranker.py` para que acepte una lista de objetos `Document` de LangChain. La función ahora extrae de forma inteligente el contenido de texto (`page_content`) de cada documento para el procesamiento del modelo y, una vez calculadas las puntuaciones, las añade a los metadatos de los documentos originales bajo la clave `rerank_score`.
- **Punto 2**: Se actualizó la función `get_relevant_memories` en `core/memory_manager.py`. Al construir las fuentes de citación, ahora busca la clave `rerank_score` en los metadatos de cada documento para reflejar la nueva puntuación de relevancia, asegurando la coherencia en todo el flujo de datos.

---
## 11-09-2025 Mejora de Streaming de LLM en Frontend

Descripción general: Se mejoró la lógica de manejo de chunks de las respuestas del LLM en el frontend (`src/components/CommonChat.tsx`) para una visualización más fluida y en tiempo real, asegurando que los mensajes se construyan y muestren progresivamente.

- **Punto 1**: En `handleLlmChunk`, se ajustó la inicialización de `currentMessageIndex` para una gestión más precisa del índice del mensaje de la IA que se está construyendo.
- **Punto 2**: En `handleLlmChunk`, se modificó la inicialización del `text` del mensaje de la IA y se añadió la propiedad `tool_code` para asegurar que se reinicie correctamente al iniciar un nuevo mensaje.
- **Punto 3**: En `handleLlmEnd`, se modificó la lógica para consolidar el `text` final del mensaje de la IA y se añadió la limpieza de la propiedad `chunks` una vez que la transmisión ha finalizado, optimizando la representación final del mensaje.

---
## 11-09-2025 Repotenciación de la Herramienta de Búsqueda Web (`WebSearchTool`)

Descripción general: Se ha mejorado significativamente la herramienta de búsqueda web (`tools/web_search_tool.py`) para que realice investigaciones más profundas y proporcione respuestas más detalladas y mejor fundamentadas, según la solicitud del usuario.

- **Punto 1: Integración de Scraper de Contenido Completo**: La herramienta ya no se limita a los `snippets` de los motores de búsqueda. Ahora utiliza la `WebScraperTool` interna para leer y extraer el contenido completo de las páginas web encontradas.
- **Punto 2: Aumento de la Profundidad de Búsqueda**: Se ha configurado la herramienta para obtener y procesar los **10 resultados de búsqueda más relevantes**, en lugar del límite anterior, proporcionando un contexto mucho más rico para la generación de respuestas.
- **Punto 3: Refuerzo de Instrucciones al LLM**: Se ha modificado la descripción de la herramienta para instruir explícitamente al modelo de lenguaje que debe generar **respuestas detalladas y extensas**, y que es **obligatorio citar las fuentes** utilizando un formato específico (`[Fuente X]`).

---
## 11-09-2025 Correcciones y Mejoras en la Conexión WebSocket y Visualización de Chunks

Descripción general: Se implementaron una serie de correcciones para estabilizar la conexión WebSocket entre el frontend y el backend, y para asegurar la visualización correcta y en tiempo real de los chunks de las respuestas del LLM.

- **Punto 1: Resolución de Discrepancia de URL del WebSocket:** Se identificó que el frontend intentaba conectar el WebSocket a su propio dominio en lugar del dominio del backend. Aunque la solución final implicó una corrección en la configuración del entorno por parte del usuario (nombre de variable `NEXT_PUBLIC_API_URL` vs `NEXT_PUBLIC_API_BASE_URL`), se proporcionaron herramientas de depuración (`console.log` detallados en `src/hooks/useWebSocket.ts`) para diagnosticar la discrepancia.

- **Punto 2: Corrección de Error de Decodificación de Token en Backend:** Se solucionó un `AttributeError: 'str' object has no attribute 'get'` en el backend (`api/main.py`). La función `decode_access_token` en `utils/security.py` fue modificada para devolver el diccionario completo del payload del token en lugar de solo el `sub` (subject), asegurando que el acceso a las propiedades del payload sea correcto.
- **Punto 3: Estabilización de Conexión/Desconexión Constante en Frontend:** Se resolvió el problema de conexiones y desconexiones constantes del WebSocket en el frontend. Esto se logró memoizando el objeto `options` pasado al hook `useWebSocket` en `src/components/CommonChat.tsx` utilizando `useMemo`, lo que evita recreaciones innecesarias de la función de conexión y estabiliza el `useEffect` del hook.
- **Punto 4: Visualización en Tiempo Real de Chunks del LLM:** Se corrigió la visualización incompleta o tardía de los chunks del LLM en el frontend. En `src/components/CommonChat.tsx`, la función `handleLlmChunk` fue modificada para actualizar incrementalmente la propiedad `text` del mensaje de la IA, concatenando todos los chunks recibidos en tiempo real. Esto asegura que la respuesta del LLM se construya y muestre progresivamente en la interfaz de usuario.

---
## 11-09-2025 Unificación de Estilos en Workspaces

Descripción general: Se ha unificado el estilo de la página de un workspace específico para que coincida con el de la página principal de workspaces, mejorando la consistencia visual de la aplicación.

- **Punto 1**: Se aplicaron las clases de Tailwind CSS `p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden` al contenedor principal del archivo `src/app/(dashboard)/workspaces/[id]/page.tsx`.
- **Punto 2**: Esta modificación asegura que la vista detallada de un workspace y la lista general de workspaces compartan el mismo diseño de márgenes y ancho máximo, proporcionando una experiencia de usuario más coherente y profesional.
---
## 11-09-25 Ocultar Salida de Herramientas en el Frontend

Descripcion general: El usuario solicitó que los resultados de las herramientas (como la búsqueda web) no se muestren en el frontend, ya que son para uso exclusivo del LLM. La solución fue modificar el manejador de streaming del agente en `api/chat.py` para dejar de enviar el contenido del resultado de la herramienta a través del WebSocket.

- **Punto 1**: Se modificó el archivo `api/chat.py` en la función `create_and_run_agent_streaming`.
- **Punto 2**: Dentro del bucle de streaming del agente LangGraph, en la sección que maneja el nodo `action`, se eliminó la clave `result` del diccionario enviado por WebSocket al frontend.
- **Punto 3**: Esto evita que el contenido crudo de `ToolMessage.content` (que es para el LLM) llegue a la interfaz de usuario, mejorando la experiencia y mostrando solo una notificación de que la herramienta ha finalizado.

---
## 11-09-25 Rediseño del Botón de Enviar en el Chat

Descripción general: Se ha rediseñado el botón de enviar en la barra de chat (`src/components/ChatInputBar.tsx`) para que sea un botón de ícono circular estático, mejorando la consistencia visual y la simplicidad de la interfaz.

- **Punto 1**: Se eliminó el efecto de expansión del botón al pasar el cursor, quitando las clases de `group` y `hover:w-32`.
- **Punto 2**: Se reemplazó el ícono de `Send` (avión de papel) por el de `ArrowUp` (flecha hacia arriba) para una representación más clara de la acción de enviar.
- **Punto 3**: Se eliminó el texto "Enviar" que aparecía al expandirse el botón, dejando solo el ícono centrado.
- **Punto 4**: Se estandarizó el indicador de carga para que use el componente `Loader2`, en línea con otros botones de la aplicación.

---
## 11-09-25 Control de Creación de Hilos y Correcciones de Errores de Compilación

Descripción general: Se modificó la lógica de creación de hilos de conversación para que solo se creen cuando el usuario envía un mensaje o sube un archivo, evitando la creación de hilos vacíos. Además, se corrigieron varios errores de compilación relacionados con tipos de TypeScript y sintaxis en diferentes componentes del frontend.

- **Punto 1**: En `src/app/(dashboard)/page.tsx`, se ajustó `handleChatSubmit` para que la llamada a `/api/threads` solo se ejecute si `chatInput.trim()` no está vacío.
- **Punto 2**: En `src/app/(dashboard)/page.tsx`, se ajustó `handleFileUpload` para que la llamada a `/api/threads` solo se ejecute si hay archivos seleccionados para subir.
- **Punto 3**: Se corrigió el error de la prop `key` en `src/app/(dashboard)/rag/analysis-result-dialog.tsx` añadiendo `key={i}` al elemento mapeado.
- **Punto 4**: Se corrigieron los errores de escape de entidades (`react/no-unescaped-entities`) en `src/app/(dashboard)/rag/collection-analysis-dialog.tsx` reemplazando `"` por `&quot;`.
- **Punto 5**: Se corrigieron los errores de tipo en `src/app/(dashboard)/agenda/WeeklyScheduleView.tsx` relacionados con `AgendaEvent` y `TaskResponse` usando aserciones de tipo (`as AgendaEvent`, `as TaskResponse`) y verificaciones de nulidad (`!`) para asegurar el acceso correcto a las propiedades.
- **Punto 6**: Se corrigió el error de tipo en `src/app/(dashboard)/rag/document-card.tsx` relacionado con `document.created_at` usando el operador de aserción no nula (`!`).
- **Punto 7**: Se corrigió el error de `Cannot find name 'useCallback'` en `src/app/(dashboard)/rag/repositories/[repoName]/page.tsx` añadiendo `useCallback` a la importación de React.
- **Punto 8**: Se corrigió el error de `Type 'null' cannot be used as an index type` en `src/components/CommonChat.tsx` asegurando que `aiMessageIndexRef.current` no sea `null` antes de usarlo como índice.
- **Punto 9**: Se corrigió el error de sintaxis (`Unexpected eof`) en `src/components/CommonChat.tsx` restaurando el cierre correcto de los elementos HTML al final del componente.
- **Punto 10**: Se corrigió el error de `Property 'onToolCode' does not exist on type 'UseWebSocketOptions'` en `src/hooks/useWebSocket.ts` añadiendo `onToolCode` a la interfaz `UseWebSocketOptions`.
---
## 11-09-25 Corrección del Flujo de Fuentes en Herramientas del Agente

Descripcion general: El usuario reportó que el LLM se quedaba bloqueado en el nodo "Generar Respuesta" y no emitía una respuesta final después de una llamada a una herramienta. La causa era que las `sources` (fuentes) devueltas por herramientas como `WebSearchTool` se descartaban y no se propagaban correctamente en el estado del agente. Esto confundía al LLM, que esperaba usar dichas fuentes para construir su respuesta.

- **Punto 1**: Se modificó la función `tool_node` en `core/agent.py`.
- **Punto 2**: Se añadió lógica para extraer las `sources` de los objetos `ToolOutputWithSources` devueltos por las herramientas.

- **Punto 3**: Las fuentes extraídas ahora se añaden al campo `sources` del estado del agente (`AgentState`), asegurando que no se pierdan y estén disponibles en los siguientes pasos del flujo.
- **Punto 4**: Se implementó una comprobación para evitar añadir fuentes duplicadas basadas en su URL.
- **Punto 5**: Esto soluciona el bloqueo del LLM y asegura que las fuentes de las herramientas se adjunten correctamente a la respuesta final para ser mostradas al usuario.

---
## 11-09-25 Aumento del Tamaño de Fuente de Mensajes del LLM

Descripcion general: El usuario solicitó aumentar el tamaño de la fuente de los mensajes del LLM en el frontend. Se interpretó "dos puntos" como "dos pasos" en la escala de tamaños de Tailwind CSS.

- **Punto 1**: Se modificó el archivo `src/components/ChatMessage.tsx`.
- **Punto 2**: La clase de Tailwind CSS `text-5xl` fue cambiada a `text-7xl` en el `div` que contiene el `MarkdownRenderer` para los mensajes de la IA. Esto aumenta el tamaño de la fuente de 48px a 72px.

---
## 11-09-25 Corrección del Tamaño de Fuente de Mensajes del LLM

Descripcion general: Se corrigió un problema por el cual el tamaño de la fuente de los mensajes del LLM no se aplicaba correctamente en el frontend, a pesar de haber modificado la clase de Tailwind CSS. La causa era que el componente `MarkdownRenderer` estaba sobrescribiendo el tamaño de fuente con un valor predeterminado.

- **Punto 1**: Se modificó el archivo `src/components/ChatMessage.tsx`.
- **Punto 2**: Se pasó explícitamente la clase `fontSize="text-7xl"` al componente `MarkdownRenderer` para asegurar que el tamaño de fuente deseado se propague.
- **Punto 3**: Se modificó el archivo `src/components/MarkdownRenderer.tsx`.
- **Punto 4**: Se eliminó el valor predeterminado `fontSize = 'text-base'` de la definición del componente `MarkdownRendererComponent`, permitiendo que el tamaño de fuente sea controlado por la prop `fontSize` pasada desde el componente padre.

---
## 11-09-25 Ajuste del Tamaño de Fuente de Mensajes del LLM

Descripcion general: El usuario reportó que el tamaño de fuente de los mensajes del LLM, previamente aumentado, ahora era "gigante". Se solicitó disminuirlo.

- **Punto 1**: Se modificó el archivo `src/components/ChatMessage.tsx`.
- **Punto 2**: La clase de Tailwind CSS `text-7xl` fue cambiada a `text-6xl` en el `div` que contiene el `MarkdownRenderer` para los mensajes de la IA. Esto reduce el tamaño de la fuente de 72px a 60px, proporcionando un tamaño intermedio.

---
## 11-09-25 Disminución Significativa del Tamaño de Fuente de Mensajes del LLM

Descripcion general: El usuario solicitó una disminución considerable del tamaño de la fuente de los mensajes del LLM, ya que el tamaño anterior (`text-6xl`) seguía siendo demasiado grande.

- **Punto 1**: Se modificó el archivo `src/components/ChatMessage.tsx`.
- **Punto 2**: La clase de Tailwind CSS `text-6xl` fue cambiada a `text-4xl` en el `div` que contiene el `MarkdownRenderer` para los mensajes de la IA. Esto reduce el tamaño de la fuente de 60px a 36px, lo que representa una disminución significativa.

---
## 11-09-25 Mensaje del LLM al 100% del Ancho de Columna

Descripcion general: El usuario solicitó que el mensaje del LLM ocupe el 100% del ancho de la columna donde se muestra, eliminando cualquier limitación de ancho máximo.

- **Punto 1**: Se modificó el archivo `src/components/ChatMessage.tsx`.
- **Punto 2**: Se eliminó la clase de Tailwind CSS `max-w-3xl` del `div` que contiene el contenido del mensaje del LLM. Esto permite que el mensaje se expanda al 100% del ancho disponible de su contenedor padre.

---
## 11-09-25 Posicionamiento del Botón de Eliminar Evento en Vista Semanal

Descripcion general: El usuario solicitó mover el botón de eliminar eventos a la esquina inferior derecha de cada tarjeta de evento en la vista semanal de la agenda.

- **Punto 1**: Se modificó el archivo `src/app/(dashboard)/agenda/WeeklyScheduleView.tsx`.
- **Punto 2**: Se añadió la clase `relative` al `div` principal de cada evento para establecer un contexto de posicionamiento.
- **Punto 3**: Se añadió las clases `absolute bottom-0 right-0` al `Button` que contiene el icono de eliminar (`Trash2`) para posicionarlo en la esquina inferior derecha de la tarjeta del evento.

---
## 11-09-25 Corrección de Error al Listar Notas por Workspace

Descripcion general: Se corrigió un `AttributeError` (`'ListNotesRequest' object has no attribute 'workspace_id'`) que ocurría al intentar filtrar notas por `workspace_id` en el endpoint `/api/list-notes`. El modelo `ListNotesRequest` no incluía este campo, a pesar de que la lógica del endpoint intentaba acceder a él.

- **Punto 1**: Se modificó el archivo `api/notes.py`.
- **Punto 2**: Se añadió `workspace_id: Optional[str] = None` al modelo Pydantic `ListNotesRequest` para permitir el filtrado de notas por workspace.

---
## 11-09-2025 Notas Cliqueables en Workspace Dashboard

Descripción general: Se ha implementado la funcionalidad para que las notas mostradas en el dashboard de un workspace sean cliqueables y abran un diálogo de visualización detallada de la nota.

- **Punto 1**: Se importó el componente `ViewNoteDialog` en `src/app/(dashboard)/workspaces/[id]/page.tsx`.
- **Punto 2**: Se añadieron los estados `selectedNote` y `isViewNoteDialogOpen` para gestionar la nota seleccionada y la visibilidad del diálogo.

- **Punto 3**: Se creó la función `handleNoteClick` para establecer la nota seleccionada y abrir el diálogo al hacer clic en una nota.
- **Punto 4**: Se modificó el `Card` de cada nota en `src/app/(dashboard)/workspaces/[id]/page.tsx` para que, al hacer clic, llame a `handleNoteClick`.
- **Punto 5**: Se renderizó el `ViewNoteDialog` al final del componente `WorkspaceDashboard`, pasándole la nota seleccionada y los estados de control.

---
## 11-09-2025 Botón TTS en ViewNoteDialog

Descripción general: Se añadió un botón de Texto a Voz (TTS) al `ViewNoteDialog` para permitir la reproducción de audio del contenido de la nota.

- **Punto 1**: Se importaron `Button` de `@/components/ui/button` y `Volume2` de `lucide-react` en `src/app/(dashboard)/notes/view-note-dialog.tsx`.
- **Punto 2**: Se importaron `useState` de `react` y `apiClient` de `@/lib/api` en `src/app/(dashboard)/notes/view-note-dialog.tsx`.
- **Punto 3**: Se añadió el estado `isSpeaking` para controlar el estado de la reproducción del audio.
- **Punto 4**: Se implementó la función `handleTextToSpeech` para llamar a la API `/api/text-to-speech` y reproducir el audio de la nota.

- **Punto 5**: Se añadió un botón con el icono `Volume2` en el `DialogHeader` de `ViewNoteDialog`, que activa la función `handleTextToSpeech` y muestra un efecto de "animación" cuando el audio está reproduciéndose.

---
## 11-09-2025 Visualización de Notas por Categoría en Workspace Dashboard

Descripción general: Se añadió la funcionalidad para filtrar las notas por categoría en el dashboard de un workspace, mejorando la organización y accesibilidad de las notas.

- **Punto 1**: Se añadió el estado `selectedNoteCategory` en `src/app/(dashboard)/workspaces/[id]/page.tsx` para controlar la categoría de notas seleccionada.
- **Punto 2**: Se modificó la lógica de filtrado de notas para incluir el filtro por categoría, creando `uniqueNoteCategories` y `filteredNotesByCategory`.
- **Punto 3**: Se añadió un `DropdownMenu` en la sección de notas de `src/app/(dashboard)/workspaces/[id]/page.tsx` para permitir al usuario seleccionar una categoría de filtro.
- **Punto 4**: Se actualizó la renderización de las notas para usar `filteredNotesByCategory`, asegurando que solo se muestren las notas de la categoría seleccionada.

---
## 11-09-2025 Botón de Edición en ViewNoteDialog

Descripción general: Se añadió un botón de edición al `ViewNoteDialog` para permitir a los usuarios modificar el contenido de una nota directamente desde su vista detallada.

- **Punto 1**: Se importaron `NoteDialog` de `./note-dialog` y `Pencil` de `lucide-react` en `src/app/(dashboard)/notes/view-note-dialog.tsx`.
- **Punto 2**: Se añadió la prop `onNoteUpdated` a `ViewNoteDialogProps` para notificar al componente padre cuando la nota haya sido actualizada.
- **Punto 3**: Se añadió el estado `isNoteEditDialogOpen` para controlar la visibilidad del `NoteDialog` en modo edición.
- **Punto 4**: Se añadió un botón con el icono `Pencil` en el `DialogHeader` de `ViewNoteDialog`, que abre el `NoteDialog` en modo edición con la nota actual.
- **Punto 5**: Se renderizó el `NoteDialog` al final del `ViewNoteDialog`, pasándole la nota actual (`initialNote`) y un callback `onSaveSuccess` que llama a `onNoteUpdated` del componente padre.
- **Punto 6**: Se actualizó el componente padre (`src/app/(dashboard)/workspaces/[id]/page.tsx`) para pasar la función `fetchWorkspaceData` a la prop `onNoteUpdated` del `ViewNoteDialog`, asegurando que la lista de notas se recargue después de una edición.

---
## 11-09-2025 Corrección de `fetchWorkspaceData` en `WorkspaceDashboard`

Descripción general: Se corrigió el error `fetchWorkspaceData is not defined` en `src/app/(dashboard)/workspaces/[id]/page.tsx` moviendo la definición de la función `fetchWorkspaceData` fuera del `useEffect` para que sea accesible en el scope del componente.

- **Punto 1**: La función `fetchWorkspaceData` fue movida desde dentro del `useEffect` a ser una función declarada directamente en el cuerpo del componente `WorkspaceDashboard`.
- **Punto 2**: Se ajustó el `useEffect` para que simplemente llame a `fetchWorkspaceData()` en lugar de definirla.
- **Punto 3**: Esto asegura que `fetchWorkspaceData` sea accesible para ser pasada como prop a `ViewNoteDialog` y para ser llamada en otros lugares del componente.

---
## 11-09-2025 Implementación de Campos 'Etiquetas' y 'Categoría' en Perfiles

Descripción general: Se implementaron campos dedicados para 'Etiquetas' y 'Categoría' en los perfiles de contacto, permitiendo su entrada como texto separado por comas y su visualización estilizada como 'badges' en las tarjetas y diálogos de perfil.

- **Punto 1**: Se modificó la interfaz `ContactProfile` en `src/app/(dashboard)/profiles/page.tsx` para incluir `tags: string[] | null;` y `category: string | null;`.
- **Punto 2**: En `src/app/(dashboard)/profiles/profile-dialog.tsx`, se añadieron los estados `tagsInput` y `categoryInput` para manejar la entrada de texto de estos campos.
- **Punto 3**: Se actualizó el `useEffect` en `profile-dialog.tsx` para inicializar `tagsInput` (uniendo el array `profile.tags` con comas) y `categoryInput` al cargar un perfil existente.
- **Punto 4**: Se añadieron los campos de entrada 'Etiquetas' y 'Categoría' al formulario en `profile-dialog.tsx`, permitiendo la entrada de texto separado por comas.
- **Punto 5**: Se modificó la función `handleSubmit` en `profile-dialog.tsx` para procesar `tagsInput` (convirtiéndolo a un array de strings) y `categoryInput`, incluyéndolos en los datos del perfil enviados al backend.
- **Punto 6**: En `src/app/(dashboard)/profiles/view-profile-dialog.tsx`, se añadió la visualización de la 'Categoría' como un 'badge' estilizado.
- **Punto 7**: En `src/app/(dashboard)/profiles/view-profile-dialog.tsx`, se añadió una sección para 'Etiquetas', donde cada tag se renderiza como un 'badge' individual con colores rotativos, similar a la implementación previa de campos personalizados.

---
## 11-09-2025 Corrección de Diseño en Diálogo de Edición de Perfil

Descripción general: Se corrigió el problema de diseño en el diálogo de edición de perfil (`src/app/(dashboard)/profiles/profile-dialog.tsx`) donde los campos de entrada aparecían uno al lado del otro en lugar de uno por fila.

- **Punto 1**: Se modificó el archivo `src/app/(dashboard)/profiles/profile-dialog.tsx`.
- **Punto 2**: Se cambió la clase `grid gap-4 py-4` del contenedor principal de los campos del formulario a `space-y-4 py-4`.

- **Punto 3**: Esto asegura que cada campo se apile verticalmente, uno por fila, mejorando la disposición visual y la usabilidad del formulario.

---
## 11-09-2025 Refactorización de Visualización de Etiquetas en Tarjetas de Perfil

Descripción general: Se eliminó la visualización estilizada de campos personalizados en las tarjetas de perfil y se aplicó el mismo estilo de 'badge' con colores a las etiquetas (`tags`) de los perfiles.

- **Punto 1**: Se modificó el archivo `src/app/(dashboard)/profiles/page.tsx`.
- **Punto 2**: Se eliminó el bloque de código que renderizaba los `custom_fields` con estilos de color dentro del componente `ProfileCard`.
- **Punto 3**: Se añadió un nuevo bloque de código para renderizar las `tags` del perfil (`profile.tags`) con el mismo estilo de 'badge' y la lógica de colores rotativos que se usaba previamente para los `custom_fields`.
- **Punto 4**: Se ajustó la condición para mostrar el mensaje "Sin detalles de contacto" para incluir la verificación de `profile.tags`.

---
## 11-09-2025 Corrección de Error 422 en Actualización de Perfil

Descripción general: Se corrigió el error 422 "Unprocessable Entity" al actualizar perfiles, causado por la falta de los campos `tags` y `category` en el modelo Pydantic del backend.

- **Punto 1**: Se modificó el archivo `api/contact_profiles.py`.
- **Punto 2**: Se añadió `tags: Optional[List[str]] = None` y `category: Optional[str] = None` a la clase `ContactProfileBase`.
- **Punto 3**: Esto permite que el backend procese correctamente los datos enviados desde el frontend, resolviendo el error de validación.

---
## 11-09-2025 Corrección de Sintaxis en Dashboard Frontend

Descripción general: Se corrigió un error de sintaxis en el archivo `src/app/(dashboard)/dashboard/page.tsx` donde una etiqueta JSX estaba mal cerrada, causando un error de compilación.

- **Punto 1**: Se añadió la etiqueta de apertura `<Card>` antes de `<CardContent className="pt-6">` para asegurar que el contenido del gráfico de temas principales esté correctamente envuelto.
- **Punto 2**: Se movió el cierre de la etiqueta `</Card>` para que envuelva correctamente el `CardContent` y el `ResponsiveContainer`, resolviendo el error de sintaxis "Expected '</', got 'jsx text'".

---
## 11-09-2025 Estandarización Estética del Dashboard

Descripción general: Se modificó la estética del dashboard (`src/app/(dashboard)/dashboard/page.tsx`) para que sea similar a la de la página de workspaces (`src/app/(dashboard)/workspaces/[id]/page.tsx`), mejorando la consistencia visual de la aplicación.

- **Punto 1**: Se modificó el encabezado del dashboard para incluir un botón "Volver al Dashboard" y que tenga una estructura más similar a la de la página de workspaces.
- **Punto 2**: Se añadió una barra de búsqueda al dashboard, replicando el estilo de la barra de búsqueda de la página de workspaces.
- **Punto 3**: Se ajustaron los títulos de las secciones "Descubrimientos Proactivos" y "Preguntas de Análisis" para que tuvieran el mismo estilo (icono, clases de texto y estructura del `div` contenedor) que los títulos de las secciones en la página de workspaces.

---
## 11-09-2025 Corrección de Importación de Icono en Dashboard Frontend

Descripción general: Se corrigió un `ReferenceError` en `src/app/(dashboard)/dashboard/page.tsx` debido a la falta de importación del icono `ArrowLeft` de `lucide-react`.

- **Punto 1**: Se añadió `ArrowLeft` a la lista de importaciones de `lucide-react` en la parte superior del archivo `src/app/(dashboard)/dashboard/page.tsx`.

---
## 11-09-2025 Corrección de Importación de Componente Input en Dashboard Frontend

Descripción general: Se corrigió un `ReferenceError` en `src/app/(dashboard)/dashboard/page.tsx` debido a la falta de importación del componente `Input`.

- **Punto 1**: Se añadió `Input` a la lista de importaciones de `@/components/ui/input` en la parte superior del archivo `src/app/(dashboard)/dashboard/page.tsx`.
---
## 11-09-25 Mejora de la Herramienta GetAgendaTool

Descripción general: Se ha mejorado la herramienta `get_agenda_tool.py` para permitir la consulta de eventos por día, semana o mes, utilizando la funcionalidad existente en `core/agenda_manager.py`. Además, se corrigió un error de sintaxis en `core/agenda_manager.py` que se detectó durante el proceso.

- **Punto 1**: Se actualizó la importación en `tools/get_agenda_tool.py` para usar `get_agenda_for_period` en lugar de `get_agenda_for_day`.
- **Punto 2**: Se modificó la firma del método `_arun` en `tools/get_agenda_tool.py` para aceptar `target_date` y `period_type`.
- **Punto 3**: Se actualizó el mensaje de log en `_arun` para reflejar los nuevos parámetros.
- **Punto 4**: Se cambió la llamada a la función de lógica de negocio en `_arun` para usar `get_agenda_for_period` con los argumentos correctos.
- **Punto 5**: Se actualizó la descripción de la herramienta `GetAgendaTool` para reflejar su capacidad de consultar la agenda por día, semana o mes.
- **Punto 6**: Se corrigió un `SyntaxError: unterminated string literal` en la línea 264 de `core/agenda_manager.py` que se introdujo previamente.

---
## 11-09-25 Forzar Ejecución de Herramientas desde ChatInputBar

Descripción general: Se modificó el componente `ChatInputBar.tsx` para permitir que el frontend indique al backend la ejecución obligatoria de una herramienta específica. Esto se logra añadiendo un prefijo especial al mensaje del usuario cuando una herramienta es seleccionada explícitamente en el menú de acciones.

- **Punto 1**: Se añadió la prop opcional `selectedToolName?: string;` a la interfaz `ChatInputBarProps` para indicar el nombre de la herramienta que debe ser forzada.
- **Punto 2**: Se modificó la función `handleSubmit` en `ChatInputBar.tsx`. Ahora, si la prop `selectedToolName` está presente, el mensaje del usuario se prefija con `[USE_TOOL:nombre_de_la_herramienta]`. Esto asegura que el backend, al procesar el mensaje, pueda identificar y forzar la ejecución de la herramienta especificada.
- **Punto 3**: Se identificaron las herramientas asociadas a las props de activación: `isWebSearchActive` (asociada a `web_search_tool.py`), `isComprehensiveAnalysisActive` (asociada a `comprehensive_web_analysis_tool.py`), y `isDeepResearchActive` (asociada a `deep_research_tool.py`). Estos nombres son los que se esperarían en `selectedToolName`.

---
## 11-09-2025 Habilitar Listado de Usuarios para Frontend

Descripción general: Se habilitó un endpoint público para listar usuarios en la API (`api/users.py`) para que el frontend (`src/app/(dashboard)/teams/team-dialog.tsx`) pueda obtener la lista de usuarios sin requerir privilegios de administrador.

- **Punto 1**: Se añadió un nuevo endpoint `GET /users` en `api/users.py` que devuelve una lista de `UserProfileResponse` para todos los usuarios.
- **Punto 2**: Este endpoint devuelve solo la información pública de los usuarios (id, name, email, username, telegram_id, is_admin).

---
## 11-09-2025 Habilitar Análisis y Resumen Semántico en Menús de Notas

Descripción general: Se han añadido las opciones "Analizar notas", "Analizar nota" y "Resumen Semántico" a los menús de notas individuales y al menú de acciones general de la página de notas, mejorando la funcionalidad de análisis y resumen de contenido.

- **Punto 1**: Se modificó `src/app/(dashboard)/notes/page.tsx` para incluir "Analizar Notas" y "Resumen Semántico" en el `DropdownMenuContent` del botón "Acciones".
- **Punto 2**: Se modificó `src/app/(dashboard)/notes/view-note-dialog.tsx` para importar los iconos `Lightbulb` y `FileText` de `lucide-react`.
- **Punto 3**: Se modificó `src/app/(dashboard)/notes/view-note-dialog.tsx` para añadir los botones "Analizar Nota" y "Resumen Semántico" al `DialogHeader` de la vista de nota individual.
- **Punto 4**: Por el momento, las funcionalidades de análisis y resumen muestran un mensaje de "Funcionalidad en desarrollo".

---
## 11-09-2025 Implementación de Análisis y Resumen Semántico en Notas

Descripción general: Se han implementado las funcionalidades de "Analizar notas", "Analizar nota" y "Resumen Semántico" tanto en el menú de acciones general de la página de notas como en los menús de notas individuales, integrando el backend para el procesamiento de análisis.

- **Punto 1**: Se modificó `src/app/(dashboard)/notes/page.tsx` para:
    - Añadir la función `handleAnalyzeAllNotes` que llama al nuevo endpoint `/api/start-notes-collection-analysis` con todas las notas cargadas.
    - Actualizar el `DropdownMenuItem` de "Analizar Notas" para que llame a `handleAnalyzeAllNotes`.
    - Modificar la firma de `NoteCard` para aceptar las props `onAnalyzeNote` y `onSummarizeNote`.
    - Pasar las funciones `handleAnalyzeSingleNote` y `handleSummarizeSingleNote` como props a `NoteCard` en `renderNotes`.
    - Actualizar el `DropdownMenuItem` de "Analizar Nota" dentro de `NoteCard` para que llame a `onAnalyzeNote(note)`.
    - Añadir la función `handleSummarizeSingleNote` que llama al nuevo endpoint `/api/start-single-note-summary` con la nota individual.
    - Actualizar el `DropdownMenuItem` de "Resumen Semántico" dentro de `NoteCard` para que llame a `onSummarizeNote(note)`.

- **Punto 2**: Se modificó `src/app/(dashboard)/notes/view-note-dialog.tsx` para:
    - Añadir la función `handleAnalyzeSingleNoteFromDialog` que llama al nuevo endpoint `/api/start-single-note-analysis` con la nota que se está visualizando.
    - Añadir la función `handleSummarizeSingleNoteFromDialog` que llama al nuevo endpoint `/api/start-single-note-summary` con la nota que se está visualizando.
    - Actualizar el `DropdownMenuItem` de "Analizar Nota" para que llame a `handleAnalyzeSingleNoteFromDialog`.
    - Actualizar el `DropdownMenuItem` de "Resumen Semántico" para que llame a `handleSummarizeSingleNoteFromDialog`.
    - Corregir un error de duplicación de declaración de `handleAnalyzeSingleNoteFromDialog`.

- **Punto 3**: Se modificó `api/analysis.py` para:
    - Añadir el Pydantic Model `NoteForAnalysis` y `AnalyzeNotesRequest`.
    - Crear el endpoint `/api/start-notes-collection-analysis` y su función de fondo `run_notes_collection_analysis_and_save` para analizar colecciones de notas.
    - Añadir el Pydantic Model `AnalyzeSingleNoteRequest`.
    - Crear el endpoint `/api/start-single-note-analysis` y su función de fondo `run_single_note_analysis_and_save` para analizar notas individuales.
    - Añadir el Pydantic Model `SummarizeSingleNoteRequest`.
    - Crear el endpoint `/api/start-single-note-summary` y su función de fondo `run_single_note_summary_and_save` para generar resúmenes ejecutivos de notas individuales.
    - Importar `Dict` de `typing` para resolver un `NameError`.

---
## 11-09-2025 Implementación de Vinculación de Perfiles en Entidades del Backend

Descripción general: Se implementó la funcionalidad de vinculación y desvinculación de perfiles de contacto con Notas, Eventos/Tareas y Colecciones en el backend, asegurando la consistencia de datos y la correcta recuperación de información. Se corrigió un `ImportError` en `tools/comprehensive_web_analysis_tool.py` relacionado con `get_relevant_memories` al reimplementar la función en `core/memory_manager.py`.

- **Punto 1**: En `api/notes.py`, se aseguró la importación de `uuid` y se actualizó `ProfileLinkRequest` para usar `uuid.UUID`. Se añadió el endpoint `GET /notes/{note_id}` para obtener notas con perfiles vinculados.
- **Punto 2**: En `core/notes_manager.py`, se confirmó la correcta implementación de los métodos de vinculación (`link_profile_to_note`, `unlink_profile_from_note`) y de obtención (`get_note_by_id`, `get_notes_as_dicts`) para manejar perfiles vinculados.
- **Punto 3**: En `api/agenda.py`, se aseguró la importación de `uuid` (corrigiendo duplicidad) y se actualizó `ProfileLinkRequest` para usar `uuid.UUID`. Se importaron las funciones de vinculación y `get_event_by_id` desde `core/agenda_manager.py`. Se añadió el endpoint `GET /agenda/events/{event_id}`.
- **Punto 4**: En `core/agenda_manager.py`, se confirmó la implementación de los métodos de vinculación (`link_profile_to_event`, `unlink_profile_from_event`) y se implementó `get_event_by_id` para cargar perfiles vinculados. **Se reimplementó la función `get_relevant_memories`** para buscar en `LangchainPgEmbedding` y devolver documentos relevantes.
- **Punto 5**: En `api/documents.py`, se aseguró la importación de `uuid` y se actualizó `ProfileLinkRequest` para usar `uuid.UUID` (corrigiendo duplicidad). Se importó `get_user_document_topic_by_name` desde `core/memory_manager.py`. Se añadió el endpoint `GET /collections/{topic}/details`.
- **Punto 6**: En `core/memory_manager.py`, se confirmó la implementación de los métodos de vinculación (`link_profile_to_collection`, `unlink_profile_from_collection`) y se implementó `get_user_document_topic_by_name` para cargar perfiles vinculados. **Se reimplementó la función `get_relevant_memories`** para buscar en `LangchainPgEmbedding` y devolver documentos relevantes.
- **Punto 7**: En `api/tasks.py`, se aseguró la importación de `uuid` (corrigiendo duplicidad) y se actualizó `ProfileLinkRequest` para usar `uuid.UUID`.
- **Punto 8**: En `core/tasks_manager.py`, se confirmó la correcta implementación de los métodos de vinculación (`link_profile_to_task`, `unlink_profile_from_task`) y de obtención (`get_task_by_id`, `list_tasks`) para manejar perfiles vinculados.
- **Punto 9**: En `tools/comprehensive_web_analysis_tool.py`, se aseguró que la herramienta importe y utilice la reimplementada `get_relevant_memories` de `core/memory_manager.py`.

---
## 11-09-2025 Corrección de AttributeError en Memory Manager

Descripción general: Se corrigió un `AttributeError: 'Config' object has no attribute 'global_collection_name'` en `core/memory_manager.py` que impedía el correcto funcionamiento de `kognito_core` y `kognito_telegram_client`. El error se debía a que la configuración `global_collection_name` no estaba definida en la clase `Config` en `core/config.py`.

- **Punto 1**: Se añadió `self.global_collection_name: str = os.getenv("GLOBAL_COLLECTION_NAME", "kognito_rag_collection")` a la clase `Config` en `core/config.py`. Esto asegura que la configuración `global_collection_name` esté disponible para ser utilizada por otros módulos.
- **Punto 2**: Se verificó que `core/memory_manager.py` estuviera importando `settings` correctamente y utilizando `settings.global_collection_name`, lo cual ya estaba implementado.

---
## 11-09-2025 Corrección de AttributeError en Configuración de Búsqueda Híbrida

Descripción general: Se corrigió un `AttributeError: 'Config' object has no attribute 'hybrid_search_bm25_weight'` que ocurría al intentar acceder a la configuración de peso para la búsqueda híbrida en `core/memory_manager.py`. El error se debía a que la configuración `hybrid_search_bm25_weight` se estaba utilizando antes de ser inicializada en la clase `Config` en `core/config.py`.
- **Punto 1**: Se reordenaron las definiciones de las variables de configuración en `core/config.py`, moviendo las configuraciones relacionadas con RAG, reranking y búsqueda híbrida (`embedding_model_name`, `embedding_chunk_size`, `embedding_chunk_overlap`, `reranker_model_name`, `reranker_top_n`, `hybrid_search_bm25_weight`) a una sección anterior dentro del método `__init__` de la clase `Config`. Esto asegura que estas configuraciones estén disponibles antes de que cualquier módulo intente acceder a ellas.

---
## 11-09-2025 Implementación de Vinculación de Perfiles a Colecciones en Memory Manager

Descripción general: Se implementaron las funciones `link_profile_to_collection` y `unlink_profile_from_collection` en `core/memory_manager.py` para permitir la asociación y desasociación de perfiles de contacto con colecciones de documentos (`UserDocumentTopic`). Estas funciones utilizan la tabla de asociación `UserDocumentTopicContactProfileAssociation` existente en `core/database.py`.

- **Punto 1**: Se añadió la función `get_user_document_topic_by_name` en `core/memory_manager.py` para facilitar la recuperación de un `UserDocumentTopic` por su nombre y contexto.
- **Punto 2**: Se implementó `link_profile_to_collection` en `core/memory_manager.py`. Esta función toma el `account_id`, `contact_profile_id` y `topic_name`, busca el `UserDocumentTopic` correspondiente y crea una nueva entrada en la tabla `UserDocumentTopicContactProfileAssociation` para establecer la relación.
- **Punto 3**: Se implementó `unlink_profile_from_collection` en `core/memory_manager.py`. Similar a la anterior, esta función elimina la entrada correspondiente en `UserDocumentTopicContactProfileAssociation`, rompiendo la relación entre el perfil y la colección.
---
## 12-09-2025 Corrección de TypeError en Memory Manager

Descripción general: Se corrigió un `TypeError: 'coroutine' object is not iterable` en `core/memory_manager.py` que ocurría al intentar iterar sobre el resultado de una función asíncrona sin usar `await`.

- **Punto 1**: Se añadió `await` a la llamada de `reranker.rerank` en la función `get_relevant_memories` en `core/memory_manager.py`. Esto asegura que la corrutina se resuelva antes de intentar iterar sobre su resultado.
---
## 12-09-2025 Implementación de Vinculación de Perfiles en Frontend

Descripción general: Se implementó la funcionalidad completa para vincular y desvincular notas, eventos, tareas y colecciones con perfiles de contacto en el frontend, utilizando los endpoints de backend ya existentes.

- **Punto 1**: Se añadió un botón "Gestionar Vinculaciones" en `src/app/(dashboard)/profiles/view-profile-dialog.tsx` para abrir un nuevo diálogo de gestión.
- **Punto 2**: Se creó el componente `src/app/(dashboard)/profiles/manage-linked-objects-dialog.tsx` para manejar la lógica de vinculación y desvinculación.
- **Punto 3**: Este nuevo diálogo carga todas las notas, eventos, tareas y colecciones disponibles, y las muestra en pestañas separadas.
- **Punto 4**: Permite al usuario vincular o desvincular elementos a un perfil de contacto mediante checkboxes, llamando a los endpoints de backend correspondientes (`/api/notes/{id}/link-profile`, `/api/agenda/events/{id}/link-profile`, `/api/tasks/{id}/link-profile`, `/api/collections/{id}/link-profile` y sus contrapartes de `unlink`).
- **Punto 5**: Se aseguró que el `ViewProfileDialog` se refresque automáticamente después de realizar cambios en las vinculaciones.

---
## 12-09-2025 Corrección de Error de Sintaxis en la Página de Agenda

Descripción general: Se corrigió un error de sintaxis en el archivo `src/app/(dashboard)/agenda/page.tsx` que impedía la compilación del frontend. El error fue causado por un bloque de código duplicado y malformado al final del archivo, producto de un error al copiar y pegar.

- **Punto 1**: Se identificó un bloque de código JSX duplicado y con errores de sintaxis al final de la función del componente `AgendaPage`.
- **Punto 2**: Se eliminó el bloque de código sobrante y erróneo, que incluía una declaración de `AlertDialog` malformada y una referencia a variables no definidas (`linkingObject`, `isLinkProfileDialogOpen`).
- **Punto 3**: Se restauró el cierre correcto de la función del componente y del JSX, solucionando el error `Expected ';', '}' or <eof>` y permitiendo que el componente se compile correctamente.

---
## 12-09-2025 Corrección de Error de Sintaxis en la Página de Notas

Descripción general: Se corrigió un error de sintaxis en el archivo `src/app/(dashboard)/notes/page.tsx` que causaba un error de compilación (`Expected '</', got '{'`). El problema se debía a un mapeo incorrecto de componentes dentro de la vista por categorías y un comentario JSX que probablemente confundía al compilador.

- **Punto 1**: Se reestructuró el bloque de renderizado para la vista de categorías (`categoryView`) para asegurar que el componente `NoteCard` se mapeara y renderizara correctamente dentro de `CategoryDropZone`.
- **Punto 2**: Se eliminó un comentario JSX (`{/* Pasada la nueva prop */}`) en la vista de notas general que, aunque sintácticamente correcto, podría haber estado contribuyendo al error del compilador en conjunto con el otro error.
- **Punto 3**: La corrección de la estructura del `map` en la vista de categorías resolvió el error de sintaxis subyacente, permitiendo que el componente se compile correctamente.
---
## 12-09-2025 Añadir Selector de Workspace en Editor de Nota Rápida

Descripción general: Se añadió un selector de workspace al editor de nota rápida (`src/app/(dashboard)/notes/note-dialog.tsx`) para permitir a los usuarios asociar una nota a un workspace específico, mejorando la organización.

- **Punto 1**: Se añadieron los estados `workspaces` y `loadingWorkspaces` en `src/app/(dashboard)/notes/note-dialog.tsx` para gestionar la lista de workspaces disponibles y su estado de carga.
- **Punto 2**: Se implementó un `useEffect` en `src/app/(dashboard)/notes/note-dialog.tsx` para cargar la lista de workspaces desde el endpoint `/api/workspaces` al abrir el diálogo.
- **Punto 3**: Se añadió un `FormField` de tipo `select` para `workspace_id` en el formulario de `src/app/(dashboard)/notes/note-dialog.tsx`, permitiendo al usuario seleccionar un workspace.
- **Punto 4**: Se aseguró que el `workspace_id` seleccionado se incluya en el `payload` al crear o actualizar una nota, y que el formulario se resetee correctamente con el `workspace_id` de la nota existente.
---
## 12-09-2025 Corrección de Precarga de Datos en Editor de Nota Rápida

Descripción general: Se corrigió un problema donde el editor de nota rápida (`NoteDialog`) se abría vacío al intentar editar una nota desde `ViewNoteDialog` o `ProfileDetailsPage`. Esto se debía a una inconsistencia en cómo se pasaba la nota a editar y cómo se inicializaba el formulario.

- **Punto 1**: En `src/app/(dashboard)/notes/view-note-dialog.tsx`, se cambió la prop `initialNote={note}` a `note={note}` en la llamada al `NoteDialog`, asegurando que la nota correcta se pase para la edición.
- **Punto 2**: En `src/app/(dashboard)/profiles/[id]/page.tsx`, se añadió un nuevo estado `editingNoteForDialog` para gestionar la nota que se va a editar en el `NoteDialog`.
- **Punto 3**: En `src/app/(dashboard)/profiles/[id]/page.tsx`, se modificó la llamada al `NoteDialog` para usar `note={editingNoteForDialog}`.
- **Punto 4**: En `src/app/(dashboard)/profiles/[id]/page.tsx`, se añadió un `DropdownMenuItem` para "Editar Nota" que establece `editingNoteForDialog` y abre el `NoteDialog` con la nota precargada.
---
## 12-09-2025 Corrección de Legibilidad en TiptapEditor en Modo Claro

Descripción general: Se corrigió un problema de legibilidad en el `TiptapEditor` (`src/components/TiptapEditor.tsx`) donde el texto se mantenía claro en modo claro, dificultando su lectura. Esto se debía a una configuración incorrecta de las clases CSS de `prose`.

- **Punto 1**: En `src/components/TiptapEditor.tsx`, se eliminó la clase `prose-invert` de la definición de la clase base del editor (`editorProps.attributes.class`).
- **Punto 2**: Se mantuvo `dark:prose-invert` para asegurar que el texto se invierta correctamente en modo oscuro.
- **Punto 3**: Esto garantiza que el texto del editor sea oscuro en modo claro y claro en modo oscuro, mejorando la legibilidad en ambos temas.
---
## 12-09-2025 Corrección de Alineación de Texto en Listas de Tareas de TiptapEditor

Descripción general: Se corrigió un problema en el `TiptapEditor` (`src/app/(dashboard)/notes/edit/[id]/page.tsx`) donde el texto de las listas de tareas se posicionaba debajo del checkbox en lugar de continuar en la misma línea. Esto se solucionó mediante la adición de estilos CSS personalizados en `globals.css`.

- **Punto 1**: Se añadieron estilos CSS específicos en `globals.css` para las listas de tareas (`.ProseMirror ul[data-type="taskList"]` y sus elementos anidados).
- **Punto 2**: Se utilizó `display: flex` y `align-items: flex-start` en los elementos `li` para asegurar que el checkbox y el texto se alineen horizontalmente.
- **Punto 3**: Se ajustó el `margin-top` del checkbox y se usó `flex-shrink: 0` para un ajuste fino de la alineación y evitar que el checkbox se encoja.
- **Punto 4**: Se aplicó `flex-grow: 1` al contenedor del texto para que ocupe el espacio restante, permitiendo que el texto fluya correctamente al lado del checkbox.
---
## 12-09-2025 Habilitar Edición de Perfil en Página de Detalles

Descripción general: Se habilitó la función de "Editar Perfil" en la página de detalles del perfil (`src/app/(dashboard)/profiles/[id]/page.tsx`), permitiendo a los usuarios modificar la información del perfil directamente desde esta vista.

- **Punto 1**: Se añadió un nuevo estado `isProfileDialogOpen` en `src/app/(dashboard)/profiles/[id]/page.tsx` para controlar la visibilidad del diálogo de edición de perfil.
- **Punto 2**: Se modificó la función `handleEditProfile` en `src/app/(dashboard)/profiles/[id]/page.tsx` para que abra el `ProfileDialog` cuando se haga clic en el botón "Editar Perfil".
- **Punto 3**: Se importó el componente `ProfileDialog` desde `../profile-dialog` en `src/app/(dashboard)/profiles/[id]/page.tsx`.
- **Punto 4**: Se renderizó el `ProfileDialog` al final del componente `ProfileDetailsPage`, pasándole el perfil actual (`profile`) y un callback `onSaveSuccess` (`fetchProfileDetails`) para refrescar los datos del perfil después de una edición exitosa.
---
## 12-09-2025 Corrección de Error `MissingGreenlet` al Crear Tareas

Descripción general: Se corrigió un error `MissingGreenlet` que ocurría al intentar crear una tarea en el backend (`core/tasks_manager.py`). Este error se debía a que la relación `contact_profiles` de la tarea se intentaba cargar de forma perezosa (`lazy-loaded`) en un contexto asíncrono sin el manejo adecuado.

- **Punto 1**: En `core/tasks_manager.py`, se modificó la función `add_task`.
- **Punto 2**: Después de crear y refrescar la nueva tarea, se añadió una consulta explícita utilizando `selectinload(Task.contact_profiles)` para cargar la relación `contact_profiles` de forma ansiosa.
- **Punto 3**: Se aseguró que la tarea cargada con sus perfiles de contacto (`loaded_task`) sea la que se pase a la función `_task_to_dict`, evitando así el error `MissingGreenlet` al acceder a la relación.
- **Punto 4**: Se añadió una verificación para asegurar que la tarea se cargue correctamente después de la creación, lanzando una excepción si no se encuentra.