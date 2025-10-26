## 25-10-24 Visualización de adjuntos en CommonChat.tsx
Descripción general: Se solucionó un problema donde los adjuntos (imágenes y contexto RAG) no se visualizaban correctamente en los mensajes del usuario en el componente CommonChat.tsx.

- **Inconsistencia de propiedad de imagen**: Se cambió el nombre de la propiedad `image_base64` a `image` en la interfaz `ChatMessageType` para que coincidiera con la propiedad esperada por el componente `ChatMessage`.
- **Paso de `ragContext`**: Se modificó la función `handleSendMessage` para asegurar que el `ragContext` (archivos adjuntos) se incluya en el objeto `userMessage` que se muestra en el frontend.
---
## 25-10-24 Visualización de adjuntos desde ContextSelectorButton
Descripción general: Se corrigió la falta de visualización de los adjuntos seleccionados a través del `ContextSelectorButton` en los mensajes del usuario.

- **Actualización de la prop `onContextSelected`**: Se modificó la prop `onContextSelected` del `ContextSelectorButton` en `src/components/CommonChat.tsx` para que apunte a la función `setSelectedContext`, permitiendo que los elementos seleccionados se pasen correctamente al estado y se visualicen.
---
## 25-10-24 Implementación de Forzado de Herramientas y Corrección de Importación
Descripción general: Se implementó la funcionalidad para forzar el uso de herramientas específicas en el `ChatInputBar` y se corrigió un error de importación en `deep_research_tool.py`.

- **Corrección de `ModuleNotFoundError`**: Se ajustaron las rutas de importación en [`tools/deep_research_tool.py`](tools/deep_research_tool.py:12) para resolver el `ModuleNotFoundError` del módulo `open_deep_research`.
- **Corrección de `ModuleNotFoundError`**: Se ajustaron las rutas de importación en [`tools/deep_research_tool.py`](tools/tools/deep_research_tool.py:12) para resolver el `ModuleNotFoundError` del módulo `open_deep_research`.
- **Actualización de `ChatInputBarProps`**: Se añadieron nuevas propiedades a la interfaz `ChatInputBarProps` en [`src/components/ChatInputBar.tsx`](src/components/ChatInputBar.tsx:39) para manejar el estado de forzado de las herramientas.
- **Modificación de `ChatInputBarComponent`**: Se actualizó el componente `ChatInputBarComponent` en [`src/components/ChatInputBar.tsx`](src/components/ChatInputBar.tsx:72) para pasar las nuevas propiedades de forzado de herramientas al `MoreActionsMenu`.
- **Creación y Modificación de `ToolSwitch`**: Se creó un nuevo componente `ToolSwitch` en [`src/components/ToolSwitch.tsx`](src/components/ToolSwitch.tsx:1) con una etiqueta opcional y se aseguró que los interruptores siempre estén activos.
- **Actualización de `MoreActionsMenuProps`**: Se modificó la interfaz `MoreActionsMenuProps` en [`src/components/MoreActionsMenu.tsx`](src/components/MoreActionsMenu.tsx:10) para incluir las propiedades de forzado de herramientas.
- **Modificación de `MoreActionsMenu`**: Se actualizó el componente `MoreActionsMenu` en [`src/components/MoreActionsMenu.tsx`](src/components/MoreActionsMenu.tsx:20) para integrar los `ToolSwitch` en los ítems del menú, eliminando la palabra "Forzar" y asegurando que los interruptores estén siempre activos.
- **Ajuste de `handleSubmit`**: Se modificó la lógica de `handleSubmit` en [`src/components/ChatInputBar.tsx`](src/components/ChatInputBar.tsx:128) para incluir la herramienta forzada en el mensaje si su interruptor está activado.
---
## 25-10-24 Extensión de la herramienta de grafo de conocimiento

Se ha extendido la herramienta `CogneeKnowledgeGraphTool` para permitir búsquedas más avanzadas y un formato de salida más flexible.

- **Nuevos parámetros en `CogneeKnowledgeGraphToolInput`**: Se añadieron los campos `relationship_types`, `source_concept`, `target_concept`, `max_hops`, `pattern_description` y `return_type` para permitir consultas más específicas y complejas.
- **Actualización de `_arun` y `_run`**: Los métodos ahora aceptan y pasan los nuevos parámetros a la capa de integración de `Cognee`.
- **Mejora en el formato de salida**: Los métodos `_format_search_results` y `_format_insights` ahora manejan diferentes `return_type` (`nodes`, `relationships`, `paths`, `summary`) para formatear los resultados de manera adecuada.
---
## 25-10-24 Mejora de Búsqueda en Grafo de Conocimiento

Se implementó una lógica de búsqueda avanzada en la función `search_knowledge_graph` para permitir consultas más complejas y específicas, yendo más allá de la búsqueda full-text.

- **Nuevos Parámetros de Búsqueda**: La función `search_knowledge_graph` ahora acepta `relationship_types`, `source_concept`, `target_concept`, `max_hops`, y `return_type` para búsquedas relacionales y de caminos.
- **Lógica de Consulta Dinámica**: Se añadió una nueva rama de código que construye una consulta Cypher dinámicamente basada en los nuevos parámetros, permitiendo explorar el grafo de forma estructurada.
- **Formateo de Resultados**: Se crearon las funciones auxiliares `_format_advanced_search_results` y `_format_path` para procesar los resultados de Neo4j y devolverlos en formatos flexibles como nodos, relaciones, caminos o un resumen.
---
## 26-10-24 Actualización de la descripción de la herramienta CogneeKnowledgeGraphTool
Descripción general: Se actualizó la descripción de la clase `CogneeKnowledgeGraphTool` para reflejar los nuevos parámetros de búsqueda avanzada disponibles en `CogneeKnowledgeGraphToolInput`.

- **Actualización de `description`**: Se modificó el atributo `description` de la clase `CogneeKnowledgeGraphTool` para incluir detalles sobre los parámetros `relationship_types`, `source_concept`, `target_concept`, `max_hops`, `pattern_description` y `return_type`, mejorando la comprensión del LLM sobre cómo utilizar la herramienta para búsquedas complejas en el grafo de conocimiento.
---
## 26-10-24 Refactorización y mejora de la función `search_knowledge_graph`
 Descripción general: Se ha refactorizado y mejorado la función `search_knowledge_graph` en [`knowledge_graph/cognee_integration.py`](knowledge_graph/cognee_integration.py) para introducir una priorización clara en los tipos de búsqueda (relacional/caminos, patrones específicos, insights generales y full-text) y refinar el manejo de `pattern_description` y la generación de insights.

 - **Priorización de Búsquedas**: Se implementó una lógica de priorización para ejecutar búsquedas relacionales/de caminos si se especifican parámetros estructurados, seguida de búsquedas de patrones específicos si se proporciona `pattern_description`, luego insights generales, y finalmente búsqueda full-text como última opción.
 - **Manejo de `pattern_description`**: Se integró el parámetro `pattern_description` para permitir búsquedas de patrones más inteligentes, utilizando una combinación de la consulta original y la descripción del patrón para la búsqueda full-text.
 - **Generación de Insights Generales**: Se mejoró la sección de insights generales para obtener estadísticas del grafo (distribución de tipos de nodos y relaciones, nodos más conectados) y generar un resumen legible.
 - **Formateo de Resultados Full-Text**: Se completó la lógica para formatear los resultados de la búsqueda full-text, convirtiendo los nodos y relaciones de Neo4j en un formato legible que incluye IDs, etiquetas, propiedades y puntuación.
 - **Ajuste de `hop_spec`**: Se ajustó la construcción de `hop_spec` en las consultas Cypher para manejar correctamente `max_hops=1` o ilimitado.
 - **Actualización de `status` y `method`**: Se actualizaron los campos `status` y `method` en los resultados de búsqueda para reflejar el tipo de búsqueda realizada (`search_completed_advanced_graph`, `search_completed_pattern`, `general_insights`, `fulltext_cypher`).
---
## 26-10-24 Mejora de la herramienta `cognee_knowledge_graph` para consultas avanzadas.
 Descripción general: Se ha extendido la funcionalidad de la herramienta `cognee_knowledge_graph` para permitir consultas más sofisticadas y una interacción más inteligente con el grafo de conocimiento. Esto incluye la capacidad de realizar búsquedas relacionales, de caminos y de patrones específicos, así como la obtención de insights generales.

 - **Extensión de `CogneeKnowledgeGraphToolInput`**: Se añadieron nuevos parámetros opcionales (`relationship_types`, `source_concept`, `target_concept`, `max_hops`, `pattern_description`, `return_type`) a la clase `CogneeKnowledgeGraphToolInput` en [`tools/cognee_knowledge_graph_tool.py`](tools/cognee_knowledge_graph_tool.py) para permitir al LLM especificar intenciones de consulta más granulares.
 - **Modificación de `_arun` en `CogneeKnowledgeGraphTool`**: La función `_arun` en [`tools/cognee_knowledge_graph_tool.py`](tools/cognee_knowledge_graph_tool.py) fue actualizada para pasar estos nuevos parámetros a la integración de Cognee.
 - **Implementación de lógica avanzada en `search_knowledge_graph`**: Se implementó una lógica de búsqueda avanzada en la función `search_knowledge_graph` de [`knowledge_graph/cognee_integration.py`](knowledge_graph/cognee_integration.py). Esta lógica prioriza las búsquedas relacionales y de caminos, seguida de la búsqueda de patrones específicos y, finalmente, la búsqueda full-text. Se corrigieron los placeholders existentes para asegurar una implementación completa de la lógica de "insights" y el formateo de resultados full-text.
 - **Actualización de la descripción de la herramienta**: Se modificó la descripción de la clase `CogneeKnowledgeGraphTool` en [`tools/cognee_knowledge_graph_tool.py`](tools/cognee_knowledge_graph_tool.py) para detallar los nuevos parámetros de búsqueda avanzada, asegurando que el LLM tenga una comprensión clara de cómo utilizarlos.
---
## 26-10-24 Corrección de NameError en `search_knowledge_graph`
 Descripción general: Se corrigió el `NameError: name 'rel_stats' is not defined` en la función `search_knowledge_graph` del archivo [`knowledge_graph/cognee_integration.py`](knowledge_graph/cognee_integration.py). La causa era que las variables `node_stats` y `rels_stats` no estaban garantizadas para ser listas en todos los escenarios, lo que podía llevar a errores al intentar iterar sobre ellas.

 - **Inicialización robusta de variables**: Se modificaron las asignaciones de `node_stats` y `rels_stats` en la función `search_knowledge_graph` para asegurar que siempre se inicialicen como listas vacías si las consultas a la base de datos no devuelven resultados. Esto se logró añadiendo `or []` a las llamadas `await self.graph_db.execute_query()`.
---
## 26-10-24 Corrección de NameError en la lógica de insights de search_knowledge_graph
Descripción general: Se ha corregido un NameError (name 'rel_stats' is not defined) en la función search_knowledge_graph de knowledge_graph/cognee_integration.py. Este error ocurría en la sección de obtención de insights generales debido a una asignación incorrecta de la variable rels_stats.

- **Corrección de NameError**: Se aseguró que la variable rels_stats se inicialice correctamente con el resultado de la consulta a la base de datos antes de ser utilizada, previniendo el NameError.
---
## 26-10-24 Corrección de rutas de importación en Deep Research Agent
Descripción general: Se corrigieron las rutas de importación en el archivo `deep_researcher.py` y se ajustaron los comentarios en `deep_research_tool.py` para resolver errores de `ModuleNotFoundError` y mejorar la claridad.

- **Actualización de importaciones en deep_researcher.py**: Se verificó que las importaciones en [`external_agents/open_deep_research/src/open_deep_research/deep_researcher.py`](external_agents/open_deep_research/src/open_deep_research/deep_researcher.py) ya eran absolutas desde la raíz del proyecto, por lo que no se aplicó ningún cambio.
- **Ajuste de importaciones en deep_research_tool.py**: Se aplicó un `diff` al archivo [`tools/deep_research_tool.py`](tools/deep_research_tool.py) para ajustar los comentarios de las importaciones de `DeepResearcher` y `ResearchConfig`, mejorando la legibilidad.
---
## 26-10-25 Solución a ModuleNotFoundError en open_deep_research
 Descripción general: Se diagnosticó un `ModuleNotFoundError` para el módulo `open_deep_research` dentro del contenedor Docker del servicio `core`. La causa raíz fue una configuración incompleta del `PYTHONPATH` en el `Dockerfile`.

 - **Diagnóstico**: El `PYTHONPATH` en el `Dockerfile.core.hybrid` solo incluía `/app`, lo que impedía que Python encontrara el módulo `open_deep_research` ubicado en `external_agents/open_deep_research/src/`.
 - **Solución propuesta**: Se modificó la línea `ENV PYTHONPATH /app` a `ENV PYTHONPATH /app:/app/external_agents/open_deep_research/src` en el [`Dockerfile.core.hybrid`](Dockerfile.core.hybrid) para añadir la ruta correcta al `PYTHONPATH`.
 - **Instrucciones para el usuario**: Para aplicar el cambio, el usuario debe reconstruir la imagen Docker (`docker-compose build core`) y reiniciar el servicio `core` (`docker-compose up -d core`).
---
## 26-10-24 Mejora de la lógica de búsqueda de patrones en `search_knowledge_graph`
 Descripción general: Se ha modificado la función `search_knowledge_graph` en [`knowledge_graph/cognee_integration.py`](knowledge_graph/cognee_integration.py) para mejorar la búsqueda de patrones específicos utilizando `pattern_description` y refinar la generación de insights generales.

 - **Priorización de búsqueda de patrones**: Se ajustó la lógica para dar mayor prioridad a la búsqueda de patrones específicos cuando se proporciona `pattern_description`, utilizando una búsqueda full-text mejorada que combina la consulta original con la descripción del patrón.
 - **Formateo de resultados de patrones**: Los resultados de la búsqueda de patrones ahora se formatean para devolver nodos y relaciones directamente, en lugar de solo conteos, proporcionando información más detallada.
 - **Manejo de insights generales**: Se mejoró la sección de insights generales para obtener estadísticas más completas del grafo, incluyendo categorías de nodos y tipos de relaciones más comunes, y se generó un resumen legible de estos insights.
 - **Mensajes de estado y resumen**: Se actualizaron los mensajes de estado y resumen para reflejar con mayor precisión si se encontraron patrones o insights generales.