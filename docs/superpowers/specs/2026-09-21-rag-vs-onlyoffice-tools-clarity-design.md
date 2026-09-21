# Especificación de Diseño: Clarificación de Herramientas y Contexto RAG vs OnlyOffice

**Fecha:** 2026-09-21  
**Estado:** Propuesto para revisión  
**Objetivo:** Eliminar la confusión del agente de IA de KAI al trabajar con documentos, delimitando con precisión las herramientas de la Base de Conocimiento RAG de las herramientas del módulo de edición OnlyOffice, tanto en las descripciones de herramientas y prompts del sistema, como en la selección y transmisión del contexto adjunto desde el frontend.

---

## 1. Contexto y Problema

En KAI existen dos dominios completamente distintos de documentos:
1. **Base de Conocimiento RAG (`document_management_skill` / `rag_skill`):**
   - Documentos (PDFs, TXT, archivos de referencia) procesados y vectorizados en PostgreSQL (`pgvector` / `langchain_pg_embedding`).
   - Propósito: Búsqueda semántica, extracción de información, responder preguntas basadas en fuentes y síntesis de contenido.
   - Herramientas principales: `get_document_content_tool` (requiere `file_name`), `get_document_list_tool`, `scoped_rag_analysis`, `process_document_for_rag`.

2. **Documentos Editables OnlyOffice (`onlyoffice_skill`):**
   - Archivos ofimáticos reales en el servidor (`.docx`, `.xlsx`, `.pptx`, etc.) registrados en la tabla `onlyoffice_documents` y editables en el visor/editor web de KAI.
   - Propósito: Crear, editar, formatear, agregar tablas/gráficos/fórmulas y abrir en el editor online.
   - Herramientas principales: `read_onlyoffice_document` (requiere UUID `document_id`), `edit_onlyoffice_document`, `create_onlyoffice_document`, `search_onlyoffice_documents`, `list_onlyoffice_documents`.

### Puntos de Fallo Actuales:
- **Descripciones genéricas:** Herramientas como `get_document_content_tool` se describen como *"La herramienta principal para leer y recuperar el contenido textual completo de un documento..."*, llevando al agente a usarla para archivos de Word/Excel de OnlyOffice. A su vez, `read_onlyoffice_document` no explicita que no debe usarse para documentos RAG.
- **Colisión de tipo en el contexto (`rag_context`):** `ContextSelectorDialog` asigna `type: 'document'` tanto a documentos RAG como a documentos OnlyOffice. Cuando el backend recibe `rag_context`, `agent.py` intenta consultar en `pgvector` los IDs de OnlyOffice (que no existen allí), generando vacíos o errores.
- **ContextSelectorButton limitado:** `ContextSelectorButton.tsx` no permite visualizar ni adjuntar documentos de OnlyOffice, limitándose solo a RAG, y no deja claro el modo de adjunción.
- **Falta de directrices canónicas en el prompt del sistema:** El modelo no tiene una regla explícita en `KAI_SYSTEM_PROMPT` ni en la cabecera de contexto que le indique: *"Si el documento adjunto es RAG, usa la herramienta X; si es OnlyOffice, usa la herramienta Y"*.

---

## 2. Arquitectura de la Solución

```
+-----------------------------------------------------------------------------------+
| FRONTEND: ContextSelectorButton & ContextSelectorDialog                           |
|  - Pestaña / Sección RAG          -> item.type = 'document' (o 'rag_document')   |
|  - Pestaña / Sección OnlyOffice   -> item.type = 'onlyoffice'                    |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v  (POST /api/chat con rag_context JSON)
+-----------------------------------------------------------------------------------+
| BACKEND CORE: core/agent.py & core/prompt_manager.py                              |
|  1. agent.py:                                                                     |
|     - Filtra explicit_doc_ids solo para items RAG (no OnlyOffice)                 |
|     - Selecciona dinámicamente 'onlyoffice_skill' si hay items 'onlyoffice'       |
|  2. prompt_manager.py:                                                            |
|     - Formatea la cabecera activa distinguiendo secciones y herramientas exactas: |
|       * [BASE DE CONOCIMIENTO RAG]: get_document_content_tool(file_name=...)      |
|       * [DOCUMENTO ONLYOFFICE]: read_onlyoffice_document(document_id=UUID)        |
|  3. core/prompts.py:                                                              |
|     - Nueva sección canónica en KAI_SYSTEM_PROMPT explicando la regla de oro.     |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| HERRAMIENTAS: LangChain Tools & SKILL.md                                          |
|  - Prefijo explícito [BASE DE CONOCIMIENTO RAG] en herramientas RAG               |
|  - Prefijo explícito [MÓDULO ONLYOFFICE DE KAI] en herramientas OnlyOffice        |
|  - Instrucciones de exclusión mutua en cada descripción                           |
+-----------------------------------------------------------------------------------+
```

---

## 3. Cambios Detallados por Componente

### 3.1. Frontend

#### `src/types/context.ts`
- Asegurar que `SelectedContextItem['type']` admita explícitamente `'onlyoffice'` y mantenga compatibilidad con `'document'` y `'collection'`.

#### `src/components/ContextSelectorButton.tsx`
- Transformar el popover simple en un selector con pestañas o secciones claras:
  - **Pestaña 1: Base de Conocimiento (RAG):** Documentos y colecciones existentes (`/api/collections` y `/api/documents/list-documents`), con iconos de libro/archivo verde/secundario y badge `RAG`.
  - **Pestaña 2: Documentos OnlyOffice:** Lista de archivos editables (`/api/onlyoffice/list`), con iconos azules y badge `OnlyOffice`.
- Al seleccionar un archivo OnlyOffice: generar `SelectedContextItem` con `type: 'onlyoffice'`, `id: doc.id`, `name: doc.filename`, `topic: 'OnlyOffice'`.
- Mantener la selección unificada al hacer clic en "Aplicar Contexto".

#### `src/components/ContextSelectorDialog.tsx`
- En la pestaña `onlyoffice`, cambiar la creación del `contextItem` para que asigne `type: 'onlyoffice'` en lugar de `type: 'document'`.
- Mantener compatibilidad visual con las etiquetas y selección actual.

#### `src/components/ChatMessage.tsx` y `src/components/ChatSettingsPanel.tsx`
- Reconocer `item.type === 'onlyoffice'` para renderizar un icono o distintivo azul claro `OnlyOffice` y diferenciarlo visualmente de los documentos RAG.

---

### 3.2. Backend: Agente y Prompts

#### `core/prompts.py` (`KAI_SYSTEM_PROMPT`)
- Añadir sección obligatoria:
  ```markdown
  **📄 DISTINCIÓN CANÓNICA: DOCUMENTOS RAG VS DOCUMENTOS ONLYOFFICE:**
  1. **Base de Conocimiento RAG (Búsqueda semántica y memorias):**
     - Son documentos (PDF, TXT, etc.) vectorizados en la base de datos de conocimiento.
     - Propósito: Buscar información, consultar datos históricos, extraer fragmentos.
     - Herramientas a usar: `get_document_content_tool` (pasando `file_name`) y `scoped_rag_analysis`.
     - NUNCA uses herramientas de OnlyOffice para consultar la base de conocimiento RAG.
  2. **Documentos OnlyOffice (Archivos editables en la nube):**
     - Son documentos reales (.docx, .xlsx, .pptx) alojados en el editor OnlyOffice de KAI.
     - Propósito: Leer estructura editable, redactar, crear, modificar celdas, tablas o diapositivas.
     - Herramientas a usar: `read_onlyoffice_document` (pasando `document_id` UUID), `edit_onlyoffice_document`, `create_onlyoffice_document`, `search_onlyoffice_documents`, `list_onlyoffice_documents`.
     - NUNCA uses `get_document_content_tool` para archivos de OnlyOffice.
  ```

#### `core/prompt_manager.py`
- En `_format_selected_context_items`:
  - Si `item_type == 'onlyoffice'` (o `topic == 'OnlyOffice'`):
    - Etiquetar como `[DOCUMENTO ONLYOFFICE (EDITABLE)]`.
    - Indicar: `(Handle: document_id="{item_id}", nombre="{exact_name}"). Herramientas a usar: 'read_onlyoffice_document' o 'edit_onlyoffice_document'.`
  - Si `item_type == 'document'`:
    - Etiquetar como `[DOCUMENTO RAG (BASE DE CONOCIMIENTO)]`.
    - Indicar: `(Handle: file_name="{file_name}", id="{item_id}"). Herramientas a usar: 'get_document_content_tool' o 'scoped_rag_analysis'.`
  - Si `item_type == 'collection'`:
    - Etiquetar como `[COLECCIÓN RAG]`.

#### `core/agent.py`
- En la extracción de `explicit_doc_ids`:
  - Filtrar para ignorar elementos de tipo `onlyoffice` (o con `topic == 'OnlyOffice'`). Así `get_relevant_memories` solo consulta UUIDs reales de RAG en `pgvector`.
- En la detección de categorías dinámicas de herramientas (`select_relevant_categories` o similar):
  - Si el contexto adjunto contiene elementos de OnlyOffice, asegurar que `onlyoffice_skill` sea incluida en la toolbox del agente para esa interacción.

---

### 3.3. Descripciones de Herramientas

#### Herramientas RAG (`document_management_skill` y `rag_skill`)
1. **`get_document_content_tool`**:
   - `description`: `"[BASE DE CONOCIMIENTO RAG] Recupera el contenido textual completo de un documento almacenado en la base de conocimiento vectorial del usuario a partir de su 'file_name'. ÚSALA EXCLUSIVAMENTE para documentos de la base de conocimiento RAG. NO LA USES para documentos de OnlyOffice (Word/Excel/PowerPoint editables); para OnlyOffice debes usar 'read_onlyoffice_document'."`
2. **`get_document_list_tool`**:
   - `description`: `"[BASE DE CONOCIMIENTO RAG] Lista los documentos y colecciones (topics) almacenados en la base de conocimiento vectorial (RAG). NO lista los archivos de OnlyOffice; para ver o buscar archivos de OnlyOffice usa 'list_onlyoffice_documents' o 'search_onlyoffice_documents'."`
3. **`process_document_for_rag`** (`DocumentRAGTool`):
   - `description`: `"[BASE DE CONOCIMIENTO RAG] Procesa, fragmenta y almacena texto de un documento en la base vectorial (RAG) para búsqueda semántica futura. NO crea archivos editables de Office; para crear documentos editables (Word/Excel/PPT) usa 'create_onlyoffice_document'."`
4. **`scoped_rag_analysis`**:
   - `description`: `"[BASE DE CONOCIMIENTO RAG] Realiza un análisis profundo y estructurado sobre la base de conocimiento vectorial del usuario (notas y documentos RAG). No opera sobre archivos de OnlyOffice."`
5. **`delete_document_tool`** y **`update_document_metadata_tool`**:
   - Agregar prefijo `[BASE DE CONOCIMIENTO RAG]` explicitando que gestionan registros vectoriales de la base de conocimiento.

#### Herramientas OnlyOffice (`onlyoffice_skill`)
1. **`read_onlyoffice_document`**:
   - `description`: `"[MÓDULO ONLYOFFICE DE KAI] Lee el contenido textual completo y estructura de un documento editable de OnlyOffice (.docx, .xlsx, .pptx, .csv, .txt) mediante su 'document_id' (UUID). ÚSALA EXCLUSIVAMENTE para documentos de OnlyOffice. NO LA USES para documentos de la base de conocimiento RAG (para esos usa 'get_document_content_tool')."`
2. **`search_onlyoffice_documents`**:
   - `description`: `"[MÓDULO ONLYOFFICE DE KAI] Busca documentos y carpetas en el módulo de documentos OnlyOffice por nombre o workspace para obtener su UUID. NO busca en la base de conocimiento RAG ni en memorias vectoriales."`
3. **`list_onlyoffice_documents`**:
   - `description`: `"[MÓDULO ONLYOFFICE DE KAI] Lista las carpetas y archivos editables de OnlyOffice en un directorio o raíz. NO lista documentos de la base de conocimiento RAG."`
4. **`create_onlyoffice_document`** y **`edit_onlyoffice_document`**:
   - Reforzar que operan exclusivamente en el módulo de documentos de KAI y sobre archivos ofimáticos (.docx, .xlsx, .pptx).

---

## 4. Plan de Verificación

1. **Prueba Unitaria de Formateo de Contexto:**
   - Verificar que `_format_selected_context_items` formatea correctamente items de tipo `document` (RAG) y `onlyoffice` con las instrucciones de herramientas apropiadas.
2. **Prueba de Filtrado en `agent.py`:**
   - Verificar que `explicit_doc_ids` solo contiene IDs de documentos RAG y excluye documentos de OnlyOffice.
3. **Prueba de Construcción y Rendereado en Frontend:**
   - Ejecutar `npm run build` o `npm run lint` en el frontend para validar que `ContextSelectorButton.tsx` y `ContextSelectorDialog.tsx` compilan sin errores de tipado en TypeScript.
4. **Validación de Carga de Herramientas:**
   - Verificar que el `SkillManager` carga las descripciones actualizadas sin errores sintácticos.
