## 14-12-2025 Actualización del formato de tool calling para OpenRouter
 Se ha actualizado la lógica de binding de herramientas en core/agent.py para usar el formato moderno "tools" en lugar del deprecated "functions" para modelos de OpenRouter, resolviendo errores de deprecación y manteniendo compatibilidad con otros proveedores.
 - **Simplificación de la lógica de binding**: Se prioriza el método bind_tools para todos los modelos que lo soporten, cayendo de vuelta al formato functions legacy si es necesario.
 - **Compatibilidad con OpenRouter**: Los modelos de OpenRouter ahora usan el formato moderno "tools" y "tool_choice" en lugar del obsoleto "functions" y "function_call".
 - **Mantenimiento de compatibilidad**: Se asegura que Gemini, OpenAI vía LiteLLM y otros proveedores continúen funcionando correctamente sin cambios negativos.
 ---
 ## 13-12-2025 Configuración de formato JSON para LLM
 Se ha ajustado la configuración del modelo de lenguaje para forzar la salida en formato JSON, con el fin de resolver errores de parseo de respuesta.
 - **Configuración de LiteLLM**: Se añadió `response_format={"type": "json_object"}` a la inicialización de `ChatLiteLLM` en [`core/llm_manager.py`](core/llm_manager.py) para el `_main_agent_llm_instance`.
 ---
 ## 13-12-2025 Mejora de Perfiles de Ideas (Concepto Central y Descripción)
 Se han realizado mejoras en la generación de los perfiles de ideas para asegurar que los títulos (conceptos centrales) y las descripciones sean más claros, descriptivos y no truncados.
 - **`_identify_central_concept`**: Se eliminó la restricción de longitud de palabras para el concepto central y se refinó el prompt para guiar al LLM a generar nombres de conceptos más específicos y evitar generalidades.
 - **`_generate_profile_description`**: Se eliminó el límite de palabras en el prompt de la descripción y se enfatizó la necesidad de un resumen detallado que destaque la importancia, la unificación de citas y las categorías principales.
 ---
 ## 13-12-2025 Ajustes en la Lógica de Fallback para Conceptos Centrales
 Se ha mejorado la robustez de la función [`_identify_central_concept`](knowledge_graph/conceptual_graph_processor.py:814) mediante la adición de una validación más estricta de la respuesta del LLM. Ahora, si el LLM devuelve un concepto central genérico o vacío, se activará la lógica de fallback, la cual también ha sido mejorada con logs más explícitos para facilitar la depuración y el monitoreo.
 ---
 ## 14-12-25 Actualización del formato de Tool Calling para OpenRouter
 Se actualizó la implementación de `tool calling` en `core/agent.py` para abordar la deprecación de "functions" y "function_call" en OpenRouter, a favor de "tools" y "tool_choice".
 - **Problema**: OpenRouter deprecó el uso de "functions" y "function_call" en su API.
 - **Solución**: Se simplificó la lógica de enlace de herramientas para priorizar `bind_tools` (formato moderno) para todos los modelos que lo soportan.
 - **Compatibilidad**: Se mantuvo la compatibilidad con otros proveedores de LLM, utilizando un mecanismo de fallback para formatos legacy cuando es necesario. Los modelos Gemini continúan usando su soporte nativo de herramientas, OpenAI a través de LiteLLM recibe el formato apropiado, y OpenRouter ahora utiliza el formato `tools`.
 - **Verificación**: La conversión del esquema de herramientas funciona correctamente a través de la utilidad `convert_to_openai_function` de LangChain, asegurando la generación adecuada del esquema JSON para todos los parámetros de las herramientas.
 ---
 ## 14-12-25 Corrección de invocación de `web_search` sin parámetro `query`
 Se ha corregido un error donde la herramienta `web_search` era invocada sin el parámetro `query` requerido, lo que causaba fallos en el agente.
 - **Problema**: El LLM podía generar llamadas a la herramienta `web_search` sin incluir el parámetro `query`, provocando un error de validación.
 - **Solución**: Se añadió lógica en la función `tool_node` de [`core/agent.py`](core/agent.py) para inferir el parámetro `query` del último mensaje del usuario (`HumanMessage`) en el historial de la conversación. Si no se encuentra un mensaje de usuario relevante, se asigna un `query` por defecto de "información general".
 - **Impacto**: Esta solución asegura que la herramienta `web_search` siempre reciba un `query` válido, derivado del contexto de la conversación, evitando así errores de parámetros faltantes y mejorando la robustez del agente.
 ## 14-12-25 Modificación del indicador de "Kognito está pensando" en CommonChat.tsx
 Modificación de la condición de renderizado del LoadingIndicator para que desaparezca cuando comienza el streaming.
 - **Cambio en src/components/CommonChat.tsx**: Se cambió la condición de renderizado del LoadingIndicator de `(isResponding || toolName)` a `isThinking && (isResponding || toolName)` para que el indicador desaparezca una vez que llega el primer chunk del streaming.
 - **Motivo**: El indicador "Kognito está pensando" debe desaparecer cuando comienza a llegar el mensaje por streaming al frontend.
 - **Resultado**: El indicador ahora se oculta inmediatamente cuando `isThinking` se establece en `false` al recibir el primer `stream_chunk`.
 ---
 ## 14-12-2025 Corrección de error 404 al actualizar metadatos de documentos
 Se ha corregido un error 404 que ocurría al intentar actualizar los metadatos de un documento. El problema se debía a que el `workspace_id` no se estaba enviando correctamente en la solicitud de actualización de metadatos desde el frontend, impidiendo que el backend localizara el documento en el workspace adecuado.
 - **Modificación en `api/documents.py`**:
   - Se añadió el campo `workspace_id: Optional[str] = None` a la clase `UpdateMetadataRequest` para permitir que el frontend envíe este identificador.
   - Se aseguró que el `workspace_id` recibido en el `request` del endpoint `@router.post("/update-document-metadata")` se pase correctamente a la función `update_document_metadata` en `core.memory_manager.py`.
 - **Verificación en `core/memory_manager.py`**: Se confirmó que la función `update_document_metadata` ya estaba preparada para aceptar y utilizar el parámetro `workspace_id` en su lógica de filtrado y actualización.
 Estos cambios garantizan que las solicitudes de actualización de metadatos incluyan toda la información necesaria para localizar y modificar documentos correctamente, resolviendo el error 404.
 ---
 ## 14-12-2025 Optimización de la Carga y Movimiento de Grafos de Conocimiento
 Se han implementado una serie de optimizaciones tanto en el backend como en el frontend para mejorar el rendimiento de la carga y el "efecto de movimiento" de los grafos de conocimiento, abordando la exigencia computacional.
 -   **Optimización de Embeddings (Backend)**:
     -   **Descripción**: Se modificó [`knowledge_graph/hybrid_graph_processor.py`](knowledge_graph/hybrid_graph_processor.py) para cambiar el método de generación de embeddings de `aembed_query` (individual) a `aembed_documents` (por lotes).
     -   **Impacto**: Esta mejora incrementa significativamente la eficiencia en la generación de embeddings sin alterar la calidad semántica de los mismos, resultando en un procesamiento de grafos más rápido.
 -   **Optimización de Consultas Neo4j (Backend)**:
     -   **Descripción**: Se optimizó [`knowledge_graph/neo4j_adapter.py`](knowledge_graph/neo4j_adapter.py) para mejorar la eficiencia de las consultas Cypher al añadir entidades y relaciones a Neo4j. Se consolidaron las consultas para usar la cláusula `UNWIND` de forma más efectiva y se pasaron valores `None` para campos opcionales directamente en las consultas `SET`.
     -   **Impacto**: Esto reduce la recompilación de consultas en Neo4j y la sobrecarga de la base de datos, agilizando el almacenamiento de los datos del grafo sin cambiar la lógica de persistencia.
 -   **Limpieza de Código (Frontend)**:
     -   **Descripción**: Se eliminó un `console.log` de depuración en [`src/components/KnowledgeGraph/NodeDetailsSidebar.tsx`](src/components/KnowledgeGraph/NodeDetailsSidebar.tsx).
     -   **Impacto**: Mejora la limpieza del código sin afectar la funcionalidad.
 -   **Optimización del Movimiento del Grafo (Frontend)**:
     -   **Descripción**: Se ajustaron los parámetros de física en [`src/components/KnowledgeGraph/GraphVisualization.tsx`](src/components/KnowledgeGraph/GraphVisualization.tsx) para reducir el "movimiento de acomodación" inicial del grafo.
         -   `stabilization.iterations` se redujo de 1000 a 200.
         -   `stabilization.updateInterval` se aumentó de 100 a 200.
         -   En el solver `barnesHut`, `gravitationalConstant` se ajustó de -2000 a -1000, `springLength` de 80 a 100 y `damping` de 0.3 a 0.6.
     -   **Impacto**: Estos cambios buscan que el proceso de estabilización del grafo sea más rápido, menos errático y visualmente más suave, mejorando la experiencia del usuario al interactuar con el grafo de conocimiento.
 ---
 ## 15-12-2025 Eliminación del límite de citas conceptuales
 Se ha eliminado el límite de 200 citas conceptuales en el procesador de grafos conceptuales para permitir un análisis más exhaustivo de los documentos.
 - **Eliminación de límite**: Se ha eliminado la línea que limitaba a 200 el número de citas conceptuales en el método `_deduplicate_and_filter_quotes` en el archivo [`knowledge_graph/conceptual_graph_processor.py`](knowledge_graph/conceptual_graph_processor.py).
 ---
 ## 15-12-2025 Creación de perfiles de ideas dependiente de LLM
 Se ha modificado el `ConceptualGraphProcessor` para que la creación de perfiles de ideas dependa exclusivamente del LLM, eliminando la lógica de fallback. Esto asegura que solo se generen perfiles de alta calidad y que el proceso falle si el LLM no puede cumplir la tarea.
 - **`_identify_central_concept`**: Se eliminó el bloque de código de fallback. Si el LLM no genera un concepto central válido, ahora se lanzará un `ValueError`.
 - **`_generate_profile_description`**: Se eliminó la descripción genérica de fallback. Si el LLM no puede generar una descripción, el método ahora lanzará un `ValueError`.
 ---
 ## 15-12-2025 Refactorización del endpoint de investigación profunda y creación de herramienta
 Se ha refactorizado el endpoint `/api/deep_research/` para usar el agente LangGraph moderno y se ha creado una nueva herramienta `DeepResearchTool` que permite lanzar investigaciones profundas directamente desde el chat.
 - **Refactorización del endpoint**: Se actualizó [`api/deep_research.py`](api/deep_research.py) para usar el agente `compile_deep_researcher_graph()` de [`core/agents/deep_researcher.py`](core/agents/deep_researcher.py) en lugar de la implementación anterior basada en LiteLLM.
 - **Creación de DeepResearchTool**: Se creó [`tools/deep_research_tool.py`](tools/deep_research_tool.py) con una herramienta que hace llamadas HTTP al endpoint refactorizado, usando URL dinámica basada en la variable de entorno `API_BASE_URL`.
 - **Integración en el sistema**: Se añadió la nueva herramienta a [`core/tools.py`](core/tools.py) para que esté disponible para el agente principal.
 - **Registro del router**: Se incluyó el router de deep_research en [`api/main.py`](api/main.py) para que el endpoint esté disponible en la ruta `/api/deep_research/`.
 - **Mejoras de robustez**: Se añadieron campos opcionales `workspace_id` y `telegram_id` para compatibilidad con el agente, se corrigieron errores de manejo de excepciones HTTP, y se mejoró el logging en [`core/agents/deep_researcher.py`](core/agents/deep_researcher.py) para facilitar la depuración.
 - **Manejo de casos edge**: Se implementó lógica para generar reportes finales incluso cuando no hay hallazgos, asegurando que el agente siempre produzca una respuesta útil.
 ---
 ## 15-12-2025 Corrección de `AttributeError` en `StateGraph`
 Se ha corregido un `AttributeError` en `core/agents/deep_researcher.py` que impedía el correcto funcionamiento del agente de investigación profunda.
 - **Error**: El objeto `StateGraph` no tiene el atributo `add_conditional_edge`, el nombre correcto es `add_conditional_edges`.
 - **Solución**: Se ha renombrado la llamada al método `add_conditional_edge` por `add_conditional_edges` en la línea 302 del archivo [`core/agents/deep_researcher.py`](core/agents/deep_researcher.py:302).
 ---
 ## 15-12-2025 Corrección de `UnsupportedParamsError` para VertexAI en LiteLLM
 Se ha solucionado un error de parámetros no soportados al usar VertexAI a través de LiteLLM, asegurando la compatibilidad del `tool_choice`.
 - **Problema**: VertexAI no soporta el valor `any` para el parámetro `tool_choice`, lo que causaba un `litellm.UnsupportedParamsError`.
 - **Solución**: Se ha añadido `drop_params=True` a la configuración de `ChatLiteLLM` en [`core/llm_manager.py`](core/llm_manager.py:42). Esto permite que LiteLLM omita automáticamente los parámetros no compatibles en las llamadas a la API, evitando el error y permitiendo que la ejecución continúe sin problemas.
 ---
 ## 15-12-2025 Corrección de `UnsupportedParamsError` para `tool_choice` en VertexAI
 Se ha corregido un `UnsupportedParamsError` al usar modelos que se enrutan a través de VertexAI, asegurando que el `tool_choice` se configure correctamente.
 - **Problema**: El `tool_choice` con valor `any` no es compatible con VertexAI, lo que provocaba un error en `litellm`.
 - **Solución**: Se ha modificado la lógica en [`core/llm_manager.py`](core/llm_manager.py) para que, si el modelo no es de OpenAI/GPT, se establezca explícitamente `tool_choice` en `"auto"`, un valor compatible. Esto evita el error y asegura el funcionamiento del `tool calling`.
 ---
 ## 15-12-2025 Corrección de `UnsupportedParamsError` en agente de investigación profunda
 Se ha corregido un `UnsupportedParamsError` persistente en el agente de investigación profunda al usar modelos que se enrutan a través de VertexAI.
 - **Problema**: El método `with_structured_output` en [`core/agents/deep_researcher.py`](core/agents/deep_researcher.py) estaba añadiendo internamente `tool_choice='any'`, que no es compatible con VertexAI, causando errores continuos.
 - **Solución**: Se ha añadido `drop_params=True` al LLM en la función `clarify_with_user` para que LiteLLM omita automáticamente parámetros no compatibles como `tool_choice='any'`. Esto permite que la ejecución continúe sin problemas y asegura la compatibilidad con VertexAI.
 ---
 ## 16-12-25 Corrección del error NameError en deep_research_tool
 Se corrigió el error NameError causado por la falta de definiciones de funciones en core/agents/deep_researcher.py después de revertir cambios de tenacity.
 - **Agregar import json**: Se agregó la importación de json para parsear respuestas JSON en la función clarify_with_user.
 - **Definir clarify_with_user**: Se definió la función clarify_with_user para generar research_brief usando el prompt transform_messages_into_research_topic_prompt con response_format json_object.
 - **Definir write_research_brief**: Se definió la función write_research_brief como un placeholder que retorna un dict vacío.
 - **Eliminar duplicados**: Se eliminaron las definiciones duplicadas e incompletas de las funciones supervisor y researcher.
 ---
 ## 16-12-25 Corrección del error BadRequestError en supervisor de deep_research_tool
 Se corrigió un error BadRequestError de VertexAI causado por mensajes mal estructurados en el supervisor del agente de investigación profunda.
 - **Problema**: VertexAI requería que las conversaciones terminaran con un mensaje de usuario o tuvieran una estructura específica, causando errores en llamadas con mensajes vacíos o que terminaban con mensajes del sistema/AI.
 - **Solución**: Se modificó la función supervisor para incluir un mensaje de sistema con el prompt lead_researcher_prompt y agregar un mensaje inicial de usuario con el research_brief en la primera llamada. Además, se cambió la lógica para acumular mensajes en la conversación en lugar de reemplazarlos, permitiendo un flujo de conversación adecuado.
 - **Cambios en supervisor**: Se agregó construcción de mensajes con SystemMessage y HumanMessage inicial, y se cambió el retorno para appendear el response en lugar de reemplazar.
 - **Cambios en supervisor_tools**: Se cambió para appendear los tool_messages a los supervisor_messages existentes en lugar de reemplazarlos, manteniendo la conversación.
 ---
 ## 16-12-2025 Corrección de `KeyError: 'date'` en `deep_researcher.py`
 Se ha corregido un `KeyError: 'date'` en la función `clarify_with_user` del archivo `core/agents/deep_researcher.py`. El error ocurría porque el prompt `transform_messages_into_research_topic_prompt` esperaba una clave `date` que no se le estaba proporcionando.
 - **Problema**: El prompt `transform_messages_into_research_topic_prompt` requería una clave `date` para su formato, pero esta no se incluía al invocarlo.
 - **Solución**: Se modificó la línea 90 en `core/agents/deep_researcher.py` para incluir la fecha actual obtenida mediante `get_today_str()` en el formato del prompt.
 - **Impacto**: Se resuelve el `KeyError`, permitiendo que la función `clarify_with_user` se ejecute correctamente y el agente de investigación profunda funcione sin interrupciones.
 ---
 ## 16-12-25 Correcciones de errores de Pylance y ajustes de tipo en `deep_researcher.py`
 Se han corregido varios errores de Pylance y se han realizado ajustes de tipo en el archivo `core/agents/deep_researcher.py` para mejorar la robustez y la claridad del código.
 - **Eliminación de `import litellm`**: Se eliminó la importación de `litellm` ya que no se utilizaba directamente en el archivo.
 - **Normalización de `account_id`**: Se añadió un casteo explícito a `str` para el parámetro `account_id` en la función `get_all_tools` para evitar errores de tipo `Any | None`.
 - **Manejo de tipos para `get_buffer_string`**: Se ajustó la lógica de construcción de `current_messages` para asegurar que siempre sea una `list[BaseMessage]` antes de pasarlo a `get_buffer_string`, resolviendo errores de tipo.
 - **Supresión de errores de Pylance en `bind_tools`**: Se añadió el comentario `# type: ignore` en las llamadas a `llm.bind_tools` en las funciones `clarify_with_user`, `supervisor` y `researcher` y `get_all_tools`, ya que Pylance no reconocía el método a pesar de que existe en tiempo de ejecución.
 - **Acceso seguro a `tool_calls`**: Se modificó el acceso a `most_recent_message.tool_calls` para usar `getattr(most_recent_message, 'tool_calls', [])`, asegurando que `tool_calls` se acceda de forma segura y se eviten `AttributeError` si `most_recent_message` no es un `AIMessage` o no tiene ese atributo.
 - **Corrección de parámetros de `StateGraph`**: Se eliminaron los parámetros `output`, `input` y `config_schema` de las inicializaciones de `StateGraph` en `create_researcher_graph`, `create_supervisor_graph` y `compile_deep_researcher_graph`, ya que no son parte del constructor de `StateGraph` y causaban errores de Pylance.
 - **Supresión de errores de Pylance en `astream_events`**: Se añadieron comentarios `# type: ignore` en las líneas relacionadas con `graph.astream_events` y el acceso a `event['data']['output']` y `event['data']['chunk']['messages']` en el bloque `if __name__ == "__main__"`, ya que Pylance generaba falsos positivos para la estructura de los eventos de LangGraph.
 ---
 ## 16-12-2025 Optimización del flujo del agente: Activación condicional de RAG y refinamiento de prompts
 Se han implementado mejoras significativas en el flujo del agente (`core/agent.py`) y en la gestión de prompts (`core/prompt_manager.py`) para optimizar el uso de la memoria RAG y hacer la comunicación del sistema más concisa y eficiente.
 - **Activación Condicional de RAG**: Se añadió la función `should_perform_rag_search` en `core/agent.py` que, mediante una heurística basada en la longitud del mensaje del usuario y palabras clave, decide si es necesario invocar el sistema RAG (Retrieval Augmented Generation). Esto evita búsquedas innecesarias en la base de conocimiento para consultas conversacionales o que no requieren información externa.
 - **Refinamiento del Prompt del Sistema**: Se ajustó la construcción del `system_prompt_content` en `core/prompt_manager.py` para:
     - Consolidar las instrucciones de RAG, haciéndolas más claras y contextualizadas.
     - Simplificar la sección de "Capacidades y Herramientas", eliminando redundancias y enfocándose en la acción crítica de usar `web_search` cuando se solicita una búsqueda.
     - Hacer más concisas las instrucciones sobre el uso secuencial de herramientas.
 - **Impacto**: Estas optimizaciones reducen la latencia del agente al evitar el procesamiento de RAG cuando no es necesario y mejoran la calidad de las respuestas al proporcionar un contexto más dirigido y prompts más claros al LLM.
 ---
 ## 16-12-2025 Implementación de reintentos con retroceso exponencial en DeepResearchTool
 Se ha implementado un mecanismo de reintentos con retroceso exponencial en `DeepResearchTool` para manejar los errores de "rate limit" (límite de velocidad) al interactuar con los modelos de lenguaje de Gemini. Esto asegura una mayor robustez y resiliencia de la herramienta frente a las limitaciones de cuota de la API.
 - **Detección de errores de "rate limit"**: Se ha configurado la herramienta para detectar excepciones `ResourceExhausted` (comunes en APIs de Google Cloud para límites de cuota) y `httpx.HTTPStatusError` con código 429 (Too Many Requests).
 - **Retroceso exponencial**: Se utiliza la librería `tenacity` para reintentar las operaciones fallidas con un tiempo de espera que aumenta exponencialmente entre 4 y 60 segundos.
 - **Número máximo de reintentos**: La operación se reintentará un máximo de 5 veces antes de fallar definitivamente.
 - **Impacto**: Esta mejora reduce la probabilidad de fallos debido a la superación de la cuota de tokens por minuto, permitiendo que las operaciones de investigación profunda se completen de manera más fiable.
 ---
 ## 16-12-2025 Mejora de granularidad en la identificación de conceptos centrales
 Se ha modificado la función `_identify_central_concept` en `knowledge_graph/conceptual_graph_processor.py` para que sea más granular en la identificación de conceptos centrales. Esto se logró ajustando el prompt enviado al LLM con instrucciones más específicas y ejemplos que fomentan una descripción más detallada. Además, se eliminó la validación estricta que lanzaba un error si el LLM devolvía un concepto genérico, reemplazándola por una advertencia y un fallback más informativo.
 - **Modificación del Prompt del LLM**: Se ajustó el prompt en `_identify_central_concept` para solicitar un concepto central altamente granular y específico, con ejemplos que ilustran la granularidad deseada.
 - **Eliminación de Validación Estricta**: Se eliminó el `raise ValueError` para conceptos genéricos del LLM, permitiendo mayor flexibilidad y proporcionando un valor de fallback.
 ---
 ## 16-12-2025 Visibilidad de propiedades de citas conceptuales en el sidebar de detalles del nodo
 Se mejoró la visibilidad de las propiedades de las citas conceptuales en el componente `NodeDetailsSidebar.tsx`. Ahora, el texto completo de la cita (`full_text`) se muestra de manera prioritaria y se ha añadido explícitamente el método de extracción (`extraction_method`) en la sección `CONCEPTUAL_QUOTE` para asegurar que todas las propiedades relevantes sean visibles para el usuario.
 - **Visualización del Texto Completo**: Se prioriza la propiedad `full_text` para mostrar el contenido completo de la cita conceptual.
 - **Método de Extracción Explícito**: Se añadió la propiedad `extraction_method` en la sección `CONCEPTUAL_QUOTE` del sidebar.
 - **Visibilidad de Concepto y Categoría**: Se hicieron más prominentes las propiedades `concept` y `category` en la sección `CONCEPTUAL_QUOTE` con la adición de iconos.
 ---
 ## 16-12-2025 Corrección de asignación de nombre de nodo CONCEPTUAL_QUOTE
 Se modificó la función `_convert_conceptual_to_neo4j_format` en `knowledge_graph/graph_integration.py` para asignar el `full_text` de la cita a la propiedad `name` del nodo `CONCEPTUAL_QUOTE`. Esto asegura que el título principal del nodo en el frontend muestre el texto completo de la cita, mientras que `concept` y `category` se mantienen como propiedades separadas.
 - **Asignación de `full_text` a `name`**: La propiedad `name` del nodo `CONCEPTUAL_QUOTE` ahora se establece con el `full_text` de la cita.
 ---
 ## 16-12-2025 Corrección de error de sobrescritura de `docs/Cambios.md`
 Se corrigió un error en el que el archivo `docs/Cambios.md` fue sobrescrito accidentalmente en lugar de ser actualizado de forma incremental. Se ha restaurado el contenido previo y se ha añadido la entrada correspondiente a la corrección del `name` del nodo `CONCEPTUAL_QUOTE`.
 ---
 ## 16-12-2025 Persistencia de propiedades `concept` y `category` en Neo4j
 Se modificó la función `_add_entities_to_neo4j` en `knowledge_graph/neo4j_adapter.py` para asegurar que las propiedades `concept` y `category` de los nodos `CONCEPTUAL_QUOTE` se extraigan correctamente y se persistan en la base de datos Neo4j.
 - **Extracción e inclusión de `concept` y `category`**: Se agregó la lógica para extraer `concept` y `category` de los datos de la entidad y se incluyeron estas propiedades en el diccionario `entity_data`.
 - **Actualización de la consulta Cypher**: Se modificó la consulta Cypher para incluir `n.concept = entity.concept` y `n.category = entity.category` en la cláusula `SET`, asegurando su almacenamiento en Neo4j.
---

## 16-12-2025 Inclusión de `concept` y `category` en la visualización del grafo

Se modificó la función `get_visualization_data` en `knowledge_graph/graph_integration.py` para asegurar que las propiedades `concept` y `category` de los nodos `CONCEPTUAL_QUOTE` se incluyan explícitamente en los resultados de la consulta Cypher para el frontend.

- **Modificación de la consulta Cypher por defecto**: Se añadió `n.concept AS concept, n.category AS category` a la cláusula `RETURN` de la consulta Cypher predeterminada.
- **Instrucciones al LLM para generación de Cypher**: Se actualizó el prompt para el LLM, indicándole que debe incluir `n.concept` y `n.category` en la cláusula `RETURN` para nodos de tipo `CONCEPTUAL_QUOTE` cuando genere consultas Cypher.