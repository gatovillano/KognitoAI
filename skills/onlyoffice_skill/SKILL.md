---
name: onlyoffice
description: Use when viewing, editing, or converting documents, spreadsheets, or
  presentations via the OnlyOffice API or local pipeline.
---

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

## Acciones de edición para .docx (Word)

| Acción | Descripción | Campos requeridos | Campos opcionales |
|---|---|---|---|
| `append` | Añade texto o Markdown completo al final | `text` | `style_theme`, `style_font_family`, `style_primary_color`, `style_secondary_color`, `style_text_color` |
| `append_heading` | Añade un título nativo (H1/H2/H3) | `text`, `heading_level` | `style_theme`, `style_font_family`, `style_primary_color`, `style_secondary_color` |
| `append_list` | Añade una lista de viñetas | `list_items` | `style_theme`, `style_font_family`, `style_text_color` |
| `replace` | Busca y reemplaza texto (soporta inline Markdown) | `search_text`, `text` | `style_theme`, `style_font_family`, `style_text_color` |
| `replace_section` | Reemplaza el párrafo que empieza con `search_text` | `search_text`, `text` | `style_theme`, `style_font_family`, `style_text_color` |
| `insert_table` | Inserta una tabla al final | `table_data` (matriz 2D) | `theme`, `has_total_row`, `auto_calculate_totals`, `col_alignments`, `col_widths`, `cell_padding` |
| `insert_styled_table` | Inserta una tabla con tema visual premium, padding y totals | `table_data` (matriz 2D) | `theme`, `has_total_row`, `auto_calculate_totals`, `col_alignments`, `col_widths`, `cell_padding` |
| `apply_bold` | Pone en negrita las ocurrencias de un texto | `search_text` | |
| `clear_and_write` | Borra todo el contenido y escribe nuevo texto/Markdown | `text` | `style_theme`, `style_font_family`, `style_primary_color`, `style_secondary_color`, `style_text_color` |
| `edit_paragraph` | Edita un párrafo por índice o búsqueda de texto | `text`, `paragraph_index` o `search_text` | `style_theme`, `style_font_family`, `style_text_color` |
| `insert_image` | Inserta una imagen en el documento | `image_path` | `image_width`, `image_height` |
| `set_page_layout` | Configura márgenes y orientación de página | | `page_margins` (dict), `page_orientation` (`portrait`/`landscape`) |
| `add_header_footer` | Añade contenido a encabezados o pies de página | `header_footer_type` (`header`/`footer`), `header_footer_content` | |
| `apply_cell_style` | Aplica estilos a celdas de tablas | `cell_coords` (ej: `A1`), `cell_style` (dict) | |

---

## Plantillas Maestras Premium (Master Templates)

Al usar `create_onlyoffice_document_tool`, puedes inicializar un documento profesional completo especificando el parámetro `template` y opcionalmente `theme`, `title` y `subtitle`.

| Formato | ID de Plantilla (`template`) | Nombre | Descripción y Componentes |
|---|---|---|---|
| **Word (.docx)** | `executive_report` | Informe Ejecutivo | Portada ejecutiva moderna, resumen ejecutivo, callout clave, tarjetas de KPI métricas, tabla financiera con totales y pie de página dinámico con numeración de páginas. |
| **Word (.docx)** | `commercial_proposal` | Propuesta Comercial | Portada ejecutiva, alcance del proyecto, tabla de entregables, cronograma, presupuesto detallado y términos comerciales. |
| **Word (.docx)** | `project_charter` | Acta de Constitución de Proyecto | Objetivos del proyecto, matriz de interesados/stakeholders, hitos clave, riesgos con callouts y presupuesto estimado. |
| **Excel (.xlsx)** | `financial_budget` | Presupuesto Financiero | Tarjetas de KPI (Presupuesto Total, Ejecutado, Desviación), desglose mensual por partida, fórmulas `=SUM()`, formatos de moneda y columnas autoajustadas. |
| **Excel (.xlsx)** | `sales_dashboard` | Tablero de Control de Ventas | Tarjetas superiores de KPI (Ventas, Meta, Cumplimiento, Ticket Promedio), tabla detallada por región/vendedor y formato condicional semafórico. |
| **Excel (.xlsx)** | `project_tracker` | Seguimiento de Tareas y Proyectos | Tarjetas de KPI de progreso (Total Tareas, Completadas, En Riesgo), tabla con Estado/Prioridad y formato condicional automático de estados. |
| **PowerPoint (.pptx)** | `pitch_deck` | Presentación de Inversión / Pitch Deck | 7 diapositivas 16:9 con diseño temático: Portada, Problema, Solución, Tarjetas de Métricas de Tracción, Modelo de Negocio (con tabla), Equipo y Llamado a la Acción. |
| **PowerPoint (.pptx)** | `quarterly_review` | Revisión Trimestral (QBR) | 6 diapositivas 16:9: Portada, Agenda, Métricas del Trimestre (KPIs), Logros Principales, Desafíos y Objetivos para el Siguiente Cuatrimestre. |

---

## Paleta de 6 Temas Unificados (`theme`)

Tanto al crear desde plantilla como al editar tablas, tarjetas o diapositivas, puedes especificar cualquiera de los 6 temas unificados:

- **`corporate_blue`** (Por defecto): Azul Rey (`#1E3A8A`), acento Celeste (`#0284C7`), fondo blanco/hielo. Ideal para finanzas, corporativo y auditorías.
- **`emerald_green`**: Verde Bosque (`#065F46`), acento Esmeralda (`#10B981`), fondo menta suave. Ideal para sustentabilidad, proyectos y salud.
- **`dark_slate`**: Grafito/Pizarra Oscura (`#0F172A`), acento Índigo (`#6366F1`), fondo gris perla. Estilo tecnológico, moderno y premium.
- **`sunset_amber`**: Ámbar/Terracota (`#9A3412`), acento Ámbar Cálido (`#F59E0B`), fondo arena claro. Ideal para marketing, creatividad y ventas.
- **`violet_gold`**: Púrpura Imperial (`#581C87`), acento Oro cálido (`#D97706`), fondo lavanda tenue. Ideal para lujo, consultoría estratégica y conferencias.
- **`minimalist_gray`**: Gris Carbón (`#374151`), acento Acero (`#6B7280`), bordes y fondos sutiles. Minimalismo ejecutivo nórdico.

---

## Cajas de Alerta y Callouts en Word (.docx)

Al usar las acciones `append` o `clear_and_write` con texto Markdown, el motor traduce automáticamente las citas de alerta estilo GitHub a bloques visuales nativos con banda lateral de color y fondo destacado:

```markdown
> [!NOTE]
> Este es un mensaje informativo o nota aclaratoria.

> [!TIP]
> Consejo o buena práctica recomendada para maximizar resultados.

> [!IMPORTANT]
> Información crítica o requisito fundamental que debe cumplirse.

> [!WARNING]
> Advertencia o aviso importante sobre posibles riesgos.

> [!CAUTION]
> Precaución o acción de alto riesgo que requiere atención inmediata.

> [!QUOTE]
> Cita textual relevante o testimonio destacado.
```

---

## Acciones de edición para .docx (Word)

| Acción | Descripción | Campos requeridos | Campos opcionales |
|---|---|---|---|
| `append` | Añade texto o Markdown completo al final (soporta callouts `> [!TIP]`, negrita, tablas, listas) | `text` | `style_theme`, `style_font_family`, `style_primary_color`, `style_secondary_color`, `style_text_color` |
| `append_heading` | Añade un título nativo (H1/H2/H3) | `text`, `heading_level` | `style_theme`, `style_font_family`, `style_primary_color`, `style_secondary_color` |
| `append_list` | Añade una lista de viñetas | `list_items` | `style_theme`, `style_font_family`, `style_text_color` |
| `replace` | Busca y reemplaza texto | `search_text`, `text` | `style_theme`, `style_font_family`, `style_text_color` |
| `replace_section` | Reemplaza el párrafo que empieza con `search_text` | `search_text`, `text` | `style_theme`, `style_font_family`, `style_text_color` |
| `docx_add_cover_page` | Añade una **portada ejecutiva** al inicio del documento con tema visual y salto de página | | `text` (título), `search_text` (subtítulo), `theme`, `format_options` (`style`: `'modern'`, `'minimal'`, `'header_block'`, `author`, `organization`) |
| `docx_add_kpi_cards` | Añade una **fila de tarjetas de métricas/KPI** destacadas | `table_data` o `format_options` (`cards`) | `theme` |
| `insert_styled_table` | Inserta una tabla con tema visual premium, padding y totales | `table_data` (matriz 2D) | `theme`, `has_total_row`, `auto_calculate_totals`, `col_alignments`, `col_widths`, `cell_padding` |
| `clear_and_write` | Borra todo el contenido y escribe nuevo texto/Markdown | `text` | `style_theme`, `style_font_family`, `style_primary_color` |
| `set_page_layout` | Configura márgenes y orientación | | `page_margins` (dict), `page_orientation` (`portrait`/`landscape`) |
| `add_header_footer` | Añade encabezado o pie de página (pie de página añade numeración dinámica `Página X de Y`) | `header_footer_type`, `header_footer_content` | |

---

## Acciones de edición para .xlsx (Excel)

| Acción | Descripción | Campos requeridos | Campos opcionales |
|---|---|---|---|
| `xlsx_add_kpi_cards` | Añade **tarjetas métricas/KPI** superiores en la hoja | `table_data` o `format_options` (`cards`) | `theme`, `row_index`, `column_index` |
| `xlsx_add_chart` | Inserta un **gráfico nativo Office** (`column`, `bar`, `line`, `pie`) vinculado a celdas | `range_address` (ej: `'B1:B10'`) | `search_text` o `format_options.chart_type`, `text` (título), `cell` (celda destino, ej: `'F2'`), `theme`, `width`, `height`, `format_options.categories_range` |
| `xlsx_apply_conditional_formatting` | Aplica **formato condicional** (`status_highlights`, `color_scale`, `cell_is`) | `range_address` (ej: `'C2:C20'`) | `search_text` (tipo de regla), `format_options` |
| `xlsx_create_table` | Crea una tabla estilizada con temas, formatos de columna y fórmulas de totales | `table_data` (matriz 2D) | `theme`, `has_total_row`, `total_formulas`, `column_formats`, `auto_fit_columns`, `start_cell`, `sheet_name` |
| `xlsx_create_sheet` | Crea una nueva pestaña en el libro | `sheet_name` | `tab_color` (hex), `sheet_index` |
| `xlsx_rename_sheet` | Renombra una pestaña existente | `sheet_name` (nuevo nombre) | `search_text` (nombre anterior), `tab_color` |
| `xlsx_delete_sheet` | Elimina una pestaña | `sheet_name` | |
| `xlsx_list_sheets` | Lista todas las pestañas disponibles | | |
| `xlsx_write_cell` | Escribe un valor o fórmula en una celda | `cell` (ej: `'B3'`), `text` | `sheet_name` |
| `xlsx_append_row` | Añade una fila al final (soporta números y fórmulas) | `row_data` (lista) | `sheet_name` |
| `xlsx_freeze_panes` | Congela filas/columnas (`cell='B2'` congela fila 1 y col A) | `cell`, `sheet_name` | |
| `xlsx_set_sheet_tab_color` | Cambia color de pestaña | `sheet_name`, `tab_color` (hex) | |

---

## Acciones de edición para .pptx (PowerPoint)

Las presentaciones de PowerPoint se gestionan en formato panorámico **16:9** nativo:

| Acción | Descripción | Campos requeridos | Campos opcionales |
|---|---|---|---|
| `pptx_add_slide` | Añade una nueva diapositiva con estructura tematizada | | `text` (título), `search_text` o `format_options.layout_type` (`title`, `agenda`, `content`, `two_columns`, `three_columns`, `kpi_metrics`, `conclusion`), `list_items` (puntos viñeta), `theme`, `format_options` (`speaker_notes`, `subtitle`, `cards`, `columns`) |
| `pptx_add_table` | Añade una tabla estilizada con el tema activo a la última diapositiva | `table_data` (matriz 2D) | `theme`, `text` (título de la diapositiva si no existe) |

---

## Notas de Uso y Buenas Prácticas

1. **Recargar el Editor**: Los archivos se guardan directamente en el backend de OnlyOffice. El usuario debe recargar el editor (`F5` o volver a abrirlo) para visualizar los cambios aplicados por el agente.
2. **Respaldo Automático**: Cada edición crea un respaldo previo en el directorio oculto `.backups/`.
3. **Smart Defaults**: Si no se especifica tema o formato, el sistema aplica automáticamente `corporate_blue`, fuentes legibles del sistema y proporciones profesionales.
4. **Fórmulas**: Cualquier valor que empiece con `=` en Excel o Word (ej: `=SUM(B2:B10)`) se inserta como fórmula nativa evaluable por OnlyOffice.

