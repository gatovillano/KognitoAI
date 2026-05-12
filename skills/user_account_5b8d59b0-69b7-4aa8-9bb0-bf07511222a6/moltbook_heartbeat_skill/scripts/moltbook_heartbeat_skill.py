from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional
import json
import os
import requests

class MoltbookInput(BaseModel):
    action: str = Field(description="Acción a realizar: 'check_feed', 'post_content', 'comment', 'vote'")
    content: Optional[str] = Field(default=None, description="Contenido para post o comentario")
    title: Optional[str] = Field(default=None, description="Título corto para el post (máximo 300 caracteres)")
    submolt: Optional[str] = Field(default=None, description="Submolt donde publicar")
    post_id: Optional[str] = Field(default=None, description="ID del post para comentar o votar")
    vote_type: Optional[str] = Field(default=None, description="Tipo de voto: 'up' o 'down'")

class MoltbookHeartbeatSkill(BaseTool):
    name: str = "moltbook_heartbeat_skill"
    description: str = "Interactúa con Moltbook (red social para IAs). Soporta publicar posts con título y contenido, comentar, votar y revisar el feed."
    args_schema: Type[BaseModel] = MoltbookInput

    def _run(self, action: str, content: Optional[str] = None, title: Optional[str] = None, 
             submolt: Optional[str] = None, post_id: Optional[str] = None, 
             vote_type: Optional[str] = None) -> str:
        
        # Cargar configuración
        config_path = os.path.expanduser("~/.config/moltbook/credentials.json")
        api_key = None
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                api_key = config.get("api_key")
        
        if not api_key:
            api_key = os.environ.get("MOLTBOOK_API_KEY")
        
        if not api_key:
            return "Error: No se encontró API key. Configura en ~/.config/moltbook/credentials.json o variable MOLTBOOK_API_KEY"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        base_url = "https://www.moltbook.com/api/v1"
        
        try:
            if action == "post_content":
                if not content or not submolt:
                    return "Error: 'content' y 'submolt' son requeridos para post_content"
                
                payload = {
                    "content": content,
                    "submolt": submolt
                }
                if title:
                    payload["title"] = title[:300]  # Máximo 300 caracteres
                
                response = requests.post(f"{base_url}/posts", json=payload, headers=headers, timeout=30)
                
                if response.status_code in [200, 201]:
                    return f"¡Post publicado exitosamente! ✅\nRespuesta: {response.json()}"
                else:
                    return f"Error publicando: {response.status_code} - {response.json()}"
            
            elif action == "check_feed":
                response = requests.get(f"{base_url}/feed", headers=headers, timeout=30)
                if response.status_code == 200:
                    return f"Feed recuperado: {response.json()}"
                else:
                    return f"Error obteniendo feed: {response.status_code}"
            
            elif action == "comment":
                if not content or not post_id:
                    return "Error: 'content' y 'post_id' son requeridos para comment"
                payload = {"content": content, "post_id": post_id}
                response = requests.post(f"{base_url}/comments", json=payload, headers=headers, timeout=30)
                if response.status_code in [200, 201]:
                    return f"Comentario agregado exitosamente ✅"
                else:
                    return f"Error comentando: {response.status_code} - {response.json()}"
            
            elif action == "vote":
                if not vote_type or not post_id:
                    return "Error: 'vote_type' y 'post_id' son requeridos para vote"
                payload = {"vote_type": vote_type, "post_id": post_id}
                response = requests.post(f"{base_url}/votes", json=payload, headers=headers, timeout=30)
                if response.status_code in [200, 201]:
                    return f"Voto registrado exitosamente ✅"
                else:
                    return f"Error votando: {response.status_code} - {response.json()}"
            
            else:
                return f"Acción '{action}' no reconocida"
        
        except Exception as e:
            return f"Error de conexión: {str(e)}"

    def _arun(self, *args, **kwargs):
        raise NotImplementedError("MoltbookHeartbeatSkill no soporta async aún")