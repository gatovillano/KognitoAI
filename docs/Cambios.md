## 25-12-25 Corrección de ReferenceError: onDevelopClick is not defined 🐞

Se corrigió un `ReferenceError: onDevelopClick is not defined` que ocurría en el componente `QuestionSliderDialog` al intentar renderizar el botón de "Iniciar Investigación Profunda".

- **Propagación de la propiedad `onDevelopClick`**: Se propagó la propiedad `onDevelopClick` a través de la jerarquía de componentes:
  - Se añadió `onDevelopClick?: () => void;` a la interfaz `QuestionSliderDialogProps` en `src/components/QuestionSliderDialog.tsx`.
  - Se añadió `onDevelopClick?: () => void;` a la interfaz `QuestionSliderProps` en `src/components/QuestionSlider.tsx`.
  - Se pasó la propiedad `onDevelopClick` desde `QuestionSlider` a `QuestionSliderDialog`.
  - Se pasó una función vacía `() => {}` como valor para `onDevelopClick` en las instancias de `QuestionSlider` dentro de `src/app/(dashboard)/analysis/page.tsx` para asegurar que el botón se renderice correctamente.

---

## 24-12-24 Corrección completa de UnboundLocalError y eliminación de código duplicado en supervisor de DeepResearcher 🐞

Se corrigió completamente el `UnboundLocalError` en la función `supervisor` del `DeepResearcher` causado por el uso de `supervisor_system_prompt` antes de su definición, y se eliminó código duplicado que causaba inconsistencias.

- **Reubicación de la definición de `supervisor_system_prompt`**: Se movió la inicialización de `supervisor_system_prompt` al inicio de la función `supervisor` en `core/agents/deep_researcher.py`, antes de su uso en la configuración de mensajes.
- **Eliminación de código duplicado**: Se removió un bloque duplicado de configuración de mensajes y lógica de invocación del LLM que estaba causando redundancia y potenciales errores.

---

## 23-12-2025 Mejora en la visualización de fuentes y recomendaciones del Deep Researcher

Se ha mejorado la presentación de las fuentes y recomendaciones generadas por el "Deep Researcher" en el componente `AnalysisDetailDialog`.

- **Implementación de `GapSource` y `GapSourceButton`**: Se crearon interfaces y componentes dedicados para manejar las fuentes de los informes de desarrollo de brechas, permitiendo una visualización estructurada e interactiva similar a las citas en los mensajes del chat.
- **Procesamiento de citas en hallazgos**: Se añadió lógica para parsear el texto de los hallazgos y reemplazar las referencias numéricas a fuentes ([1], [2], etc.) con botones interactivos que muestran los detalles de la fuente al hacer clic.
- **Mejora en la visualización de recomendaciones**: Las recomendaciones ahora se presentan de forma más clara y estructurada dentro de su propia pestaña en el detalle del análisis de desarrollo de brecha.

---

## 24-12-25 Optimización de Tavily Search con Fast LLM

Se ha confirmado y documentado que la función `tavily_search` en `core/agents/deep_researcher_utils.py` utiliza exclusivamente el "fast llm" para las operaciones de sumarización de contenido web, mientras que la interacción directa con la API de Tavily no requiere un LLM local.

- **Clarificación en el código**: Se añadió un comentario en la función `tavily_search` para especificar que el `get_fast_llm()` se usa para la sumarización y que la búsqueda de Tavily no utiliza un LLM local.

---

## 24-12-24 Corrección de Error de Declaración Duplicada de `ExternalLink` 🚀

Se corrigió un error de compilación `Module parse failed: Identifier 'ExternalLink' has already been declared` en el archivo `analysis-detail-dialog.tsx` debido a una importación duplicada del componente `ExternalLink`.

- **Eliminación de Importación Duplicada**: Se eliminó la línea de importación redundante de `ExternalLink` en [`src/app/(dashboard)/analysis/analysis-detail-dialog.tsx:18`](src/app/(dashboard)/analysis/analysis-detail-dialog.tsx:18), ya que el componente ya estaba importado en la línea 5 del mismo archivo.

---

## 24-12-24 Integración de Herramientas Avanzadas en Deep Researcher 🛠️

Se ha ampliado la capacidad del `DeepResearcher` para utilizar un conjunto más diverso de herramientas, incluyendo búsqueda web, análisis web completo, búsqueda en grafos de conocimiento y generación de consultas Cypher. Esto aborda el problema de que el LLM no estaba invocando herramientas de búsqueda.

- **Inclusión de `GraphCypherGeneratorTool`**: Se importó e integró la `GraphCypherGeneratorTool` en `core/tools.py` para permitir la generación y ejecución de consultas Cypher en el grafo de conocimiento.
- **Actualización de `research_system_prompt`**: Se modificó el `research_system_prompt` en `core/agents/deep_researcher_prompts.py` para listar explícitamente todas las herramientas disponibles (`tavily_search`, `web_search`, `comprehensive_web_analyzer`, `knowledge_search`, `knowledge_graph`, `graph_cypher_generator_tool`, `think_tool`). Esto mejora la visibilidad de las herramientas para el LLM del `researcher`, incentivando su uso.

---

## 24-12-24 Mejora en la Delegación de Investigación del Deep Researcher 🚀

Se implementaron mejoras en el agente `DeepResearcher` para asegurar que la investigación delegada se realice de manera más efectiva y no se detenga prematuramente, abordando la generación de "pre-informes" sin investigación real.

- **Modificación de `lead_researcher_prompt`**: Se ajustó el prompt del supervisor (`lead_researcher_prompt` en `core/agents/deep_researcher_prompts.py`) para enfatizar la delegación de tareas de investigación, instruyendo al supervisor a desglosar el `research_brief` en tareas delegables y a llamar a `ResearchComplete` solo después de que la investigación haya sido efectivamente realizada.
- **Aumento de `max_researcher_iterations`**: Se incrementó el valor de `max_researcher_iterations` de 3 a 10 en `core/agents/deep_researcher_config.py` para permitir que el supervisor realice más iteraciones de delegación, facilitando una investigación más profunda y completa.

---

## 24-12-24 Corrección de `ModuleNotFoundError` en `graph_cypher_generator_tool` 🐞

Se solucionó un error `ModuleNotFoundError: No module named 'knowledge_graph.cognee_integration'` que impedía el arranque del servicio `kognito_core`. El problema se debía a un cambio de nombre no actualizado en el código.

- **Renombramiento de Clase y Archivo**: La clase `CogneeIntegration` fue renombrada a `GraphIntegration` y el archivo `cognee_integration.py` a `graph_integration.py`.
- **Actualización de Importación**: Se corrigió la importación en `tools/graph_cypher_generator_tool.py` para que apunte a `knowledge_graph.graph_integration` y utilice la clase `GraphIntegration`.
- **Ajuste en la Instanciación**: Se modificó la forma en que se instancia `GraphIntegration` para pasarle el objeto `graph_db` requerido.

---

## 24-12-2025 Implementación de barra de progreso en tiempo real para el Deep Researcher

Se ha implementado una barra de progreso en tiempo real en el frontend para las investigaciones del "Deep Researcher" (`gap_development`).

- **Modificación de `core/agents/deep_researcher.py`**: Se añadió un mecanismo de `progress_callback` en los nodos clave del grafo del Deep Researcher para enviar actualizaciones de progreso y mensajes descriptivos durante la ejecución de las diferentes etapas de la investigación. Se implementó un esquema de progreso jerárquico donde cada nodo calcula su progreso dentro de un rango asignado, asegurando una granularidad fina.
- **Modificación de `api/gap_development.py`**: Se integró una función `send_progress_update` en la API que invoca al Deep Researcher, la cual escala el progreso interno del grafo a un porcentaje global (0-100%) y lo envía al frontend a través de WebSockets. Además, se inicializaron los parámetros `base_progress` y `max_sub_progress` en la configuración principal para facilitar el cálculo jerárquico del progreso.
- **Actualización de `src/components/QuestionSliderDialog.tsx` y `src/components/GapDevelopmentDialog.tsx`**: Se eliminó la simulación de progreso en ambos componentes del frontend y se configuraron para que utilicen directamente el valor de progreso enviado por el backend, permitiendo una visualización precisa y en tiempo real del estado de la investigación.

---

## 24-12-2025 Ocultar etiquetas de relaciones en el grafo de conocimiento

Se ha modificado el componente `GraphVisualization` para que las etiquetas de las relaciones (edges) en el grafo de conocimiento no se muestren por defecto, sino que aparezcan al pasar el mouse sobre ellas.

- **Modificación de `src/components/KnowledgeGraph/GraphVisualization.tsx`**: Se modificó la función `convertEdgesToVis` para establecer la propiedad `label` de las aristas como una cadena vacía (`label: ''`). La información de la relación se sigue mostrando a través de la propiedad `title`, que es utilizada por vis-network para mostrar tooltips al pasar el mouse.

---

## 24-12-25 Corrección de `TypeError` en `deep_researcher` por concatenación de tipos

- **Error**: Se produjo un `TypeError: can only concatenate list (not "str") to list` en el agente `DeepResearcher`.
- **Causa**: El nodo `compress_research` del grafo de investigación estaba devolviendo el campo `raw_notes` como una cadena de texto (`string`), mientras que el estado del agente (`ResearcherState`) esperaba una lista de cadenas (`list[str]`). Al intentar actualizar el estado, el reductor `operator.add` fallaba al intentar concatenar una lista con una cadena.
- **Solución**: Se modificó la función `compress_research` en `core/agents/deep_researcher.py` para que devuelva el campo `raw_notes` como una lista que contiene una única cadena (`[raw_notes_content]`). Esto alinea el tipo de dato con la definición del estado y resuelve el `TypeError`.

---

## 24-12-25 Corrección de errores en inicialización de herramientas de grafo de conocimiento

Se corrigieron múltiples errores que impedían la inicialización de las herramientas de grafo de conocimiento: AttributeError por atributo faltante, TypeError por parámetro inesperado, AttributeError por nombre de atributo incorrecto y TypeError por método abstracto faltante.

- **Adición de atributo llm_max_retries**: Se agregó el atributo llm_max_retries a la clase Config en [`core/config.py`](core/config.py) con un valor por defecto de 3, configurable mediante la variable de entorno LLM_MAX_RETRIES.
- **Corrección de instanciación HybridGraphProcessor**: Se eliminó el parámetro max_retries de la instanciación de HybridGraphProcessor en [`knowledge_graph/graph_integration.py`](knowledge_graph/graph_integration.py) ya que este procesador local no acepta dicho parámetro.
- **Corrección de instanciación ConceptualGraphProcessor**: Se eliminó el parámetro max_retries de la instanciación de ConceptualGraphProcessor en [`knowledge_graph/graph_integration.py`](knowledge_graph/graph_integration.py) ya que este procesador tampoco acepta dicho parámetro.
- **Corrección de variables indefinidas en ConceptualGraphProcessor**: Se agregaron las variables `max_retries` y `retry_delay` faltantes en el método `_call_llm_with_retry_and_validation` de [`knowledge_graph/conceptual_graph_processor.py`](knowledge_graph/conceptual_graph_processor.py) para evitar errores de `NameError`.
- **Corrección de acceso a graph_integration**: Se cambió el acceso a `_knowledge_graph_service.cognee_integration` por `_knowledge_graph_service.graph_integration` en [`core/tools.py`](core/tools.py) para que coincida con el nombre correcto del atributo en la clase KnowledgeGraphService.
- **Adición de método _run faltante**: Se agregó el método `_run` requerido por BaseTool en [`tools/graph_cypher_generator_tool.py`](tools/graph_cypher_generator_tool.py) que lanza NotImplementedError ya que la herramienta solo soporta ejecución asíncrona.
- **Sidebar redimensionable con iconos progresivos**: Se implementó un sidebar redimensionable usando `react-resizable-panels` donde las etiquetas de texto de las herramientas desaparecen cuando el sidebar se hace más pequeño (por debajo del 8% del ancho), manteniendo solo los iconos para un diseño más compacto. El header mantiene el texto hasta que el sidebar se colapsa completamente (por debajo del 12%).

---

## 24-12-25 Sidebar redimensionable con el mouse

Se implementó un sidebar redimensionable que permite a los usuarios ajustar el ancho manualmente arrastrando con el mouse.

- **Implementación de paneles redimensionables**: Se reemplazó el layout fijo del sidebar con `react-resizable-panels` en [`src/components/AppShell.tsx`](src/components/AppShell.tsx), permitiendo redimensionar el sidebar entre 4% y 35% del ancho de la pantalla.
- **Eliminación del botón de colapso**: Se removió el botón de colapso/expansión del sidebar ya que ahora es completamente redimensionable.
- **Persistencia automática**: El ancho del sidebar se mantiene automáticamente entre sesiones gracias a la librería `react-resizable-panels`.

---

## 24-12-25 Prevención de Relaciones Bidireccionales Duplicadas en Neo4j 🔄

Se implementó una verificación en el `Neo4jAdapter` para evitar la creación de relaciones bidireccionales idénticas entre los mismos nodos y con el mismo tipo de relación. Esto resuelve el problema de la visualización de dos flechas en sentidos opuestos para una única relación lógica.

- **Adición de `_relationship_exists_in_db`**: Se añadió una función auxiliar asíncrona `_relationship_exists_in_db` a la clase `Neo4jAdapter` en [`knowledge_graph/neo4j_adapter.py`](knowledge_graph/neo4j_adapter.py). Esta función consulta la base de datos para verificar si ya existe una relación (o su inversa) con los mismos IDs de origen, destino y tipo.
- **Modificación de `_add_relationships_to_neo4j`**: Se modificó la función `_add_relationships_to_neo4j` en [`knowledge_graph/neo4j_adapter.py`](knowledge_graph/neo4j_adapter.py) para que, antes de crear cada relación, utilice `_relationship_exists_in_db`. Si la relación propuesta (o su inversa idéntica) ya existe, se omite su creación, evitando así la duplicación.

---

## 24-12-25 Implementación de visualización de Memorias Vectoriales en Configuración 🧠

Se ha implementado la funcionalidad para recuperar y visualizar las memorias vectoriales del usuario en la sección "Memorias" de la página de configuración. Estas memorias corresponden a los `content_type` `user_memory_proactive_llm` y `user_memories` almacenadas en la tabla `langchain_pg_embedding`.

- **Creación del endpoint `/api/memories`**: Se creó un nuevo archivo `api/memory.py` que define un router para gestionar las memorias vectoriales.
  - El endpoint `GET /api/memories` recupera las memorias del usuario filtrando por los `content_type` especificados (`user_memory_proactive_llm`, `user_memories`, `general_memory`) utilizando la función `get_relevant_memories` de `core/memory_manager.py`.
  - El endpoint `POST /api/memories` permite añadir nuevas memorias vectoriales a través de la función `add_memory_to_vector_db` de `core/memory_manager.py`.
- **Integración del router en `api/main.py`**: Se añadió el `memory_router` a la aplicación principal de FastAPI para que los nuevos endpoints sean accesibles.
- **Actualización de `src/app/(dashboard)/settings/page.tsx`**:
  - La función `fetchMemories` ahora realiza una llamada al nuevo endpoint `/api/memories` para obtener la lista de memorias vectoriales.
  - La función `addMemory` ahora utiliza el endpoint `POST /api/memories` para guardar nuevas memorias.
  - Se añadió un mensaje informativo en la función `deleteMemory` indicando que la eliminación de memorias vectoriales aún no está implementada.

---

## 28-12-25 Integración de Notas de Workspace en Búsqueda RAG

Se ha mejorado el sistema de recuperación de información (RAG) para que incluya automáticamente las notas del workspace actual al alimentar el contexto del LLM.

- **Filtrado de Notas por Workspace**: Se actualizaron las funciones `_run_semantic_search` y `_run_fts_search` en [`core/memory_manager.py`](core/memory_manager.py) para aplicar el filtro de `workspace_id` al buscar en la tabla de notas.
- **RAG Automático en el Agente**: Se implementó una búsqueda RAG proactiva en el nodo `call_model_node` de [`core/agent.py`](core/agent.py). Ahora, el agente recupera memorias, documentos y notas relevantes del workspace antes de generar cada respuesta, asegurando que el LLM tenga contexto actualizado sin depender de llamadas explícitas a herramientas.
- **Consistencia en Herramientas**: Se verificó que las herramientas de búsqueda de conocimiento utilicen la lógica actualizada, garantizando que los resultados respeten el ámbito del workspace activo.

---

## 24-12-25 Eliminación del Límite de Nodos en el Grafo de Conocimiento 📈

Se eliminó el límite superior de 2000 nodos en la configuración del grafo de conocimiento, permitiendo la visualización de un número ilimitado de nodos.

- **Modificación de `max` en Input**: Se eliminó la propiedad `max={2000}` del componente Input en [`src/app/(dashboard)/analysis/graph/page.tsx:716`](src/app/(dashboard)/analysis/graph/page.tsx:716).
- **Ajuste en `onBlur`**: Se modificó la lógica en la función `onBlur` del mismo Input para eliminar el límite superior `Math.min(2000, value)` y solo aplicar el límite inferior `Math.max(10, value)`.

---

## 24-12-25 Definición de Esquema para Nodo DOCUMENT y Relaciones en Neo4j 📝

Se ha definido y documentado el esquema detallado para el nodo `DOCUMENT` y sus relaciones asociadas para la implementación en Neo4j.

- **Definición del Nodo DOCUMENT**: Se especificaron todos los atributos del nodo `DOCUMENT`, incluyendo `id`, `title`, `url`, `content_hash`, `summary`, `keywords`, `embedding`, `topic`, `publication_date`, `author`, `source_type`, `created_at`, `updated_at`, `workspace_id`, `account_id`, y `type="DOCUMENT"`.
- **Definición de Relaciones**: Se detallaron las propiedades para las relaciones clave:
  - **CONTAINS_QUOTE (DOCUMENT -> CONCEPTUAL_QUOTE)**: Con propiedades `position_in_document` y `page_number`.
  - **HAS_IDEA_PROFILE (DOCUMENT -> IDEA_PROFILE)**: Con propiedades `contribution_score` y `relevant_quotes_count`.
  - **MISMO_TOPICO_(NOMBRETOPICO) (DOCUMENT -> DOCUMENT)**: Relación dinámica basada en el tópico, con propiedades `similarity_score` y `topic`.
  - **RELATED_TO_DOCUMENT (DOCUMENT -> DOCUMENT)**: Con propiedades `similarity_score`, `shared_ideas_count` y `reason`.
- **Documentación del Esquema**: Se creó el archivo `docs/DOCUMENT_SCHEMA.md` para consolidar esta información.

---

## 24-12-25 Corrección de error de sintaxis en `AppShell.tsx`

- **Error**: Se produjo un error de sintaxis "Expected '</', got 'jsx text (" en `src/components/AppShell.tsx` en la línea 200.
- **Causa**: Faltaba una etiqueta de cierre `</div>` para el `div` que contenía el `header` y `main` dentro del segundo `Panel` del `PanelGroup`.
- **Solución**: Se añadió la etiqueta de cierre `</div>` antes de la etiqueta de cierre `</Panel>` en `src/components/AppShell.tsx` para corregir la estructura del JSX.

---

## 24-12-24 Corrección de UnboundLocalError en DeepResearcher 🐞

Se corrigió un `UnboundLocalError` en la función `clarify_with_user` del `DeepResearcher` que ocurría porque la variable `current_messages` era accedida antes de ser asignada.

- **Reubicación de la inicialización de `current_messages`**: La inicialización de la variable `current_messages` en `core/agents/deep_researcher.py` se movió a una línea anterior para asegurar que siempre esté definida antes de su primer uso, resolviendo así el error.

---

## 24-12-24 Corrección de NameError para 'fast_llm' en DeepResearcher 🐞

Se corrigió un `NameError: name 'fast_llm' is not defined` en la función `clarify_with_user` del `DeepResearcher`.

- **Inicialización de `fast_llm`**: Se añadió la inicialización de `fast_llm` dentro de la función `clarify_with_user` en `core/agents/deep_researcher.py` para asegurar que el modelo LLM rápido esté disponible antes de su uso.

---

## 24-12-24 Corrección de UnboundLocalError para 'pruned_messages_for_supervisor' en DeepResearcher 🐞

Se corrigió un `UnboundLocalError` en la función `supervisor` del `DeepResearcher` que ocurría porque la variable `pruned_messages_for_supervisor` era accedida antes de ser asignada.

- **Reubicación de la inicialización de `pruned_messages_for_supervisor`**: La inicialización de la variable `pruned_messages_for_supervisor` en `core/agents/deep_researcher.py` se movió a una línea anterior para asegurar que siempre esté definida antes de su primer uso, resolviendo así el error.

---

## 24-12-24 Corrección de UnboundLocalError para 'supervisor_system_prompt' en DeepResearcher 🐞

Se corrigió un `UnboundLocalError` en la función `supervisor` del `DeepResearcher` que ocurría porque la variable `supervisor_system_prompt` era accedida antes de ser asignada.

- **Reubicación de la inicialización de `supervisor_system_prompt`**: La inicialización de la variable `supervisor_system_prompt` en `core/agents/deep_researcher.py` se movió a una línea anterior para asegurar que siempre esté definida antes de su primer uso, resolviendo así el error.

---

## 24-12-24 Corrección de `litellm.BadRequestError` en DeepResearcher 🐞

Se corrigió un `litellm.BadRequestError` en la función `supervisor` del `DeepResearcher` que ocurría porque la API de LiteLLM no recibía los mensajes o el prompt de la manera esperada.

- **Formato de mensajes para LiteLLM**: Se modificó la función `supervisor` en `core/agents/deep_researcher.py` para asegurar que el `supervisor_system_prompt` se envíe como un `SystemMessage` explícito al inicio de la lista de mensajes, seguido de los mensajes históricos y el mensaje inicial del usuario. Esto garantiza que LiteLLM reciba una lista de mensajes bien formada y resuelva el error de `Input required: specify "prompt" or "messages"`.

---

## 24-12-24 Mejora en la Delegación de Tareas del Supervisor de DeepResearcher 🚀

Se mejoró el `lead_researcher_prompt` para hacer más explícita la conexión entre la planificación con `think_tool` y la ejecución de `ConductResearch`, asegurando que el supervisor delegue tareas de investigación de manera más proactiva.

- **Instrucción explícita para `ConductResearch`**: Se añadió un nuevo punto en la sección `Instructions` que indica que, después de la planificación con `think_tool`, el supervisor *debe* llamar a `ConductResearch` para cada subtarea identificada si la investigación no está completa.
- **Refuerzo en `Show Your Thinking`**: Se modificó la sección `Show Your Thinking` para enfatizar que el plan del supervisor *debe* culminar en una o más llamadas a `ConductResearch` si el `research_brief` general aún no está completamente abordado.

---

## 24-12-25 Corrección de conexión WebSocket en componentes de progreso de investigación 🔌

Se corrigió el problema donde las notificaciones de progreso del Deep Researcher no se mostraban en el frontend debido a que los componentes QuestionSliderDialog y GapDevelopmentDialog no estaban conectados correctamente al WebSocket.

- **Cambio de useWebSocket a useWebSocketContext**: Se modificaron `src/components/QuestionSliderDialog.tsx` y `src/components/GapDevelopmentDialog.Dialog.tsx` para usar `useWebSocketContext` en lugar de `useWebSocket` directamente, permitiendo que reciban las actualizaciones de progreso enviadas por el backend a través de WebSocket.

---

## 24-12-25 Corrección de TypeError en supervisor_tools del DeepResearcher 🐞

Se corrigió un `TypeError: sequence item 0: expected str instance, list found` en la función `supervisor_tools` del `DeepResearcher` causado por un manejo incorrecto de los datos `raw_notes`.

- **Manejo correcto de listas en raw_notes**: Se modificó la lógica en `core/agents/deep_researcher.py` para aplanar correctamente las listas de `raw_notes` antes de concatenarlas, ya que `compress_research` devuelve `raw_notes` como una lista de cadenas.

---

## 26-12-25 Corrección de KeyError 'workspace_id' en ConceptualGraphProcessor 🐞

Se corrigió un `KeyError: 'workspace_id'` que ocurría en `knowledge_graph/conceptual_graph_processor.py` al intentar acceder directamente a `documents[0]['workspace_id']` y `documents[0]['account_id']`.

- **Acceso seguro a `workspace_id` y `account_id`**: Se modificó la función `process_documents_conceptually` en `knowledge_graph/conceptual_graph_processor.py` para acceder a `workspace_id` y `account_id` de forma segura desde el diccionario `metadata` de los documentos (`documents[0].get('metadata', {}).get('workspace_id')`). Esto evita el error cuando estas claves no están presentes directamente en el nivel superior del diccionario del documento, asignando `None` si no se encuentran.

---

## 26-12-25 Corrección de indentación de métodos en ConceptualGraphProcessor 🐞

Se corrigió un error de `AttributeError: 'ConceptualGraphProcessor' object has no attribute '_create_document_nodes'` causado por una indentación incorrecta de varios métodos al final del archivo.

- **Corrección de indentación**: Se ajustó la indentación de los métodos `_create_document_nodes`, `_process_single_document_for_node`, `_generate_document_summary` y `_generate_document_keywords` en [`knowledge_graph/conceptual_graph_processor.py`](knowledge_graph/conceptual_graph_processor.py) para que sean reconocidos correctamente como métodos de la clase `ConceptualGraphProcessor`.
- **Validación de clase**: Se verificó que los métodos ahora son accesibles desde instancias de la clase, permitiendo que el flujo de procesamiento de documentos funcione sin errores de atributo.

---

## 26-12-25 Depuración de Análisis y Descentralización de TTS 🎙️🚀

Se resolvieron problemas de visualización en los análisis de "Desarrollo de Brechas" e "Insights Proactivos", y se completó la descentralización de los botones de Texto a Voz (TTS) en todos los componentes de análisis.

- **Alineación de Datos en Deep Research**: Se modificaron `api/deep_research.py` y `api/gap_development.py` para devolver un objeto de reporte completo con `final_report`, `sources` y `recommendations`, asegurando que el frontend pueda renderizar todos los elementos correctamente.
- **Mejora en Proactive Insights**: Se actualizó la interfaz `ProactiveInsightResult` en `src/lib/models.ts` para incluir `kai_synthesis`, permitiendo la visualización de la síntesis de KAI en estos análisis.
- **Descentralización Completa de TTS**: Se implementaron botones TTS individuales (`SectionTTSButton`) en todos los componentes de análisis:
  - `DocumentAnalysis.tsx`
  - `NoteAnalysis.tsx`
  - `NoteCollectionAnalysis.tsx`
  - `DeepResearchAnalysis.tsx`
  - `ProactiveInsightAnalysis.tsx`
  - `ComprehensiveWebAnalysis.tsx`
  - `ScopedRagAnalysis.tsx`
- **Limpieza de Interfaz**: Se eliminó el botón TTS global del encabezado en `analysis-detail-dialog.tsx` para favorecer el control granular por sección, mejorando la usabilidad y modularidad del sistema.

---

## 26-12-25 Mejora en Visualización de Desarrollo de Brecha 🚀

Se ha mejorado significativamente la visualización del análisis de "Desarrollo de Brecha" (`DeepResearchAnalysis`), alineándola con la experiencia de chat y simplificando la interfaz.

- **Integración de `MarkdownRenderer`**: Se reemplazó el renderizado manual por `MarkdownRenderer`, permitiendo una visualización de texto enriquecida y consistente con el resto de la aplicación.
- **Citas Interactivas**: Se implementó la lógica para procesar referencias bibliográficas (`[1]`, `[2]`) y convertirlas en botones interactivos que despliegan información detallada de la fuente, utilizando el mismo sistema que en el chat.
- **Eliminación de Pestaña Redundante**: Se eliminó la pestaña de "Recomendaciones", integrando la información de manera más fluida y eliminando elementos innecesarios de la interfaz.
- **Adaptación de Tipos**: Se aseguró la compatibilidad de los tipos de fuentes del análisis con el sistema de renderizado de componentes compartidos.

---

## 26-12-25 Corrección de Propagación de Fuentes en Deep Research 🐛

Se solucionó un problema crítico donde el contenido del reporte de "Desarrollo de Brecha" no se visualizaba debido a la pérdida de datos de fuentes bibliográficas durante la generación del reporte y problemas de parsing en el frontend.

- **Propagación de Fuentes en Backend**: Se modificó la arquitectura del agente `DeepResearcher` (`core/agents/deep_researcher.py` y `state.py`) para que las fuentes recolectadas por los sub-investigadores se propaguen explícitamente a través del estado hasta el reporte final. Anteriormente, el supervisor intentaba extraer fuentes de mensajes que no contenían esa información.
- **Parsing Robusto en Frontend**: Se añadió lógica en `analysis-detail-dialog.tsx` para manejar casos donde el objeto `gapData` llega como una cadena JSON, asegurando que siempre se parsee correctamente antes de pasarlo al componente de visualización.
- **Información de Depuración en UI**: Se agregó un bloque de visualización de datos JSON crudos en `DeepResearchAnalysis.tsx` que se muestra cuando no hay contenido de informe, para facilitar el diagnóstico de problemas de datos.

---

## 26-12-25 Corrección de ReferenceError: apiClient is not defined 🐞

Descripcion general incluye solicitud de usuario y solucion propuesta.

- **Importación de apiClient**: Se añadió la importación de `apiClient` desde `@/lib/api` en el archivo `src/components/QuestionSliderDialog.tsx` para resolver el `ReferenceError` que impedía el inicio del deep researcher.
- **Verificación de la ruta**: Se verificó la ruta correcta del archivo `apiClient` en `src/lib/api.ts` para asegurar que la importación fuera exitosa.

---

## 26-12-25 Corrección de NameError: supervisor_messages is not defined en final_report_generation 🐞

Se corrigió un `NameError: name 'supervisor_messages' is not defined` en la función `final_report_generation` del `DeepResearcher`.

- **Acceso seguro a `supervisor_messages`**: Se modificó la función `final_report_generation` en `core/agents/deep_researcher.py` para acceder a `supervisor_messages` a través del objeto `state` (`state.get("supervisor_messages", [])`), asegurando que la variable esté siempre definida antes de ser utilizada.

---

## 26-12-25 Mejora en la granularidad del progreso de investigación en Deep Researcher 🚀

Se mejoró la granularidad del progreso de investigación en el componente `QuestionSliderDialog` para que el progreso avance de manera más continua y detallada durante la ejecución de las herramientas de investigación.

- **Mejora en `researcher_tools`**: Se modificó la función `researcher_tools` en `core/agents/deep_researcher.py` para enviar actualizaciones de progreso más precisas al frontend:
  - **Inicio de ejecución de herramientas**: Se añadió un `progress_callback` que envía el 70% del rango asignado al investigador, indicando que se están ejecutando las herramientas de investigación.
  - **Fin de ejecución de herramientas**: Se añadió un `progress_callback` que envía el 90% del rango asignado al investigador, indicando que las herramientas han terminado y el proceso está listo para la fase de síntesis.
- **Impacto en la experiencia de usuario**: Esta mejora proporciona al usuario una indicación visual más clara y granular del progreso durante la ejecución de las herramientas, reduciendo la sensación de que la barra de progreso se "congela" durante la investigación profunda.

---

## 26-12-25 Corrección de visualización incompleta de Insights Proactivos en el frontend 💡

Se corrigió el problema donde los insights proactivos no se visualizaban completamente en el frontend, faltaba mostrar información importante como la puntuación de confianza y otros datos relevantes.

- **Agregar visualización de confidence_score**: Se añadió la visualización de la puntuación de confianza (`confidence_score`) en un panel destacado que muestra el porcentaje de confianza con códigos de color (verde para alta, amarillo para media, rojo para baja).
- **Mejorar mapeo de tipos de insight**: Se implementó la función `getInsightTypeLabel()` para traducir los tipos de insight del inglés al español ('duplicidad' → 'Duplicidad', 'sinergia' → 'Sinergia', etc.).
- **Agregar resumen de métricas clave**: Se creó un encabezado con 3 tarjetas que muestran: tipo de insight, puntuación de confianza, y número de elementos relacionados.
- **Mejorar robustez de datos relacionados**: Se mejoró la visualización de elementos relacionados para manejar casos donde falten campos como `title`, `content`, `description`, etc., mostrando valores por defecto apropiados.
- **Mejorar manejo de errores**: Se añadieron verificaciones para campos opcionales y casos donde los datos podrían estar incompletos o malformados.
- **Agregar indicadores visuales**: Se añadieron badges para mostrar el tipo de cada elemento relacionado y mejorar la experiencia visual.

---

## 26-12-25 Implementación de Análisis General en Colecciones y Notas 📚

Se ha implementado un nuevo apartado de "Análisis General" extenso para los análisis de colecciones de documentos y colecciones de notas, equiparándolos en profundidad con el análisis de documentos individuales.

- **Actualización de `AdvancedTextAnalyzer`**: Se modificó el prompt y el modelo Pydantic en `utils/advanced_text_analyzer.py` para incluir los campos `general_analysis` (extenso y profundo) y `authorial_tone` en el análisis de colecciones.
- **Actualización de Modelos Frontend**: Se actualizaron las interfaces `CollectionAnalysis` y `NoteCollectionAnalysisResult` en `src/lib/models.ts` para soportar los nuevos campos.
- **Nueva Pestaña en `CollectionAnalysis`**: Se añadió una pestaña dedicada "Análisis General" en `src/app/(dashboard)/analysis/CollectionAnalysis.tsx` para mostrar el análisis extenso y el tono del autor.
- **Nueva Pestaña en `NoteCollectionAnalysis`**: Se añadió una pestaña dedicada "Análisis General" en `src/app/(dashboard)/analysis/NoteCollectionAnalysis.tsx` con la misma funcionalidad, asegurando consistencia en la experiencia de usuario.
- **Verificación de Backend**: Se confirmó que `api/analysis.py` utiliza la función actualizada `analyze_collection` para ambos tipos de análisis, garantizando que los datos fluyan correctamente desde el LLM hasta la base de datos y el frontend.

---

## 26-12-25 Notificación inmediata de subida de archivos al LLM 📤

Se ha implementado una mejora para que el LLM sea notificado inmediatamente cuando el usuario sube un archivo al chat, permitiéndole reconocer el documento sin necesidad de una mención explícita posterior.

- **Frontend (`CommonChat.tsx`)**: Se modificó la función `handleFileUpload` para incluir el `thread_id` en la solicitud de subida de archivos (`/api/documents/upload-chat-document`).
- **Backend (`api/documents.py`)**:
  - Se actualizó el endpoint `upload_chat_document_endpoint` para aceptar el parámetro `thread_id`.
  - Se implementó la lógica para inyectar un mensaje de sistema en el historial del chat (`PostgresChatMessageHistory`) una vez que el archivo se ha procesado correctamente. El mensaje tiene el formato: "Sistema: El usuario ha subido el archivo '{file_name}' (ID: {document_id}) al contexto del chat."

---

## 26-12-25 Reorganización de la pestaña "Temas" en Análisis de Colección 🎨

Se modificó la disposición de los componentes "Conceptos Centrales" y "Relaciones Conceptuales" en la pestaña "Temas" de la vista de "Análisis de Colección" para que se muestren de forma vertical, uno debajo del otro, en lugar de en un diseño de dos columnas.

- **Eliminación de diseño en columnas**: Se eliminaron las clases de CSS `grid grid-cols-1 md:grid-cols-2 gap-6` del contenedor principal de "Conceptos Centrales" y "Relaciones Conceptuales" en `src/app/(dashboard)/analysis/CollectionAnalysis.tsx`.
- **Ajuste de espaciado**: Se añadió un margen inferior (`mb-6`) al contenedor de "Conceptos Centrales" para mejorar la separación visual entre ambas secciones.

---

## 26-12-25 Renderizado de Markdown en Sidebar de Detalles del Nodo 📝

Se implementó el renderizado de contenido Markdown en el `NodeDetailsSidebar` para mejorar la presentación de la información detallada de los nodos en el grafo de conocimiento.

- **Integración de `react-markdown`**: Se añadió la importación de `ReactMarkdown` y `remark-gfm` en `src/components/KnowledgeGraph/NodeDetailsSidebar.tsx`.
- **Aplicación de `ReactMarkdown`**: Se reemplazaron los elementos de texto plano (`<p>`, `<div>`) por el componente `ReactMarkdown` en las secciones donde se muestran descripciones, textos completos y propiedades adicionales del nodo, permitiendo la interpretación y visualización de contenido formateado con Markdown.

---

## 26-12-25 Implementación de resaltado de texto en búsqueda de colecciones 🔍

Se implementó la funcionalidad para resaltar y desplazar automáticamente la vista al fragmento de texto encontrado al abrir un documento desde los resultados de búsqueda en una colección.

- **Modificación de `PreviewDocumentDialog`**: Se actualizó el componente para aceptar una propiedad `highlightText`. Se añadió lógica para buscar este texto dentro del contenido del documento, resaltarlo visualmente con una etiqueta `<mark>` y desplazar la vista automáticamente hacia él utilizando `scrollIntoView`.
- **Actualización de `DocumentCollectionDisplay`**: Se modificó el manejo del clic en los resultados de búsqueda (`onResultClick`) para capturar el fragmento de texto encontrado y pasarlo al `PreviewDocumentDialog` a través de la nueva propiedad `highlightText`.

---

## 26-12-25 Limpieza de Markdown en Conceptos Centrales 🧹

Se eliminaron los asteriscos de markdown (**) que aparecían en las etiquetas de los conceptos centrales en el análisis de colección, mejorando la legibilidad.

- **Limpieza de etiquetas**: Se añadió `.replace(/\*\*/g, '')` al renderizado de la etiqueta en `src/app/(dashboard)/analysis/CollectionAnalysis.tsx` para eliminar los caracteres de negrita de markdown visualizados incorrectamente.

---

## 26-12-25 Añadir Sidebar de Información en Grafos de Conocimiento ℹ️

Se añadió una barra lateral informativa en la página de grafos de conocimiento, accesible mediante un botón "i", para mantener la consistencia con el resto de la aplicación y proporcionar contexto al usuario.

- **Modificación de `src/app/(dashboard)/analysis/graph/page.tsx`**:
  - Se importaron los componentes `Sheet`, `SheetContent`, `SheetHeader`, `SheetTitle`, `SheetDescription` desde `@/components/ui/sheet`.
  - Se añadió el estado `isInfoSheetOpen` para controlar la visibilidad del sidebar.
  - Se agregó un botón con el icono `Info` en el encabezado de la página que activa el sidebar.
  - Se implementó el componente `Sheet` con información detallada sobre el Grafo de Conocimiento, explicando sus modos de procesamiento (Híbrido y Conceptual), funcionalidades clave y consejos de uso.

---

## 26-12-25 Integración de Resultados de Análisis Web y Deep Research en Dashboard 📊

Se ha completado la integración de los resultados generados por `ComprehensiveWebAnalysisTool` y `DeepResearchTool` en la página principal de análisis, asegurando su persistencia, filtrado y correcta visualización.

- **Persistencia en Base de Datos**:
  - Se modificó `tools/comprehensive_web_analysis_tool.py` para guardar los reportes generados en la tabla `AnalysisTask` con el tipo `comprehensive_web_analysis`.
  - Se modificó `tools/deep_research_tool.py` para guardar los resultados de investigación en la tabla `AnalysisTask` con el tipo `gap_development`.
- **Actualización del Dashboard de Análisis**:
  - Se actualizó `src/app/(dashboard)/analysis/page.tsx` para incluir `comprehensive_web_analysis` y `deep_research` en los filtros de tipo y en las funciones auxiliares de visualización (iconos, etiquetas, colores).
- **Visualización Detallada**:
  - Se verificó y validó que `AnalysisDetailDialog` maneje correctamente los nuevos tipos de análisis.
  - Se confirmó la correcta implementación de los componentes `DeepResearchAnalysis` y `ComprehensiveWebAnalysis` para mostrar reportes, fuentes, insights y preguntas de manera estructurada.
  
  ---

  ## 26-12-25 Corrección de errores de integración con LiteLLM en Deep Researcher 🐛

  Se corrigieron varios errores relacionados con la integración de LiteLLM en el agente Deep Researcher, incluyendo nombres de herramientas duplicados, límites de contexto excedidos y problemas de configuración de proveedores.

  - **Renombramiento de herramienta think_tool**: Se cambió el nombre de la herramienta `think_tool` a `deep_research_think_tool` en `core/agents/deep_researcher_utils.py` para evitar conflictos con otras herramientas que puedan tener el mismo nombre.
  - **Reducción del límite de tokens de entrada**: Se redujo el `max_input_tokens` de 200000 a 150000 en `core/agents/deep_researcher_config.py` para prevenir errores de contexto excedido en proveedores como OpenRouter.
  - **Mejora en el pruning de mensajes**: Se hizo más agresivo el pruning de mensajes en `core/utils/llm_utils.py`, reduciendo el espacio reservado para resúmenes del 50% al 30% del límite de tokens.
  - **Configuración específica para OpenRouter**: Se añadió configuración específica para el proveedor OpenRouter en `core/llm_manager.py`, configurándolo como proxy de OpenAI para mejorar la compatibilidad.
  - **Actualización de referencias**: Se actualizaron todas las referencias a `think_tool` por `deep_research_think_tool` en `core/agents/deep_researcher.py` y `core/agents/deep_researcher_utils.py`.

  ---

  ## 26-12-25 Corrección del fallback en DeepResearcher
  
  Se corrigió el problema donde el Fast LLM fallaba al generar el research brief y en lugar de usar el Main LLM como fallback, intentaba de nuevo con el Fast LLM.
  
  - **Modificación en write_research_brief**: Se cambió la lógica de fallback para usar el Main LLM cuando el Fast LLM no genera el brief correctamente.
  - **Modificación en clarify_with_user**: Se agregó la inicialización del Main LLM y se cambió el fallback similarmente.
  
  ---
  
  ## 26-12-25 Supresión de mensajes de debug de LiteLLM y mejora de manejo de errores 🐛
  
  Se corrigieron los mensajes repetidos "Give Feedback / Get Help" de LiteLLM que aparecían en los logs del contenedor, mejorando la experiencia de desarrollo al reducir el ruido en los logs.
  
  - **Desactivación del modo debug de LiteLLM**: Se reemplazó `litellm._turn_on_debug()` por `litellm.suppress_debug_info = True` en `core/llm_manager.py` para suprimir los mensajes de feedback de errores.
  - **Mejora en mensajes de error de inicialización**: Se añadieron mensajes informativos en español en la función `initialize_llms` para guiar al usuario sobre la configuración correcta de API keys cuando falla la inicialización.
  - **Reducción de verbosidad en logs**: Se cambió `verbose=True` a `verbose=False` en la inicialización del fast LLM para reducir logs innecesarios.
  
  ---
  
  ## 26-12-25 Prevención de bucle infinito en clarificación del Deep Researcher 🐛
  
  Se implementó un contador de intentos de clarificación para evitar que el agente Deep Researcher quede atrapado en un bucle infinito solicitando aclaraciones repetidamente cuando el modelo LLM utilizado no maneja bien las instrucciones de clarificación.
  
  - **Adición de campo clarification_attempts**: Se agregó el campo `clarification_attempts` al estado `AgentState` en `core/agents/deep_researcher_state.py` para rastrear el número de intentos de clarificación realizados.
  - **Lógica de prevención de bucle**: Se modificó la función `clarify_with_user` en `core/agents/deep_researcher.py` para verificar si los intentos exceden 2, forzando la continuación del proceso de investigación si es así.
  - **Incremento del contador**: Se actualizaron todas las salidas de la función `clarify_with_user` para incrementar el contador de intentos en cada llamada.

---

## 26-12-25 Corrección de errores de contexto excedido en DeepResearcher 🐛

Se corrigieron los errores `litellm.BadRequestError: OpenrouterException` que ocurrían en los nodos `clarify_with_user` y `write_research_brief` del agente `DeepResearcher` debido a que el contexto de entrada excedía el límite de tokens del LLM.

- **Poda proactiva de mensajes en `clarify_with_user`**: Se implementó la función `prune_messages_to_fit_token_limit` en el nodo `clarify_with_user` de `core/agents/deep_researcher.py` para podar el historial de mensajes antes de construir el prompt, asegurando que no se exceda el `max_input_tokens` configurado.
- **Poda proactiva de mensajes en `write_research_brief`**: Se implementó la función `prune_messages_to_fit_token_limit` en el nodo `write_research_brief` de `core/agents/deep_researcher.py` para podar el historial de mensajes antes de construir el prompt, asegurando que no se exceda el `max_input_tokens` configurado.

---

## 26-12-25 Corrección de `ValueError: "DeepResearchTool" object has no field "progress_callback"` 🐞

Se corrigió el error `ValueError: "DeepResearchTool" object has no field "progress_callback"` que ocurría al intentar asignar directamente el `progress_callback` a la herramienta `DeepResearchTool` en `core/agent.py`. Este error se debía a que `DeepResearchTool` espera el `progress_callback` a través de la configuración de ejecución (`RunnableConfig`) y no como un atributo directo.

- **Importación de `DeepResearchTool` y `RunnableConfig`**: Se importaron las clases necesarias en `core/agent.py`.
- **Eliminación de inyección directa de atributos**: Se eliminó la asignación directa de `account_id`, `workspace_id`, `telegram_id` y `thread_id` al objeto `selected_tool`.
- **Eliminación de inyección directa de `progress_callback`**: Se eliminó la asignación directa de la función `progress_callback` al objeto `selected_tool`.
- **Creación de `RunnableConfig`**: Se creó una instancia de `RunnableConfig` que encapsula el `progress_callback` y los IDs de contexto (`account_id`, `workspace_id`, `telegram_id`, `thread_id`, `task_id`).
- **Modificación de la invocación de la herramienta**: La llamada a `selected_tool.ainvoke()` se modificó para aceptar la `run_config` como parámetro, asegurando que el `progress_callback` y el contexto se pasen correctamente a `DeepResearchTool` y otras herramientas que lo requieran a través de la configuración.

---

## 26-12-25 Corrección de error 404 en la búsqueda de grafos 🔍

Se corrigió un error 404 que ocurría al intentar realizar búsquedas en el grafo de conocimiento desde el frontend. El problema se debía a que el frontend estaba llamando a una URL incorrecta para el endpoint de búsqueda.

- **Verificación del endpoint en el backend**: Se confirmó que el endpoint `@router.post("/search-graph")` está definido en `api/knowledge_graph.py` y que el router se incluye en `api/main.py` con el prefijo `/api/knowledge-graph`.
- **Corrección de la URL en el frontend**: Se modificó la llamada a la API en `src/app/(dashboard)/analysis/graph/page.tsx` para que la función `searchGraph` utilice la URL correcta `/api/knowledge-graph/search-graph`, resolviendo así el error 404.

---

## 26-12-25 Optimización del pool de conexiones de la base de datos y resolución de errores 401 ⚙️

Se abordó la saturación del pool de conexiones de SQLAlchemy, que causaba `sqlalchemy.exc.TimeoutError` y, como consecuencia, `fastapi.exceptions.HTTPException: 401` en la validación de credenciales.

- **Aumento del tamaño del pool de conexiones**: Se modificó `core/database.py` para aumentar `pool_size` a 10 y `max_overflow` a 20 en la configuración de `create_async_engine`.
- **Aumento del tiempo de espera del pool**: Se incrementó `pool_timeout` a 60 segundos en `core/database.py` para dar más margen al sistema para adquirir una conexión.
- **Impacto en la autenticación**: Se determinó que los errores 401 en `utils/security.py` eran un síntoma directo de la saturación del pool, ya que la validación de credenciales no podía acceder a la base de datos. La solución del pool de conexiones debería resolver indirectamente estos errores de autenticación.

---

## 26-12-25 Mejora en la búsqueda textual de grafos 🔍

Se mejoró la capacidad de la búsqueda textual en el grafo de conocimiento para encontrar nodos de manera más efectiva, incluso cuando se busca por el nombre exacto. Anteriormente, la búsqueda era restrictiva y no incluía todos los tipos de nodos ni propiedades relevantes.

- **Ampliación del índice Full-Text para nodos**: Se modificó la función `_create_fulltext_indexes` en `knowledge_graph/graph_integration.py` para incluir una gama más amplia de tipos de nodos (`DOCUMENT`, `PERSON`, `ORGANIZATION`, `EVENT`, `LOCATION`, `PRODUCT`, `TOPIC`, `CHAT_MESSAGE`, `USER_MEMORY`) y propiedades (`n.name`, `n.title`, `n.description`, `n.concept`, `n.full_text`, `n.category`, `n.summary`, `n.content`) en el índice `node_fulltext_index`.
- **Modificación de la consulta Cypher de búsqueda Full-Text**: Se ajustó la consulta Cypher en el método `search_knowledge_graph` de `knowledge_graph/graph_integration.py`. Se eliminó la restricción de tipo de nodo `CONCEPTUAL_QUOTE` en el `OPTIONAL MATCH` y se aseguró que el filtro `dataset_name` se aplicara correctamente a los nodos relacionados. Esto permite que la búsqueda encuentre nodos de cualquier tipo indexado y sus relaciones.

---

## 26-12-25 Optimización del manejo de sesiones de base de datos en el flujo de grafos 🚀

Se refactorizó el flujo de procesamiento de grafos para asegurar que solo se utilice una sesión de base de datos de PostgreSQL por solicitud de FastAPI, inyectada y gestionada por el sistema de dependencias. Esto resuelve la saturación del pool de conexiones (`sqlalchemy.exc.TimeoutError`) y los errores de autenticación 401 que eran un síntoma.

- **Modificación de `_fetch_documents_from_db`**: En `knowledge_graph/graph_integration.py`, la función `_fetch_documents_from_db` ahora acepta un parámetro `db_session: AsyncSession` y elimina la creación de una nueva sesión, utilizando la sesión proporcionada.
- **Modificación de `process_documents`**: En `knowledge_graph/graph_integration.py`, la función `process_documents` ahora acepta un parámetro `db_session: AsyncSession` y lo pasa a la llamada a `self._fetch_documents_from_db`.
- **Modificación de `process_documents_flow`**: En `utils/knowledge_graph_service.py`, la función `process_documents_flow` ahora acepta un parámetro `db_session: AsyncSession` y lo pasa a la llamada a `self.graph_integration.process_documents`.
- **Actualización de endpoints de FastAPI**: Los endpoints `process_knowledge_graph_optimized` y `process_knowledge_graph_with_cooccurrence` en `api/knowledge_graph.py` ahora pasan la sesión `db` (inyectada por `Depends(get_db_session)`) a `kg_service.process_documents_flow`.

---

## 26-12-25 Corrección de NameError: AsyncSession no definida en GraphIntegration 🐞

Se corrigió un `NameError: name 'AsyncSession' is not defined` que ocurría en `knowledge_graph/graph_integration.py` al no tener importada la clase `AsyncSession`.

- **Importación de `AsyncSession`**: Se añadió la importación de `AsyncSession` desde `sqlalchemy.ext.asyncio` en `knowledge_graph/graph_integration.py`.

---

## 26-12-25 Corrección de bucle infinito en clarificación del Deep Researcher 🐛

Se corrigió un bucle infinito en la clarificación del Deep Researcher que ocurría porque el estado `final_report` no se actualizaba correctamente al forzar el avance de la investigación.

- **Adición de `max_clarification_attempts`**: Se añadió el campo `max_clarification_attempts` a la clase `Configuration` en `core/agents/deep_researcher_config.py` con un valor por defecto de 3, permitiendo controlar el número máximo de intentos de clarificación.
- **Actualización explícita de `final_report`**: Se modificó la función `clarify_with_user` en `core/agents/deep_researcher.py` para que, al exceder el número máximo de intentos de clarificación o al no necesitar más clarificación, establezca explícitamente `final_report: None` en el estado retornado. Esto asegura que la función `should_start_research` evalúe correctamente el estado y permita que el grafo avance a `write_research_brief` en lugar de volver a `await_user_clarification`.

---

## 27-12-25 Corrección de expresión regular inválida en InlineMarkdownRenderer 🐞

Se corrigió un error de compilación `Module parse failed: Invalid regular expression` causado por una expresión regular malformada en el componente `InlineMarkdownRenderer`.

- **Corrección de regex**: Se arregló la expresión regular en `src/components/InlineMarkdownRenderer.tsx` para que coincida correctamente con enlaces anidados de Markdown, cambiando `/\[([^\]]+)\]\(([^\)]+]\)([^\]]+)\]\(([^\)]+)\)/g` por `/\[([^\]]+)\]\(([^\)]+)\)\[([^\]]+)\]\(([^\)]+)\)/g`.
- **Eliminación de código duplicado**: Se removió la función `sanitizeMarkdown` duplicada y el código redundante, consolidando la lógica en una sola función.

---

## 27-12-25 Optimización de animaciones en visualización de grafos de conocimiento 🎨

Se mejoró la experiencia de usuario en la visualización de grafos de conocimiento para que los nodos y relaciones se posicionen inmediatamente sin animaciones prolongadas, mientras que las animaciones solo ocurren durante el arrastre manual de nodos.

- **Reducción de tiempo de estabilización**: Se disminuyeron los parámetros de estabilización en `src/components/KnowledgeGraph/GraphVisualization.tsx` de 200 iteraciones con 200ms de intervalo a 50 iteraciones con 50ms de intervalo, acelerando el posicionamiento inicial.
- **Habilitación de física durante arrastre**: Se añadieron eventos `dragStart` y `dragEnd` para activar la física de vis-network solo durante el arrastre de nodos, permitiendo movimientos suaves, y desactivarla después con un retraso de 500ms para estabilizar la posición.

---

## 27-12-25 Conversión de KnowledgeSearchTool a herramienta de función con inyección de argumentos 🛠️

Se convirtió la clase `KnowledgeSearchTool` a una función decorada con `@tool` para resolver errores de validación de Pydantic relacionados con campos requeridos no proporcionados.

- **Conversión a función tool**: Se transformó `KnowledgeSearchTool` de clase a función en `tools/knowledge_search_tool.py`, utilizando `@tool` y `InjectedToolArg` para `account_id`, `workspace_id`, `team_id` y `telegram_id`.
- **Actualización de importaciones**: Se modificó `core/agents/deep_researcher_utils.py` para importar `knowledge_search` en lugar de `KnowledgeSearchTool`, y se actualizó `core/tools.py` para remover la herramienta de la lista de instanciación ya que ahora se importa directamente.
- **Campo opcional en KnowledgeGraphTool**: Se hizo `account_id` opcional en `tools/knowledge_graph_tool.py` para evitar errores similares de validación.

---

## 27-12-25 Corrección de reconstrucción de contenido de documentos en grafo de conocimiento 🐞

Se corrigió un error en la reconstrucción del contenido de documentos en el grafo de conocimiento que ocurría cuando los documentos no tenían un `workspace_id` asignado. Anteriormente, la lógica de filtrado no manejaba correctamente el caso de `workspace_id` nulo, lo que provocaba que la función `_reconstruct_document_content` devolviera una lista vacía y, consecuentemente, un error de "No se pudo reconstruir contenido de documentos.".

- **Modificación de `get_full_document_content`**: Se ajustó la lógica en la función `get_full_document_content` dentro de `core/memory_manager.py`. Ahora, si el `workspace_id` proporcionado es `None` (o una cadena vacía después de la validación), la consulta SQL para recuperar los chunks del documento incluirá explícitamente la cláusula `workspace_id IS NULL`. Esto asegura que los documentos sin un `workspace_id` asignado sean correctamente recuperados y su contenido pueda ser reconstruido.

---

## 27-12-25 Corrección de reconstrucción de contenido de documentos en grafo de conocimiento (2) 🐞

Se corrigió un error persistente en la reconstrucción del contenido de documentos en el grafo de conocimiento. El problema radicaba en que el `workspace_id` no se estaba propagando correctamente a la función `get_full_document_content`.

- **Modificación de `_reconstruct_document_content`**: Se ajustó la lógica en la función `_reconstruct_document_content` dentro de `knowledge_graph/graph_integration.py`. Ahora, se extrae el `workspace_id` de cada documento y se pasa explícitamente a la llamada a `get_full_document_content`. Esto asegura que la reconstrucción del contenido se realice en el contexto del workspace correcto, evitando que la función devuelva una lista vacía y soluciona el error "No se pudo reconstruir contenido de documentos.".

---

## 27-12-25 Corrección de SyntaxError en knowledge_search_tool.py 🐞

Se corrigió un `SyntaxError: parameter without a default follows parameter with a default` en `tools/knowledge_search_tool.py`. El error se debía a que el parámetro `account_id` no tenía un valor por defecto y estaba definido después de otros parámetros que sí lo tenían.

- **Reordenamiento de parámetros**: Se movió el parámetro `account_id` al principio de la lista de parámetros de la función `knowledge_search`, antes de cualquier parámetro con valor por defecto, para cumplir con las reglas de sintaxis de Python.

---

## 27-12-25 Corrección de ValidationError en GraphCypherGeneratorTool 🐞

Se corrigió un `pydantic_core._pydantic_core.ValidationError` que ocurría al instanciar `GraphCypherGeneratorTool` sin proporcionar el campo requerido `account_id`.

- **Campo `account_id` opcional**: Se modificó la definición de la clase `GraphCypherGeneratorTool` en `tools/graph_cypher_generator_tool.py` para que el campo `account_id` sea opcional (`Optional[str] = None`). Esto permite que la herramienta se instancie sin errores y que el `account_id` se inyecte más tarde en el flujo de ejecución del agente.

---

## 27-12-25 Corrección de ValidationError en knowledge_search 🐞

Se corrigió un `pydantic_core._pydantic_core.ValidationError` que ocurría al invocar la herramienta `knowledge_search` sin que el `account_id` fuera inyectado correctamente.

- **Campo `account_id` opcional y validación en tiempo de ejecución**: Se modificó la definición de la función `knowledge_search` en `tools/knowledge_search_tool.py` para que el parámetro `account_id` sea opcional. Además, se añadió una validación al inicio de la función para lanzar un `ValueError` si `account_id` es `None`, asegurando que la herramienta falle con un error claro si el `account_id` no se inyecta correctamente en tiempo de ejecución.

---

## 27-12-25 Corrección de inyección de `account_id` en herramientas de Deep Researcher 🛠️

Se corrigió un error de validación de Pydantic que ocurría porque el `account_id` no se estaba inyectando correctamente en las herramientas `GraphCypherGeneratorTool` y `knowledge_search` dentro del sub-grafo del `DeepResearcher`.

- **Inyección explícita de `account_id` en `GraphCypherGeneratorTool`**: Se modificó la función `get_all_tools` en `core/agents/deep_researcher_utils.py` para extraer el `account_id` del `RunnableConfig` y pasarlo explícitamente al constructor de `GraphCypherGeneratorTool`.
- **Restablecimiento de `account_id` como requerido en `knowledge_search`**: Se revirtió el cambio en `tools/knowledge_search_tool.py`, volviendo a hacer que el parámetro `account_id` sea requerido y confiando en la inyección de `InjectedToolArg` por parte de LangGraph.
- **Restablecimiento de `account_id` como requerido en `GraphCypherGeneratorTool`**: Se revirtió el cambio en `tools/graph_cypher_generator_tool.py`, volviendo a hacer que el campo `account_id` sea requerido.

---

## 27-12-25 Corrección de `AttributeError: 'NoneType' object has no attribute 'execute'` en `ConceptualProcessingTool` 🐞

Se corrigió un error `AttributeError: 'NoneType' object has no attribute 'execute'` que ocurría en la herramienta `ConceptualProcessingTool` porque no se estaba pasando una sesión de base de datos (`db_session`) a la función `process_documents_flow`.

- **Inyección de `db_session`**: Se modificó la herramienta `ConceptualProcessingTool` en `tools/conceptual_processing_tool.py` para que obtenga una sesión de base de datos usando `get_db_session` de `core.dependencies` y la pase explícitamente a `knowledge_graph_service.process_documents_flow`. Esto asegura que las operaciones de base de datos dentro del flujo de procesamiento del grafo de conocimiento tengan una sesión de base de datos válida.

---

## 27-12-25 Corrección de `NameError: name 'logging' is not defined` en `conceptual_processing_tool.py` 🐞

Se corrigió un `NameError: name 'logging' is not defined` que ocurría en `tools/conceptual_processing_tool.py` porque el módulo `logging` no había sido importado antes de ser utilizado.

- **Importación de `logging`**: Se añadió la línea `import logging` al principio del archivo `tools/conceptual_processing_tool.py` para asegurar que el módulo `logging` esté disponible cuando se inicializa el logger.

---

## 27-12-25 Corrección de `ValidationError` en `knowledge_search` por falta de `account_id` 🐞

Se corrigió un `pydantic_core._pydantic_core.ValidationError` que ocurría en la herramienta `knowledge_search` porque el `account_id` no se estaba inyectando correctamente. El enfoque de usar `InjectedToolArg` no funcionó como se esperaba dentro del sub-grafo del `DeepResearcher`.

- **Conversión a Clase `BaseTool`**: Se convirtió la herramienta `knowledge_search` de una función decorada con `@tool` a una clase `KnowledgeSearchTool` que hereda de `BaseTool`. Esto permite un control explícito sobre su instanciación.
- **Inyección Explícita de Dependencias**: Se modificó la función `get_all_tools` en `core/agents/deep_researcher_utils.py` para instanciar `KnowledgeSearchTool` explícitamente, pasando los valores de `account_id` y `workspace_id` extraídos del `RunnableConfig`. Esto elimina la dependencia de la inyección automática y asegura que la herramienta siempre reciba los parámetros necesarios.

---

## 27-12-25 Corrección de `ValidationError` en `knowledge_search` (Intento 2) 🐞

Se corrigió un `pydantic_core._pydantic_core.ValidationError` persistente en las herramientas `knowledge_search` y `graph_cypher_generator_tool` dentro del sub-grafo del `DeepResearcher`. El problema se debía a que el `account_id` y `workspace_id` no se estaban inyectando correctamente en el constructor de las herramientas.

- **Inyección de `account_id` y `workspace_id` en `KnowledgeSearchTool`**: Se modificó la función `get_all_tools` en `core/agents/deep_researcher_utils.py` para pasar explícitamente `account_id` y `workspace_id` al constructor de `KnowledgeSearchTool`.
- **Inyección de `account_id` y `workspace_id` en `GraphCypherGeneratorTool`**: Se modificó la función `get_all_tools` en `core/agents/deep_researcher_utils.py` para pasar explícitamente `account_id` y `workspace_id` al constructor de `GraphCypherGeneratorTool`.
- **Actualización de `KnowledgeSearchTool`**: Se actualizó la clase `KnowledgeSearchTool` en `tools/knowledge_search_tool.py` para aceptar `account_id` y `workspace_id` en su constructor y utilizarlos en el método `_run`.
- **Actualización de `GraphCypherGeneratorTool`**: Se actualizó la clase `GraphCypherGeneratorTool` en `tools/graph_cypher_generator_tool.py` para aceptar `account_id` y `workspace_id` en su constructor y utilizarlos en el método `_arun`.

---

## 28-12-25 Implementación de análisis de notas en Workspaces 🚀

Se ha añadido la funcionalidad para analizar notas directamente desde la página de detalles de un workspace, permitiendo obtener insights tanto de notas individuales como del conjunto de notas del espacio de trabajo.

- **Botón de Análisis General**: Se añadió un botón "Analizar Notas" en el encabezado de la sección de notas del workspace para procesar todas las notas cargadas.
- **Acciones en Notas Individuales**: Cada tarjeta de nota ahora incluye un menú de acciones con opciones para ver el detalle de la nota y ejecutar un análisis individual.
- **Visualización de Resultados**: Se integró el componente `AnalysisDetailDialog` para mostrar los resultados de los análisis generados (insights, resúmenes, etc.) sin salir de la página del workspace.
- **Lógica de Integración con API**: Se implementaron los controladores `handleAnalyzeAllNotes` y `handleAnalyzeSingleNote` utilizando los endpoints `/api/analyze-note-collection` y `/api/analyze-note`.

---

## 28-12-25 Corrección de TypeError en ReactMarkdown en NoteCollectionAnalysis 🐞

Se corrigió un `TypeError` en `src/app/(dashboard)/analysis/NoteCollectionAnalysis.tsx` donde el componente `ReactMarkdown` recibía un objeto en lugar de una cadena de texto para la propiedad `children`.

- **Conversión a String**: Se modificó la línea `analysis.kai_synthesis` para que se convierta explícitamente a `String(analysis.kai_synthesis)` antes de pasarlo al componente `ReactMarkdown`. Esto asegura que el componente reciba el tipo de dato esperado y resuelve el error.

---

## 28-12-25 Solución a Error 401 Client Error: Unauthorized en GitHubRepoTool 🔑

Se diagnosticó y propuso una solución para el error `401 Client Error: Unauthorized` al intentar acceder a repositorios de GitHub mediante `GitHubRepoTool`. Este error indica que la aplicación no tiene los permisos necesarios para acceder al repositorio.

- **Causa del problema**: Se identificó que el `github_token` no se estaba proporcionando correctamente a la herramienta, ya sea porque no se enviaba en la solicitud POST a `/api/collections`, la variable de entorno `GITHUB_TOKEN` no estaba configurada en el contenedor `kognito_core`, o el token utilizado era inválido/caducado o no tenía los scopes adecuados.
- **Solución propuesta**:
  1. **Obtener un token de acceso personal de GitHub**: Generar un nuevo token con los scopes necesarios (al menos `repo` para repositorios privados o `public_repo` para públicos).
  2. **Añadir el token al archivo `.env`**: Incluir la línea `GITHUB_TOKEN=tu_token_personal_de_github` en el archivo `.env` en la raíz del proyecto.
  3. **Reconstruir y reiniciar los contenedores de Docker**: Ejecutar `docker-compose down` y luego `docker-compose up --build` para aplicar los cambios.

- **Impacto**: Al asegurar que el `GITHUB_TOKEN` esté correctamente configurado y sea válido, el `kognito_core` podrá autenticarse exitosamente con la API de GitHub, permitiendo que `GitHubRepoTool` realice sus operaciones sin errores de autorización.

---

## 28-12-25 Corrección de header de autorización para tokens de GitHub 🔑

Se corrigió el error 401 Unauthorized al acceder a repositorios de GitHub cambiando el header de autorización de 'token' a 'Bearer' para tokens de acceso personal de GitHub.

- **Actualización del header de autorización**: Se cambió 'Authorization': f'token {self.github_token}' por 'Authorization': f'Bearer {self.github_token}' en ambas funciones **init** y _arun de tools/github_repo_tool.py para usar el formato correcto para fine-grained PATs.

---

## 28-12-25 Refuerzo de contención de texto, mejora de Resumen Ejecutivo y Estabilización de Procesamiento 🚀

Se aplicaron medidas integrales para mejorar la visualización de análisis, enriquecer los reportes técnicos y asegurar la estabilidad del procesamiento de grafos.

- **Corrección de Desbordamientos (UI)**:
  - En `src/app/(dashboard)/analysis/CodeAnalysis.tsx`, se añadieron clases `w-full min-w-0` y la propiedad CSS `[word-break:break-word]` junto con `break-words` y `overflow-hidden` en todas las secciones críticas (Resumen, Arquitectura, Dependencias y Calidad).
  - En `src/app/(dashboard)/analysis/analysis-detail-dialog.tsx`, se restringió el ancho del contenedor con `max-w-full min-w-0 overflow-hidden` y se corrigió el anidamiento de etiquetas en `DialogDescription` usando `asChild`.
- **Enriquecimiento del Resumen Ejecutivo (Backend)**: Se actualizó el prompt en `utils/advanced_code_analyzer.py` para que el análisis incluya una reseña de la aplicación y sus funcionalidades principales.
- **Robustez en Procesamiento por Lotes (Backend)**:
  - Se corrigieron los validadores de respuesta en `knowledge_graph/conceptual_graph_processor.py` para soportar arrays JSON y eliminar bloques de código markdown.
  - Se optimizó la concurrencia en `_create_parallel_batch_tasks` usando un semáforo (`asyncio.Semaphore`) para procesar todos los lotes sin omisiones y con mayor estabilidad.

---

## 29-12-25 Configuración flexible de Rate Limiting y límites de tokens para LLMs ⚙️🚀

 Se implementaron variables de entorno para permitir la desactivación y configuración granular del rate limiting en todos los LLMs, así como la personalización del límite máximo de tokens para los reportes de Deep Research.

- **Nuevas variables de entorno**: Se agregaron `RATE_LIMIT_ENABLED`, `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_PER_SECONDS` y `DEEP_RESEARCH_MAX_TOKENS` a [`core/config.py`](core/config.py) para un control centralizado.
- **Desactivación global de Rate Limit**: Se modificó la clase `RateLimiter` en [`core/llm_manager.py`](core/llm_manager.py) para permitir omitir las esperas si el rate limit está desactivado, optimizando la velocidad de respuesta cuando no hay restricciones de proveedor.
- **Configuración dinámica de tokens**: Se vinculó el límite de tokens de los modelos del agente Deep Researcher y del LLM principal a la nueva configuración global, permitiendo ajustar la extensión de los reportes generados.

---

## 28-12-25 Corrección de ReferenceError en la página de colecciones RAG 🐞

Se corrigió un `ReferenceError: can't access lexical declaration 'fetchCollections' before initialization` que ocurría en la página de colecciones RAG (`src/app/(dashboard)/rag/page.tsx`).

- **Causa del error**: El error se producía porque la función `fetchCollections`, definida con `useCallback`, se utilizaba en el array de dependencias de otro hook `useCallback` (`onUploadCompleted`) antes de que su declaración fuera procesada por el intérprete de JavaScript, cayendo en la "zona muerta temporal" (Temporal Dead Zone).
- **Solución**: Se reorganizó el código moviendo la declaración del hook `useCallback` para `fetchCollections` a una posición anterior a los hooks que dependen de él. Esto asegura que la función esté inicializada y disponible cuando los otros hooks la necesiten, resolviendo el `ReferenceError`.

---

## 29-12-25 Solución a errores 404 en descargas de PDF y archivos media 🐞🚀

Se corrigió un problema donde los enlaces de descarga de archivos PDF generados devolvían un error 404, debido a inconsistencias en las rutas y la configuración del proxy inverso.

- **URLs Absolutas en Herramientas**: Se modificó `tools/create_pdf_tool.py` para generar URLs de descarga absolutas utilizando `settings.api_server_url`, asegurando que el frontend siempre apunte al servidor correcto.
- **Rutas Físicas Robustas**: Se actualizaron `tools/create_pdf_tool.py` y `api/main.py` para utilizar `MEDIA_ROOT` (ruta absoluta `/app/media`) en lugar de rutas relativas al guardar archivos, evitando fallos por cambios en el directorio de trabajo.
- **Optimización de Nginx**: Se ajustó `nginx.conf` para delegar la gestión de la ruta `/media/` directamente al backend (FastAPI) mediante `proxy_pass`. Esto elimina la dependencia de volúmenes compartidos en el contenedor de Nginx y garantiza que los archivos sean servidos correctamente por el sistema de archivos estáticos del backend.

---

## 29-12-25 Corrección de alucinación de enlaces en generación de PDF 🐞

Se corrigió un problema donde el agente proporcionaba enlaces incorrectos (ej. `.../chat/sandbox/...`) para descargar los PDFs generados, debido a una alucinación del LLM sobre la ubicación del archivo.

- **URL explícita en contexto**: Se modificó `tools/create_pdf_tool.py` para incluir la URL de descarga absoluta y explícita en el mensaje de contexto (`context_for_llm`) que se devuelve al agente. Esto fuerza al LLM a utilizar el enlace real proporcionado por la herramienta en lugar de intentar construir uno basado en el contexto de la conversación.

---

## 29-12-25 Modernización del Indicador de Pensamiento 'Cyberpunk Gradient' 🎨

Se ha rediseñado el componente `LoadingIndicator` en el chat para ofrecer una experiencia visual más moderna y sofisticada.

- **Animación de 4 Puntos**: Se implementó una animación de ondas con 4 puntos utilizando un degradado progresivo de azul a morado (`#3B82F6` a `#A855F7`) y `framer-motion`.
- **Efecto de Brillo**: Cada punto incluye una sombra suave del mismo tono para añadir profundidad y un toque futurista.
- **Diseño Minimalista**: Se eliminó la burbuja de chat gris para un look más limpio y flotante.
- **Feedback de Estado**: El texto de estado ahora aparece sutilmente debajo de la animación.
- **Integración Fluida**: El nuevo indicador reemplaza al anterior en todos los estados de carga estándar.

---

## 29-12-25 Centrado del Indicador de Pensamiento en CommonChat 🎨

Se ha centrado el componente `LoadingIndicator` dentro de `CommonChat` para mejorar la estética y la alineación visual durante los estados de carga y pensamiento del asistente.

- **Ajuste de alineación en `CommonChat.tsx`**: Se modificaron las clases CSS del contenedor del `LoadingIndicator` en `src/components/CommonChat.tsx`. Se cambió `items-start` por `items-center` y se eliminó el padding izquierdo (`pl-2`) para lograr una alineación central perfecta.

---

## 29-12-25 Corrección de renderizado Markdown en PDFs 📄

Se solucionó un problema donde el contenido Markdown no se renderizaba correctamente en los PDFs generados, mostrándose como texto plano debido a saltos de línea escapados o configuración incorrecta de `is_html`.

- **Sanitización de saltos de línea**: Se implementó el reemplazo automático de secuencias literales `\n` por saltos de línea reales en el contenido de entrada.
- **Detección automática de Markdown**: Se añadió lógica para detectar si el contenido es Markdown (presencia de `#`, `**`, `---`) incluso si `is_html` es `True`, forzando el procesamiento correcto.
- **Mejora en extensiones Markdown**: Se incluyó la extensión `nl2br` para asegurar que los saltos de línea simples se respeten en el PDF final.

---

## 29-12-25 Mejora de Autoscroll con Indicadores de Carga 📜

Se ha mejorado la experiencia de usuario en el chat asegurando que la vista se desplace automáticamente hacia abajo cuando aparecen indicadores de carga o estado, evitando que queden ocultos fuera de la vista.

- **Nuevo efecto de scroll en `CommonChat.tsx`**: Se implementó un `useEffect` que detecta cambios en los estados `isResponding`, `toolName`, `isDeepResearchActive` y `backgroundTasks`.
- **Scroll automático**: Cuando cualquiera de estos estados se activa, se dispara un `scrollToBottom` con un ligero retraso para garantizar que el nuevo indicador renderizado sea visible para el usuario.

---

## 29-12-25 Reparación Robusta de Estructura Markdown en PDFs 📄🛠️

Se implementó una solución avanzada para corregir problemas de renderizado en PDFs donde el contenido Markdown llegaba sin los saltos de línea estructurales necesarios (todo en una sola línea).

- **Función `_repair_markdown`**: Se creó un pre-procesador que detecta patrones de encabezados (`#`, `##`) y reglas horizontales (`---`) incrustados dentro del texto y fuerza la inserción de saltos de línea (`\n\n`) antes de ellos.
- **Sanitización profunda**: Se asegura la conversión de caracteres de escape `\n` y la eliminación de `\r` para normalizar el texto antes del procesamiento.
- **Detección de Markdown relajada**: Se ajustó la lógica de detección automática para identificar contenido Markdown incluso si los marcadores estructurales no se encuentran al inicio de la cadena, permitiendo corregir y renderizar documentos mal formados.

---

## 29-12-25 Corrección de scroll inicial en chat 📜

Se corrigió un problema de usabilidad donde al entrar a un chat, la vista se mantenía en el primer mensaje en lugar de mostrar el último.

- **Scroll automático al cargar**: Se implementó un `useEffect` en `CommonChat.tsx` que detecta cuando finaliza la carga inicial de mensajes (`isLoading` pasa a `false`).
- **Visualización inmediata**: Se fuerza un desplazamiento inmediato al final del chat para asegurar que el usuario vea los mensajes más recientes al abrir la conversación.

---

## 29-12-25 Eliminación de icono de usuario en chat 👤

Se eliminó el icono (avatar) del usuario que aparecía junto a la burbuja de chat en `CommonChat` para limpiar la interfaz.

- **Modificación en `ChatMessage.tsx`**: Se eliminó el componente `<ChatAvatar sender="user" />` dentro del bloque condicional que renderiza los mensajes del usuario.

---

## 29-12-25 Visualización condicional del indicador KAI Assistant en ChatMessage 🎨

Se ha modificado el componente `ChatMessage` para que el encabezado "KAI Assistant" solo se muestre cuando el mensaje ya tiene contenido (texto o código de herramienta), evitando que aparezca prematuramente antes de que comience el streaming.

- **Renderizado condicional del encabezado**: Se envolvió el bloque del encabezado "KAI Assistant" en `src/components/ChatMessage.tsx` con una condición `(msg.text || msg.tool_code)`. Esto asegura que el indicador permanezca oculto mientras el mensaje sea un marcador de posición vacío y solo aparezca una vez que se reciba el primer fragmento de texto o se ejecute una herramienta.

---

## 29-12-25 Visualización condicional de botones de acción en ChatMessage 🎨

Se ha extendido la lógica de visualización condicional a los botones de acción del mensaje de la IA (copiar, reproducir audio y editar).

- **Ocultamiento de botones durante el inicio del streaming**: Se envolvió el contenedor de botones de acción en `src/components/ChatMessage.tsx` con la condición `(msg.text || msg.tool_code)`. Esto evita que los iconos aparezcan debajo de la burbuja de chat vacía antes de que el asistente comience a generar contenido, manteniendo la interfaz limpia y coherente.

---
---

## 01-01-26 Implementación de Herramienta para Generación de Datos Estructurados (CSV, Excel, ODS) 📊🚀

Se ha creado una nueva herramienta que permite al LLM generar y exportar datos estructurados en formatos profesionales, facilitando la creación de reportes y tablas descargables.

- **Nueva Herramienta `StructuredDataGeneratorTool`**: Implementada en [`tools/structured_data_generator_tool.py`](tools/structured_data_generator_tool.py). Utiliza `pandas` para procesar listas de diccionarios y convertirlas a archivos `.csv`, `.xlsx` (Excel) y `.ods` (OpenDocument).
- **Registro en el Sistema**: La herramienta ha sido registrada en [`core/tools.py`](core/tools.py) y está disponible para ser utilizada por el agente principal.
- **Gestión de Dependencias**: Se añadieron `openpyxl` (para Excel) y `odfpy` (para ODS) al archivo `requirements.txt` y se instalaron en el contenedor `kognito_core`.
- **Almacenamiento y Limpieza Automática**: Los archivos generados se guardan en `media/generated_data/` y `media/generated_pdfs/`. Se implementó un sistema de limpieza automática ([`utils/file_cleanup.py`](utils/file_cleanup.py)) que elimina archivos con más de 24 horas de antigüedad al arrancar la API y antes de cada nueva generación de archivos.
- **Integración en Panel de Administración**: Se añadió un endpoint de limpieza manual y un botón "Ejecutar Limpieza Manual" en la pestaña de métricas del panel de administración, permitiendo a los administradores gestionar el almacenamiento bajo demanda.
- **Verificación Exitosa**: Se validó el funcionamiento de la herramienta, el sistema de limpieza y la integración administrativa dentro del contenedor `kognito_core`.

---

## 01-01-26 Implementación del Sistema de Citación y Renderizado de Fuentes en ContextualChat 🚀

Se ha implementado exitosamente el mismo sistema de citación y renderizado de fuentes que existe en `ChatMessage.tsx` dentro del componente `ContextualChat.tsx`, proporcionando una experiencia consistente en toda la aplicación.

- **Creación de archivo de utilidades**: Se creó [`src/lib/chatUtils.ts`](src/lib/chatUtils.ts) que contiene las funciones `processMessageWithCitations` y `collectSourcesFromMessage` para manejar el procesamiento de citas y la recolección de fuentes de manera centralizada.
- **Actualización de la interfaz Message**: Se extendieron las propiedades de la interfaz `Message` en `ContextualChat.tsx` para incluir `sources`, `ragContext`, `chunks`, `tool_code` y `document_url`.
- **Modificación del WebSocket**: Se actualizó el `useEffect` del WebSocket para capturar y manejar las fuentes enviadas en los eventos `stream_end` y `agent_response`.
- **Implementación del renderizado de citas**: Se integró la lógica de procesamiento de fuentes y citas en el renderizado de mensajes de la IA, utilizando `contentParts` cuando hay citas presentes.
- **Refactorización de ChatMessage**: Se eliminaron las interfaces redundantes (`Source`, `ContentPart`) y las funciones locales (`SourceButton`, `processMessageWithCitations`) de `ChatMessage.tsx`, usando ahora las versiones centralizadas.
- **Limpieza de imports**: Se removió la importación innecesaria de `uuid` y se actualizaron todos los imports para usar las interfaces y funciones centralizadas.
- **Consistencia de comportamiento**: Ahora tanto `ContextualChat` como `ChatMessage` utilizan el mismo sistema de renderizado de citas, proporcionando una experiencia uniforme al usuario.

---

## 01-01-26 Integración de Chat Contextual en Diálogos de Análisis 💬🚀

Se ha integrado exitosamente el componente `ContextualChat` en los diálogos de análisis para permitir que los usuarios chateen directamente con los análisis específicos, mejorando la experiencia de interacción con el contenido analítico.

- **Integración en `analysis-detail-dialog.tsx`**:
  - Se agregó la importación del componente `ContextualChat` desde `@/components/ContextualChat`.
  - Se añadió el estado `isChatOpen` para controlar la visibilidad del chat contextual.
  - Se implementó un botón de chat con ícono `MessageSquare` en el header del diálogo, junto a los botones de eliminación.
  - Se integró el componente `ContextualChat` al final del componente con el contexto del análisis actual (`type: 'analysis'`, `id: analysis.id`, `snapshot: analysis`).

- **Integración en `deep-research-detail-dialog.tsx`**:
  - Se agregó la importación del componente `ContextualChat` y los estados necesarios (`useState`).
  - Se añadió el estado `isChatOpen` para controlar la visibilidad del chat contextual.
  - Se reestructuró el header del diálogo para incluir un botón de chat con ícono `MessageSquare` en la esquina superior derecha.
  - Se integró el componente `ContextualChat` al final del componente con el contexto de la investigación profunda (`type: 'analysis'`, `id: analysis.id`, `snapshot: analysis`).

- **Funcionalidad Implementada**:
  - **Chat Contextual por Análisis**: Los usuarios pueden hacer preguntas específicas sobre cualquier análisis o investigación profunda.
  - **Contexto Automático**: El chat se inicializa con el contexto del análisis específico, incluyendo título y snapshot del análisis.
  - **Interfaz Integrada**: El botón de chat se integra naturalmente en la interfaz existente de los diálogos.
  - **Experiencia Consistente**: Utiliza el mismo sistema de citación y renderizado de fuentes que el resto de la aplicación.

- **Beneficios para el Usuario**:
  - **Interacción Directa**: Permite hacer preguntas específicas sobre los resultados de análisis sin salir del contexto.
  - **Exploración Profunda**: Facilita la exploración de insights, fuentes y recomendaciones de manera conversacional.
  - **Eficiencia Mejorada**: Elimina la necesidad de cambiar entre múltiples ventanas o pestañas para hacer consultas.

---

## 01-01-26 Unificación del sistema de citación en ContextualChat 💬📚

Se implementó el sistema de citación y renderizado de fuentes en el chat contextual para igualar la funcionalidad y experiencia del chat principal, asegurando que las referencias bibliográficas sean interactivas y consistentes.

- **Procesamiento de fuentes**: Se integraron las funciones `collectSourcesFromMessage` y `processMessageWithCitations` en `src/components/ContextualChat.tsx` para manejar fuentes provenientes tanto de `sources` como de `ragContext`.
- **Renderizado de citas**: Se actualizó el uso de `MarkdownRenderer` para soportar `contentParts`, permitiendo mostrar botones de fuentes interactivos dentro del texto del chat contextual.
- **Soporte para streaming**: Se modificó el manejador de WebSocket para inicializar y acumular `chunks` de mensajes, permitiendo que el renderizador detecte correctamente el estado de streaming y mejore la fluidez visual.
- **Visualización de fuentes adicionales**: Se añadió una sección para mostrar fuentes no citadas directamente en el texto, proporcionando un contexto completo al usuario.
- **Corrección de UX en Diálogos**: Se solucionó un problema donde el chat contextual se cerraba al interactuar con él dentro de los diálogos de análisis. Se implementó la detención de propagación de eventos y se configuró `onPointerDownOutside` en los diálogos padres para permitir una interacción fluida sin cierres inesperados.

---

## 02-01-26 Implementación de creación y edición de tablas en Conocimientos 📊

Se implementó la lógica de creación, edición de estructura y gestión de datos para tablas personalizadas, proporcionando una experiencia similar a Nextcloud Tables.

- **Creación de Tablas**: Se creó el componente [`create-table-dialog.tsx`](src/app/(dashboard)/rag/create-table-dialog.tsx) que permite a los usuarios definir el esquema inicial de una tabla (nombre, descripción y columnas con tipos específicos).
- **Interfaz de Gestión**: Se integró la opción de creación en la vista principal de tablas ([`tables-view.tsx`](src/app/(dashboard)/rag/tables-view.tsx)).
- **Edición de Datos por Tipo**: Se mejoró [`editable-data-grid.tsx`](src/app/(dashboard)/rag/editable-data-grid.tsx) para soportar inputs específicos según el tipo de columna (Checkbox para booleanos, selectores de fecha, inputs numéricos).
- **Gestión de Columnas**: Se actualizó [`column-manager-dialog.tsx`](src/app/(dashboard)/rag/column-manager-dialog.tsx) para asegurar la consistencia de los tipos de datos entre la creación y la edición posterior.

---

## 02-01-26 Reemplazo de Paneles Redimensionables por Sidebar Fijo 🛠️🚀

Se ha simplificado la interfaz del dashboard eliminando la funcionalidad de paneles redimensionables y estableciendo un sidebar fijo con un ancho consistente, mejorando la estabilidad visual y la coherencia con la versión móvil.

- **Eliminación de `react-resizable-panels`**: Se removió la dependencia y la lógica de paneles ajustables en el componente `AppShell.tsx`.
- **Implementación de Sidebar Fijo**: Se estableció un ancho fijo de `w-72` para el sidebar en la versión de escritorio (`hidden md:block`), igualando el tamaño utilizado en el menú lateral de la versión móvil.
- **Optimización de Layout**: Se reemplazó la estructura de `PanelGroup` por un contenedor `flex` estándar, asegurando que el contenido principal (`flex-1`) ocupe todo el espacio restante de manera fluida.
- **Limpieza de Interfaz**: Se eliminó el estado `sidebarSize` y los controladores de redimensionamiento manual, proporcionando una interfaz más sólida y predecible.
- **Mantenimiento de Responsividad**: Se conservó la funcionalidad del menú lateral (drawer) para dispositivos móviles, asegurando una experiencia de usuario uniforme en todos los tamaños de pantalla.

---

## 02-01-26 Renderizado de Markdown y Limpieza Avanzada de JSON/Python 📝✨

Se ha implementado una solución definitiva para la visualización de resúmenes de análisis, manejando tanto JSON estándar como diccionarios de Python.

- **Extracción Robusta con Regex**: Se añadió una capa de seguridad que utiliza expresiones regulares para extraer campos como `final_report` o `summary` cuando el parseo JSON falla (común en strings de Python con comillas simples).
- **Limpieza de Caracteres Escapados**: Se implementó la función `cleanExtractedText` para procesar saltos de línea (`\n`) y comillas escapadas, asegurando un texto limpio para el renderizado.
- **Triple Validación de Datos**: El sistema ahora intenta tres métodos de recuperación de texto (JSON, Regex y Conversión de tipos) antes de recurrir al texto original.
- **Integración de `InlineMarkdownRenderer`**: Se reemplazó el renderizado de texto plano por el componente `InlineMarkdownRenderer` en las tarjetas de análisis de `AnalysisView`.
- **Consistencia Visual**: Se mantuvo el truncado de texto (`line-clamp-3`) para asegurar que el diseño de la cuadrícula de tarjetas permanezca ordenado y profesional.

---

## 02-01-26 Modernización Integral de la Agenda 📅🧊

Se ha realizado una transformación visual completa del módulo de Agenda para alinearlo con la nueva estética premium del proyecto.

- **Interfaz Glassmorphism**: Implementación de contenedores con `backdrop-blur-xl` y bordes `rounded-[2rem]` en todas las vistas de la agenda.
- **Vistas Diaria, Semanal y Mensual**:
  - **Mensual**: Rediseño de la cuadrícula con celdas de cristal y eventos tipo "píldora" con gradientes dinámicos.
  - **Semanal**: Sustitución de tablas tradicionales por una rejilla moderna de alta legibilidad.
  - **Diaria**: Mejora de la jerarquía visual en la lista de tareas y eventos con tarjetas interactivas.
- **Navegación Premium**: Nuevas barras de navegación con botones de cristal y tipografía de alto impacto (font-black).
- **Micro-interacciones**: Añadidos efectos de escalado, resplandor (glow) y transiciones fluidas en el hover y drag-and-drop.
- **Optimización de Espacio**: Mejora en el layout general para maximizar el área de visualización de compromisos.

---

## 02-01-26 Modernización de Mensajes de Chat (ChatMessage) 🤖🧊

Se ha rediseñado la presentación de los mensajes del agente y del usuario para una experiencia de chat más inmersiva y premium.

- **Burbujas de IA Glassmorphism**: Implementación de contenedores translúcidos con `backdrop-blur-xl` y bordes ultra-redondeados (`rounded-[2rem]`).
- **Controles de Acción Dinámicos**:
  - Rediseño de botones de copiar, reproducir audio y editar con estilo de cristal y animaciones de entrada (`translate-y`).
  - Mejora en la respuesta táctil y visual (hover effects) de todas las acciones del mensaje.
- **Identidad Visual del Agente**: Sustitución de texto plano por un badge premium de "KAI Intelligence" con efectos de pulso y gradientes.
- **Bloques de Ejecución Técnicos**: Mejora en la visualización de herramientas utilizadas, con un diseño más limpio, tipografía mono-espaciada y fondos translúcidos.
- **Optimización de Lectura**: Ajuste de paddings y tamaños de fuente para mejorar la legibilidad del contenido generado por la IA.

---

## 02-01-26 Modernización de Estadísticas y Cabecera (AnalysisView) 📊✨

Se ha completado la segunda fase de la transformación visual del Centro de Análisis, enfocándose en la cabecera y los paneles de métricas.

- **Cabecera de Alto Impacto**: Rediseño del título con gradientes dinámicos y botones con estilo de cristal y bordes `rounded-2xl`.
- **Paneles de Métricas "Glow"**:
  - Implementación de tarjetas con efecto `backdrop-blur-xl` y bordes ultra-redondeados (`rounded-[2rem]`).
  - Acompañamiento de iconos con resplandor (glow) cromático para cada tipo de métrica.
  - Uso de gradientes vibrantes en las cifras principales para mejorar la legibilidad y el atractivo visual.
- **Micro-interacciones Dinámicas**: Añadidos efectos de elevación, sombras ambientales de colores y escalado de iconos en el hover.
- **Refinamiento Tipográfico**: Mejora en la jerarquía de la información utilizando fuentes en mayúsculas para metadatos y tracking ajustado para títulos.

---

## 02-01-26 Modernización de la Interfaz Principal (AppShell) 🎨✨

Se ha realizado una transformación visual profunda de la estructura principal de la aplicación para adoptar un estilo más moderno, fluido y "premium".

- **Sidebar Flotante**: Se rediseñó el sidebar para que aparezca como un panel flotante con bordes redondeados (`rounded-3xl`) y efecto de cristal profundo (`backdrop-blur-2xl`).
- **Efecto Glassmorphism**: Se mejoró el uso de desenfoques y transparencias en el header y contenedores, utilizando `bg-card/40` y `backdrop-blur-xl` para una sensación de ligereza.
- **Gradientes de Profundidad**: Se añadió un gradiente de fondo sutil al contenedor principal para mejorar la jerarquía visual y la profundidad.
- **Refinamiento de Componentes**:
  - Se actualizaron los bordes redondeados a `rounded-2xl` y `rounded-3xl` en toda la estructura.
  - Se mejoraron los indicadores de estado de conexión con animaciones de pulso y sombras dinámicas.
  - Se añadió un efecto de brillo (glow) al logo y contenedores de herramientas.
- **Optimización de Layout**: Se aumentó el espaciado interno del contenido principal y se centró en un contenedor de ancho máximo (`max-w-7xl`) para mejorar la legibilidad en pantallas grandes.

---

## 03-01-26 Integración de Visión Multimodal con Mistral Small 3.1 👁️🚀

Se ha dotado a KognitoAI de capacidades visuales avanzadas mediante la integración del modelo multimodal **Mistral Small 3.1** a través de OpenRouter, permitiendo el procesamiento de imágenes y documentos escaneados tanto en el chat como en la base de conocimientos.

- **Configuración de Modelo de Visión**: Se añadió la variable `VISION_MODEL` en `core/config.py` (por defecto `openrouter/mistralai/mistral-small-3.1-24b-instruct:free`) para centralizar la gestión del motor de visión.
- **Gestión de LLM Multimodal**: Se implementó `get_vision_llm()` en `core/llm_manager.py`, asegurando que el modelo de visión se inicialice correctamente con soporte para OpenRouter y rate limiting.
- **OCR Multimodal en Documentos**: Se transformó `extract_text_and_metadata_from_document` en `utils/document_parser.py` en una función asíncrona que:
  - Detecta automáticamente imágenes (`.png`, `.jpg`, `.jpeg`, `.webp`).
  - Identifica PDFs escaneados (sin capa de texto digital).
  - Utiliza el modelo de visión para realizar OCR inteligente, preservando la estructura de facturas, tablas y escritura a mano.
- **Soporte Multimodal en Chat**: Se modificó el nodo `call_model_node` en `core/agent.py` para detectar la presencia de imágenes en los mensajes del usuario. En caso de detectarse una imagen, el agente cambia automáticamente al modelo de visión para generar la respuesta, permitiendo interacciones directas sobre contenido visual.
- **Actualización de Flujos Asíncronos**: Se actualizaron `core/tasks.py`, `api/documents.py` y `telegram_client/handlers/document_handlers.py` para soportar la nueva naturaleza asíncrona del procesamiento de documentos, garantizando la estabilidad del sistema durante la ingesta de archivos pesados.
- **Impacto**: KAI ahora puede "ver" y entender facturas, pizarras, apuntes manuales y capturas de pantalla, integrándolos plenamente en su memoria a largo plazo y permitiendo consultas visuales en tiempo real.

---

## 03-01-26 Corrección en Procesamiento y Visualización de Memorias en el Grafo 🧠

Se solucionó un problema que impedía que las memorias del usuario (tanto proactivas como explícitas) se procesaran y visualizaran correctamente en el grafo de conocimiento.

- **Activación de KnowledgeExtractionNode**: Se habilitó e inicializó correctamente el nodo de extracción de conocimiento en `core/agent.py` para asegurar que la información se persista en el grafo.
- **Corrección en memory_graph_processor.py**: Se corrigió un error crítico donde no se pasaba la sesión de base de datos, se redujo el umbral de procesamiento a 1 para feedback inmediato, y se estandarizó el nombre del dataset a "Agent Memories".
- **Estandarización de Datos**: Se ajustó `KnowledgeExtractionNode` para incluir `dataset_name`, `account_id` y `workspace_id` en el nivel superior de las entidades y relaciones, garantizando su correcta visualización y filtrado en la interfaz.

---

## 03-01-26 Restauración de Fuentes y Citas para Herramientas de Notas 📝🔍

Se corrigió un problema crítico que impedía que las fuentes (citations) de las notas aparecieran en el chat al utilizar las herramientas de búsqueda y obtención de notas.

- **Corrección en el Procesamiento de Salida de Herramientas**: Se modificó [`core/agent.py`](core/agent.py) para reconocer y procesar correctamente los objetos `ToolOutputWithSources` devueltos por las herramientas. Anteriormente, estos objetos se convertían a texto plano, descartando las fuentes bibliográficas.
- **Sincronización del Modelo de Fuentes en la API**: Se actualizó la definición de la clase `Source` en [`api/chat.py`](api/chat.py) para incluir el campo `metadata` y permitir IDs de tipo string. Esto asegura que la información extendida de las notas (como IDs de referencia y puntuaciones de relevancia) se preserve durante la transmisión via WebSocket y al recargar el historial.
- **Mejora en la Persistencia de Citas**: Con estos cambios, las notas citadas por el asistente ahora aparecen correctamente en la sección de "Fuentes y Referencias" del frontend, permitiendo al usuario abrir la nota original directamente desde la cita.
