# skills/onlyoffice_skill/scripts/read_onlyoffice_document_tool.py

import os
import logging
import uuid
import csv
from typing import Any, Type, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import select
from core.database import SessionLocal, Document

# Librerías de procesamiento de documentos (Office)
try:
    import docx
    from openpyxl import load_workbook
    from pptx import Presentation
except ImportError:
    # Esto no debería pasar ya que acabamos de instalarlas, pero por seguridad:
    docx = None
    load_workbook = None
    Presentation = None

logger = logging.getLogger(__name__)

# Definir la raíz de los documentos (misma lógica que en api/onlyoffice.py)
DOCUMENTS_ROOT = os.environ.get("ONLYOFFICE_DOCS_ROOT", "media/onlyoffice")

class ReadOnlyOfficeInput(BaseModel):
    document_id: str = Field(..., description="ID del documento UUID que se desea leer.")

class ReadOnlyOfficeDocumentTool(BaseTool):
    name: str = "read_onlyoffice_document"
    description: str = (
        "Lee el contenido textual completo de un documento almacenado en OnlyOffice. "
        "Soporta formatos .docx (Word), .xlsx (Excel), .pptx (PowerPoint), .txt y .csv. "
        "Úsala después de haber encontrado el ID del documento."
    )
    args_schema: Type[BaseModel] = ReadOnlyOfficeInput
    
    account_id: str = Field(..., description="ID de cuenta del usuario, inyectado automáticamente.")

    async def _arun(self, document_id: str, **kwargs: Any) -> str:
        try:
            acc_id = uuid.UUID(self.account_id)
            doc_id = uuid.UUID(document_id)
            
            async with SessionLocal() as db:
                stmt = select(Document).where(
                    Document.id == doc_id,
                    Document.account_id == acc_id
                )
                result = await db.execute(stmt)
                doc = result.scalar_one_or_none()
                
                if not doc:
                    return f"Documento con ID '{document_id}' no encontrado o no tienes permiso para leerlo."
                
                # Construir ruta física absoluta
                file_path = doc.file_path
                if not os.path.isabs(file_path):
                    file_path = os.path.join(os.getcwd(), file_path)
                
                if not os.path.exists(file_path):
                    return f"El archivo físico '{doc.filename}' no se encuentra en el servidor. Ruta: {file_path}"
                
                ext = doc.extension.lower().replace(".", "")
                content = f"--- CONTENIDO DE '{doc.filename}' ---\n\n"
                
                # --- PROCESAR POR EXTENSIÓN ---
                
                # 1. WORD (.docx)
                if ext == "docx" and docx:
                    doc_obj = docx.Document(file_path)
                    text_parts = [p.text for p in doc_obj.paragraphs if p.text.strip()]
                    content += "\n".join(text_parts)
                
                # 2. EXCEL (.xlsx)
                elif ext == "xlsx" and load_workbook:
                    wb = load_workbook(file_path, data_only=True)
                    for sheet in wb.sheetnames:
                        content += f"\n[Hoja: {sheet}]\n"
                        ws = wb[sheet]
                        # Leer primeras 100 filas para evitar saturar el contexto
                        row_strings = []
                        for row in ws.iter_rows(min_row=1, max_row=100, values_only=True):
                            if any(cell is not None for cell in row):
                                row_strings.append(" | ".join([str(c) if c is not None else "" for c in row]))
                        content += "\n".join(row_strings)
                
                # 3. PPTX (.pptx)
                elif ext == "pptx" and Presentation:
                    prs = Presentation(file_path)
                    for i, slide in enumerate(prs.slides):
                        content += f"\n[Slide {i+1}]\n"
                        texts = []
                        for shape in slide.shapes:
                            if hasattr(shape, "text"):
                                texts.append(shape.text)
                        content += "\n".join(texts)
                
                # 4. CSV
                elif ext == "csv":
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        reader = csv.reader(f)
                        rows = [", ".join(row) for i, row in enumerate(reader) if i < 150]
                        content += "\n".join(rows)
                
                # 5. TXT / OTROS (Fallback a lectura de texto)
                else:
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            content += f.read(10000) # Leer los primeros 10k caracteres
                    except Exception as e:
                        content += f"(Error al leer como texto plano: {str(e)})"
                
                return content

        except Exception as e:
            logger.error(f"Error en ReadOnlyOfficeDocumentTool: {e}", exc_info=True)
            return f"Error al leer el documento: {str(e)}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
