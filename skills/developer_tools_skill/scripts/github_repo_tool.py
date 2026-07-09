# tools/github_repo_tool.py
import logging
import os
from typing import List, Any, Dict, Optional, Union, Type
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import hashlib
import subprocess
import tempfile
import shutil

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from utils.db_session import DBSession
from core.citation_models import Source, ToolOutputWithSources, create_github_source, format_context_with_sources

logger = logging.getLogger(__name__)

class GitHubRepoInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de exploración de repositorios de GitHub.
    Valida que el LLM proporcione todos los argumentos necesarios.
    """
    repo_url: str = Field(
        ...,
        description="La URL completa del repositorio de GitHub a explorar (por ejemplo, https://github.com/usuario/repositorio)."
    )
    action: str = Field(
        ...,
        description="La acción a realizar en el repositorio. Las opciones válidas son: 'list_tree' (listar todos los archivos), 'read_file' (leer un archivo específico), 'navigate' (listar contenido de un directorio), 'read_directory' (leer todos los documentos de un directorio), 'read_directory_recursively' (leer todos los documentos de un directorio y sus subdirectorios), 'add_as_knowledge_collection' (añadir como colección de conocimientos), 'update_knowledge_collection' (actualizar colección de conocimientos)."
    )
    path: Optional[str] = Field(
        None,
        description="La ruta al archivo o directorio dentro del repositorio. Requerido para las acciones 'read_file', 'navigate' y 'read_directory'."
    )
    github_token: Optional[str] = Field(
        None,
        description="Token de acceso personal de GitHub para acceder a repositorios privados. Opcional, pero puede ser necesario para repositorios privados."
    )
    collection_topic: Optional[str] = Field(
        None,
        description="Tema de la colección RAG donde se gestionarán los documentos. Opcional. Si no se proporciona, se usará el account_id para el conocimiento general."
    )
    vectorize: Optional[bool] = Field(
        None,
        description="Indica si los documentos deben ser vectorizados al añadirlos o actualizarlos como colección de conocimientos. Por defecto es False."
    )

class GitHubRepoTool(BaseTool):
    args_schema: Type[BaseModel] = GitHubRepoInput
    name: str = "github_repository_explorer"
    description: str = (
        "Este tool permite explorar repositorios de GitHub y gestionarlos como colecciones de conocimientos. Debes proporcionar la URL del repositorio en el parámetro 'repo_url', la acción a realizar (list_tree, read_file, navigate, read_directory, read_directory_recursively, add_as_knowledge_collection, update_knowledge_collection) en el parámetro 'action', y, opcionalmente, la ruta al archivo o directorio en el parámetro 'path', el token de GitHub en el parámetro 'github_token', el ID del workspace en 'workspace_id' y el ID de la cuenta en 'account_id' si es necesario. Asegúrate de proporcionar la URL completa del repositorio y de utilizar los nombres de parámetro y acción correctos."
    )
    github_token: Optional[str] = Field(
        None,
        description="El token de GitHub a utilizar para acceder a repositorios privados. Si no se proporciona, se utilizará la variable de entorno GITHUB_TOKEN.",
    )
    session: Optional[requests.Session] = Field(
        default_factory=requests.Session,
        description="La sesión HTTP a utilizar para realizar las solicitudes."
    )

    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del workspace, inyectado automáticamente.")
    telegram_id: Optional[str] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente si está disponible.")
    thread_id: Optional[str] = Field(None, description="El ID del hilo de conversación, inyectado automáticamente si está disponible.")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.session = requests.Session()
        self.github_token = kwargs.get("github_token")
        self._local_clone_path: Optional[str] = None
        self._clone_branch: Optional[str] = None
        logger.debug("GitHubRepoTool initialized. Version: 2025-07-24_05:00")
    
    def _run(self, repo_url: str, action: str, path: Optional[str] = None, github_token: Optional[str] = None, collection_topic: Optional[str] = None) -> Any:
        """
        Ejecuta la acción especificada en el repositorio de GitHub (síncrono).
        """
        logger.debug(f"DEBUG: _run (sync) called with repo_url={repo_url}, action={action}")
        
        try:
            result_content = ""
            if action == "list_tree":
                result_content = self._list_tree(repo_url)
            elif action == "read_file":
                if not path:
                    return "Error: Debes especificar la ruta del archivo para leer."
                result_content = self._read_file(repo_url, path)
            elif action == "navigate":
                if not path:
                    return "Error: Debes especificar la ruta para navegar."
                result_content = self._navigate(repo_url, path)
            elif action == "read_directory":
                if not path:
                    return "Error: Debes especificar la ruta del directorio para leer los documentos."
                result_content = self._read_directory(repo_url, path)
            elif action == "read_directory_recursively":
                result_content = self._read_directory_recursively(repo_url, path or "")
            elif action in ["add_as_knowledge_collection", "update_knowledge_collection"]:
                 return "Error: Las acciones de knowledge collection solo están disponibles en modo asíncrono."
            else:
                return f"Error: Acción no válida. Las acciones válidas son: list_tree, read_file, navigate, read_directory, read_directory_recursively"
            
            full_url = repo_url
            if path:
                if action == "read_file":
                    branch = "main"
                    full_url = f"{repo_url}/blob/{branch}/{path}"
                elif action in ["navigate", "read_directory", "read_directory_recursively"]:
                    branch = "main"
                    full_url = f"{repo_url}/tree/{branch}/{path}"
            
            source_id = hashlib.sha256(full_url.encode()).hexdigest()[:8]
            
            source = create_github_source(
                source_id=source_id,
                title=f"{path} ({action})" if path else f"Repo: {repo_url}",
                url=full_url,
                snippet=f"Result of {action}: " + (str(result_content)[:200] + "..." if len(str(result_content)) > 200 else str(result_content)),
                metadata={"file_path": path, "repo_url": repo_url}
            )
            
            logger.info(f"✅ Fuente GitHub creada en _run: {source.title}")

            return ToolOutputWithSources(
                context_for_llm=str(result_content),
                sources=[source]
            )
        except Exception as e:
            logger.error(f"Error en _run para {repo_url}: {e}", exc_info=True)
            return f"Error al ejecutar la acción: {e}"
    
    # -------------------------------------------------------------------------
    # Local clone fallback (para evitar rate limits de la API de GitHub)
    # -------------------------------------------------------------------------

    def _ensure_local_clone(self, repo_url: str, branch: Optional[str] = None) -> Optional[str]:
        """
        Clona el repositorio localmente en un directorio temporal usando git.
        Retorna la ruta del clone o None si falla.
        """
        if self._local_clone_path and os.path.isdir(self._local_clone_path):
            return self._local_clone_path

        parsed = urlparse(repo_url)
        path_segments = parsed.path.strip("/").split("/")
        if len(path_segments) < 2:
            return None
        username, repo_name = path_segments[0], path_segments[1]

        clone_url = repo_url
        active_token = self.github_token or os.environ.get("GITHUB_TOKEN")
        if active_token and parsed.hostname and "github.com" in parsed.hostname:
            clone_url = f"https://{active_token}@{parsed.hostname}/{username}/{repo_name}.git"

        temp_dir = tempfile.mkdtemp(prefix="github_repo_clone_")
        try:
            cmd = ["git", "clone", "--depth", "1"]
            if branch:
                cmd += ["--branch", branch]
            cmd += [clone_url, temp_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.warning(f"git clone failed: {result.stderr.strip()}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None

            self._local_clone_path = temp_dir
            self._clone_branch = branch
            logger.info(f"Repositorio clonado localmente en: {temp_dir}")
            return temp_dir
        except Exception as e:
            logger.error(f"Error al clonar repositorio localmente: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

    def _cleanup_clone(self) -> None:
        """Elimina el directorio de clonado local si existe."""
        if self._local_clone_path and os.path.isdir(self._local_clone_path):
            try:
                shutil.rmtree(self._local_clone_path, ignore_errors=True)
            except Exception:
                pass
            self._local_clone_path = None
            self._clone_branch = None

    def _get_local_path(self, repo_url: str, path: Optional[str] = None, branch: Optional[str] = None) -> Optional[str]:
        """
        Retorna la ruta absoluta en el filesystem local para un archivo/directorio
        dentro del repositorio clonado. Si no hay clone activo, intenta crearlo.
        """
        clone_path = self._ensure_local_clone(repo_url, branch=branch)
        if not clone_path:
            return None
        if not path:
            return clone_path
        return os.path.join(clone_path, path)

    def _read_file_local(self, file_path: str) -> str:
        """Lee un archivo desde el sistema de archivos local."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return f"Contenido del archivo {os.path.basename(file_path)}:\n{content}"
        except Exception as e:
            return f"Error al leer el archivo local {file_path}: {e}"

    def _list_tree_local(self, clone_path: str) -> str:
        """Lista el árbol de archivos desde el filesystem local."""
        try:
            entries = []
            for root, dirs, files in os.walk(clone_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.git']
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, clone_path)
                    entries.append(f"- {rel_path} (file)")
            return "Árbol de archivos (local):\n" + "\n".join(entries)
        except Exception as e:
            return f"Error al listar árbol local: {e}"

    def _navigate_local(self, dir_path: str) -> str:
        """Lista el contenido de un directorio local."""
        try:
            if not os.path.isdir(dir_path):
                return f"Error: {dir_path} no es un directorio."
            entries = []
            for entry in os.listdir(dir_path):
                full = os.path.join(dir_path, entry)
                entries.append(f"- {entry} ({'directory' if os.path.isdir(full) else 'file'})")
            return "Contenido del directorio (local):\n" + "\n".join(entries)
        except Exception as e:
            return f"Error al navegar directorio local: {e}"

    def _read_directory_local(self, dir_path: str) -> str:
        """Lee todos los archivos de un directorio local."""
        try:
            if not os.path.isdir(dir_path):
                return f"Error: {dir_path} no es un directorio."
            result = []
            for entry in sorted(os.listdir(dir_path)):
                full = os.path.join(dir_path, entry)
                if os.path.isfile(full):
                    result.append(f"Archivo: {entry}\n{self._read_file_local(full)}\n{'-'*50}")
            return "\n".join(result) if result else f"No se encontraron archivos en {dir_path}."
        except Exception as e:
            return f"Error al leer directorio local: {e}"

    def _make_request(self, url: str, headers: Optional[Dict] = None) -> requests.Response:
        """Realiza una petición HTTP GET a la API de GitHub."""
        req_headers = headers or {}
        active_token = self.github_token or os.environ.get("GITHUB_TOKEN")
        if active_token:
            req_headers["Authorization"] = f"token {active_token}"
        return self.session.get(url, headers=req_headers, timeout=30)

    def _get_api_url(self, repo_url: str) -> str:
        """Convierte una URL de GitHub a la URL de la API."""
        parsed = urlparse(repo_url)
        path = parsed.path.strip("/")
        return f"https://api.github.com/repos/{path}"

    def _get_content_with_retry(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """Obtiene contenido de un archivo vía API con reintentos."""
        for attempt in range(max_retries):
            try:
                response = self._make_request(url)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    logger.warning(f"Rate limit alcanzado en API de GitHub (intento {attempt + 1})")
                    import time
                    time.sleep(2 ** attempt)
                else:
                    return None
            except Exception as e:
                logger.warning(f"Error en intento {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
        return None

    def _is_temporary_file(self, file_path: str) -> bool:
        """Verifica si un archivo es temporal o de sistema."""
        temp_patterns = ['.tmp', '.temp', '.swp', '.swo', '.pyc', '__pycache__', '.git', '.DS_Store', 'Thumbs.db']
        return any(file_path.endswith(p) or file_path.startswith(p) for p in temp_patterns)

    def _is_binary_file(self, file_path: str) -> bool:
        """Verifica si un archivo es binario basado en extensión."""
        binary_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.pdf', '.zip', '.tar', '.gz', 
                            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.mp3', '.mp4', '.avi', '.mov',
                            '.wav', '.flac', '.ogg', '.webm', '.ttf', '.otf', '.woff', '.woff2', '.eot']
        return any(file_path.lower().endswith(ext) for ext in binary_extensions)

    def _list_tree(self, repo_url: str) -> str:
        """Lista el árbol de archivos del repositorio."""
        try:
            # Intentar clonado local primero
            local_path = self._ensure_local_clone(repo_url)
            if local_path:
                result = self._list_tree_local(local_path)
                self._cleanup_clone()
                return result
            
            # Fallback a API
            api_url = self._get_api_url(repo_url)
            response = self._make_request(f"{api_url}?depth=1")
            if response.status_code >= 400:
                return f"Error al acceder al repositorio (código: {response.status_code}). Verifica el token de GitHub."
            
            repo_info = response.json()
            default_branch = repo_info.get("default_branch", "main")
            
            tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
            tree_response = self._make_request(tree_url)
            if tree_response.status_code >= 400:
                return f"Error al obtener el árbol (código: {tree_response.status_code})."
            
            tree_response.raise_for_status()
            tree = tree_response.json()["tree"]
            
            entries = [f"- {item['path']} ({item['type']})" for item in tree if item['type'] == 'blob']
            return "Árbol de archivos:\n" + "\n".join(entries[:100])
        except Exception as e:
            logger.error(f"Error listando árbol: {e}")
            return f"Error: {e}"

    def _read_file(self, repo_url: str, file_path: str) -> str:
        """Lee un archivo específico del repositorio."""
        try:
            # Intentar clonado local primero
            local_full_path = self._get_local_path(repo_url, file_path)
            if local_full_path and os.path.isfile(local_full_path):
                result = self._read_file_local(local_full_path)
                self._cleanup_clone()
                return result
            
            # Fallback a API
            api_url = self._get_api_url(repo_url)
            content_data = self._get_content_with_retry(f"{api_url}/contents/{file_path}")
            
            if not content_data or 'content' not in content_data:
                return f"Error: No se pudo obtener el archivo {file_path}."
            
            import base64
            content_base64 = content_data["content"]
            encoding = content_data["encoding"]
            
            if encoding == "base64":
                content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
            else:
                content = content_base64
            
            return f"Contenido del archivo {file_path}:\n{content}"
        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}")
            return f"Error: {e}"

    def _navigate(self, repo_url: str, path: str) -> str:
        """Lista el contenido de un directorio en el repositorio."""
        try:
            # Intentar clonado local primero
            local_path = self._get_local_path(repo_url, path)
            if local_path and os.path.isdir(local_path):
                result = self._navigate_local(local_path)
                self._cleanup_clone()
                return result
            
            # Fallback a API
            api_url = self._get_api_url(repo_url)
            tree_url = f"{api_url}/git/trees/main?recursive=1"
            response = self._make_request(tree_url)
            if response.status_code >= 400:
                return f"Error al acceder al árbol (código: {response.status_code})."
            
            tree_data = response.json()
            tree = tree_data.get("tree", [])
            
            # Filtrar por el path específico
            items = [item for item in tree if item['path'].startswith(path + '/') or item['path'] == path]
            entries = [f"- {os.path.basename(item['path'])} ({item['type']})" for item in items if item['path'] != path]
            
            return "Contenido del directorio:\n" + "\n".join(entries[:50])
        except Exception as e:
            logger.error(f"Error navegando: {e}")
            return f"Error: {e}"

    def _read_directory(self, repo_url: str, path: str) -> str:
        """Lee todos los documentos de un directorio."""
        try:
            # Intentar clonado local primero
            local_path = self._get_local_path(repo_url, path)
            if local_path and os.path.isdir(local_path):
                result = self._read_directory_local(local_path)
                self._cleanup_clone()
                return result
            
            # Fallback a API
            api_url = self._get_api_url(repo_url)
            tree_url = f"{api_url}/git/trees/main?recursive=1"
            response = self._make_request(tree_url)
            if response.status_code >= 400:
                return f"Error al acceder al árbol (código: {response.status_code})."
            
            tree_data = response.json()
            tree = tree_data.get("tree", [])
            
            # Filtrar archivos en el directorio
            files = [item['path'] for item in tree if item['type'] == 'blob' and item['path'].startswith(path + '/')]
            
            results = []
            for file_path in files[:10]:
                content_data = self._get_content_with_retry(f"{api_url}/contents/{file_path}")
                if content_data and 'content' in content_data:
                    import base64
                    content = base64.b64decode(content_data["content"]).decode("utf-8", errors="ignore")
                    results.append(f"Archivo: {file_path}\n{content}\n{'-'*50}")
            
            return "\n".join(results) if results else f"No se encontraron archivos en {path}."
        except Exception as e:
            logger.error(f"Error leyendo directorio: {e}")
            return f"Error: {e}"

    def _read_directory_recursively(self, repo_url: str, path: str = "") -> str:
        """Lee todos los documentos de un directorio recursivamente."""
        try:
            # Intentar clonado local primero
            local_path = self._ensure_local_clone(repo_url)
            if local_path:
                target_path = os.path.join(local_path, path) if path else local_path
                result = self._read_directory_local(target_path)
                self._cleanup_clone()
                return result
            
            # Fallback a API
            api_url = self._get_api_url(repo_url)
            tree_url = f"{api_url}/git/trees/main?recursive=1"
            response = self._make_request(tree_url)
            if response.status_code >= 400:
                return f"Error al acceder al árbol (código: {response.status_code})."
            
            tree_data = response.json()
            tree = tree_data.get("tree", [])
            
            # Filtrar por path si se especificó
            if path:
                tree = [item for item in tree if item['path'].startswith(path)]
            
            # Leer archivos
            results = []
            for item in tree[:20]:  # Limitar a 20 archivos
                if item['type'] == 'blob' and not self._is_binary_file(item['path']) and not self._is_temporary_file(item['path']):
                    content_data = self._get_content_with_retry(f"{api_url}/contents/{item['path']}")
                    if content_data and 'content' in content_data:
                        import base64
                        content = base64.b64decode(content_data["content"]).decode("utf-8", errors="ignore")
                        results.append(f"Archivo: {item['path']}\n{content}\n{'-'*50}")
            
            return "\n".join(results) if results else f"No se encontraron archivos."
        except Exception as e:
            logger.error(f"Error leyendo directorio recursivamente: {e}")
            return f"Error: {e}"
    
    # -------------------------------------------------------------------------
    # Async methods for knowledge collection
    # -------------------------------------------------------------------------

    async def _arun(self, repo_url: str, action: str, path: Optional[str] = None, github_token: Optional[str] = None, collection_topic: Optional[str] = None, vectorize: bool = False) -> Any:
        """
        Versión asíncrona que soporta add_as_knowledge_collection y update_knowledge_collection.
        """
        logger.debug(f"DEBUG: _arun (async) called with repo_url={repo_url}, action={action}")
        
        if action in ["add_as_knowledge_collection", "update_knowledge_collection"]:
            if action == "add_as_knowledge_collection":
                return await self._add_as_knowledge_collection(repo_url, collection_topic, vectorize)
            elif action == "update_knowledge_collection":
                return await self._update_knowledge_collection(repo_url, collection_topic, vectorize)
        else:
            return self._run(repo_url, action, path, github_token, collection_topic)

    async def _add_as_knowledge_collection(self, repo_url: str, collection_topic: Optional[str] = None, vectorize: bool = False) -> str:
        """
        Añade un repositorio de GitHub como colección de conocimientos.
        Intenta clonado local primero, luego fallback a API de GitHub.
        """
        try:
            from core.database import SessionLocal, GitHubDocument
            from sqlalchemy import select
            import base64
            from datetime import datetime
            import hashlib
            from skills.rag_skill.scripts.document_rag_tool import DocumentRAGTool
            
            if self.session is None:
                self.session = requests.Session()
            
            api_url = self._get_api_url(repo_url)
            repo_name = None
            default_branch = "main"
            tree = []
            local_path = None

            # Intentar clonado local primero (sin peticiones a API)
            local_path = self._ensure_local_clone(repo_url)
            if local_path:
                try:
                    # Obtener repo_name del directorio local
                    repo_name = os.path.basename(local_path.rstrip('/'))
                    
                    # Recorrer el árbol local
                    for root, dirs, files in os.walk(local_path):
                        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.git']
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, local_path)
                            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                            tree.append({"path": rel_path, "type": "blob", "content": content})
                    
                    logger.info(f"✅ Clonado local exitoso para {repo_name}: {len(tree)} archivos")
                except Exception as e:
                    logger.warning(f"Error con clonado local: {e}")
                    local_path = None

            # Fallback a API de GitHub si el clonado local falla
            if not local_path or not tree:
                try:
                    repo_info_response = self._make_request(api_url)
                    if repo_info_response.status_code < 400:
                        repo_info = repo_info_response.json()
                        repo_name = repo_info.get("name")
                        default_branch = repo_info.get("default_branch", "main")
                        
                        tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
                        response = self._make_request(tree_url)
                        if response.status_code < 400:
                            response.raise_for_status()
                            tree = response.json()["tree"]
                    else:
                        logger.warning(f"API de GitHub falló con código: {repo_info_response.status_code}")
                        return f"Error: No se pudo acceder al repositorio (código API: {repo_info_response.status_code}). Verifica el token de GitHub."
                except Exception as e:
                    logger.error(f"Error accediendo a repositorio vía API: {e}")
                    return f"Error al acceder al repositorio: {e}"

            if not tree:
                return f"Error: No se encontraron archivos en el repositorio"
            
            async with DBSession(SessionLocal) as db_session:
                file_count = 0
                vectorized_count = 0
                
                if self.account_id is None:
                    raise ValueError("Account ID must be provided.")

                rag_tool = DocumentRAGTool(account_id=self.account_id, workspace_id=self.workspace_id, telegram_id=self.telegram_id, thread_id=self.thread_id)

                for item in tree:
                    file_path = item['path']

                    if self._is_temporary_file(file_path):
                        continue
                    
                    if self._is_binary_file(file_path):
                        continue

                    if local_path:
                        full_local_path = os.path.join(local_path, file_path)
                        if os.path.isfile(full_local_path):
                            with open(full_local_path, "r", encoding="utf-8", errors="ignore") as f:
                                clean_content = f.read()
                            content_sha = hashlib.sha256(clean_content.encode('utf-8')).hexdigest()
                        else:
                            continue
                    else:
                        content_data = self._get_content_with_retry(f"{api_url}/contents/{file_path}")
                        if not content_data or 'content' not in content_data:
                            continue

                        content_base64 = content_data["content"]
                        encoding = content_data["encoding"]
                        
                        if encoding == "base64":
                            decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                        else:
                            decoded_content = content_base64
                        
                        clean_content = decoded_content.replace('\\x00', '')
                        content_sha = hashlib.sha256(clean_content.encode('utf-8')).hexdigest()

                    existing_doc_query = select(GitHubDocument).where(
                        GitHubDocument.repo_url == repo_url,
                        GitHubDocument.file_path == file_path,
                        GitHubDocument.account_id == self.account_id
                    )
                    existing_doc_result = await db_session.execute(existing_doc_query)
                    existing_doc = existing_doc_result.scalars().first()

                    if existing_doc:
                        if existing_doc.sha != content_sha:
                            existing_doc.content = clean_content
                            existing_doc.sha = content_sha
                            existing_doc.topic = collection_topic
                            existing_doc.updated_at = datetime.now()
                            file_count += 1
                    else:
                        github_doc = GitHubDocument(
                            repo_url=repo_url,
                            file_path=file_path,
                            sha=content_sha,
                            content=clean_content,
                            account_id=self.account_id,
                            workspace_id=self.workspace_id if self.workspace_id else None,
                            topic=collection_topic,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        db_session.add(github_doc)
                        file_count += 1
                    
                    if vectorize:
                        try:
                            repo_metadata = {
                                "repo_url": repo_url,
                                "repo_name": repo_name or "",
                                "file_extension": file_path.split('.')[-1] if '.' in file_path else '',
                                "directory": '/'.join(file_path.split('/')[:-1]) if '/' in file_path else ''
                            }
                            
                            result = await rag_tool._arun(
                                extracted_text=clean_content,
                                file_name=file_path,
                                topic=collection_topic if collection_topic else "repositorio",
                                workspace_id=self.workspace_id,
                                metadata=repo_metadata
                            )
                            
                            if "chunks added" in result.context_for_llm:
                                vectorized_count += 1
                        except Exception as vec_error:
                            logger.error(f"❌ Error vectorizando {file_path}: {vec_error}")

                return f"Repositorio {repo_name} añadido/actualizado con {file_count} archivos. {vectorized_count} archivos vectorizados correctamente."

        except Exception as e:
            logger.error(f"Error al añadir el repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al añadir el repositorio: {e}"

    async def _update_repository_documents(self, repo_url: str, account_id: str, workspace_id: Optional[str] = None, collection_topic: Optional[str] = "repositorio", vectorize: bool = False) -> str:
        """
        Actualiza los documentos de un repositorio en la base de datos.
        Usa clonado local primero, luego fallback a API de GitHub.
        """
        try:
            from core.database import SessionLocal, GitHubDocument
            from sqlalchemy import select, delete
            import base64
            from datetime import datetime
            import hashlib
            from skills.rag_skill.scripts.document_rag_tool import DocumentRAGTool
            
            if self.session is None:
                self.session = requests.Session()

            api_url = self._get_api_url(repo_url)
            repo_name = None
            default_branch = "main"
            local_path = None

            # Intentar clonado local primero
            local_path = self._ensure_local_clone(repo_url)
            if local_path:
                try:
                    repo_name = os.path.basename(local_path.rstrip('/'))
                    
                    # Construir árbol local
                    tree = []
                    for root, dirs, files in os.walk(local_path):
                        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.git']
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, local_path)
                            tree.append({"path": rel_path, "type": "blob"})
                    
                    logger.info(f"✅ Clonado local para actualización: {repo_name}")
                except Exception as e:
                    logger.warning(f"Error con clonado local: {e}")
                    local_path = None

            # Fallback a API de GitHub
            if not local_path:
                try:
                    repo_info_response = self._make_request(api_url)
                    if repo_info_response.status_code >= 400:
                        return f"Error: No se pudo acceder al repositorio (código: {repo_info_response.status_code}). Verifica el token de GitHub."
                    
                    repo_info = repo_info_response.json()
                    repo_name = repo_info.get("name")
                    default_branch = repo_info.get("default_branch", "main")
                    
                    tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
                    response = self._make_request(tree_url)
                    if response.status_code >= 400:
                        return f"Error: No se pudo obtener el árbol (código: {response.status_code})."
                    response.raise_for_status()
                    tree = response.json()["tree"]
                except Exception as e:
                    logger.error(f"Error accediendo a repositorio: {e}")
                    return f"Error al acceder al repositorio: {e}"

            if account_id is None:
                return "Error: Account ID required."

            async with DBSession(SessionLocal) as db_session:
                updated_files = 0
                new_files = 0
                deleted_files = 0

                rag_tool = DocumentRAGTool(account_id=account_id, workspace_id=workspace_id, telegram_id=self.telegram_id, thread_id=self.thread_id)

                # Obtener archivos existentes en la base de datos
                existing_github_docs_query = select(GitHubDocument).where(
                    GitHubDocument.repo_url == repo_url,
                    GitHubDocument.account_id == account_id
                )
                result = await db_session.execute(existing_github_docs_query)
                existing_db_docs = {doc.file_path: doc for doc in result.scalars().all()}

                # Obtener SHAs de GitHub (local o API)
                github_files = {}
                if local_path:
                    # Usar hashes locales
                    for item in tree:
                        if item['type'] == 'blob':
                            full_local_path = os.path.join(local_path, item['path'])
                            if os.path.isfile(full_local_path):
                                with open(full_local_path, "r", encoding="utf-8", errors="ignore") as f:
                                    content = f.read()
                                file_sha = hashlib.sha256(content.encode('utf-8')).hexdigest()
                                github_files[item['path']] = file_sha
                else:
                    # Usar API de GitHub
                    for item in tree:
                        if item['type'] == 'blob':
                            github_files[item['path']] = item.get('sha', '')

                # Eliminar archivos que ya no existen
                for file_path, db_doc in list(existing_db_docs.items()):
                    if file_path not in github_files:
                        await db_session.delete(db_doc)
                        deleted_files += 1

                # Procesar archivos
                for file_path, file_sha in github_files.items():
                    if self._is_temporary_file(file_path) or self._is_binary_file(file_path):
                        continue

                    if file_path in existing_db_docs and existing_db_docs[file_path].sha == file_sha:
                        continue

                    if local_path:
                        full_local_path = os.path.join(local_path, file_path)
                        if os.path.isfile(full_local_path):
                            with open(full_local_path, "r", encoding="utf-8", errors="ignore") as f:
                                clean_content = f.read()
                        else:
                            continue
                    else:
                        content_data = self._get_content_with_retry(f"{api_url}/contents/{file_path}")
                        if not content_data or 'content' not in content_data:
                            continue
                        decoded_content = base64.b64decode(content_data["content"]).decode("utf-8", errors="ignore")
                        clean_content = decoded_content.replace('\\x00', '')

                    if file_path in existing_db_docs:
                        db_doc = existing_db_docs[file_path]
                        db_doc.content = clean_content
                        db_doc.sha = file_sha
                        db_doc.updated_at = datetime.now()
                        updated_files += 1
                    else:
                        github_doc = GitHubDocument(
                            repo_url=repo_url,
                            file_path=file_path,
                            sha=file_sha,
                            content=clean_content,
                            account_id=account_id,
                            workspace_id=workspace_id,
                            topic=collection_topic,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        db_session.add(github_doc)
                        new_files += 1

                    if vectorize:
                        try:
                            res = await rag_tool._arun(
                                extracted_text=clean_content, 
                                file_name=file_path,
                                topic=collection_topic, 
                                workspace_id=workspace_id,
                                metadata={"repo_url": repo_url, "repo_name": repo_name}
                            )
                            if "chunks added" in res.context_for_llm:
                                pass  # Vectorizado
                        except:
                            pass

                return f"Repositorio {repo_name} actualizado. Nuevos: {new_files}, Actualizados: {updated_files}, Eliminados: {deleted_files}."
        except Exception as e:
            logger.error(f"Error actualizando documentos: {e}")
            return f"Error: {e}"

    async def _update_knowledge_collection(self, repo_url: str, collection_topic: Optional[str] = None, vectorize: bool = False) -> str:
        """
        Actualiza una colección de conocimientos.
        Usa clonado local primero, luego fallback a API de GitHub.
        """
        try:
            from core.database import SessionLocal, GitHubDocument
            from sqlalchemy import select
            import base64
            from datetime import datetime
            import hashlib
            from skills.rag_skill.scripts.document_rag_tool import DocumentRAGTool
            from core.memory_manager import remove_document_from_rag
            
            if self.session is None:
                self.session = requests.Session()
            
            api_url = self._get_api_url(repo_url)
            repo_name = None
            default_branch = "main"
            local_path = None

            # Intentar clonado local primero
            local_path = self._ensure_local_clone(repo_url)
            if local_path:
                try:
                    repo_name = os.path.basename(local_path.rstrip('/'))
                    
                    # Construir árbol local
                    tree = []
                    for root, dirs, files in os.walk(local_path):
                        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.git']
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, local_path)
                            tree.append({"path": rel_path, "type": "blob"})
                    
                    logger.info(f"✅ Clonado local para knowledge collection: {repo_name}")
                except Exception as e:
                    logger.warning(f"Error con clonado local: {e}")
                    local_path = None

            # Fallback a API de GitHub
            if not local_path:
                try:
                    repo_info_response = self._make_request(api_url)
                    if repo_info_response.status_code >= 400:
                        return f"Error: No se pudo acceder al repositorio (código: {repo_info_response.status_code}). Verifica el token de GitHub."
                    
                    repo_info = repo_info_response.json()
                    repo_name = repo_info.get("name")
                    default_branch = repo_info.get("default_branch", "main")
                    
                    tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
                    response = self._make_request(tree_url)
                    if response.status_code >= 400:
                        return f"Error: No se pudo obtener el árbol (código: {response.status_code})."
                    response.raise_for_status()
                    tree = response.json()["tree"]
                except Exception as e:
                    logger.error(f"Error accediendo a repositorio: {e}")
                    return f"Error al acceder al repositorio: {e}"

            async with DBSession(SessionLocal) as db_session:
                updated_files = 0
                new_files = 0
                deleted_files = 0
                vectorized_count = 0
                
                if self.account_id is None:
                    return "Error: Account ID required."

                rag_tool = DocumentRAGTool(account_id=self.account_id, workspace_id=self.workspace_id, telegram_id=self.telegram_id, thread_id=self.thread_id)
                
                # Obtener archivos existentes en la base de datos
                query = select(GitHubDocument).where(
                    GitHubDocument.repo_url == repo_url,
                    GitHubDocument.account_id == self.account_id,
                    GitHubDocument.topic == collection_topic
                )
                result = await db_session.execute(query)
                existing_db_docs = {doc.file_path: doc for doc in result.scalars().all()}

                # Obtener SHAs de los archivos
                github_files = {}
                if local_path:
                    for item in tree:
                        if item['type'] == 'blob':
                            full_local_path = os.path.join(local_path, item['path'])
                            if os.path.isfile(full_local_path):
                                with open(full_local_path, "r", encoding="utf-8", errors="ignore") as f:
                                    content = f.read()
                                file_sha = hashlib.sha256(content.encode('utf-8')).hexdigest()
                                github_files[item['path']] = file_sha
                else:
                    for item in tree:
                        if item['type'] == 'blob':
                            github_files[item['path']] = item.get('sha', '')

                # Eliminar archivos que ya no existen
                for file_path, db_doc in list(existing_db_docs.items()):
                    if file_path not in github_files:
                        try:
                            await remove_document_from_rag(self.account_id, file_path, collection_topic or "repositorio")
                        except:
                            pass
                        await db_session.delete(db_doc)
                        deleted_files += 1
                
                # Procesar archivos
                for file_path, file_sha in github_files.items():
                    if self._is_temporary_file(file_path) or self._is_binary_file(file_path):
                        continue

                    if file_path in existing_db_docs and existing_db_docs[file_path].sha == file_sha:
                        continue

                    if local_path:
                        full_local_path = os.path.join(local_path, file_path)
                        if os.path.isfile(full_local_path):
                            with open(full_local_path, "r", encoding="utf-8", errors="ignore") as f:
                                clean_content = f.read()
                        else:
                            continue
                    else:
                        content_data = self._get_content_with_retry(f"{api_url}/contents/{file_path}")
                        if not content_data or 'content' not in content_data:
                            continue
                        decoded_content = base64.b64decode(content_data["content"]).decode("utf-8", errors="ignore")
                        clean_content = decoded_content.replace('\\x00', '')

                    if file_path in existing_db_docs:
                        db_doc = existing_db_docs[file_path]
                        try:
                            await remove_document_from_rag(self.account_id, file_path, collection_topic or "repositorio")
                        except:
                            pass
                        db_doc.content = clean_content
                        db_doc.sha = file_sha
                        db_doc.updated_at = datetime.now()
                        updated_files += 1
                    else:
                        db_doc = GitHubDocument(
                            repo_url=repo_url, 
                            file_path=file_path, 
                            sha=file_sha, 
                            content=clean_content,
                            account_id=self.account_id, 
                            workspace_id=self.workspace_id, 
                            topic=collection_topic,
                            created_at=datetime.now(), 
                            updated_at=datetime.now()
                        )
                        db_session.add(db_doc)
                        new_files += 1
                    
                    if vectorize:
                        try:
                            res = await rag_tool._arun(
                                extracted_text=clean_content, 
                                file_name=file_path,
                                topic=collection_topic or "repositorio", 
                                workspace_id=self.workspace_id,
                                metadata={"repo_url": repo_url, "repo_name": repo_name}
                            )
                            if "chunks added" in res.context_for_llm:
                                vectorized_count += 1
                        except:
                            pass

                return f"Actualizado {repo_name}. Nuevos: {new_files}, Actualizados: {updated_files}, Eliminados: {deleted_files}. Vectorizados: {vectorized_count}."
        except Exception as e:
            logger.error(f"Error: {e}")
            return f"Error: {e}"

