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