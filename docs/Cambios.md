## 11-11-2025 Desactivación de la herramienta `knowledge_base_analyzer`

Se desactivó la herramienta `knowledge_base_analyzer` para el LLM, eliminando sus referencias y el archivo de la herramienta.

- **Eliminación de importación**: Se eliminó la importación de `KnowledgeAnalysisTool` en [`core/tools.py`](core/tools.py:66).
- **Eliminación de descripción**: Se eliminó la descripción de `knowledge_base_analyzer` en [`core/config.py`](core/config.py:207).
- **Eliminación de referencia en `prompt_manager`**: Se eliminó la referencia a `knowledge_base_analyzer` en [`core/prompt_manager.py`](core/prompt_manager.py:127).
- **Eliminación del archivo de la herramienta**: Se eliminó el archivo [`tools/knowledge_analysis_tool.py`](tools/knowledge_analysis_tool.py).

---

## 11-11-2025 Corrección de error 404 en `get-document-content`

Se corrigió un error 404 al acceder al endpoint `/api/get-document-content` modificando las llamadas en el frontend para que coincidieran con la definición del endpoint en el backend.

- **Modificación en `api/documents.py`**: Se cambió el método del endpoint `/get-document-content` de `POST` a `GET` y se ajustó para recibir el `file_name` como parámetro de consulta.
- **Modificación en `src/app/(dashboard)/teams/[id]/dashboard/page.tsx`**: Se actualizó la llamada a la API de `apiClient.post` a `apiClient.get` y se pasó el `file_name` como parámetro de consulta.
- **Modificación en `src/app/(dashboard)/rag/preview-document-dialog.tsx`**: Se actualizó la llamada a la API de `apiClient.post` a `apiClient.get` y se pasó el `file_name` como parámetro de consulta.

---

## 11-11-2025 Mejora en la actualización de títulos en tiempo real

Se mejoró la actualización de títulos en tiempo real en la página de detalles de la colección para que sea más fluida y no recargue toda la lista de documentos.

- **Modificación en `src/components/DocumentCollectionDisplay.tsx`**:
    - Se eliminó el `toast` de la función `onTitleUpdated` para evitar notificaciones excesivas.
    - Se eliminó la llamada a `fetchPageData()` de la función `onTitleExtractionCompleted` para evitar la recarga completa de la página.

---

## 11-11-2025 Corrección de codificación de URL y prefijo en `get-document-content`

Se corrigió un error 404 que ocurría con nombres de archivo que contenían caracteres especiales y la falta del prefijo `/documents` en la URL. El problema se resolvió codificando correctamente el `file_name` y añadiendo el prefijo `/documents` en el frontend antes de enviarlo al backend.

- **Modificación en `src/app/(dashboard)/teams/[id]/dashboard/page.tsx`**: Se utilizó `encodeURIComponent` para codificar el `file_name` y se añadió el prefijo `/documents` en la llamada a `/api/get-document-content`.
- **Modificación en `src/app/(dashboard)/rag/preview-document-dialog.tsx`**: Se utilizó `encodeURIComponent` para codificar el `file_name` y se añadió el prefijo `/documents` en la llamada a `/api/get-document-content`.

---

## 11-11-2025 Corrección de `ReferenceError: router is not defined` en `AnalysisPage`

Se corrigió el error `ReferenceError: router is not defined` en el componente `AnalysisPage` al inicializar correctamente el hook `useRouter` de Next.js.

- **Modificación en `src/app/(dashboard)/analysis/page.tsx`**: Se añadió la línea `const router = useRouter();` dentro del componente funcional `AnalysisPage`.
---
## 11-11-25 Mejora en la visualización de detalles de análisis

Se ha mejorado el componente `analysis-detail-dialog.tsx` para que muestre correctamente los campos de todos los tipos de análisis, incluyendo los de código, por tema y los insights proactivos manuales.

- **Análisis de `analysis-detail-dialog.tsx`**: Se analizó el componente para entender su estructura y la lógica de renderizado de los diferentes tipos de análisis.
- **Identificación de tipos de datos**: Se revisaron los archivos `utils/advanced_text_analyzer.py`, `utils/advanced_code_analyzer.py` y `utils/analysis_on_topic.py` para identificar la estructura de datos de cada tipo de análisis.
- **Implementación de la lógica de renderizado**: Se añadió la lógica necesaria en `analysis-detail-dialog.tsx` para mostrar los campos específicos de cada tipo de análisis.
- **Corrección de errores de TypeScript**: Se solucionaron los errores de tipos y de sintaxis JSX que surgieron durante la implementación.
---
## 11-11-25 Corrección en la reconstrucción de contenido de documentos para Cognee
Se ha corregido un error en la función `_reconstruct_document_content` en `knowledge_graph/cognee_integration.py` que impedía la correcta reconstrucción del contenido de los documentos. El problema se debía a que la función no buscaba el `file_name` en la ubicación correcta del diccionario de documentos.

- **Modificación en `knowledge_graph/cognee_integration.py`**: Se actualizó la línea 409 para incluir `doc.get("file_name")` en la lógica de obtención del nombre del archivo, asegurando que se encuentre correctamente cuando se pasa directamente en la raíz del diccionario del documento.
---
## 11-11-25 Cambio de herramienta para "Crear Grafo de Conocimiento" en RAG

Se ha modificado la funcionalidad de "Crear Grafo de Conocimiento" en la interfaz de usuario de RAG para que utilice la herramienta `cognee_knowledge_graph_tool` en lugar de `cognee_conceptual_processing_tool`. Este cambio asegura que la acción de crear grafos desde el frontend esté alineada con la herramienta más adecuada para esta tarea.

- **Modificación en `src/app/(dashboard)/rag/page.tsx`**: La función `handleProcessKnowledgeGraph` fue actualizada para invocar la herramienta `cognee_knowledge_graph` con la acción `process_documents` a través del endpoint `/api/tools/run`.
- **Modificación en `src/components/DocumentCollectionDisplay.tsx`**: La función `handleProcessKnowledgeGraph` fue actualizada para invocar la herramienta `cognee_knowledge_graph` con la acción `process_documents` a través del endpoint `/api/tools/run`.