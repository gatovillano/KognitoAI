# ONLYOFFICE_SKILL: Editor de Documentos en la Plataforma KAI

> ⚠️ **ANTES DE USAR ESTE SKILL, LEE LA SECCIÓN "¿QUÉ HERRAMIENTA USAR?"**
> Este skill opera **EXCLUSIVAMENTE** sobre el módulo de documentos de la plataforma KAI (OnlyOffice).
> NO crea archivos en el sistema de archivos local del usuario ni en la base de conocimientos.

---

## ¿Qué herramienta usar? — Tabla de Decisión

El agente DEBE elegir la herramienta correcta según el **destino final** del archivo:

| El usuario quiere... | Herramienta correcta | Skill |
|---|---|---|
| Crear/editar un **documento Word, Excel o PowerPoint** que aparezca en la sección "Documentos" de KAI y pueda abrir en el editor online | `create_onlyoffice_document_tool` / `edit_onlyoffice_document_tool` | **Este skill (onlyoffice_skill)** |
| Generar un **PDF** para descargar o compartir | `create_pdf_tool` | `document_management_skill` |
| Guardar un **archivo de texto o código en el disco** del servidor o del usuario (archivos locales reales) | `write_file_tool` / `local_file_navigator` | `developer_tools_skill` |
| Guardar **información, notas o conocimiento** en la memoria de KAI (base vectorial) | `add_memory_tool` | `knowledge_and_memory_skill` |
| Subir un documento existente a la base de conocimientos para que KAI lo indexe y recuerde | `upload_document` vía API | `rag_skill` / `document_management_skill` |

### 🚨 Reglas de decisión obligatorias

**USA este skill (OnlyOffice) ÚNICAMENTE si:**
- El usuario pide explícitamente crear o editar un **documento Word (.docx), Excel (.xlsx) o PowerPoint (.pptx)**
- El usuario quiere verlo en la **sección "Documentos"** de la interfaz de KAI
- El usuario quiere **editar el archivo online** con el editor integrado de OnlyOffice
- El usuario dice "crea un documento en KAI", "crea un Word", "crea una hoja de cálculo", "ábrelo en el editor"

**NO uses este skill si:**
- El usuario pide guardar un archivo en su computador o en el servidor (usa `developer_tools_skill`)
- El usuario quiere que KAI "recuerde" algo o lo guarde en la memoria (usa `knowledge_and_memory_skill`)
- El usuario pide un PDF descargable (usa `create_pdf_tool`)
- El usuario quiere subir un documento para que KAI lo analice (usa la API de documentos RAG)
- El usuario pide crear un script Python, archivo JSON, CSV, Markdown u otro archivo de trabajo (usa `developer_tools_skill`)

---

## Qué es OnlyOffice en KAI

OnlyOffice es el **editor de documentos integrado** en la plataforma KAI. Los archivos creados con este skill:
- Aparecen en la sección **"📁 Documentos"** del panel de KAI
- Pueden ser **abiertos y editados online** directamente desde el navegador
- Son archivos reales almacenados en el servidor de KAI (no en la computadora local del usuario)
- Se registran en la base de datos de KAI y están disponibles en el workspace seleccionado
- Son independientes de la base de conocimientos/memoria de KAI (no se indexan automáticamente para RAG)

---

## Herramientas disponibles

1. `search_onlyoffice_documents_tool` — Listar o buscar archivos en el módulo OnlyOffice por nombre
2. `read_onlyoffice_document_tool` — Leer el contenido de un archivo (.docx, .xlsx, .txt, .csv, .pptx)
3. `create_onlyoffice_document_tool` — **Crear un nuevo documento** en el módulo OnlyOffice (Word, Excel, PowerPoint, Texto)
4. `edit_onlyoffice_document_tool` — **Editar directamente** un documento existente en el módulo OnlyOffice

---

## Flujo de trabajo recomendado

1. Si no tienes el ID del documento, usa `search_onlyoffice_documents_tool` para encontrarlo.
2. Lee el documento con `read_onlyoffice_document_tool` para entender su estructura actual.
3. Aplica los cambios con `edit_onlyoffice_document_tool` usando la acción más apropiada.
4. Informa al usuario que los cambios están guardados y que debe **recargar el editor (F5)** para verlos.

---

## Motor de Renderizado Markdown → Word (.docx)

Al editar documentos `.docx` con `append` o `clear_and_write`, puedes enviar **Markdown completo**. El motor lo traduce automáticamente a elementos nativos de Office aplicando un diseño premium.

### Temas visuales predefinidos (`style_theme`)
Puedes seleccionar uno de los siguientes temas visuales pasándolo en la edición:

- **`modern_blue`** (Por defecto): Fuente `Segoe UI`, títulos en Azul Rey (`#1E3A8A`), texto base gris pizarra (`#334155`). Muy profesional y corporativo.
- **`classic_navy`**: Fuente `Georgia` (serif), títulos en Azul Marino Oscuro (`#0F172A`), texto base negro. Ideal para propuestas formales, contratos y cartas.
- **`emerald_creative`**: Fuente `Calibri`, títulos en Verde Bosque (`#064E3B`), acentos en Esmeralda, texto base gris oscuro. Excelente para ecología, reportes creativos u organizacionales.
- **`corporate_teal`**: Fuente `Arial`, títulos en Teal Oscuro (`#115E59`), acentos en Teal Medio, texto base pizarra. Moderno, limpio y tecnológico.
- **`charcoal_minimalist`**: Fuente `Arial`, títulos y texto base en Negro puro (`#000000`), bordes y sombreados en Gris Claro. Estilo minimalista escandinavo.
- **`warm_amber`**: Fuente `Verdana`, títulos en Ámbar Oscuro (`#78350F`), acentos cálidos, texto base color piedra. Estilo cálido, amigable y natural.

### Personalización a medida (Overrides)
Si prefieres un diseño único, puedes anular aspectos del tema seleccionado usando:
- **`style_font_family`**: Tipografía personalizada (ej: `'Arial'`, `'Georgia'`, `'Times New Roman'`).
- **`style_primary_color`**: Código Hex (ej: `'FF5733'`) para títulos H1 y color de fondo de cabecera de tablas.
- **`style_secondary_color`**: Código Hex para títulos H2.
- **`style_text_color`**: Código Hex para el texto de párrafos principales.

---

## Acciones de edición para .docx

| Acción | Descripción | Campos requeridos | Campos opcionales |
|---|---|---|---|
| `append` | Añade texto o Markdown completo al final | `text` | `style_theme`, `style_font_family`, `style_primary_color`, `style_secondary_color`, `style_text_color` |
| `append_heading` | Añade un título nativo (H1/H2/H3) | `text`, `heading_level` | `style_theme`, `style_font_family`, `style_primary_color`, `style_secondary_color` |
| `append_list` | Añade una lista de viñetas | `list_items` | `style_theme`, `style_font_family`, `style_text_color` |
| `replace` | Busca y reemplaza texto (soporta inline Markdown) | `search_text`, `text` | `style_theme`, `style_font_family`, `style_text_color` |
| `replace_section` | Reemplaza el párrafo que empieza con `search_text` | `search_text`, `text` | `style_theme`, `style_font_family`, `style_text_color` |
| `insert_table` | Inserta una tabla al final | `table_data` (matriz 2D) | `style_theme`, `style_font_family`, `style_primary_color`, `style_text_color` |
| `apply_bold` | Pone en negrita las ocurrencias de un texto | `search_text` | |
| `clear_and_write` | Borra todo el contenido y escribe nuevo texto/Markdown | `text` | `style_theme`, `style_font_family`, `style_primary_color`, `style_secondary_color`, `style_text_color` |
| `edit_paragraph` | Edita un párrafo por índice o búsqueda de texto | `text`, `paragraph_index` o `search_text` | `style_theme`, `style_font_family`, `style_text_color` |
| `insert_image` | Inserta una imagen en el documento | `image_path` | `image_width`, `image_height` |
| `set_page_layout` | Configura márgenes y orientación de página | | `page_margins` (dict), `page_orientation` (`portrait`/`landscape`) |
| `add_header_footer` | Añade contenido a encabezados o pies de página | `header_footer_type` (`header`/`footer`), `header_footer_content` | |
| `apply_cell_style` | Aplica estilos a celdas de tablas | `cell_coords` (ej: `A1`), `cell_style` (dict) | |

## Acciones de edición para .xlsx (Excel)

| Acción | Descripción | Campos requeridos |
|---|---|---|
| `xlsx_write_cell` | Escribe en una celda específica | `cell` (ej: 'B3'), `text`, (`sheet_name`) |
| `xlsx_append_row` | Añade una fila al final de la hoja | `row_data` (lista de valores), (`sheet_name`) |

---

## Tipos de documentos para crear

Usa `create_onlyoffice_document_tool` con el parámetro `doc_type`:

| `doc_type` | Archivo creado | Cuándo usarlo |
|---|---|---|
| `word` | `.docx` | Reportes, propuestas, contratos, documentos de texto con formato |
| `excel` | `.xlsx` | Tablas de datos, presupuestos, planillas, cálculos |
| `powerpoint` | `.pptx` | Presentaciones, slides |
| `text` | `.txt` | Texto plano sin formato |

---

## Limitaciones

- La edición de `.pptx` (PowerPoint) no está soportada aún en `edit_onlyoffice_document_tool`
- Los archivos se crean en el servidor de KAI, **no en el disco local del usuario**
- Se crea un **respaldo automático** antes de cada edición
- El usuario debe **recargar el editor de OnlyOffice (F5 o cerrar y abrir)** para ver los cambios aplicados por el agente
- Estos archivos NO se indexan automáticamente en la base de conocimientos/RAG de KAI

---

**IMPORTANTE**: Siempre lee el documento antes de editar para entender su estructura y evitar sobreescribir contenido valioso. Informa al usuario que debe recargar el editor para ver los cambios.
