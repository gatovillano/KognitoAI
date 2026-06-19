from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Dict, Any
import requests
import json
import os

class MoltbookFullSkillInput(BaseModel):
    action: str = Field(description="Acción a realizar. Opciones: 'register', 'status', 'me', 'create_post', 'list_posts', 'get_post', 'delete_post', 'add_comment', 'list_comments', 'upvote_post', 'downvote_post', 'upvote_comment', 'create_submolt', 'list_submolts', 'get_submolt', 'subscribe', 'unsubscribe', 'follow', 'unfollow', 'personalized_feed', 'semantic_search'")
    # Parámetros generales
    api_key: Optional[str] = Field(default=None, description="API Key de Moltbook. Si no se provee, se busca en ~/.config/moltbook/credentials.json o en la variable de entorno MOLTBOOK_API_KEY")
    # Parámetros para Posts
    submolt_name: Optional[str] = Field(default=None, description="Nombre del submolt (para create_post, list_posts)")
    title: Optional[str] = Field(default=None, description="Título del post (para create_post)")
    content: Optional[str] = Field(default=None, description="Contenido del post o comentario")
    post_id: Optional[str] = Field(default=None, description="ID del post (para get_post, delete_post, add_comment, upvote/downvote)")
    url: Optional[str] = Field(default=None, description="URL para link posts")
    post_type: Optional[str] = Field(default="text", description="Tipo de post: 'text', 'link', 'image'")
    sort: Optional[str] = Field(default="hot", description="Ordenamiento: 'hot', 'new', 'top', 'rising'")
    limit: Optional[int] = Field(default=25, description="Límite de resultados")
    cursor: Optional[str] = Field(default=None, description="Cursor para paginación")
    # Parámetros para Comments
    comment_id: Optional[str] = Field(default=None, description="ID del comentario (para upvote)")
    parent_id: Optional[str] = Field(default=None, description="ID del comentario padre (para replies)")
    # Parámetros para Submolts
    name: Optional[str] = Field(default=None, description="Nombre del submolt (URL safe)")
    display_name: Optional[str] = Field(default=None, description="Nombre para mostrar")
    description: Optional[str] = Field(default=None, description="Descripción")
    allow_crypto: Optional[bool] = Field(default=False, description="Permitir contenido crypto")
    # Parámetros para Follow/Search
    agent_name: Optional[str] = Field(default=None, description="Nombre del agente a seguir o buscar")
    query: Optional[str] = Field(default=None, description="Consulta de búsqueda semántica")
    filter_type: Optional[str] = Field(default="all", description="Filtro para feed: 'all' o 'following'")

class MoltbookFullSkill(BaseTool):
    name: str = "moltbook_full_skill"
    description: str = "Skill completa para interactuar con la red social Moltbook. Soporta registro, posts, comentarios, votos, submolts, seguimiento de agentes y búsqueda semántica."
    args_schema: Type[BaseModel] = MoltbookFullSkillInput

    def _get_api_key(self, provided_key: Optional[str]) -> str:
        if provided_key:
            return provided_key
        
        # Intentar desde archivo de credenciales
        cred_path = os.path.expanduser("~/.config/moltbook/credentials.json")
        if os.path.exists(cred_path):
            try:
                with open(cred_path, 'r') as f:
                    creds = json.load(f)
                    return creds.get("api_key")
            except: pass
        
        # Intentar desde variable de entorno
        return os.environ.get("MOLTBOOK_API_KEY", "")

    def _request(self, method, endpoint, api_key, data=None, params=None):
        base_url = "https://www.moltbook.com/api/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        url = f"{base_url}/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=15)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=15)
            
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _run(self, action: str, api_key: Optional[str] = None, submolt_name: Optional[str] = None, 
             title: Optional[str] = None, content: Optional[str] = None, post_id: Optional[str] = None,
             url: Optional[str] = None, post_type: Optional[str] = "text", sort: Optional[str] = "hot",
             limit: Optional[int] = 25, cursor: Optional[str] = None, comment_id: Optional[str] = None,
             parent_id: Optional[str] = None, name: Optional[str] = None, display_name: Optional[str] = None,
             description: Optional[str] = None, allow_crypto: Optional[bool] = False, agent_name: Optional[str] = None,
             query: Optional[str] = None, filter_type: Optional[str] = "all"):
        
        api_key = self._get_api_key(api_key)
        if not api_key:
            return "Error: No se encontró API Key. Regístrala en ~/.config/moltbook/credentials.json o usa la variable MOLTBOOK_API_KEY"

        # AGENTE
        if action == "register":
            data = {"name": name or "KAI_Agent", "description": description or "KAI Assistant"}
            return self._request("POST", "agents/register", api_key, data=data)
        
        elif action == "status":
            return self._request("GET", "agents/status", api_key)
        
        elif action == "me":
            return self._request("GET", "agents/me", api_key)

        # POSTS
        elif action == "create_post":
            data = {"submolt_name": submolt_name or "general", "title": title}
            if content: data["content"] = content
            if url: data["url"] = url
            data["type"] = post_type
            return self._request("POST", "posts", api_key, data=data)
        
        elif action == "list_posts":
            params = {"sort": sort, "limit": limit}
            if submolt_name: params["submolt"] = submolt_name
            if cursor: params["cursor"] = cursor
            return self._request("GET", "posts", api_key, params=params)
        
        elif action == "get_post":
            return self._request("GET", f"posts/{post_id}", api_key)
        
        elif action == "delete_post":
            return self._request("DELETE", f"posts/{post_id}", api_key)

        # COMMENTS
        elif action == "add_comment":
            data = {"content": content}
            if parent_id: data["parent_id"] = parent_id
            return self._request("POST", f"posts/{post_id}/comments", api_key, data=data)
        
        elif action == "list_comments":
            params = {"sort": sort, "limit": limit}
            return self._request("GET", f"posts/{post_id}/comments", api_key, params=params)

        # VOTING
        elif action == "upvote_post":
            return self._request("POST", f"posts/{post_id}/upvote", api_key)
        elif action == "downvote_post":
            return self._request("POST", f"posts/{post_id}/downvote", api_key)
        elif action == "upvote_comment":
            return self._request("POST", f"comments/{comment_id}/upvote", api_key)

        # SUBMOLTS
        elif action == "create_submolt":
            data = {"name": name, "display_name": display_name, "description": description, "allow_crypto": allow_crypto}
            return self._request("POST", "submolts", api_key, data=data)
        elif action == "list_submolts":
            return self._request("GET", "submolts", api_key)
        elif action == "get_submolt":
            return self._request("GET", f"submolts/{name}", api_key)
        elif action == "subscribe":
            return self._request("POST", f"submolts/{submolt_name}/subscribe", api_key)
        elif action == "unsubscribe":
            return self._request("DELETE", f"submolts/{submolt_name}/subscribe", api_key)

        # FOLLOWING
        elif action == "follow":
            return self._request("POST", f"agents/{agent_name}/follow", api_key)
        elif action == "unfollow":
            return self._request("DELETE", f"agents/{agent_name}/follow", api_key)

        # FEED
        elif action == "personalized_feed":
            params = {"sort": sort, "limit": limit, "filter": filter_type}
            return self._request("GET", "feed", api_key, params=params)

        # SEARCH
        elif action == "semantic_search":
            params = {"q": query, "limit": limit}
            return self._request("GET", "search", api_key, params=params)

        return f"Acción '{action}' no reconocida."

