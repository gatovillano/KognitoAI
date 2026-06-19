# skills/onlyoffice_skill/scripts/list_onlyoffice_documents_tool.py

import logging
import uuid
from typing import Any, Type, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import select
from core.database import SessionLocal, Document, DocumentFolder

logger = logging.getLogger(__name__)

class ListOnlyOfficeInput(BaseModel):
    folder_id: Optional[str] = Field(None, description="ID de la carpeta que se desea explorar. Si se omite, se listará el contenido de la raíz.")
    workspace_id: Optional[str] = Field(None, description="ID del workspace (opcional) para filtrar el contenido del nivel principal.")

class ListOnlyOfficeDocumentsTool(BaseTool):
    name: str = "list_onlyoffice_documents"
    description: str = (
        "Lista el contenido (carpetas y documentos) de un nivel específico o carpeta de OnlyOffice. "
        "Úsala para navegar paso a paso por la estructura de directorios del usuario. "
        "Si no sabes por dónde empezar, úsala sin argumentos para ver la raíz."
    )
    args_schema: Type[BaseModel] = ListOnlyOfficeInput
    
    account_id: str = Field(..., description="ID de cuenta del usuario, inyectado automáticamente.")

    async def _arun(self, folder_id: Optional[str] = None, workspace_id: Optional[str] = None, **kwargs: Any) -> str:
        try:
            acc_id = uuid.UUID(self.account_id)
            f_id = uuid.UUID(folder_id) if folder_id and folder_id != "null" else None
            ws_id = uuid.UUID(workspace_id) if workspace_id and workspace_id != "null" else None
            
            async with SessionLocal() as db:
                # 1. Listar Subcarpetas
                f_stmt = select(DocumentFolder).where(DocumentFolder.account_id == acc_id)
                if f_id:
                    f_stmt = f_stmt.where(DocumentFolder.parent_id == f_id)
                else:
                    f_stmt = f_stmt.where(DocumentFolder.parent_id == None)
                    if ws_id:
                        f_stmt = f_stmt.where(DocumentFolder.workspace_id == ws_id)
                
                f_result = await db.execute(f_stmt)
                folders = f_result.scalars().all()
                
                # 2. Listar Documentos
                d_stmt = select(Document).where(Document.account_id == acc_id)
                if f_id:
                    d_stmt = d_stmt.where(Document.folder_id == f_id)
                else:
                    d_stmt = d_stmt.where(Document.folder_id == None)
                    if ws_id:
                        d_stmt = d_stmt.where(Document.workspace_id == ws_id)
                
                d_result = await db.execute(d_stmt)
                docs = d_result.scalars().all()
                
                if not folders and not docs:
                    loc = f"carpeta '{folder_id}'" if folder_id else "directorio raíz"
                    return f"No hay contenido en {loc}."
                
                title = f"Contenido en carpeta '{folder_id}':" if folder_id else "Contenido raíz de OnlyOffice:"
                response = f"{title}\n\n"
                
                if folders:
                    response += "📁 CARPETAS:\n"
                    for f in folders:
                        ws_tag = f" [WS: {f.workspace_id}]" if f.workspace_id else ""
                        response += f"- {f.name} (ID: {f.id}){ws_tag}\n"
                    response += "\n"
                
                if docs:
                    response += "📄 DOCUMENTOS:\n"
                    for d in docs:
                        response += f"- {d.filename} (ID: {d.id}) [.{d.extension}]\n"
                
                return response

        except Exception as e:
            logger.error(f"Error en ListOnlyOfficeDocumentsTool: {e}", exc_info=True)
            return f"Error al listar contenido: {str(e)}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
