# ONLYOFFICE_SKILL: Gestión y Edición Proactiva de Documentos

Esta habilidad permite al agente **leer, analizar y editar directamente** los documentos almacenados en el módulo OnlyOffice del usuario. Es la forma más directa de intervenir en un documento de trabajo sin que el usuario tenga que copiar y pegar.

## Cuándo usar esta habilidad:
- El usuario pide "leer", "resumir", "analizar" o **"editar"** un archivo específico por su nombre.
- El usuario quiere que el agente **escriba**, **corrija**, **formatee** o **estructure** un documento Word o Excel.
- El usuario quiere añadir una sección, un título, una lista o una tabla a un documento.
- El usuario dice "añade esto al final del documento", "reemplaza X por Y", "pon en negrita el título".

## Herramientas principales:
1. `search_onlyoffice_documents_tool`: Listar o buscar archivos por nombre en un workspace.
2. `read_onlyoffice_document_tool`: Leer el contenido completo de un archivo (.docx, .xlsx, .txt, .csv, .pptx).
3. `create_onlyoffice_document_tool`: **Crear un nuevo documento** desde cero (Word, Excel, PowerPoint, Texto).
4. `edit_onlyoffice_document_tool`: **Editar** el archivo directamente. Soporta:
   - `.docx` (Word): `append`, `append_heading`, `append_list`, `replace`, `replace_section`, `insert_table`, `apply_bold`, `clear_and_write`.
   - `.xlsx` (Excel): `xlsx_write_cell`, `xlsx_append_row`.

## Flujo de trabajo RECOMENDADO:
1. Si no tienes el ID del documento, usa `search_onlyoffice_documents_tool` para encontrarlo.
2. Lee el documento con `read_onlyoffice_document_tool` para entender su estructura actual.
3. Aplica los cambios con `edit_onlyoffice_document_tool` usando la acción más apropiada.
4. Informa al usuario de los cambios realizados y pídele que recargue el editor para verlos.

## 🚀 Motor de Renderizado de Markdown Avanzado (Exclusivo .docx)
Al editar documentos de Word (`.docx`) usando las acciones **`append`** o **`clear_and_write`**, puedes enviar **texto completo estructurado en Markdown**. El motor de renderizado avanzado lo traducirá automáticamente a elementos nativos de Office con un diseño y tipografía de altísima calidad (Premium):

- **Tipografía**: Fuente **Segoe UI** moderna con tamaños de lectura ideales y color slate-gray profesional.
- **Títulos**: `# H1` (Azul Rey, 18pt), `## H2` (Azul Medio, 14pt), `### H3` (Slate Dark, 12pt).
- **Listas**: Formateadas nativamente como viñetas o números.
- **Tablas Modernas**: Soportadas mediante formato de tablas Markdown (`| Col | Col |`). Se renderizan sin bordes verticales ruidosos, con bordes horizontales sutiles y elegantes, encabezados sombreados de azul y filas alternas con sombreado gris claro (Zebra Striping).
- **Bloques de Código**: Sombreado de fondo gris claro (`#F8FAFC`) con borde lateral sutil e tipografía `Courier New`.
- **Estilos Inline**: Negritas (`**texto**`), cursivas (`*texto*`) y código inline (`` `código` ``) se traducen nativamente a atributos de Runs de Word sin dejar caracteres crudos de Markdown.

## Acciones de edición disponibles para .docx:
| Acción | Descripción | Campos requeridos |
|---|---|---|
| `append` | Añade texto o Markdown completo al final | `text` |
| `append_heading` | Añade un título nativo (H1/H2/H3) | `text`, `heading_level` |
| `append_list` | Añade una lista de viñetas | `list_items` |
| `replace` | Busca y reemplaza texto (soporta inline Markdown en el reemplazo) | `search_text`, `text` |
| `replace_section` | Reemplaza el párrafo que empieza con `search_text` (soporta inline Markdown) | `search_text`, `text` |
| `insert_table` | Inserta una tabla al final | `table_data` (matriz 2D) |
| `apply_bold` | Pone en negrita las ocurrencias de un texto | `search_text` |
| `clear_and_write` | Borra todo el contenido y escribe nuevo texto o Markdown completo | `text` |

## Creación de documentos:
Para crear un archivo nuevo, usa `create_onlyoffice_document_tool` especificando el `doc_type`:
- `word`: crea un archivo .docx
- `excel`: crea un archivo .xlsx
- `powerpoint`: crea un archivo .pptx
- `text`: crea un archivo .txt

## Acciones para .xlsx (Excel):
| Acción | Descripción | Campos requeridos |
|---|---|---|
| `xlsx_write_cell` | Escribe en una celda específica | `cell` (ej: 'B3'), `text`, (`sheet_name`) |
| `xlsx_append_row` | Añade una fila al final de la hoja | `row_data` (lista de valores), (`sheet_name`) |

## Limitaciones:
- La edición de `.pptx` (PowerPoint) no está soportada aún.
- Los cambios se aplican directamente y **se crea un respaldo automático** antes de cada edición.
- El usuario debe **recargar el editor de OnlyOffice** (F5 o cerrar y abrir) para ver los cambios.

---
**IMPORTANTE**: Siempre lee el documento antes de editar para entender su estructura y evitar sobreescribir contenido valioso. Informa al usuario que debe recargar el editor para ver los cambios.

