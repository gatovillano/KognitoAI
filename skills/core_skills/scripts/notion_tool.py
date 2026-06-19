import logging
import uuid
import httpx
from typing import List, Any, Dict, Optional, Union, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from core.database import SessionLocal
from utils.db_session import DBSession
from core.repositories.secret_repository import SecretRepository
from core.citation_models import Source, ToolOutputWithSources

logger = logging.getLogger(__name__)

class NotionToolInput(BaseModel):
    action: str = Field(
        ...,
        description="Acción a realizar en Notion. Opciones: 'list_databases', 'read_page', 'create_page'."
    )
    database_id: Optional[str] = Field(
        None,
        description="ID de la base de datos de Notion. Requerido para 'create_page'."
    )
    page_id: Optional[str] = Field(
        None,
        description="ID de la página de Notion. Requerido para 'read_page'."
    )
    title: Optional[str] = Field(
        None,
        description="Título para la nueva página. Requerido para 'create_page'."
    )
    content: Optional[str] = Field(
        None,
        description="Contenido en texto plano (Markdown) para la nueva página."
    )

class NotionTool(BaseTool):
    name: str = "notion_integration"
    description: str = (
        "Permite interactuar con Notion para gestionar conocimiento. "
        "Acciones: 'list_databases' (lista bases de datos disponibles), "
        "'read_page' (lee el contenido de una página), "
        "'create_page' (crea una nueva página en una base de datos con un título y contenido)."
    )
    args_schema: Type[BaseModel] = NotionToolInput
    
    account_id: str = Field(..., description="ID de la cuenta del usuario.")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _arun(
        self, 
        action: str, 
        database_id: Optional[str] = None, 
        page_id: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> Union[str, ToolOutputWithSources]:
        """Ejecución asíncrona de la herramienta de Notion."""
        
        api_key = await self._get_token()
        if not api_key:
            return "Error: No se encontró una NOTION_API_KEY configurada. Por favor, configura tus credenciales de Notion en Ajustes."

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            try:
                if action == "list_databases":
                    return await self._list_databases(client, headers)
                elif action == "read_page":
                    if not page_id:
                        return "Error: Se requiere 'page_id' para leer una página."
                    return await self._read_page(client, headers, page_id)
                elif action == "create_page":
                    if not database_id or not title:
                        return "Error: Para crear una página se requiere 'database_id' y 'title'."
                    return await self._create_page(client, headers, database_id, title, content)
                else:
                    return f"Error: Acción '{action}' no reconocida."
            except Exception as e:
                logger.error(f"Error en NotionTool ({action}): {e}")
                return f"Error al ejecutar la acción en Notion: {str(e)}"

    def _run(self, *args, **kwargs):
        raise NotImplementedError("Utilice la ejecución asíncrona (_arun).")

    async def _get_token(self) -> Optional[str]:
        async with DBSession(SessionLocal) as db:
            secret_repo = SecretRepository(db)
            return await secret_repo.get_decrypted_secret(uuid.UUID(self.account_id), "NOTION_API_KEY")

    async def _list_databases(self, client: httpx.AsyncClient, headers: Dict) -> str:
        payload = {"filter": {"value": "database", "property": "object"}}
        response = await client.post("https://api.notion.com/v1/search", headers=headers, json=payload)
        data = response.json()
        
        databases = []
        for db in data.get("results", []):
            title = db.get("title", [{}])[0].get("plain_text", "Sin título")
            databases.append(f"- {title} (ID: {db['id']})")
        
        if not databases:
            return "No se encontraron bases de datos accesibles. Asegúrate de haber compartido la base de datos con tu Integración de Notion."
        return "Bases de datos disponibles en Notion:\n" + "\n".join(databases)

    async def _read_page(self, client: httpx.AsyncClient, headers: Dict, page_id: str) -> str:
        # Obtener bloques (contenido)
        response = await client.get(f"https://api.notion.com/v1/blocks/{page_id}/children", headers=headers)
        data = response.json()
        
        content = []
        for block in data.get("results", []):
            block_type = block.get("type")
            block_data = block.get(block_type, {})
            rich_text = block_data.get("rich_text", [])
            if rich_text:
                text = "".join([t.get("plain_text", "") for t in rich_text])
                content.append(text)
        
        return f"Contenido de la página {page_id}:\n\n" + "\n".join(content)

    async def _create_page(self, client: httpx.AsyncClient, headers: Dict, database_id: str, title: str, content: Optional[str]) -> str:
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": { "title": [ { "text": { "content": title } } ] }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [ { "type": "text", "text": { "content": content or "Página creada desde KognitoAI" } } ]
                    }
                }
            ]
        }
        
        response = await client.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        if response.status_code != 200:
            return f"Error al crear página: {response.text}"
        
        data = response.json()
        return f"Página '{title}' creada con éxito en Notion (ID: {data['id']})."
