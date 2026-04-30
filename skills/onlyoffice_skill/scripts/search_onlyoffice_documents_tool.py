# skills/onlyoffice_skill/scripts/search_onlyoffice_documents_tool.py

import logging
import uuid
from typing import Any, Type, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import select, or_
from core.database import SessionLocal, Document, DocumentFolder

logger = logging.getLogger(__name__)

class SearchOnlyOfficeInput(BaseModel):
    query: Optional[str] = Field(None, description="Término de búsqueda para filtrar por nombre de archivo o carpeta.")
    workspace_id: Optional[str] = Field(None, description="ID del workspace para limitar la búsqueda (opcional).")

class SearchOnlyOfficeDocumentsTool(BaseTool):
    name: str = "search_onlyoffice_documents"
    description: str = (
        "Busca y lista documentos y carpetas en el módulo OnlyOffice del usuario. "
        "Úsala para encontrar el ID exacto de un archivo o para ver qué archivos hay disponibles "
        "antes de intentar leer uno. Puedes filtrar por nombre o por workspace."
    )
    args_schema: Type[BaseModel] = SearchOnlyOfficeInput
    
    account_id: str = Field(..., description="ID de cuenta del usuario, inyectado automáticamente.")

    async def _arun(self, query: Optional[str] = None, workspace_id: Optional[str] = None, **kwargs: Any) -> str:
        try:
            acc_id = uuid.UUID(self.account_id)
            ws_id = uuid.UUID(workspace_id) if workspace_id and workspace_id != "null" else None
            
            async with SessionLocal() as db:
                # Buscar Carpetas
                f_stmt = select(DocumentFolder).where(DocumentFolder.account_id == acc_id)
                if ws_id:
                    f_stmt = f_stmt.where(DocumentFolder.workspace_id == ws_id)
                if query:
                    f_stmt = f_stmt.where(DocumentFolder.name.ilike(f"%{query}%"))
                
                f_result = await db.execute(f_stmt)
                folders = f_result.scalars().all()
                
                # Buscar Documentos
                d_stmt = select(Document).where(Document.account_id == acc_id)
                if ws_id:
                    d_stmt = d_stmt.where(Document.workspace_id == ws_id)
                if query:
                    d_stmt = d_stmt.where(Document.filename.ilike(f"%{query}%"))
                
                d_result = await db.execute(d_stmt)
                docs = d_result.scalars().all()
                
                if not folders and not docs:
                    return "No se encontraron documentos ni carpetas que coincidan con la búsqueda."
                
                response = "Resultados de búsqueda en OnlyOffice:\n\n"
                
                if folders:
                    response += "📁 CARPETAS:\n"
                    for f in folders:
                        response += f"- {f.name} (ID: {f.id})\n"
                    response += "\n"
                
                if docs:
                    response += "📄 DOCUMENTOS:\n"
                    for d in docs:
                        ws_info = f" [Workspace: {d.workspace_id}]" if d.workspace_id else ""
                        response += f"- {d.filename} (ID: {d.id}){ws_info}\n"
                
                return response

        except Exception as e:
            logger.error(f"Error en SearchOnlyOfficeDocumentsTool: {e}", exc_info=True)
            return f"Error al buscar documentos: {str(e)}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
