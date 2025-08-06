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
- **Punto 3**: Se importó `settings` desde `core.config` y se reemplazaron las variables de configuración de Neo4j (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`) por `settings.neo4j_uri`, `settings.neo4j_user` y `settings.neo4j_password` para asegurar el acceso correcto a la configuración.
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
- **Punto 3**: Se eliminaron las descripciones de las herramientas del prompt del sistema en `core/prompt_manager.py`, ya que el LLM ahora las recibe directamente a través de `bind_tools`.
- **Punto 4**: Se actualizó la llamada a `prompt_manager.build_system_prompt` en `core/agent.py` para que ya no pase el argumento `tools`.
- **Punto 5**: Se actualizó la definición de la función `build_system_prompt` en `core/prompt_manager.py` para eliminar el parámetro `tools`.
- **Punto 6**: Se corrigió un `SyntaxError` en `core/prompt_manager.py` debido a una cadena de texto de varias líneas sin terminar.
- **Punto 7**: Se corrigió un `NameError` en `core/prompt_manager.py` eliminando una línea de depuración que intentaba acceder a la variable `tools` después de que se eliminara el parámetro.
---
## 06-08-25 Corrección de TypeError en PromptManager.build_system_prompt
Descripción general: Se solucionó un `TypeError` en `PromptManager.build_system_prompt()` causado por el paso de un argumento `tools` inesperado. La corrección consistió en eliminar este argumento de la llamada a la función en `core/agent.py`.

- **Punto 1**: Se identificó que la función `build_system_prompt` en `core/prompt_manager.py` no esperaba el argumento `tools`.
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