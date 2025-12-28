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

## 24-12-2025 Corrección de `TypeError` en `deep_researcher` por concatenación de tipos

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

Se corrigió el problema donde las notificaciones de progreso del Deep Researcher no se mostrabn en el frontend debido a que los componentes QuestionSliderDialog y GapDevelopmentDialog no estaban conectados correctamente al WebSocket.

- **Cambio de useWebSocket a useWebSocketContext**: Se modificaron `src/components/QuestionSliderDialog.tsx` y `src/components/GapDevelopmentDialog.tsx` para usar `useWebSocketContext` en lugar de `useWebSocket` directamente, permitiendo que reciban las actualizaciones de progreso enviadas por el backend a través de WebSocket.

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

Se corrigió un error de validación de Pydantic que ocurría porque el `account_id` no se estaba inyectando correctamente en las herramientas `GraphCypherGeneratorTool` y `knowledge_search` dentro del agente `DeepResearcher`.

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

Se corrigió un `pydantic_core._pydantic_core.ValidationError` persistente en las herramientas `knowledge_search` y `graph_cypher_generator` del `DeepResearcher`. El problema se debía a un conflicto entre la validación de Pydantic en el momento de la instanciación y la inyección de dependencias en tiempo de ejecución.

- **Campos Opcionales en `BaseTool`**: Se modificaron las clases `KnowledgeSearchTool` y `GraphCypherGeneratorTool` para que el campo `account_id` (y `workspace_id` en `KnowledgeSearchTool`) sea opcional (`Optional[str] = None`).
- **Inyección Post-Instanciación**: Se actualizó la función `get_all_tools` en `core/agents/deep_researcher_utils.py` para que primero instancie las herramientas sin argumentos y luego asigne los atributos `account_id` y `workspace_id` a las instancias creadas. Este enfoque de dos pasos evita el error de validación inicial y asegura que las dependencias estén presentes antes de la ejecución de la herramienta.

---

## 27-12-25 Corrección del indicador de progreso de Deep Research en el chat 🐛

Se corrigió un problema donde el indicador de progreso para la herramienta "Deep Research" no aparecía en el chat. Esto se debía a una discrepancia en el nombre de la propiedad utilizada para el nombre de la herramienta en los eventos de WebSocket enviados desde el backend.

- **Estandarización de `tool_name`**: Se modificó `core/agent.py` para enviar la propiedad `tool_name` (snake_case) en lugar de `toolName` (camelCase) en los eventos `tool_start` y `tool_end`. Esto alinea el backend con la interfaz `ToolStatusMessage` esperada por el componente frontend `CommonChat.tsx`.

---

## 27-12-25 Adición de Logging para Depuración de `BadRequestError` en Deep Researcher 🐞

Se añadió logging detallado en la función `researcher` del agente `DeepResearcher` para diagnosticar un error `litellm.BadRequestError` con el mensaje "Not the same number of function calls and responses".

- **Logging de Mensajes**: Se añadió una línea de log en `core/agents/deep_researcher.py` para imprimir el contenido de la variable `pruned_messages_for_researcher` justo antes de que sea enviada al modelo LLM. Esto permitirá inspeccionar la secuencia de mensajes y verificar si hay un desajuste entre las llamadas a herramientas y las respuestas de las mismas.

---

## 27-12-25 Corrección de actualizaciones de progreso en Deep Research 🐛

Se solucionó un problema donde el indicador de progreso de Deep Research se quedaba estático en 0%. Esto se debía a que la función de callback de progreso no se estaba inyectando correctamente en la herramienta y había una discrepancia en la firma de la función.

- **Inyección de `progress_callback`**: Se añadió el campo `progress_callback` a la clase `DeepResearchTool` y se modificó `core/agent.py` para inyectar explícitamente la función de callback en la instancia de la herramienta antes de su ejecución.
- **Corrección de firma de callback**: Se actualizó la función `progress_callback` en `core/agent.py` para aceptar argumentos variables (`*args`, `**kwargs`) y utilizar directamente el valor de progreso absoluto calculado por el agente de investigación, resolviendo conflictos de tipos y lógica de cálculo.

---

## 27-12-25 Corrección de `invalid_request_message_order` en Deep Researcher 🐞

Se corrigió un error `litellm.BadRequestError: OpenrouterException` con el mensaje "Not the same number of function calls and responses" que ocurría cuando el historial de mensajes era podado por exceder el límite de tokens.

- **Preservación de secuencias de herramientas en `prune_messages_to_fit_token_limit`**: Se reescribió la función `prune_messages_to_fit_token_limit` en `core/utils/llm_utils.py` para agrupar los mensajes en bloques atómicos. Esto asegura que un `AIMessage` con llamadas a herramientas y sus correspondientes `ToolMessage`s nunca se separen durante el proceso de poda, manteniendo la integridad de la conversación.
- **Corrección de conteo de tokens**: Se solucionó un bug en la misma función donde los tokens de los mensajes retenidos se contaban múltiples veces, lo que llevaba a una poda excesiva e incorrecta.
- **Mejora en `remove_up_to_last_ai_message`**: Se actualizó la función `remove_up_to_last_ai_message` en `core/utils/llm_utils.py` para que, al eliminar un mensaje de IA, también elimine los mensajes de herramientas subsiguientes si el mensaje de IA contenía llamadas a herramientas. Esto evita dejar respuestas de herramientas huérfanas en el historial.

---

## 27-12-25 Corrección de `TypeError` en `ConceptualProcessingTool` por `async_generator` 🐞

Se corrigió un `TypeError: 'async_generator' object does not support the asynchronous context manager protocol` que ocurría en `tools/conceptual_processing_tool.py` al intentar usar `get_db_session` con `async with`.

- **Uso de `@asynccontextmanager`**: Se decoró la función `get_db_session` en `core/dependencies.py` con `@asynccontextmanager` de la librería `contextlib`. Esto convierte el generador asíncrono en un gestor de contexto asíncrono adecuado, permitiendo que se use correctamente con `async with` en toda la aplicación y resolviendo el `TypeError`.

---

## 27-12-25 Corrección de `UnboundLocalError` en `Neo4jAdapter` 🐞

Se corrigió un error `UnboundLocalError: cannot access local variable 'batch_data' where it is not associated with a value` que ocurría en el procesamiento conceptual del grafo de conocimiento cuando no se encontraban entidades para procesar.

- **Retorno temprano para entidades vacías**: Se añadió una verificación al inicio de `_add_entities_to_neo4j` en `knowledge_graph/neo4j_adapter.py` para retornar inmediatamente si la lista de entidades está vacía. Esto evita que el código intente ejecutar el bucle de procesamiento y acceda a variables no inicializadas.
- **Reubicación de la creación de menciones**: Se movió la llamada a `_add_document_mentions` dentro del bucle de procesamiento por lotes. Esto asegura que las relaciones `MENTIONS` se creen correctamente para cada lote de entidades procesado y elimina la dependencia de la variable `batch_data` fuera del ámbito del bucle.
- **Mejora en el mapeo de datos**: Se incluyó el campo `dataset_name` directamente en el diccionario de datos de la entidad durante el mapeo, permitiendo una propagación más limpia y robusta de los metadatos hacia las relaciones de mención.
