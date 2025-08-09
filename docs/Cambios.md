## 05-08-24 Corrección en el registro de cambios
Descripción general: Se corrigió un error en el proceso de registro de cambios en `docs/Cambios.md` donde se sobrescribía el contenido en lugar de añadirlo. Ahora, los nuevos cambios se añadirán correctamente al final del archivo, separados por `---`.

- **Punto 1**: Se implementó una lógica para leer el contenido existente del archivo antes de añadir nuevas entradas.
- **Punto 2**: Se aseguró que las nuevas entradas se concatenen al contenido existente, utilizando el separador `---`.
- **Punto 3**: Se verificó que el archivo se escriba con el contenido completo y actualizado.
---
## 05-08-24 Corrección de reconexión constante de WebSocket
Descripción general: Se solucionó el problema de reconexión constante del WebSocket en la página de colecciones de RAG (`/rag/[topic]`) que causaba el cierre inesperado de menús.

- **Punto 1**: Se identificó que el componente `DocumentCollectionDisplay.tsx` estaba causando re-renders excesivos, lo que provocaba que el hook `useWebSocket` se desmontara y se volviera a montar repetidamente.
- **Punto 2**: Se memoizó el objeto de opciones pasado a `useWebSocket` en `src/components/DocumentCollectionDisplay.tsx` utilizando `useMemo`.
- **Punto 3**: Esto asegura que el hook `useWebSocket` no se re-ejecute innecesariamente en cada re-render del componente padre, estabilizando la conexión WebSocket.
---
## 05-08-24 Corrección de manejo de `docs/Cambios.md`
Descripción general: Se ha corregido el error recurrente de sobrescribir el archivo `docs/Cambios.md` en lugar de añadir nuevas entradas. A partir de ahora, todas las nuevas entradas se añadirán correctamente al final del archivo, separadas por `---`, manteniendo el historial completo de cambios.

- **Punto 1**: Se ha implementado un proceso robusto para leer el contenido existente del archivo antes de cualquier modificación.
- **Punto 2**: Se garantiza que las nuevas entradas se concatenen al contenido previo, utilizando el separador `---` para una clara delimitación.
- **Punto 3**: Se ha verificado que el archivo se escriba con el contenido completo y actualizado, preservando el historial.
---
## 05-08-25 Corrección de configuración de Neo4j en Docker Compose
Descripción general: Se corrigió el error de configuración en `docker-compose.yml` para Neo4j, donde el valor de `NEO4J_dbms_logs_query_enabled` era `false` y no era aceptado.

- **Punto 1**: Se identificó que el valor `false` para `NEO4J_dbms_logs_query_enabled` no es válido según la documentación de Neo4j.
- **Punto 2**: Se cambió el valor de `NEO4J_dbms_logs_query_enabled` de `false` a `OFF` en el archivo `docker-compose.yml` para cumplir con los valores permitidos (`OFF`, `INFO`, `VERBOSE`).
- **Punto 3**: Esta corrección asegura que la configuración de logs de consultas de Neo4j sea válida y evita errores al iniciar el servicio.
---
## 05-08-25 Modificación de Sidebar: Botón "Nuevo Mensaje"
Descripción general: Se reemplazó el logo y el texto de Kognito AI Labs en la parte superior de la barra lateral (`Sidebar.tsx`) por un botón "Nuevo Mensaje" para mejorar la usabilidad y el acceso rápido a la creación de nuevas conversaciones.

- **Punto 1**: Se eliminó el componente `Image` y los `span` que mostraban el logo y el nombre de la aplicación.
- **Punto 2**: Se añadió un botón con el texto "Nuevo Mensaje" y un icono de `Plus` en la parte superior de la barra lateral.
- **Punto 3**: Se eliminó el botón duplicado de "Nuevo Chat" que aparecía en la sección de herramientas cuando la barra lateral estaba colapsada.
---
## 05-08-25 Modificación de Sidebar: Ajustes de Diseño
Descripción general: Se realizaron ajustes de diseño en la barra lateral (`Sidebar.tsx`) para mejorar la organización visual y simplificar la interfaz, distanciando la sección de "Herramientas" y eliminando la barra de búsqueda de conversaciones.

- **Punto 1**: Se añadió un margen superior (`mt-4`) a la sección de "Herramientas" para distanciarla visualmente de los elementos superiores.
- **Punto 2**: Se eliminó la barra de búsqueda de conversaciones y los botones de filtro por plataforma para simplificar la interfaz.
---
## 05-08-25 Corrección de Importaciones y Carga de Herramientas en `core/tools.py`
Descripción general: Se resolvieron múltiples errores de `NameError` y se estandarizó la carga de herramientas en `core/tools.py` para asegurar que todas las dependencias estén correctamente importadas y las herramientas se instancien de forma adecuada, incluyendo las funciones de fábrica.

- **Punto 1**: Se añadió la importación de `BaseTool` desde `langchain_core.tools` para resolver el `NameError` inicial.
- **Punto 2**: Se importó `GraphDB` desde `knowledge_graph.graph_database` para corregir el `NameError` relacionado.
- **Punto 3**: Se importó `settings` desde `core.config` y se reemplazaron las variables de configuración de Neo4j (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`) por `settings.neo4j_uri` y `settings.neo4j_user` y `settings.neo4j_password` para asegurar el acceso correcto a la configuración.
- **Punto 4**: Se importó `LLMManager` desde `core.llm_manager` para resolver el `NameError` correspondiente.
- **Punto 5**: Se importaron `HybridGraphProcessor` desde `knowledge_graph.hybrid_graph_processor` y `Neo4jAdapter` desde `knowledge_graph.neo4j_adapter` para corregir los errores de `NameError` de estas clases.
- **Punto 6**: Se corrigió la instanciación de `GithubRepositoryExplorerTool` a `GitHubRepoTool` para que coincidiera con el nombre de la clase importada.
- **Punto 7**: Se modificó la lógica de carga de herramientas para manejar correctamente las funciones de fábrica (`create_ddg_search_tool` y `get_web_search_tool`), llamándolas y añadiendo sus resultados a la lista de herramientas.
---
## 06-08-25 Corrección de `NameError` en `core/tools.py`
Descripción general: Se solucionó un `NameError` que ocurría en `core/tools.py` debido a que `LLMManager` no estaba importado. Además, se ajustó la inicialización de `CogneeIntegration` para pasar los parámetros correctos.

- **Punto 1**: Se añadió la importación de `LLMManager` desde `core.llm_manager` en el archivo `core/tools.py`.
- **Punto 2**: Se corrigió la instanciación de `CogneeIntegration`, pasándole `llm_manager=LLMManager()` y los demás parámetros requeridos, asegurando que la herramienta se inicialice correctamente.
---
## 06-08-25 Refactorización del Flujo de Reflexión del Agente
Descripción general: Se revirtió la estrategia de pasar la reflexión a través del historial de mensajes y se volvió al enfoque original de usar una variable de estado separada (`reflection`) para mejorar la claridad y la robustez del flujo del agente en `core/agent.py`.

- **Punto 1**: Se modificó el `reflection_node` para que guarde su resultado en el campo `reflection` del estado del agente, en lugar de añadirlo al historial de mensajes.
- **Punto 2**: Se ajustó el `response_generator_node` para que lea la reflexión desde `state.get("reflection", ...)` y la utilice para construir el prompt de la respuesta final.
- **Punto 3**: Esta corrección simplifica el flujo de datos, evita la modificación innecesaria del historial de conversación y resuelve el problema de que el LLM se quedara atascado.
---
## 06-08-25 Corrección de Invocación de Herramientas por el LLM
Descripción general: Se corrigió el problema donde el LLM no invocaba las herramientas correctamente, enviando el "tool code" como mensaje. Esto se solucionó vinculando las herramientas directamente al LLM a través de `llm.bind_tools` en el grafo de LangGraph y eliminando las descripciones de las herramientas del prompt del sistema.

- **Punto 1**: Se añadió un nuevo nodo `llmToolInvocation` en `core/agent.py` para invocar al LLM con las herramientas vinculadas.
- **Punto 2**: Se modificó el flujo del grafo en `create_langgraph_agent` para que el nodo `llmToolInvocation` se ejecute después de `getContext` y antes del `routing_node`.
- **Punto 3**: Se eliminaron las descripciones de las herramientas del prompt del sistema en `core/prompts.py`, ya que el LLM ahora las recibe directamente a través de `bind_tools`.
- **Punto 4**: Se actualizó la llamada a `prompt_manager.build_system_prompt` en `core/agent.py` para que ya no pase el argumento `tools`.
- **Punto 5**: Se actualizó la definición de la función `build_system_prompt` en `core/prompts.py` para eliminar el parámetro `tools`.
- **Punto 6**: Se corrigió un `SyntaxError` en `core/prompts.py` debido a una cadena de texto de varias líneas sin terminar.
- **Punto 7**: Se corrigió un `NameError` en `core/prompts.py` eliminando una línea de depuración que intentaba acceder a la variable `tools` después de que se eliminara el parámetro.
---
## 06-08-25 Corrección de TypeError en PromptManager.build_system_prompt
Descripción general: Se solucionó un `TypeError` en `PromptManager.build_system_prompt()` causado por el paso de un argumento `tools` inesperado. La corrección consistió en eliminar este argumento de la llamada a la función en `core/agent.py`.

- **Punto 1**: Se identificó que la función `build_system_prompt` en `core/prompts.py` no esperaba el argumento `tools`.
- **Punto 2**: Se encontró que la llamada a `prompt_manager.build_system_prompt` en `core/agent.py` estaba pasando el argumento `tools`.
- **Punto 3**: Se eliminó el argumento `tools` de la llamada a `prompt_manager.build_system_prompt` en `core/agent.py` para resolver el `TypeError`.

---
## 06-08-25 Ajuste de Nivel de Logging para Depuración
Descripción general: Se ajustó la configuración de logging en `api/main.py` para aumentar el nivel de detalle, permitiendo la visualización de mensajes de `DEBUG` y `ERROR` que antes estaban ocultos. Esto facilitará la depuración de errores de instanciación de herramientas y otros problemas.

- **Punto 1**: Se cambió el nivel de logging principal de `INFO` a `DEBUG` en la configuración de `logging.basicConfig`.
- **Punto 2**: Se actualizó el nivel de logging para `setup_llm_detailed_logging` de `INFO` a `DEBUG` para obtener un seguimiento más detallado de los modelos de lenguaje.
---
## 06-08-25 Corrección de error 'workspace_id' en la creación de notas
Descripción general: Se solucionó el error "invalid keyword argument 'workspace_id' for Nota" al intentar guardar notas, asegurando que el `workspace_id` se maneje correctamente en todo el flujo de creación de notas.

- **Punto 1**: Se modificó `tools/add_note_tool.py` para pasar el `workspace_id` a la función `add_note` del `NotesManager`.
- **Punto 2**: Se añadió la columna `workspace_id` a la clase `Nota` en `core/database.py`, incluyendo su relación con la tabla `workspaces`.
- **Punto 3**: Se actualizó el modelo `NoteRequest` en `api/notes.py` para incluir `workspace_id` como un campo opcional y se aseguró que este se pase correctamente a `notes_manager.add_note` desde el endpoint de la API.
---
## 06-08-25 Corrección de error 'telegram_id' y 'thread_id' en la creación de notas
Descripción general: Se solucionó el error "invalid keyword argument 'telegram_id' for Nota" y "invalid keyword argument 'thread_id' for Nota" al intentar guardar notas. El problema era que estos parámetros se estaban pasando a la clase `Nota` cuando no eran necesarios.

- **Punto 1**: Se revirtió el cambio en `core/database.py` para eliminar las columnas `telegram_id` y `thread_id` de la clase `Nota`.
- **Punto 2**: Se modificó `core/notes_manager.py` para eliminar `telegram_id` y `thread_id` de la firma de la función `add_note` y de la instanciación de `Nota`.
- **Punto 3**: Se modificó `tools/add_note_tool.py` para eliminar `telegram_id` y `thread_id` de los argumentos que se pasan a `notes_manager.add_note`.
---
## 06-08-25 Incorporación de Estructura de Respuesta Detallada para Informes y Análisis
Descripción general: Se ha incorporado una nueva estructura de respuesta al `KAI_SYSTEM_PROMPT` en `core/prompts.py` para asegurar que las respuestas que soliciten información, informes, análisis o resultados sean empáticas, detalladas, bien organizadas y con un cierre colaborativo.

- **Punto 1**: Se añadió una sección detallada en el `KAI_SYSTEM_PROMPT` que describe la estructura esperada para informes y análisis, incluyendo introducción empática, estructura lógica, profundidad en la explicación, uso de emojis y formato, y un cierre colaborativo.
- **Punto 2**: La nueva estructura se insertó en la sección "TONO Y ESTILO DE COMUNICACIÓN" del prompt, justo después de la instrucción de "Extensa y Detallada".
---
## 06-08-25 Corrección de Importación de Optional en GetAgendaTool
Descripción general: Se añadió la importación de `Optional` desde `typing` en `tools/get_agenda_tool.py` para resolver un `NameError` después de añadir `workspace_id: Optional[str] = None` a la clase `GetAgendaTool`.

- **Punto 1**: Se añadió `from typing import Optional` en `tools/get_agenda_tool.py`.
---
## 06-08-25 Adición de `telegram_id` como campo opcional en `GetAgendaTool`
Descripción general: Se añadió `telegram_id: Optional[int] = None` a la clase `GetAgendaTool` en `tools/get_agenda_tool.py` para que la herramienta pueda recibir este parámetro sin generar errores, alineándose con la estandarización de herramientas.

- **Punto 1**: Se añadió `telegram_id: Optional[int] = None` como atributo a la clase `GetAgendaTool` en `tools/get_agenda_tool.py`.
---
## 07-08-25 Corrección de TypeError en WebSearchTool
Descripción general: Se solucionó un TypeError en la herramienta WebSearchTool (tools/web_search_tool.py) que ocurría porque el método _arun devolvía un diccionario (.dict()) en lugar de un objeto ToolOutputWithSources.

- **Punto 1**: Se identificó que la firma de la función _arun esperaba un objeto ToolOutputWithSources como valor de retorno.
- **Punto 2**: Se observó que la línea de retorno estaba convirtiendo incorrectamente el objeto a un diccionario con .dict().
- **Punto 3**: Se eliminó la llamada a .dict() en la sentencia return de la función _arun para que devuelva el objeto correcto, solucionando así el error.
---
## 07-08-25 Mejoras de UI y Responsividad en Chat y RAG
Descripción general: Se implementaron varias mejoras en la interfaz de usuario y la responsividad, especialmente para dispositivos móviles, en los componentes de chat y las páginas de RAG.

- **Punto 1**: Se eliminó la "cola" de la burbuja de chat del usuario en `src/components/ChatMessage.tsx` para un diseño más limpio.
- **Punto 2**: Se hizo que la esquina inferior derecha de la burbuja de chat del usuario fuera recta en `src/components/ChatMessage.tsx` (`rounded-br-none`).
- **Punto 3**: Se corrigió la visualización de mensajes cortos en la burbuja de chat del usuario en smartphones, ajustando el ancho máximo en `src/components/ChatMessage.tsx` a `max-w-[80%]`.
- **Punto 4**: Se implementó el ordenamiento de mensajes por fecha (los más recientes primero) en `src/components/CommonChat.tsx`.
- **Punto 5**: Se eliminó el scroll horizontal en la vista de chat en smartphones, añadiendo `overflow-x-hidden` al contenedor principal en `src/components/CommonChat.tsx`.
- **Punto 6**: Se eliminó el botón de despliegue del menú de la derecha en `src/components/AppShell.tsx` y se corrigió el error de sintaxis del comentario HTML a JSX.
- **Punto 7**: Se aplicó la misma responsividad (`overflow-x-hidden`) a toda la página en `src/components/AppShell.tsx` para evitar el scroll horizontal general.
- **Punto 8**: Se adaptó la responsividad de las páginas de RAG (`src/app/(dashboard)/rag/**/page.tsx`) para evitar el scroll horizontal en smartphones, añadiendo `overflow-x-hidden` a sus contenedores principales.
---
## 07-08-25 Correcciones y Mejoras en Herramientas y UI
Descripción general: Se implementaron varias correcciones y mejoras en las herramientas de análisis web y en la interfaz de usuario, incluyendo la gestión de errores de React y la visualización de logos.

- **Punto 1**: Se corrigió el error en `tools/comprehensive_web_analysis_tool.py` donde la herramienta se saltaba pasos debido a una extracción incorrecta de URLs. Se modificó `_extract_urls` para procesar objetos `Source` directamente.
- **Punto 2**: Se instruyó al LLM en `tools/comprehensive_web_analysis_tool.py` para que intente citar y referenciar fuentes en formato APA en sus respuestas.
- **Punto 3**: Se resolvió el `NameError: name 'Source'` en `tools/comprehensive_web_analysis_tool.py` añadiendo la importación de `Source` desde `core/citation_models`.
- **Punto 4**: Se solucionó el error "Objects are not valid as a React child" en `src/app/(dashboard)/layout.tsx` asegurando que solo se pasen elementos React válidos a `AppShell` mediante `React.isValidElement()`.
- **Punto 5**: Se corrigió el error de compilación en `src/components/AppShell.tsx` causado por un comentario HTML inválido, reemplazándolo por `null` para que no se renderice nada en esa posición.
- **Punto 6**: Se modificó `src/components/AppShell.tsx` para eliminar el logo "Kognito AI Labs" y posicionar `public/logo-simple.png` en la esquina superior derecha de la barra superior.
---
## 07-08-25 Corrección de Parámetro Innecesario en UpdateProfileTool
Descripción general: Se solucionó el error `ValueError: "UpdateProfileTool" object has no field "thread_id"` al instanciar `UpdateProfileTool`.

- **Punto 1**: Se añadió `UpdateProfileTool` a la lista de herramientas excluidas de recibir el parámetro `thread_id` en `core/tools.py`.
---
## 07-08-25 Integración de KNOWLEDGE_SHARE_PRROMPT en ComprehensiveWebAnalysisTool
Descripción general: Se modificó la herramienta de análisis web (`ComprehensiveWebAnalysisTool`) para utilizar la plantilla `KNOWLEDGE_SHARE_PRROMPT` definida en `core/prompts.py` al generar el análisis final. Esto asegura que la respuesta del LLM siga un formato detallado y estructurado, incluyendo la referencia a las fuentes.

- **Punto 1**: Se importó `KNOWLEDGE_SHARE_PRROMPT` desde `core/prompts.py` en `tools/comprehensive_web_analysis_tool.py`.
- **Punto 2**: Se ajustó el `final_prompt` en la función `_arun` para que use `KNOWLEDGE_SHARE_PRROMPT` como plantilla.
- **Punto 3**: Se implementó el llenado de los marcadores de posición (`query`, `combined_web_content_accumulated`, `relevant_memories`, `formatted_sources`) en la plantilla `KNOWLEDGE_SHARE_PRROMPT`.
- **Punto 4**: Se mejoró la generación de `formatted_sources` para que se adapte al formato de fuentes de la plantilla.
---
## 07-08-25 Mejora del Contexto del Chat con Metadatos de Documentos
Descripción general: Se ha mejorado la capacidad del chat para utilizar el contexto de los documentos seleccionados. Ahora, el LLM recibe no solo el contenido del documento, sino también sus metadatos, lo que le permite tener conversaciones más ricas y precisas en torno al texto.

- **Punto 1**: Se modificó el backend en `api/chat.py` para que, al recibir un contexto de RAG, busque en la base de datos el contenido y los metadatos de los documentos y colecciones seleccionados.
- **Punto 2**: Se ha enriquecido el `user_message` que se envía al LLM, anteponiendo un texto con el contexto extraído, incluyendo el contenido y los metadatos de cada documento.
- **Punto 3**: Se ha realizado un pequeño ajuste en el frontend, en `src/components/ContextSelectorButton.tsx`, para mostrar de forma más clara si un ítem es un "Documento" o una "Colección", mejorando la usabilidad.
---
## 07-08-25 Ordenación de Conversaciones por Fecha de Creación
Descripción general: Se ha corregido el comportamiento de la lista de conversaciones para que se ordene por fecha de creación, mostrando las más recientes primero.

- **Punto 1**: Se ha modificado la consulta a la base de datos en `api/chat.py` en el endpoint que devuelve la lista de hilos (`/threads`).
- **Punto 2**: Se ha añadido `.order_by(ChatThread.created_at.desc())` a la consulta de SQLAlchemy para asegurar que los resultados se ordenen de forma descendente por fecha de creación.
---
## 07-08-25 Nombramiento Automático de Conversaciones con Actualización en Tiempo Real
Descripción general: Se ha implementado un sistema de nombramiento automático para las conversaciones. Los títulos se generan y actualizan mediante un LLM después de un cierto número de mensajes, y los cambios se reflejan en la interfaz de usuario en tiempo real sin necesidad de recargar la página.

- **Punto 1**: Se ha modificado `api/chat.py` para que, después de cada mensaje, se verifique el número de mensajes en la conversación. Si se alcanzan los 3 o 10 mensajes, se lanza una tarea en segundo plano para generar un nuevo título.
- **Punto 2**: Se ha mejorado la función `force_update_thread_title` en `core/agent.py` para que, además de actualizar la base de datos, envíe una notificación a través de un WebSocket al frontend.
- **Punto 3**: Se ha actualizado el componente `src/components/Sidebar.tsx` para que establezca una conexión WebSocket y escuche las notificaciones de `thread_title_updated`. Al recibir una, actualiza el título de la conversación correspondiente en el estado de React, logrando una actualización visual instantánea.
---
## 07-08-25 Corrección de Error de Importación en `api/chat.py`
Descripción general: Se ha solucionado un error crítico de `ImportError` y `NameError` en `api/chat.py` que impedía el correcto funcionamiento del enriquecimiento de contexto del chat. El error se debía a la importación de modelos incorrectos y a una lógica de consulta desactualizada.

- **Punto 1**: Se eliminó la importación incorrecta de `Document` y `Collection` que causaba el `ImportError`.
- **Punto 2**: Se importó el modelo correcto, `LangchainPgEmbedding`, desde `core/database`.
- **Punto 3**: Se ha reescrito por completo la lógica de enriquecimiento de contexto para que consulte la tabla `langchain_pg_embedding` utilizando los `document_id` proporcionados. La nueva lógica recupera todos los `chunks` de un documento, los ordena correctamente y reconstruye el contenido completo para inyectarlo en el prompt del LLM.
---
## 07-08-25 Corrección de NameError en api/chat.py
Descripción general: Se solucionó el error `NameError: name 'Integer' is not defined` en `api/chat.py` añadiendo la importación de `Integer` desde `sqlalchemy`.
- **Punto 1**: Se añadió `from sqlalchemy import Integer` en `api/chat.py` para resolver el error de nombre.
---
## 07-08-25 Corrección de Parámetro Innecesario en InternalKnowledgeSearchTool
Descripción general: Se solucionó el error `ValueError: "InternalKnowledgeSearchTool" object has no field "thread_id"` al instanciar `InternalKnowledgeSearchTool`.

- **Punto 1**: Se añadió `InternalKnowledgeSearchTool` a la lista de herramientas excluidas de recibir el parámetro `thread_id` en `core/tools.py`.
---
## 07-08-25 Corrección de Parámetro Innecesario en GetDocumentListTool
Descripción general: Se solucionó el error `ValueError: "GetDocumentListTool" object has no field "thread_id"` al instanciar `GetDocumentListTool`.

- **Punto 1**: Se añadió `GetDocumentListTool` a la lista de herramientas excluidas de recibir el parámetro `thread_id` en `core/tools.py`.
---
## 07-08-25 Ajuste de Tamaño de Fuente en Etiquetas de Documentos del Chat
Descripción general: Se ajustó el tamaño de la fuente de las etiquetas que muestran los documentos en el contexto del chat en `src/components/CommonChat.tsx` para que sean más pequeñas y se integren mejor visualmente.

- **Punto 1**: Se modificó el tamaño de la fuente de las etiquetas de contexto dentro de los mensajes del chat a `text-xs` (extra pequeñas).
- **Punto 2**: Se modificó el tamaño de la fuente de las etiquetas de contexto en la barra de entrada del chat a `text-xs` (extra pequeñas).
---
## 08-08-25 Mejora en la Subida de Documentos con Indicador de Carga Realista
Descripción general: Se ha mejorado la experiencia de usuario al subir documentos en la sección RAG. Anteriormente, se mostraba una notificación de éxito de forma prematura. Ahora, se ha implementado un sistema de seguimiento en tiempo real que muestra un indicador de carga individual para cada archivo hasta que su procesamiento en el backend finaliza.

- **Punto 1 (Backend - `core/memory_manager.py`):** Se modificó la función `process_document_for_rag` para que envíe notificaciones WebSocket granulares al frontend en tres momentos clave: `document_processing_started`, `document_processing_completed` y `document_processing_failed`.
- **Punto 2 (Frontend - `src/app/(dashboard)/rag/upload-document-dialog.tsx`):** Se eliminó la notificación `toast` de éxito inmediato y la lógica de `await`. Ahora, el diálogo se cierra al instante y la petición de subida se realiza en segundo plano, delegando la responsabilidad de la retroalimentación visual al componente padre.
- **Punto 3 (Frontend - `src/components/DocumentCollectionDisplay.tsx`):** Se implementó la lógica para escuchar los nuevos eventos de WebSocket. Al recibir `document_processing_started`, se añade un *placeholder* a la tabla con estado "Procesando". Al recibir `document_processing_completed`, se recarga la lista de documentos para mostrar el archivo final. Si se recibe `document_processing_failed`, se actualiza el *placeholder* para mostrar un estado de error.
---
## 08-08-25 Corrección del Botón "Nombrar" en el Menú de Chats
Descripción general: Se ha corregido el botón "Nombrar" en el menú contextual de cada conversación en la barra lateral (`Sidebar.tsx`), que no funcionaba correctamente. El problema se debía a un conflicto entre la actualización manual del estado en el frontend y el sistema de actualización en tiempo real a través de WebSockets.

- **Punto 1**: Se simplificó la lógica del `onClick` del botón "Nombrar" en `src/components/Sidebar.tsx`.
- **Punto 2**: Se eliminó el código que intentaba actualizar el estado de React (`setThreads`, `setPinnedThreads`) directamente después de recibir la respuesta de la API.
- **Punto 3**: Ahora, el botón solo envía la solicitud a la API (`/api/threads/${thread.id}/generate-title`) y muestra una notificación `toast`. La actualización del título en la interfaz de usuario es gestionada exclusivamente por el listener de WebSocket existente, que ya se encarga de las notificaciones `thread_title_updated`, asegurando una única fuente de verdad y un funcionamiento correcto.
---
## 08-08-25 Corrección de `IntegrityError` en `langchain_pg_collection`
Descripción general: Se solucionó el error `IntegrityError: duplicate key value violates unique constraint "langchain_pg_collection_name_key"` que ocurría al intentar insertar una colección de Langchain con un nombre ya existente, como "Formulación". La causa fue que la lógica no verificaba la existencia de la colección antes de intentar crearla, lo que provocaba una duplicidad.

- **Punto 1**: Se modificó la función `process_document_for_rag` en `core/memory_manager.py` para verificar la existencia de la colección en la tabla `LangchainPgCollection` antes de inicializar `PGVector`.
- **Punto 2**: Si la colección ya existe, se reutiliza su UUID. Si no existe, se permite que Langchain la cree y luego se obtiene su UUID para asegurar la consistencia.
- **Punto 3**: Este cambio evita la violación de la restricción de unicidad al asegurar que no se intenten crear colecciones duplicadas en la base de datos.

---
## 08-08-25 Implementación de Sistema de Citas y RAG Explícito

**Descripción general:** Se ha refactorizado profundamente el sistema de Recuperación Aumentada por Generación (RAG) para soportar un contexto explícito seleccionado por el usuario y se ha implementado un sistema de citas en el frontend para mostrar las fuentes de la información. Esto mejora drásticamente la precisión, eficiencia y transparencia de las respuestas del LLM.

- **Punto 1 (RAG Explícito - Backend):**
    - Se modificó `core/memory_manager.py` para que la función `get_relevant_memories` acepte filtros explícitos por `document_ids` y `topics`.
    - Se ajustó la función `search_vector_db_optimized` para que la consulta SQL una los filtros de `document_ids` y `topics` con un operador `OR`, permitiendo búsquedas en contextos mixtos.
    - Se actualizó `core/agent.py` para que el `AgentState` transporte el `rag_context` y las `sources`. El `call_model_node` ahora procesa este contexto y lo pasa a `get_relevant_memories`.
    - Se ajustó `api/chat.py` para pasar el `rag_context` de la solicitud del usuario al estado inicial del agente.

- **Punto 2 (Sistema de Citas - Backend):**
    - Se modificó `get_relevant_memories` para que, en lugar de devolver una cadena de texto, devuelva un objeto `ToolOutputWithSources` que contiene tanto el contexto formateado para el LLM como una lista estructurada de objetos `Source`.
    - Se importaron los modelos de `core/citation_models.py` en `core/memory_manager.py` para construir las fuentes.

- **Punto 3 (Sistema de Citas - Frontend):**
    - Se actualizaron los tipos de datos en `src/components/CommonChat.tsx` para que cada mensaje pueda almacenar una lista de `sources`.
    - Se modificó la lógica de streaming en `CommonChat.tsx` para capturar y almacenar las `sources` que llegan desde el backend.
    - Se creó un nuevo componente `<Citation />` en `src/components/ChatMessage.tsx` que utiliza un `Popover` para mostrar los detalles de una fuente (título, snippet, relevancia).
    - Se modificó el `MarkdownRenderer` para que detecte los marcadores de cita (ej. `[1]`) en el texto de la IA y los reemplace dinámicamente por el componente `<Citation />` interactivo.

- **Punto 4 (Correcciones Menores):**
    - Se solucionaron varios errores de `NameError` y de importación en `ChatMessage.tsx` y `core/agent.py` que surgieron durante la refactorización.
---
## 08-08-25 Corrección de TypeError en GitHubRepoTool._arun()

Descripción general: Se solucionó un `TypeError` en la invocación de `GitHubRepoTool._arun()` en `api/github.py`. El error se debía a que el método esperaba un objeto `GitHubRepoInput` como argumento, pero se le estaban pasando los parámetros directamente.

- **Punto 1**: Se identificó que la función `_arun` en `tools/github_repo_tool.py` esperaba un objeto `GitHubRepoInput` como `tool_input`.
- **Punto 2**: Se encontró que en `api/github.py`, la función `manage_github_collection` estaba llamando a `_arun` con argumentos directos (`repo_url`, `action`, `collection_topic`, `account_id_to_use`, `workspace_id`, `github_token`).
- **Punto 3**: Se modificó `api/github.py` para construir un objeto `GitHubRepoInput` con los parámetros necesarios y pasarlo como `tool_input` a `github_tool._arun()`.
