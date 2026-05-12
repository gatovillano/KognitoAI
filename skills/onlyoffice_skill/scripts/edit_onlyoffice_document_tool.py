# skills/onlyoffice_skill/scripts/edit_onlyoffice_document_tool.py

"""
Herramienta de Edición Avanzada para Documentos OnlyOffice.
Soporta Word (.docx) y Excel (.xlsx) con múltiples acciones de formato.
"""

import os
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
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

logger = logging.getLogger(__name__)

DEFAULT_DOCS_ROOT = os.path.join("/app/media", "documents")
DOCUMENTS_ROOT = os.environ.get("ONLYOFFICE_DOCS_ROOT", DEFAULT_DOCS_ROOT)

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
            "'append' (añadir párrafo al final), "
            "'append_heading' (añadir título - requiere heading_level 1/2/3), "
            "'append_list' (añadir lista de viñetas - requiere list_items), "
            "'replace' (buscar y reemplazar - requiere search_text), "
            "'replace_section' (reemplaza la sección que empieza con search_text), "
            "'insert_table' (insertar tabla - requiere table_data), "
            "'apply_bold' (poner en negrita - requiere search_text), "
            "'clear_and_write' (borrar todo y escribir nuevo texto), "
            "'xlsx_write_cell' (escribir en celda Excel - requiere cell, sheet_name), "
            "'xlsx_append_row' (añadir fila a Excel - requiere row_data)."
        ),
    )
    text: Optional[str] = Field(None, description="Texto principal a insertar o nuevo texto en 'replace'.")
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
        "Edita documentos de OnlyOffice (Word .docx y Excel .xlsx) con operaciones avanzadas: "
        "añadir párrafos, títulos, listas de viñetas, tablas, buscar/reemplazar texto, "
        "poner texto en negrita, reescribir secciones, o modificar celdas de Excel. "
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
                doc_obj.add_paragraph(text)
                msg = f"✅ Párrafo añadido al final de '{filename}'."

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
                # Eliminar todos los párrafos existentes
                for p in doc_obj.paragraphs:
                    p._element.getparent().remove(p._element)
                # Escribir nuevo contenido
                for line in text.split("\n"):
                    doc_obj.add_paragraph(line)
                msg = f"✅ Documento '{filename}' reescrito con nuevo contenido."

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
        """Reemplaza texto en párrafos y tablas, preservando el formato de los runs."""
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
                        run.text = run.text.replace(search, replacement)
                        count += 1
                # Fallback: si el texto está dividido entre runs
                if search in paragraph.text:
                    full_text = paragraph.text.replace(search, replacement)
                    for run in paragraph.runs:
                        run.text = ""
                    if paragraph.runs:
                        paragraph.runs[0].text = full_text
                    count += 1
        return count

    def _replace_section_in_docx(self, doc_obj, section_start: str, new_content: str) -> bool:
        """Reemplaza el primer párrafo cuyo texto empiece con section_start."""
        for paragraph in doc_obj.paragraphs:
            if paragraph.text.strip().startswith(section_start):
                # Limpiar todos los runs y escribir el nuevo contenido
                for run in paragraph.runs:
                    run.text = ""
                if paragraph.runs:
                    paragraph.runs[0].text = new_content
                else:
                    paragraph.add_run(new_content)
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
