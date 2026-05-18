# skills/onlyoffice_skill/scripts/edit_onlyoffice_document_tool.py

"""
Herramienta de Edición Avanzada para Documentos OnlyOffice.
Soporta Word (.docx) y Excel (.xlsx) con múltiples acciones de formato.
"""

import os
import re
import logging
import uuid
import shutil
from typing import Any, Type, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import select
from core.database import SessionLocal, Document
from datetime import datetime

# Librerías de procesamiento de documentos (Office)
try:
    import docx
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

logger = logging.getLogger(__name__)

# Intentar importar settings, con fallback si no está disponible
try:
    from core.config import settings
    DEFAULT_DOCS_ROOT = os.path.join(settings.media_root, "documents")
except ImportError:
    DEFAULT_DOCS_ROOT = os.path.join(os.getenv("MEDIA_ROOT", "/media/documents"), "documents")
DOCUMENTS_ROOT = os.environ.get("ONLYOFFICE_DOCS_ROOT", DEFAULT_DOCS_ROOT)

# Regex para tokenizar estilos inline en markdown: bold-italic, bold, italic, code
inline_regex = re.compile(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|__.*?__|__.*?__|\*.*?\*|_.*?_|`.*?`)')

def set_cell_background(cell, hex_color: str):
    """Establece el color de fondo (sombreado) de una celda en Word."""
    try:
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        tcPr.append(shd)
    except Exception as e:
        logger.warning(f"No se pudo establecer el fondo de celda: {e}")

def set_table_borders(table, hex_color: str = "CBD5E1"):
    """Aplica bordes sutiles horizontales de estilo minimalista a una tabla."""
    try:
        tblPr = table._tbl.tblPr
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{hex_color}"/>'
            f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{hex_color}"/>'
            f'  <w:left w:val="none"/>'
            f'  <w:right w:val="none"/>'
            f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{hex_color}"/>'
            f'  <w:insideV w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr.append(borders)
    except Exception as e:
        logger.warning(f"No se pudieron aplicar bordes de tabla: {e}")

def _add_inline_formatted_text(paragraph, text: str, default_font: str = "Segoe UI", default_size = Pt(10.5), default_color = RGBColor(51, 65, 85)):
    """Divide un texto por marcadores inline de Markdown y añade Runs formateados."""
    if not text:
        return
    
    tokens = inline_regex.split(text)
    for token in tokens:
        if not token:
            continue
        
        is_bold = False
        is_italic = False
        is_code = False
        clean_text = token
        
        if token.startswith("***") and token.endswith("***") and len(token) > 6:
            is_bold = True
            is_italic = True
            clean_text = token[3:-3]
        elif token.startswith("**") and token.endswith("**") and len(token) > 4:
            is_bold = True
            clean_text = token[2:-2]
        elif token.startswith("__") and token.endswith("__") and len(token) > 4:
            is_bold = True
            clean_text = token[2:-2]
        elif token.startswith("*") and token.endswith("*") and len(token) > 2:
            is_italic = True
            clean_text = token[1:-1]
        elif token.startswith("_") and token.endswith("_") and len(token) > 2:
            is_italic = True
            clean_text = token[1:-1]
        elif token.startswith("`") and token.endswith("`") and len(token) > 2:
            is_code = True
            clean_text = token[1:-1]
            
        run = paragraph.add_run(clean_text)
        if is_code:
            run.font.name = "Courier New"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(239, 68, 68) # soft red-500
            try:
                rPr = run._r.get_or_add_rPr()
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>') # slate-100
                rPr.append(shd)
            except Exception:
                pass
        else:
            run.font.name = default_font
            run.font.size = default_size
            run.font.color.rgb = default_color
            run.bold = is_bold
            run.italic = is_italic

def _parse_and_render_markdown(doc_obj, md_text: str):
    """Parsea texto Markdown estructurado y lo añade como elementos nativos y estilizados a docx."""
    if not md_text:
        return
        
    lines = md_text.split('\n')
    i = 0
    n = len(lines)
    
    while i < n:
        line = lines[i]
        stripped = line.strip()
        
        # 1. Líneas vacías
        if not stripped:
            i += 1
            continue
            
        # 2. Bloques de código
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < n:
                i += 1 # Consumir cierre
                
            code_text = "\n".join(code_lines)
            p = doc_obj.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.05
            p.paragraph_format.left_indent = Pt(12)
            
            run = p.add_run(code_text)
            run.font.name = "Courier New"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(15, 23, 42) # dark slate
            
            try:
                pPr = p._p.get_or_add_pPr()
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8FAFC"/>') # slate-50 background
                pPr.append(shd)
                pbdr = parse_xml(
                    f'<w:pBdr {nsdecls("w")}>'
                    f'  <w:left w:val="single" w:sz="18" w:space="8" w:color="CBD5E1"/>' # 2.25pt border left
                    f'</w:pBdr>'
                )
                pPr.append(pbdr)
            except Exception:
                pass
            continue
            
        # 3. Títulos (H1, H2, H3, H4)
        h_match = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if h_match:
            level = len(h_match.group(1))
            content = h_match.group(2).strip()
            
            p = doc_obj.add_paragraph()
            p.paragraph_format.keep_with_next = True
            
            if level == 1:
                p.paragraph_format.space_before = Pt(18)
                p.paragraph_format.space_after = Pt(6)
                _add_inline_formatted_text(p, content, default_font="Segoe UI", default_size=Pt(18), default_color=RGBColor(30, 58, 138))
                for r in p.runs:
                    r.bold = True
            elif level == 2:
                p.paragraph_format.space_before = Pt(14)
                p.paragraph_format.space_after = Pt(4)
                _add_inline_formatted_text(p, content, default_font="Segoe UI", default_size=Pt(14), default_color=RGBColor(37, 99, 235))
                for r in p.runs:
                    r.bold = True
            else:
                p.paragraph_format.space_before = Pt(10)
                p.paragraph_format.space_after = Pt(2)
                _add_inline_formatted_text(p, content, default_font="Segoe UI", default_size=Pt(12), default_color=RGBColor(30, 41, 59))
                for r in p.runs:
                    r.bold = True
            i += 1
            continue
            
        # 4. Regla horizontal
        if stripped in ("---", "***", "___") or re.match(r'^[-*_]{3,}$', stripped):
            p = doc_obj.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(12)
            try:
                pPr = p._p.get_or_add_pPr()
                pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="1" w:color="E2E8F0"/></w:pBdr>')
                pPr.append(pBdr)
            except Exception:
                pass
            i += 1
            continue
            
        # 5. Tablas
        if stripped.startswith("|"):
            table_lines = []
            while i < n and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
                
            rows = []
            for tl in table_lines:
                cols = [col.strip() for col in tl.split("|")[1:-1]]
                rows.append(cols)
                
            if len(rows) > 1 and all(re.match(r'^:?-+:?$', c) for c in rows[1]):
                rows.pop(1) # Remover fila de guiones divisores
                
            if rows:
                num_rows = len(rows)
                num_cols = max(len(r) for r in rows)
                
                table = doc_obj.add_table(rows=num_rows, cols=num_cols)
                table.autofit = True
                set_table_borders(table)
                
                for row_idx, r_data in enumerate(rows):
                    for col_idx, cell_val in enumerate(r_data):
                        if col_idx < num_cols:
                            cell = table.cell(row_idx, col_idx)
                            p = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
                            p.paragraph_format.space_before = Pt(4)
                            p.paragraph_format.space_after = Pt(4)
                            p.paragraph_format.line_spacing = 1.0
                            
                            if row_idx == 0:
                                _add_inline_formatted_text(p, cell_val, default_font="Segoe UI", default_size=Pt(10), default_color=RGBColor(255, 255, 255))
                                for run in p.runs:
                                    run.bold = True
                                set_cell_background(cell, "1E3A8A") # azul rey
                            else:
                                _add_inline_formatted_text(p, cell_val, default_font="Segoe UI", default_size=Pt(9.5), default_color=RGBColor(51, 65, 85))
                                if row_idx % 2 == 0:
                                    set_cell_background(cell, "F8FAFC") # zebra
                                else:
                                    set_cell_background(cell, "FFFFFF")
                
                # Párrafo vacío para espaciado post-tabla
                p_after = doc_obj.add_paragraph()
                p_after.paragraph_format.space_before = Pt(0)
                p_after.paragraph_format.space_after = Pt(6)
            continue
            
        # 6. Listas (viñetas o numeradas)
        bullet_match = re.match(r'^([\s]*)([-*+])\s+(.*)$', line)
        num_match = re.match(r'^([\s]*)(\d+)\.\s+(.*)$', line)
        if bullet_match or num_match:
            list_lines = []
            while i < n:
                curr_line = lines[i]
                if not curr_line.strip():
                    break
                b_m = re.match(r'^([\s]*)([-*+])\s+(.*)$', curr_line)
                n_m = re.match(r'^([\s]*)(\d+)\.\s+(.*)$', curr_line)
                if b_m or n_m:
                    list_lines.append((curr_line, b_m, n_m))
                    i += 1
                else:
                    # Continuación identada
                    if list_lines and curr_line.startswith("   "):
                        prev_text, prev_bm, prev_nm = list_lines[-1]
                        updated_text = prev_text + " " + curr_line.strip()
                        b_m_up = re.match(r'^([\s]*)([-*+])\s+(.*)$', updated_text)
                        n_m_up = re.match(r'^([\s]*)(\d+)\.\s+(.*)$', updated_text)
                        list_lines[-1] = (updated_text, b_m_up, n_m_up)
                        i += 1
                    else:
                        break
                        
            for item_line, bm, nm in list_lines:
                p = doc_obj.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.line_spacing = 1.15
                
                if bm:
                    indent_level = len(bm.group(1)) // 2
                    content = bm.group(3).strip()
                    p.style = 'List Bullet'
                    p.paragraph_format.left_indent = Pt(18 * (indent_level + 1))
                    _add_inline_formatted_text(p, content, default_font="Segoe UI", default_size=Pt(10.5), default_color=RGBColor(51, 65, 85))
                else:
                    indent_level = len(nm.group(1)) // 2
                    content = nm.group(3).strip()
                    p.style = 'List Number'
                    p.paragraph_format.left_indent = Pt(18 * (indent_level + 1))
                    _add_inline_formatted_text(p, content, default_font="Segoe UI", default_size=Pt(10.5), default_color=RGBColor(51, 65, 85))
            continue
            
        # 7. Párrafo estándar (agrupamiento de líneas contiguas)
        para_lines = []
        while i < n:
            curr_line = lines[i]
            curr_stripped = curr_line.strip()
            if not curr_stripped:
                break
            if (curr_stripped.startswith("```") or 
                re.match(r'^(#{1,6})\s+(.*)$', curr_stripped) or 
                curr_stripped.startswith("|") or 
                re.match(r'^([\s]*)([-*+])\s+(.*)$', curr_line) or 
                re.match(r'^([\s]*)(\d+)\.\s+(.*)$', curr_line) or
                curr_stripped in ("---", "***", "___") or 
                re.match(r'^[-*_]{3,}$', curr_stripped)):
                break
            para_lines.append(curr_stripped)
            i += 1
            
        if para_lines:
            para_text = " ".join(para_lines)
            p = doc_obj.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.15
            _add_inline_formatted_text(p, para_text, default_font="Segoe UI", default_size=Pt(10.5), default_color=RGBColor(51, 65, 85))


# --- Acciones disponibles ---
SUPPORTED_ACTIONS = [
    "append",            # Añadir párrafo de texto al final
    "append_heading",    # Añadir un título (H1, H2, H3)
    "append_list",       # Añadir una lista de viñetas
    "replace",           # Buscar y reemplazar texto en todo el documento
    "replace_section",   # Reemplazar la sección que empieza con cierto texto
    "insert_table",      # Insertar una tabla al final
    "apply_bold",        # Poner en negrita las ocurrencias de un texto
    "clear_and_write",   # Borrar todo el contenido y escribir nuevo
    # xlsx-only
    "xlsx_write_cell",   # Escribir en una celda específica de una hoja Excel
    "xlsx_append_row",   # Añadir una fila al final de una hoja Excel
]


class EditOnlyOfficeInput(BaseModel):
    document_id: str = Field(..., description="ID UUID del documento a editar.")
    action: str = Field(
        ...,
        description=(
            "Acción a realizar. Opciones disponibles: "
            "'append' (añadir texto/Markdown formateado al final), "
            "'append_heading' (añadir título - requiere heading_level 1/2/3), "
            "'append_list' (añadir lista de viñetas - requiere list_items), "
            "'replace' (buscar y reemplazar - requiere search_text), "
            "'replace_section' (reemplaza la sección que empieza con search_text), "
            "'insert_table' (insertar tabla - requiere table_data), "
            "'apply_bold' (poner en negrita - requiere search_text), "
            "'clear_and_write' (borrar todo el contenido y escribir nuevo texto/Markdown formateado), "
            "'xlsx_write_cell' (escribir en celda Excel - requiere cell, sheet_name), "
            "'xlsx_append_row' (añadir fila a Excel - requiere row_data)."
        ),
    )
    text: Optional[str] = Field(None, description="Texto principal a insertar (soporta Markdown enriquecido) o nuevo texto en 'replace'.")
    search_text: Optional[str] = Field(None, description="Texto a buscar (para 'replace', 'replace_section', 'apply_bold').")
    heading_level: Optional[int] = Field(None, description="Nivel del título: 1 (H1), 2 (H2), 3 (H3). Usar con 'append_heading'.")
    list_items: Optional[List[str]] = Field(None, description="Lista de cadenas para crear una lista de viñetas. Usar con 'append_list'.")
    table_data: Optional[List[List[str]]] = Field(None, description="Matriz de filas/columnas para crear una tabla. La primera fila es el encabezado. Usar con 'insert_table'.")
    # Para Excel
    sheet_name: Optional[str] = Field(None, description="Nombre de la hoja de Excel. Si no se indica, se usa la primera hoja.")
    cell: Optional[str] = Field(None, description="Coordenada de celda Excel (ej: 'A1', 'B3'). Usar con 'xlsx_write_cell'.")
    row_data: Optional[List[str]] = Field(None, description="Lista de valores para añadir como fila. Usar con 'xlsx_append_row'.")


class EditOnlyOfficeDocumentTool(BaseTool):
    name: str = "edit_onlyoffice_document"
    description: str = (
        "Edita documentos de OnlyOffice (Word .docx y Excel .xlsx) con operaciones avanzadas. "
        "Soporta añadir texto/Markdown completo con formatos complejos (negrita, cursiva, "
        "bloques de código, listas numeradas/viñetas, tablas estructuradas, títulos) que se traducen "
        "automáticamente a estilos nativos premium sin dejar caracteres crudos de Markdown. "
        "Permite buscar/reemplazar texto, poner texto en negrita, reescribir secciones o modificar celdas de Excel. "
        "Los cambios se guardan directamente en el servidor con respaldo automático. "
        "El usuario verá los cambios al recargar el editor. "
        "Usa esta herramienta cuando el usuario pida redactar, corregir o dar formato a su documento."
    )
    args_schema: Type[BaseModel] = EditOnlyOfficeInput

    account_id: str = Field(..., description="ID de cuenta del usuario, inyectado automáticamente.")

    async def _arun(
        self,
        document_id: str,
        action: str,
        text: Optional[str] = None,
        search_text: Optional[str] = None,
        heading_level: Optional[int] = None,
        list_items: Optional[List[str]] = None,
        table_data: Optional[List[List[str]]] = None,
        sheet_name: Optional[str] = None,
        cell: Optional[str] = None,
        row_data: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        try:
            acc_id = uuid.UUID(self.account_id)
            doc_id = uuid.UUID(document_id)

            async with SessionLocal() as db:
                stmt = select(Document).where(
                    Document.id == doc_id,
                    Document.account_id == acc_id,
                )
                result = await db.execute(stmt)
                doc = result.scalar_one_or_none()

                if not doc:
                    return f"❌ Documento con ID '{document_id}' no encontrado o no tienes permiso para editarlo."

                ext = doc.extension.lower().lstrip(".")

                # Construir ruta física
                file_path = doc.file_path
                if not os.path.isabs(file_path):
                    file_path = os.path.join(DOCUMENTS_ROOT, file_path)

                if not os.path.exists(file_path):
                    return f"❌ El archivo físico '{doc.filename}' no se encuentra en el servidor ({file_path})."

                # Dispatch por tipo de archivo
                if ext == "docx":
                    msg = await self._edit_docx(
                        file_path, action, text, search_text,
                        heading_level, list_items, table_data, doc.filename
                    )
                elif ext in ("xlsx", "xls"):
                    msg = await self._edit_xlsx(
                        file_path, action, text, cell,
                        sheet_name, row_data, doc.filename
                    )
                else:
                    return (
                        f"❌ El tipo de archivo '.{ext}' no está soportado para edición. "
                        "Se soportan: .docx (Word) y .xlsx (Excel)."
                    )

                if msg.startswith("❌"):
                    return msg

                # Actualizar timestamp en DB para invalidar caché de OnlyOffice
                doc.updated_at = datetime.now()
                await db.commit()
                return msg

        except Exception as e:
            logger.error(f"Error en EditOnlyOfficeDocumentTool: {e}", exc_info=True)
            return f"❌ Error inesperado al editar el documento: {str(e)}"

    # ------------------------------------------------------------------ #
    #  DOCX Editing
    # ------------------------------------------------------------------ #
    async def _edit_docx(
        self,
        file_path: str,
        action: str,
        text: Optional[str],
        search_text: Optional[str],
        heading_level: Optional[int],
        list_items: Optional[List[str]],
        table_data: Optional[List[List[str]]],
        filename: str,
    ) -> str:
        if not DOCX_AVAILABLE:
            return "❌ La librería 'python-docx' no está instalada. No se puede editar documentos Word."

        try:
            doc_obj = docx.Document(file_path)

            if action == "append":
                if not text:
                    return "❌ La acción 'append' requiere el campo 'text'."
                _parse_and_render_markdown(doc_obj, text)
                msg = f"✅ Contenido (Markdown parsed) añadido al final de '{filename}'."

            elif action == "append_heading":
                if not text:
                    return "❌ La acción 'append_heading' requiere el campo 'text'."
                level = heading_level if heading_level in (1, 2, 3) else 2
                doc_obj.add_heading(text, level=level)
                msg = f"✅ Título H{level} '{text}' añadido a '{filename}'."

            elif action == "append_list":
                if not list_items:
                    return "❌ La acción 'append_list' requiere el campo 'list_items'."
                for item in list_items:
                    doc_obj.add_paragraph(item, style="List Bullet")
                msg = f"✅ Lista de {len(list_items)} ítems añadida a '{filename}'."

            elif action == "replace":
                if not search_text:
                    return "❌ La acción 'replace' requiere 'search_text'."
                if text is None:
                    return "❌ La acción 'replace' requiere 'text' con el nuevo contenido."
                count = self._replace_in_docx(doc_obj, search_text, text)
                if count == 0:
                    return f"⚠️ No se encontró '{search_text}' en el documento."
                msg = f"✅ Reemplazadas {count} ocurrencia(s) de '{search_text}' en '{filename}'."

            elif action == "replace_section":
                if not search_text:
                    return "❌ La acción 'replace_section' requiere 'search_text' (inicio de la sección)."
                if text is None:
                    return "❌ La acción 'replace_section' requiere 'text' con el nuevo contenido."
                replaced = self._replace_section_in_docx(doc_obj, search_text, text)
                if not replaced:
                    return f"⚠️ No se encontró ningún párrafo que empiece con '{search_text}'."
                msg = f"✅ Sección que comenzaba con '{search_text}' reemplazada en '{filename}'."

            elif action == "insert_table":
                if not table_data or len(table_data) < 1:
                    return "❌ La acción 'insert_table' requiere 'table_data' con al menos una fila."
                cols = max(len(row) for row in table_data)
                table = doc_obj.add_table(rows=len(table_data), cols=cols)
                table.style = "Table Grid"
                for i, row in enumerate(table_data):
                    for j, cell_val in enumerate(row):
                        cell = table.cell(i, j)
                        cell.text = str(cell_val)
                        if i == 0:
                            # Negrita para el encabezado
                            for run in cell.paragraphs[0].runs:
                                run.bold = True
                msg = f"✅ Tabla de {len(table_data)} fila(s) × {cols} columna(s) insertada en '{filename}'."

            elif action == "apply_bold":
                if not search_text:
                    return "❌ La acción 'apply_bold' requiere 'search_text'."
                count = self._apply_bold_in_docx(doc_obj, search_text)
                if count == 0:
                    return f"⚠️ No se encontró '{search_text}' para poner en negrita."
                msg = f"✅ '{search_text}' puesto en negrita ({count} ocurrencia(s)) en '{filename}'."

            elif action == "clear_and_write":
                if not text:
                    return "❌ La acción 'clear_and_write' requiere 'text'."
                # Eliminar todos los elementos existentes en el cuerpo para una limpieza completa
                for element in list(doc_obj.element.body):
                    if element.tag.endswith('sectPr'):
                        continue
                    doc_obj.element.body.remove(element)
                # Escribir el nuevo contenido parsed a partir de Markdown
                _parse_and_render_markdown(doc_obj, text)
                msg = f"✅ Documento '{filename}' reescrito con nuevo contenido estructurado."

            else:
                return (
                    f"❌ Acción '{action}' no reconocida para .docx. "
                    f"Acciones disponibles: {', '.join(SUPPORTED_ACTIONS)}"
                )

            # Backup y guardado
            self._backup_file(file_path)
            doc_obj.save(file_path)
            return msg

        except Exception as e:
            logger.error(f"Error procesando DOCX: {e}")
            return f"❌ Error al procesar el archivo Word: {str(e)}"

    def _replace_in_docx(self, doc_obj, search: str, replacement: str) -> int:
        """Reemplaza texto en párrafos y tablas, formateando con Markdown en el fallback."""
        count = 0
        all_paragraphs = list(doc_obj.paragraphs)
        for table in doc_obj.tables:
            for row in table.rows:
                for cell in row.cells:
                    all_paragraphs.extend(cell.paragraphs)

        for paragraph in all_paragraphs:
            if search in paragraph.text:
                for run in paragraph.runs:
                    if search in run.text:
                        # Si el reemplazo tiene marcadores markdown, usamos el fallback de formateado
                        if any(marker in replacement for marker in ('**', '*', '__', '_', '`')):
                            break
                        run.text = run.text.replace(search, replacement)
                        count += 1
                        
                # Fallback: si el texto está dividido entre runs o contiene Markdown para formatear
                if search in paragraph.text:
                    full_text = paragraph.text.replace(search, replacement)
                    p_element = paragraph._p
                    runs_to_remove = list(paragraph.runs)
                    for r in runs_to_remove:
                        p_element.remove(r._r)
                    _add_inline_formatted_text(paragraph, full_text)
                    count += 1
        return count

    def _replace_section_in_docx(self, doc_obj, section_start: str, new_content: str) -> bool:
        """Reemplaza el primer párrafo cuyo texto empiece con section_start aplicando inline Markdown."""
        for paragraph in doc_obj.paragraphs:
            if paragraph.text.strip().startswith(section_start):
                p_element = paragraph._p
                runs_to_remove = list(paragraph.runs)
                for r in runs_to_remove:
                    p_element.remove(r._r)
                _add_inline_formatted_text(paragraph, new_content)
                return True
        return False

    def _apply_bold_in_docx(self, doc_obj, search: str) -> int:
        """Divide los runs para poner en negrita solo las ocurrencias del texto."""
        count = 0
        for paragraph in doc_obj.paragraphs:
            if search not in paragraph.text:
                continue
            # Reconstruir el párrafo split por el término buscado
            full_text = paragraph.text
            parts = full_text.split(search)
            if len(parts) < 2:
                continue
            # Guardar el estilo del primer run
            existing_style = {}
            if paragraph.runs:
                r = paragraph.runs[0]
                existing_style = {"font_size": r.font.size, "color": r.font.color.rgb if r.font.color.type else None}
            # Limpiar párrafo
            for run in paragraph.runs:
                run.text = ""
            # Reconstruir con el texto en negrita
            for i, part in enumerate(parts):
                if part:
                    run = paragraph.add_run(part)
                    run.bold = False
                if i < len(parts) - 1:
                    bold_run = paragraph.add_run(search)
                    bold_run.bold = True
                    count += 1
        return count

    # ------------------------------------------------------------------ #
    #  XLSX Editing
    # ------------------------------------------------------------------ #
    async def _edit_xlsx(
        self,
        file_path: str,
        action: str,
        text: Optional[str],
        cell: Optional[str],
        sheet_name: Optional[str],
        row_data: Optional[List[str]],
        filename: str,
    ) -> str:
        if not XLSX_AVAILABLE:
            return "❌ La librería 'openpyxl' no está instalada. No se pueden editar archivos Excel."

        try:
            wb = openpyxl.load_workbook(file_path)

            # Seleccionar hoja
            if sheet_name and sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
            else:
                ws = wb.active
                sheet_name = ws.title

            if action == "xlsx_write_cell":
                if not cell:
                    return "❌ La acción 'xlsx_write_cell' requiere el campo 'cell' (ej: 'A1')."
                if text is None:
                    return "❌ La acción 'xlsx_write_cell' requiere 'text' con el valor a escribir."
                ws[cell.upper()] = text
                msg = f"✅ Celda '{cell.upper()}' de la hoja '{sheet_name}' en '{filename}' actualizada con: {text}"

            elif action == "xlsx_append_row":
                if not row_data:
                    return "❌ La acción 'xlsx_append_row' requiere 'row_data' (lista de valores)."
                ws.append(row_data)
                msg = f"✅ Fila añadida a la hoja '{sheet_name}' de '{filename}': {row_data}"

            else:
                return (
                    f"❌ Acción '{action}' no válida para .xlsx. "
                    "Usa 'xlsx_write_cell' o 'xlsx_append_row'."
                )

            self._backup_file(file_path)
            wb.save(file_path)
            return msg

        except Exception as e:
            logger.error(f"Error procesando XLSX: {e}")
            return f"❌ Error al procesar el archivo Excel: {str(e)}"

    # ------------------------------------------------------------------ #
    #  Utilidades
    # ------------------------------------------------------------------ #
    def _backup_file(self, file_path: str) -> str:
        """Crea un respaldo del archivo antes de modificarlo."""
        backups_dir = os.path.join(os.path.dirname(file_path), ".backups")
        os.makedirs(backups_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(
            backups_dir,
            f"{os.path.basename(file_path)}.{timestamp}.ai_edit.bak"
        )
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
