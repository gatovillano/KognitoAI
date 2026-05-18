# skills/onlyoffice_skill/scripts/create_onlyoffice_document_tool.py

"""
Herramienta para crear nuevos documentos de OnlyOffice (Word, Excel, PowerPoint, Texto) desde cero.
"""

import os
import logging
import uuid
from typing import Any, Type, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import SessionLocal, Document
from core.config import settings
from datetime import datetime

# Librerías de procesamiento de documentos (Office)
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from openpyxl import Workbook
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

logger = logging.getLogger(__name__)

DEFAULT_DOCS_ROOT = os.path.join(settings.media_root, "documents")
DOCUMENTS_ROOT = os.environ.get("ONLYOFFICE_DOCS_ROOT", DEFAULT_DOCS_ROOT)

class CreateOnlyOfficeInput(BaseModel):
    name: str = Field(..., description="Nombre del archivo (con o sin extensión).")
    doc_type: str = Field(
        ..., 
        description="Tipo de documento a crear: 'word' (.docx), 'excel' (.xlsx), 'powerpoint' (.pptx) o 'text' (.txt)."
    )
    workspace_id: Optional[str] = Field(None, description="ID del workspace (opcional).")
    folder_id: Optional[str] = Field(None, description="ID de la carpeta (opcional).")

class CreateOnlyOfficeDocumentTool(BaseTool):
    name: str = "create_onlyoffice_document"
    description: str = (
        "Crea un nuevo documento vacío en OnlyOffice. "
        "Soporta Word, Excel, PowerPoint y Texto plano. "
        "Úsala cuando el usuario quiera empezar un nuevo documento desde cero."
    )
    args_schema: Type[BaseModel] = CreateOnlyOfficeInput
    
    account_id: str = Field(..., description="ID de cuenta del usuario, inyectado automáticamente.")

    async def _arun(
        self, 
        name: str, 
        doc_type: str, 
        workspace_id: Optional[str] = None, 
        folder_id: Optional[str] = None, 
        **kwargs: Any
    ) -> str:
        try:
            acc_id = uuid.UUID(self.account_id)
            
            # Determinar extensión y validar librerías
            doc_type = doc_type.lower()
            extension = ""
            if doc_type == 'word':
                if not DOCX_AVAILABLE:
                    return "❌ Error: La librería 'python-docx' no está instalada."
                extension = 'docx'
            elif doc_type == 'excel':
                if not XLSX_AVAILABLE:
                    return "❌ Error: La librería 'openpyxl' no está instalada."
                extension = 'xlsx'
            elif doc_type == 'powerpoint':
                if not PPTX_AVAILABLE:
                    return "❌ Error: La librería 'python-pptx' no está instalada."
                extension = 'pptx'
            elif doc_type == 'text':
                extension = 'txt'
            else:
                return f"❌ Tipo de documento '{doc_type}' no soportado. Usa: 'word', 'excel', 'powerpoint' o 'text'."

            # Asegurar nombre con extensión
            if not name.lower().endswith(f".{extension}"):
                full_filename = f"{name}.{extension}"
            else:
                full_filename = name

            # Generar ruta física
            unique_filename = f"{uuid.uuid4()}.{extension}"
            user_dir = os.path.join(DOCUMENTS_ROOT, self.account_id)
            os.makedirs(user_dir, exist_ok=True)
            file_path = os.path.join(user_dir, unique_filename)

            # Crear archivo físico
            try:
                if doc_type == 'word':
                    doc = docx.Document()
                    doc.save(file_path)
                elif doc_type == 'excel':
                    wb = Workbook()
                    wb.save(file_path)
                elif doc_type == 'powerpoint':
                    prs = Presentation()
                    prs.save(file_path)
                elif doc_type == 'text':
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write("")
            except Exception as e:
                logger.error(f"Error al crear archivo físico OnlyOffice: {e}")
                return f"❌ Error al crear el archivo físico en el servidor: {str(e)}"

            # Registrar en DB
            async with SessionLocal() as db:
                new_doc = Document(
                    account_id=acc_id,
                    workspace_id=uuid.UUID(workspace_id) if workspace_id and workspace_id != "null" else None,
                    folder_id=uuid.UUID(folder_id) if folder_id and folder_id != "null" else None,
                    filename=full_filename,
                    extension=extension,
                    file_path=os.path.join(self.account_id, unique_filename)
                )
                db.add(new_doc)
                await db.commit()
                await db.refresh(new_doc)
                
                return (
                    f"✅ Documento '{full_filename}' creado con éxito.\n"
                    f"ID: {new_doc.id}\n"
                    "Ahora puedes usar 'edit_onlyoffice_document' para añadir contenido."
                )

        except Exception as e:
            logger.error(f"Error en CreateOnlyOfficeDocumentTool: {e}", exc_info=True)
            return f"❌ Error inesperado al crear el documento: {str(e)}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
