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
import json
from typing import Any, Type, Optional, List
from pydantic import BaseModel, Field, field_validator
from langchain_core.tools import BaseTool
from sqlalchemy import select
from core.database import SessionLocal, Document
from core.onlyoffice_storage import resolve_onlyoffice_file_path
from datetime import datetime

# Librerías de procesamiento de documentos (Office)
DOCX_IMPORT_ERROR = None
try:
    import docx
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.section import WD_ORIENT
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    DOCX_AVAILABLE = True
except Exception as e:
    DOCX_AVAILABLE = False
    DOCX_IMPORT_ERROR = str(e)


try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter
    import openpyxl.styles.numbers as numbers
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
    # DOCX new actions
    "edit_paragraph",    # Editar párrafo por índice o búsqueda
    "insert_image",      # Insertar imagen en el documento
    "set_page_layout",   # Configurar márgenes y orientación de página
    "add_header_footer", # Añadir encabezados y pies de página
    "apply_cell_style",  # Aplicar estilo a celdas de tabla
    # XLSX new actions
    "xlsx_write_cell",   # Escribir en una celda específica de una hoja Excel
    "xlsx_append_row",   # Añadir una fila al final de una hoja Excel
    "xlsx_write_range",  # Escribir en un rango de celdas
    "xlsx_format_cells", # Formatear celdas con estilos
    "xlsx_insert_row",   # Insertar fila en posición específica
    "xlsx_insert_column",# Insertar columna en posición específica
    "xlsx_delete_row",   # Eliminar fila
    "xlsx_delete_column",# Eliminar columna
    "xlsx_merge_cells",  # Fusionar celdas
    "xlsx_set_column_width",  # Establecer ancho de columna
    "xlsx_set_row_height",    # Establecer altura de fila
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
            "'edit_paragraph' (editar párrafo por índice o búsqueda - requiere paragraph_index o search_text), "
            "'insert_image' (insertar imagen - requiere image_path y opcionalmente image_width/image_height), "
            "'set_page_layout' (configurar márgenes/orientación - requiere page_margins y/o page_orientation), "
            "'add_header_footer' (añadir encabezado/pie - requiere header_footer_type y content), "
            "'apply_cell_style' (aplicar estilo a celda - requiere cell_style y cell_coords), "
            "'xlsx_write_cell' (escribir en celda Excel - requiere cell, sheet_name), "
            "'xlsx_append_row' (añadir fila a Excel - requiere row_data), "
            "'xlsx_write_range' (escribir en rango - requiere range_address y range_data), "
            "'xlsx_format_cells' (formatear celdas - requiere range_address y format_options), "
            "'xlsx_insert_row' (insertar fila - requiere row_index), "
            "'xlsx_insert_column' (insertar columna - requiere column_index), "
            "'xlsx_delete_row' (eliminar fila - requiere row_index), "
            "'xlsx_delete_column' (eliminar columna - requiere column_index), "
            "'xlsx_merge_cells' (fusionar celdas - requiere range_address), "
            "'xlsx_set_column_width' (ancho columna - requiere column_index y width), "
            "'xlsx_set_row_height' (altura fila - requiere row_index y height)."
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
    # Nuevos campos DOCX
    paragraph_index: Optional[int] = Field(None, description="Índice del párrafo a editar (0-based). Usar con 'edit_paragraph'.")
    image_path: Optional[str] = Field(None, description="Ruta del archivo de imagen a insertar. Usar con 'insert_image'.")
    image_width: Optional[float] = Field(None, description="Ancho de la imagen en cm. Por defecto 10cm. Usar con 'insert_image'.")
    image_height: Optional[float] = Field(None, description="Alto de la imagen en cm. Por defecto autoajustado. Usar con 'insert_image'.")
    page_margins: Optional[dict] = Field(None, description="Diccionario con márgenes en cm: {'top': 2.5, 'bottom': 2.5, 'left': 2.5, 'right': 2.5}. Usar con 'set_page_layout'.")
    page_orientation: Optional[str] = Field(None, description="Orientación de página: 'portrait' o 'landscape'. Usar con 'set_page_layout'.")
    header_footer_type: Optional[str] = Field(None, description="Tipo: 'header' o 'footer'. Usar con 'add_header_footer'.")
    header_footer_content: Optional[str] = Field(None, description="Contenido del encabezado/pie de página. Usar con 'add_header_footer'.")
    cell_style: Optional[dict] = Field(None, description="Estilo a aplicar: {'bold': True, 'italic': False, 'font_size': 12, 'font_color': 'FF0000'}. Usar con 'apply_cell_style'.")
    cell_coords: Optional[str] = Field(None, description="Coordenadas de celda: 'A1'. Usar con 'apply_cell_style'.")
    # Nuevos campos XLSX
    range_address: Optional[str] = Field(None, description="Rango de celdas (ej: 'A1:C3'). Usar con 'xlsx_write_range', 'xlsx_format_cells', 'xlsx_merge_cells'.")
    range_data: Optional[List[List[str]]] = Field(None, description="Datos para escribir en el rango. Usar con 'xlsx_write_range'.")
    format_options: Optional[dict] = Field(None, description="Opciones de formato: {'bold': True, 'font_size': 12, 'fill_color': 'FFFF00', 'align': 'center'}. Usar con 'xlsx_format_cells'.")
    row_index: Optional[int] = Field(None, description="Índice de fila (0-based). Usar con 'xlsx_insert_row', 'xlsx_delete_row'.")
    column_index: Optional[int] = Field(None, description="Índice de columna (0-based). Usar con 'xlsx_insert_column', 'xlsx_delete_column'.")
    width: Optional[float] = Field(None, description="Ancho en cm. Usar con 'xlsx_set_column_width'.")
    height: Optional[float] = Field(None, description="Alto en filas. Usar con 'xlsx_set_row_height'.")

    @field_validator(
        "list_items",
        "table_data",
        "row_data",
        "page_margins",
        "cell_style",
        "range_data",
        "format_options",
        mode="before"
    )
    @classmethod
    def parse_json_fields(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            if (v_stripped.startswith('[') and v_stripped.endswith(']')) or \
               (v_stripped.startswith('{') and v_stripped.endswith('}')):
                try:
                    return json.loads(v)
                except Exception:
                    pass
        return v


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
        # Nuevos parámetros DOCX
        paragraph_index: Optional[int] = None,
        image_path: Optional[str] = None,
        image_width: Optional[float] = None,
        image_height: Optional[float] = None,
        page_margins: Optional[dict] = None,
        page_orientation: Optional[str] = None,
        header_footer_type: Optional[str] = None,
        header_footer_content: Optional[str] = None,
        cell_style: Optional[dict] = None,
        cell_coords: Optional[str] = None,
        # Nuevos parámetros XLSX
        range_address: Optional[str] = None,
        range_data: Optional[List[List[str]]] = None,
        format_options: Optional[dict] = None,
        row_index: Optional[int] = None,
        column_index: Optional[int] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
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
                try:
                    file_path = str(resolve_onlyoffice_file_path(doc.file_path))
                except Exception as exc:
                    return f"❌ Ruta física inválida para documento: {exc}"

                if not os.path.exists(file_path):
                    return f"❌ El archivo físico '{doc.filename}' no se encuentra en el servidor ({file_path})."

                # Dispatch por tipo de archivo
                if ext == "docx":
                    msg = await self._edit_docx(
                        file_path, action, text, search_text,
                        heading_level, list_items, table_data,
                        paragraph_index, image_path, image_width, image_height,
                        page_margins, page_orientation, header_footer_type, header_footer_content,
                        cell_style, cell_coords, doc.filename
                    )
                elif ext in ("xlsx", "xls"):
                    msg = await self._edit_xlsx(
                        file_path, action, text, cell,
                        sheet_name, row_data, range_address, range_data,
                        format_options, row_index, column_index, width, height,
                        doc.filename
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
        paragraph_index: Optional[int],
        image_path: Optional[str],
        image_width: Optional[float],
        image_height: Optional[float],
        page_margins: Optional[dict],
        page_orientation: Optional[str],
        header_footer_type: Optional[str],
        header_footer_content: Optional[str],
        cell_style: Optional[dict],
        cell_coords: Optional[str],
        filename: str,
    ) -> str:
        if not DOCX_AVAILABLE:
            return f"❌ La librería 'python-docx' no está instalada. No se puede editar documentos Word. Error de importación: {DOCX_IMPORT_ERROR}"

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

            elif action == "edit_paragraph":
                if paragraph_index is None and not search_text:
                    return "❌ La acción 'edit_paragraph' requiere 'paragraph_index' o 'search_text'."
                msg = self._handle_edit_paragraph(doc_obj, paragraph_index, search_text, text)

            elif action == "insert_image":
                if not image_path:
                    return "❌ La acción 'insert_image' requiere 'image_path'."
                msg = self._handle_insert_image(doc_obj, image_path, image_width, image_height)

            elif action == "set_page_layout":
                msg = self._handle_set_page_layout(doc_obj, page_margins, page_orientation)

            elif action == "add_header_footer":
                if not header_footer_type:
                    return "❌ La acción 'add_header_footer' requiere 'header_footer_type' ('header' o 'footer')."
                if not header_footer_content:
                    return "❌ La acción 'add_header_footer' requiere 'header_footer_content'."
                msg = self._handle_header_footer(doc_obj, header_footer_type, header_footer_content)

            elif action == "apply_cell_style":
                if not cell_coords:
                    return "❌ La acción 'apply_cell_style' requiere 'cell_coords' (ej: 'A1')."
                if not cell_style:
                    return "❌ La acción 'apply_cell_style' requiere 'cell_style' (diccionario con estilos)."
                msg = self._handle_cell_style(doc_obj, cell_coords, cell_style)

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

    def _handle_edit_paragraph(self, doc_obj, paragraph_index: Optional[int], search_text: Optional[str], new_text: Optional[str]) -> str:
        """Edita un párrafo por índice o búsqueda."""
        if new_text is None:
            return "❌ La acción 'edit_paragraph' requiere 'text' con el nuevo contenido."
        
        if paragraph_index is not None:
            if paragraph_index < 0:
                return "❌ El índice del párrafo debe ser >= 0."
            paragraphs = list(doc_obj.paragraphs)
            # También incluir párrafos de tablas
            for table in doc_obj.tables:
                for row in table.rows:
                    for cell in row.cells:
                        paragraphs.extend(cell.paragraphs)
            
            if paragraph_index >= len(paragraphs):
                return f"❌ Índice de párrafo {paragraph_index} fuera de rango (máximo: {len(paragraphs)-1})."
            
            paragraph = paragraphs[paragraph_index]
            p_element = paragraph._p
            runs_to_remove = list(paragraph.runs)
            for r in runs_to_remove:
                p_element.remove(r._r)
            _add_inline_formatted_text(paragraph, new_text)
            return f"✅ Párrafo en posición {paragraph_index} actualizado."
        
        elif search_text:
            paragraphs = list(doc_obj.paragraphs)
            for table in doc_obj.tables:
                for row in table.rows:
                    for cell in row.cells:
                        paragraphs.extend(cell.paragraphs)
            
            for idx, paragraph in enumerate(paragraphs):
                if search_text in paragraph.text:
                    p_element = paragraph._p
                    runs_to_remove = list(paragraph.runs)
                    for r in runs_to_remove:
                        p_element.remove(r._r)
                    _add_inline_formatted_text(paragraph, new_text)
                    return f"✅ Párrafo encontrado con '{search_text}' actualizado."
            return f"⚠️ No se encontró ningún párrafo con '{search_text}'."
        else:
            return "❌ La acción 'edit_paragraph' requiere 'paragraph_index' o 'search_text'."

    def _handle_insert_image(self, doc_obj, image_path: str, image_width: Optional[float], image_height: Optional[float]) -> str:
        """Inserta una imagen en el documento."""
        if not os.path.exists(image_path):
            return f"❌ La imagen '{image_path}' no existe."
        
        try:
            width_cm = image_width if image_width else 10.0
            height_cm = image_height
            
            if height_cm:
                # Tamaño fijo especificado
                run = doc_obj.add_paragraph().add_run()
                run.add_picture(image_path, width=Cm(width_cm), height=Cm(height_cm))
            else:
                # Ancho fijo, alto automático
                run = doc_obj.add_paragraph().add_run()
                run.add_picture(image_path, width=Cm(width_cm))
            
            return f"✅ Imagen '{os.path.basename(image_path)}' insertada (ancho: {width_cm}cm)."
        except Exception as e:
            logger.error(f"Error insertando imagen: {e}")
            return f"❌ Error al insertar imagen: {str(e)}"

    def _handle_set_page_layout(self, doc_obj, page_margins: Optional[dict], page_orientation: Optional[str]) -> str:
        """Configura márgenes y orientación de página."""
        try:
            sections = doc_obj.sections
            if not sections:
                return "❌ No hay secciones en el documento."
            
            section = sections[0]  # Modificar la primera sección
            
            if page_margins:
                top = Cm(page_margins.get('top', 2.5))
                bottom = Cm(page_margins.get('bottom', 2.5))
                left = Cm(page_margins.get('left', 2.5))
                right = Cm(page_margins.get('right', 2.5))
                section.top_margin = top
                section.bottom_margin = bottom
                section.left_margin = left
                section.right_margin = right
            
            if page_orientation:
                if page_orientation.lower() == 'landscape':
                    section.orientation = WD_ORIENT.LANDSCAPE
                else:
                    section.orientation = WD_ORIENT.PORTRAIT
            
            return "✅ Configuración de página actualizada."
        except Exception as e:
            logger.error(f"Error configurando layout: {e}")
            return f"❌ Error al configurar la página: {str(e)}"

    def _handle_header_footer(self, doc_obj, header_footer_type: str, content: str) -> str:
        """Añade encabezado o pie de página."""
        try:
            if header_footer_type not in ('header', 'footer'):
                return "❌ Tipo debe ser 'header' o 'footer'."
            
            section = doc_obj.sections[0]
            
            if header_footer_type == 'header':
                header = section.header
                header_para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
                header_para.text = content
            else:
                footer = section.footer
                footer_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
                footer_para.text = content
            
            return f"✅ {header_footer_type.capitalize()} añadido con contenido: '{content}'."
        except Exception as e:
            logger.error(f"Error añadiendo header/footer: {e}")
            return f"❌ Error al añadir {header_footer_type}: {str(e)}"

    def _handle_cell_style(self, doc_obj, cell_coords: str, cell_style: dict) -> str:
        """Aplica estilo a una celda de tabla."""
        try:
            # Buscar la primera tabla del documento
            if not doc_obj.tables:
                return "❌ No hay tablas en el documento."
            
            table = doc_obj.tables[0]
            
            # Parsear coordenadas (ej: "A1", "B2")
            col_letter = ''.join([c for c in cell_coords if c.isalpha()]).upper()
            row_num = int(''.join([c for c in cell_coords if c.isdigit()]))
            
            # Convertir letra a índice (A=0, B=1, etc.)
            col_idx = 0
            for c in col_letter:
                col_idx = col_idx * 26 + (ord(c.upper()) - ord('A') + 1)
            col_idx -= 1
            
            row_idx = row_num - 1  # 1-based a 0-based
            
            if row_idx >= len(table.rows) or col_idx >= len(table.columns):
                return f"❌ Coordenadas {cell_coords} fuera de rango."
            
            cell = table.cell(row_idx, col_idx)
            
            # Aplicar estilos
            if cell_style.get('bold'):
                for run in cell.paragraphs[0].runs:
                    run.bold = True
            
            if cell_style.get('italic'):
                for run in cell.paragraphs[0].runs:
                    run.italic = True
            
            if cell_style.get('font_size'):
                for run in cell.paragraphs[0].runs:
                    run.font.size = Pt(cell_style['font_size'])
            
            if cell_style.get('font_color'):
                color_hex = cell_style['font_color']
                if color_hex.startswith('#'):
                    color_hex = color_hex[1:]
                for run in cell.paragraphs[0].runs:
                    run.font.color.rgb = RGBColor(int(color_hex[:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16))
            
            return f"✅ Estilo aplicado a celda {cell_coords}."
        except Exception as e:
            logger.error(f"Error aplicando estilo a celda: {e}")
            return f"❌ Error al aplicar estilo: {str(e)}"

    # ------------------------------------------------------------------ #
    #  XLSX Editing
    # ------------------------------------------------------------------ #
    # ------------------------------------------------------------------ #
    async def _edit_xlsx(
        self,
        file_path: str,
        action: str,
        text: Optional[str],
        cell: Optional[str],
        sheet_name: Optional[str],
        row_data: Optional[List[str]],
        range_address: Optional[str],
        range_data: Optional[List[List[str]]],
        format_options: Optional[dict],
        row_index: Optional[int],
        column_index: Optional[int],
        width: Optional[float],
        height: Optional[float],
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

            elif action == "xlsx_write_range":
                if not range_address:
                    return "❌ La acción 'xlsx_write_range' requiere 'range_address' (ej: 'A1:C3')."
                if not range_data:
                    return "❌ La acción 'xlsx_write_range' requiere 'range_data' (matriz 2D)."
                msg = self._xlsx_write_range(ws, range_address, range_data, filename, sheet_name)

            elif action == "xlsx_format_cells":
                if not range_address:
                    return "❌ La acción 'xlsx_format_cells' requiere 'range_address' (ej: 'A1:C3')."
                if not format_options:
                    return "❌ La acción 'xlsx_format_cells' requiere 'format_options'."
                msg = self._xlsx_format_cells(ws, range_address, format_options, filename, sheet_name)

            elif action == "xlsx_insert_row":
                if row_index is None:
                    return "❌ La acción 'xlsx_insert_row' requiere 'row_index'."
                msg = self._xlsx_insert_row(ws, row_index, filename, sheet_name)

            elif action == "xlsx_insert_column":
                if column_index is None:
                    return "❌ La acción 'xlsx_insert_column' requiere 'column_index'."
                msg = self._xlsx_insert_column(ws, column_index, filename, sheet_name)

            elif action == "xlsx_delete_row":
                if row_index is None:
                    return "❌ La acción 'xlsx_delete_row' requiere 'row_index'."
                msg = self._xlsx_delete_row(ws, row_index, filename, sheet_name)

            elif action == "xlsx_delete_column":
                if column_index is None:
                    return "❌ La acción 'xlsx_delete_column' requiere 'column_index'."
                msg = self._xlsx_delete_column(ws, column_index, filename, sheet_name)

            elif action == "xlsx_merge_cells":
                if not range_address:
                    return "❌ La acción 'xlsx_merge_cells' requiere 'range_address' (ej: 'A1:C3')."
                msg = self._xlsx_merge_cells(ws, range_address, filename, sheet_name)

            elif action == "xlsx_set_column_width":
                if column_index is None or width is None:
                    return "❌ La acción 'xlsx_set_column_width' requiere 'column_index' y 'width'."
                msg = self._xlsx_set_column_width(ws, column_index, width, filename, sheet_name)

            elif action == "xlsx_set_row_height":
                if row_index is None or height is None:
                    return "❌ La acción 'xlsx_set_row_height' requiere 'row_index' y 'height'."
                msg = self._xlsx_set_row_height(ws, row_index, height, filename, sheet_name)

            else:
                return (
                    f"❌ Acción '{action}' no válida para .xlsx. "
                    f"Acciones disponibles: {', '.join(SUPPORTED_ACTIONS)}"
                )

            self._backup_file(file_path)
            wb.save(file_path)
            return msg

        except Exception as e:
            logger.error(f"Error procesando XLSX: {e}")
            return f"❌ Error al procesar el archivo Excel: {str(e)}"

    # ------------------------------------------------------------------ #
    #  XLSX Helper Methods
    # ------------------------------------------------------------------ #
    def _xlsx_write_range(self, ws, range_address: str, range_data: List[List[str]], filename: str, sheet_name: str) -> str:
        """Escribe datos en un rango de celdas."""
        try:
            from openpyxl.utils import coordinate_to_tuple
            start_row, start_col = coordinate_to_tuple(range_address.split(':')[0])
            
            for i, row in enumerate(range_data):
                for j, value in enumerate(row):
                    ws.cell(row=start_row + i, column=start_col + j, value=value)
            
            return f"✅ Rango '{range_address}' en hoja '{sheet_name}' actualizado."
        except Exception as e:
            logger.error(f"Error escribiendo rango: {e}")
            return f"❌ Error al escribir en rango: {str(e)}"

    def _xlsx_format_cells(self, ws, range_address: str, format_options: dict, filename: str, sheet_name: str) -> str:
        """Formatea celdas con estilos."""
        try:
            if ':' in range_address:
                range_ref = [cell for row in ws[range_address] for cell in row]
            else:
                range_ref = [ws[range_address]]
            
            for cell in range_ref:
                font_kwargs = {}
                if format_options.get('bold'):
                    font_kwargs['bold'] = True
                if format_options.get('italic'):
                    font_kwargs['italic'] = True
                if format_options.get('font_size'):
                    font_kwargs['size'] = format_options['font_size']
                if font_kwargs:
                    cell.font = Font(**font_kwargs)
                if format_options.get('fill_color'):
                    fill = PatternFill(start_color=format_options['fill_color'], end_color=format_options['fill_color'], fill_type='solid')
                    cell.fill = fill
                if format_options.get('align'):
                    align = format_options['align'].lower()
                    if align in ('center', 'left', 'right'):
                        cell.alignment = Alignment(horizontal=align)
            
            return f"✅ Formato aplicado al rango '{range_address}' en hoja '{sheet_name}'."
        except Exception as e:
            logger.error(f"Error formateando celdas: {e}")
            return f"❌ Error al formatear celdas: {str(e)}"

    def _xlsx_insert_row(self, ws, row_index: int, filename: str, sheet_name: str) -> str:
        """Inserta una fila en la posición especificada."""
        try:
            ws.insert_rows(row_index)
            return f"✅ Fila insertada en posición {row_index} en hoja '{sheet_name}'."
        except Exception as e:
            logger.error(f"Error insertando fila: {e}")
            return f"❌ Error al insertar fila: {str(e)}"

    def _xlsx_insert_column(self, ws, column_index: int, filename: str, sheet_name: str) -> str:
        """Inserta una columna en la posición especificada."""
        try:
            ws.insert_cols(column_index)
            return f"✅ Columna insertada en posición {column_index} en hoja '{sheet_name}'."
        except Exception as e:
            logger.error(f"Error insertando columna: {e}")
            return f"❌ Error al insertar columna: {str(e)}"

    def _xlsx_delete_row(self, ws, row_index: int, filename: str, sheet_name: str) -> str:
        """Elimina una fila en la posición especificada."""
        try:
            ws.delete_rows(row_index)
            return f"✅ Fila eliminada en posición {row_index} en hoja '{sheet_name}'."
        except Exception as e:
            logger.error(f"Error eliminando fila: {e}")
            return f"❌ Error al eliminar fila: {str(e)}"

    def _xlsx_delete_column(self, ws, column_index: int, filename: str, sheet_name: str) -> str:
        """Elimina una columna en la posición especificada."""
        try:
            ws.delete_cols(column_index)
            return f"✅ Columna eliminada en posición {column_index} en hoja '{sheet_name}'."
        except Exception as e:
            logger.error(f"Error eliminando columna: {e}")
            return f"❌ Error al eliminar columna: {str(e)}"

    def _xlsx_merge_cells(self, ws, range_address: str, filename: str, sheet_name: str) -> str:
        """Fusiona celdas en un rango."""
        try:
            ws.merge_cells(range_address)
            return f"✅ Celdas fusionadas en rango '{range_address}' de hoja '{sheet_name}'."
        except Exception as e:
            logger.error(f"Error fusionando celdas: {e}")
            return f"❌ Error al fusionar celdas: {str(e)}"

    def _xlsx_set_column_width(self, ws, column_index: int, width: float, filename: str, sheet_name: str) -> str:
        """Establece el ancho de una columna (en caracteres, no cm)."""
        try:
            col_letter = get_column_letter(column_index + 1)
            ws.column_dimensions[col_letter].width = width
            return f"✅ Ancho de columna {col_letter} establecido en {width} en hoja '{sheet_name}'."
        except Exception as e:
            logger.error(f"Error estableciendo ancho de columna: {e}")
            return f"❌ Error al establecer ancho de columna: {str(e)}"

    def _xlsx_set_row_height(self, ws, row_index: int, height: float, filename: str, sheet_name: str) -> str:
        """Establece la altura de una fila."""
        try:
            ws.row_dimensions[row_index].height = height
            return f"✅ Altura de fila {row_index} establecida en {height} en hoja '{sheet_name}'."
        except Exception as e:
            logger.error(f"Error estableciendo altura de fila: {e}")
            return f"❌ Error al establecer altura de fila: {str(e)}"

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
