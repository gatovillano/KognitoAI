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

class SlackToolInput(BaseModel):
    action: str = Field(
        ...,
        description="Acción a realizar en Slack. Opciones: 'list_channels', 'send_message', 'get_history'."
    )
    channel_id: Optional[str] = Field(
        None,
        description="ID del canal de Slack. Requerido para 'send_message' y 'get_history'."
    )
    message: Optional[str] = Field(
        None,
        description="Contenido del mensaje a enviar. Requerido para 'send_message'."
    )
    limit: Optional[int] = Field(
        10,
        description="Número de mensajes a recuperar en 'get_history'. Por defecto 10."
    )

class SlackTool(BaseTool):
    name: str = "slack_integration"
    description: str = (
        "Permite interactuar con Slack para enviar mensajes, listar canales y leer el historial. "
        "Acciones disponibles: 'list_channels' (no requiere parámetros), "
        "'send_message' (requiere 'channel_id' y 'message'), "
        "'get_history' (requiere 'channel_id')."
    )
    args_schema: Type[BaseModel] = SlackToolInput
    
    account_id: str = Field(..., description="ID de la cuenta del usuario.")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _arun(
        self, 
        action: str, 
        channel_id: Optional[str] = None, 
        message: Optional[str] = None,
        limit: Optional[int] = 10
    ) -> Union[str, ToolOutputWithSources]:
        """Ejecución asíncrona de la herramienta de Slack."""
        
        token = await self._get_token()
        if not token:
            return "Error: No se encontró un SLACK_BOT_TOKEN configurado. Por favor, configura tus credenciales de Slack primero."

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                if action == "list_channels":
                    return await self._list_channels(client, headers)
                elif action == "send_message":
                    if not channel_id or not message:
                        return "Error: Para enviar un mensaje se requiere 'channel_id' y 'message'."
                    return await self._send_message(client, headers, channel_id, message)
                elif action == "get_history":
                    if not channel_id:
                        return "Error: Para obtener el historial se requiere 'channel_id'."
                    return await self._get_history(client, headers, channel_id, limit)
                else:
                    return f"Error: Acción '{action}' no reconocida."
            except Exception as e:
                logger.error(f"Error en SlackTool ({action}): {e}")
                return f"Error al ejecutar la acción en Slack: {str(e)}"

    def _run(self, *args, **kwargs):
        """Uso de _arun preferido."""
        raise NotImplementedError("Utilice la ejecución asíncrona (_arun).")

    async def _get_token(self) -> Optional[str]:
        """Recupera el token cifrado de la base de datos."""
        async with DBSession(SessionLocal) as db:
            secret_repo = SecretRepository(db)
            return await secret_repo.get_decrypted_secret(uuid.UUID(self.account_id), "SLACK_BOT_TOKEN")

    async def _list_channels(self, client: httpx.AsyncClient, headers: Dict) -> str:
        response = await client.get("https://slack.com/api/conversations.list", headers=headers)
        data = response.json()
        if not data.get("ok"):
            return f"Error de Slack: {data.get('error')}"
        
        channels = [f"- {c['name']} (ID: {c['id']})" for c in data.get("channels", []) if not c.get("is_archived")]
        return "Canales disponibles en Slack:\n" + "\n".join(channels)

    async def _send_message(self, client: httpx.AsyncClient, headers: Dict, channel_id: str, message: str) -> str:
        payload = {"channel": channel_id, "text": message}
        response = await client.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)
        data = response.json()
        if not data.get("ok"):
            return f"Error al enviar mensaje: {data.get('error')}"
        return f"Mensaje enviado con éxito al canal {channel_id}."

    async def _get_history(self, client: httpx.AsyncClient, headers: Dict, channel_id: str, limit: int) -> str:
        params = {"channel": channel_id, "limit": limit}
        response = await client.get("https://slack.com/api/conversations.history", headers=headers, params=params)
        data = response.json()
        if not data.get("ok"):
            return f"Error al recuperar historial: {data.get('error')}"
        
        messages = data.get("messages", [])
        history = []
        for msg in messages:
            user = msg.get("user", "Bot/System")
            text = msg.get("text", "[Sin texto]")
            history.append(f"[{user}]: {text}")
        
        return f"Últimos {len(history)} mensajes en el canal {channel_id}:\n" + "\n".join(history)
