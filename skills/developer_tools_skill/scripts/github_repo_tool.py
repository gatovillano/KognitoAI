# tools/github_repo_tool.py
import logging
import os
from typing import List, Any, Dict, Optional, Union, Type
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json
import hashlib

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
        logger.debug("GitHubRepoTool initialized. Version: 2025-07-24_05:00")
    
    def _run(self, repo_url: str, action: str, path: Optional[str] = None, github_token: Optional[str] = None, collection_topic: Optional[str] = None) -> Any:
        """
        Ejecuta la acción especificada en el repositorio de GitHub (síncrono).
        Devuelve ToolOutputWithSources para incluir metadatos de fuente.
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
    
    async def _arun(self, repo_url: str, action: str, path: Optional[str] = None, github_token: Optional[str] = None, collection_topic: Optional[str] = None, vectorize: Optional[bool] = False) -> str:
        """
        Ejecuta la acción especificada en el repositorio de GitHub (asíncrono).
        """
        logger.debug(f"DEBUG: _arun called with repo_url={repo_url}, action={action}")

        if not repo_url or not action:
            return "Error: 'repo_url' y 'action' son parámetros requeridos."

        if self.session is None:
            self.session = requests.Session()
        
        active_token = github_token or self.github_token or os.environ.get("GITHUB_TOKEN")
        
        if active_token:
            self.session.headers.update({'Authorization': f'Bearer {active_token.strip()}'})
            logger.info("Using GitHub token for access")
        else:
            self.session.headers.pop('Authorization', None)
            
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
            elif action == "add_as_knowledge_collection":
                result_content = await self._add_as_knowledge_collection(repo_url, collection_topic, vectorize=vectorize or False)
            elif action == "update_knowledge_collection":
                result_content = await self._update_knowledge_collection(repo_url, collection_topic, vectorize=vectorize or False)
            else:
                return f"Error: Acción no válida. Las acciones válidas son: list_tree, read_file, navigate, read_directory, read_directory_recursively, add_as_knowledge_collection, update_knowledge_collection"
            
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
            
            return ToolOutputWithSources(
                context_for_llm=str(result_content),
                sources=[source]
            )
        except Exception as e:
            logger.error(f"Error al ejecutar la acción {action} en el repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al ejecutar la acción: {e}"
    

    def _list_tree(self, repo_url: str) -> str:
        """
        Lista el árbol de archivos del repositorio.
        """
        try:
            if self.session is None:
                self.session = requests.Session()
            api_url = self._get_api_url(repo_url)
            repo_info_response = self._make_request(api_url)
            repo_info_response.raise_for_status()
            repo_info = repo_info_response.json()
            default_branch = repo_info.get("default_branch", "main")
            
            tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
            response = self._make_request(tree_url)
            response.raise_for_status()
            tree = response.json()["tree"]
            file_list = "\n".join([f"- {item['path']} ({item['type']})" for item in tree])
            return f"Árbol de archivos:\n{file_list}"
        except Exception as e:
            logger.error(f"Error al listar el árbol de archivos del repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al listar el árbol de archivos: {e}. Asegúrate de que el repositorio existe y que el token tiene los permisos necesarios."
    
    def _read_file(self, repo_url: str, file_path: str) -> str:
        """
        Lee el contenido de un archivo del repositorio.
        """
        try:
            if self.session is None:
                self.session = requests.Session()
            api_url = self._get_api_url(repo_url) + f"/contents/{file_path}"
            response = self._make_request(api_url)
            response.raise_for_status()
            content_data = response.json()
            content = content_data["content"]
            encoding = content_data["encoding"]
            if encoding == "base64":
                import base64
                decoded_content = base64.b64decode(content)
                try:
                    content = decoded_content.decode("utf-8")
                except UnicodeDecodeError:
                    content = f"[Contenido binario no decodificable en UTF-8 (tamaño: {len(decoded_content)} bytes)]"
            return f"Contenido del archivo {file_path}:\n{content}"
        except Exception as e:
            logger.error(f"Error al leer el archivo {file_path} del repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al leer el archivo: {e}"
    
    def _navigate(self, repo_url: str, path: str) -> str:
        """
        Navega a un directorio específico del repositorio y lista su contenido.
        """
        try:
            if self.session is None:
                self.session = requests.Session()
            api_url = self._get_api_url(repo_url) + f"/contents/{path}"
            response = self._make_request(api_url)
            response.raise_for_status()
            contents = response.json()
            if isinstance(contents, list):
                file_list = "\n".join([f"- {item['name']} ({item['type']})" for item in contents])
                return f"Contenido del directorio {path}:\n{file_list}"
            else:
                return f"Error: {path} no es un directorio."
        except Exception as e:
            logger.error(f"Error al navegar al directorio {path} del repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al navegar al directorio: {e}"

    def _read_directory(self, repo_url: str, path: str) -> str:
        """
        Lee el contenido de todos los archivos en un directorio específico del repositorio.
        """
        try:
            if self.session is None:
                self.session = requests.Session()
            api_url = self._get_api_url(repo_url) + f"/contents/{path}"
            response = self._make_request(api_url)
            response.raise_for_status()
            contents = response.json()
            if isinstance(contents, list):
                result = []
                for item in contents:
                    if item['type'] == 'file':
                        file_content = self._read_file(repo_url, item['path'])
                        result.append(f"Archivo: {item['path']}\n{file_content}\n{'-'*50}")
                return "\n".join(result) if result else f"No se encontraron archivos en el directorio {path}."
            else:
                return f"Error: {path} no es un directorio."
        except Exception as e:
            logger.error(f"Error al leer el directorio {path} del repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al leer el directorio: {e}"

    def _read_directory_recursively(self, repo_url: str, directory_path: str) -> str:
        """
        Lee el contenido de todos los archivos en un directorio específico del repositorio, incluyendo subdirectorios.
        """
        try:
            if self.session is None:
                self.session = requests.Session()
            
            api_url = self._get_api_url(repo_url)
            repo_info_response = self._make_request(api_url)
            repo_info_response.raise_for_status()
            repo_info = repo_info_response.json()
            default_branch = repo_info.get("default_branch", "main")
            
            tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
            response = self._make_request(tree_url)
            response.raise_for_status()
            tree = response.json()["tree"]

            result = []
            
            prefix = directory_path.strip('/') if directory_path else ''
            if prefix:
                prefix += '/'

            for item in tree:
                if item['type'] == 'blob' and item['path'].startswith(prefix):
                    file_content = self._read_file(repo_url, item['path'])
                    result.append(f"Archivo: {item['path']}\n{file_content}\n{'-'*50}")
            
            return "\n".join(result) if result else f"No se encontraron archivos en el directorio '{directory_path}' o sus subdirectorios."
        except Exception as e:
            logger.error(f"Error al leer recursivamente el directorio {directory_path} del repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al leer recursivamente el directorio: {e}"


    async def _add_as_knowledge_collection(self, repo_url: str, collection_topic: Optional[str] = None, vectorize: bool = False) -> str:
        """
        Añade un repositorio de GitHub como colección de conocimientos.
        """
        try:
            from core.database import SessionLocal, GitHubDocument
            from sqlalchemy import select
            import uuid
            import base64
            from datetime import datetime
            import hashlib
            from skills.rag_skill.scripts.document_rag_tool import DocumentRAGTool
            
            if self.session is None:
                self.session = requests.Session()
            
            api_url = self._get_api_url(repo_url)
            repo_info_response = self._make_request(api_url)
            repo_info_response.raise_for_status()
            repo_info = repo_info_response.json()
            default_branch = repo_info.get("default_branch", "main")
            repo_name = repo_info["name"]
            
            tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
            response = self._make_request(tree_url)
            response.raise_for_status()
            tree = response.json()["tree"]
            
            async with DBSession(SessionLocal) as db_session:
                file_count = 0
                vectorized_count = 0
                
                if self.account_id is None:
                    raise ValueError("Account ID must be provided.")

                rag_tool = DocumentRAGTool(account_id=self.account_id, workspace_id=self.workspace_id, telegram_id=self.telegram_id, thread_id=self.thread_id)

                for item in tree:
                    if item['type'] == 'blob':
                        file_path = item['path']

                        if self._is_temporary_file(file_path):
                            continue
                        
                        if self._is_binary_file(file_path):
                            continue

                        content_data = self._get_content_with_retry(f"{api_url}/contents/{file_path}")
                        if not content_data or 'content' not in content_data:
                            continue

                        content_base64 = content_data["content"]
                        encoding = content_data["encoding"]
                        
                        if encoding == "base64":
                            decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                        else:
                            decoded_content = content_base64
                        
                        clean_content = decoded_content.replace('\x00', '')
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
                                    "repo_name": repo_name,
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
        """
        try:
            from core.database import SessionLocal, GitHubDocument
            from sqlalchemy import select, delete
            import base64
            from datetime import datetime
            
            if self.session is None:
                self.session = requests.Session()

            api_url = self._get_api_url(repo_url)
            repo_info_response = self._make_request(api_url)
            repo_info_response.raise_for_status()
            repo_name = repo_info_response.json()["name"]
            default_branch = repo_info_response.json().get("default_branch", "main")

            async with DBSession(SessionLocal) as db_session:
                updated_files = 0
                new_files = 0
                deleted_files = 0

                if account_id is None:
                    return "Error: Account ID required."

                tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
                response = self._make_request(tree_url)
                response.raise_for_status()
                github_tree = response.json()["tree"]
                github_files = {item['path']: item['sha'] for item in github_tree if item['type'] == 'blob'}

                existing_github_docs_query = select(GitHubDocument).where(
                    GitHubDocument.repo_url == repo_url,
                    GitHubDocument.account_id == account_id
                )
                result = await db_session.execute(existing_github_docs_query)
                existing_db_docs = {doc.file_path: doc for doc in result.scalars().all()}
                
                for file_path, db_doc in existing_db_docs.items():
                    if file_path not in github_files:
                        await db_session.delete(db_doc)
                        deleted_files += 1

                for file_path, github_sha in github_files.items():
                    if self._is_temporary_file(file_path) or self._is_binary_file(file_path):
                        continue

                    content_data = self._get_content_with_retry(f"{api_url}/contents/{file_path}")
                    if not content_data or 'content' not in content_data:
                        continue

                    decoded_content = base64.b64decode(content_data["content"]).decode("utf-8", errors="ignore")
                    clean_content = decoded_content.replace('\x00', '')

                    if file_path in existing_db_docs:
                        db_doc = existing_db_docs[file_path]
                        if db_doc.sha != github_sha:
                            db_doc.content = clean_content
                            db_doc.sha = github_sha
                            db_doc.updated_at = datetime.now()
                            updated_files += 1
                    else:
                        github_doc = GitHubDocument(
                            repo_url=repo_url,
                            file_path=file_path,
                            sha=github_sha,
                            content=clean_content,
                            account_id=account_id,
                            workspace_id=workspace_id,
                            topic=collection_topic,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        db_session.add(github_doc)
                        new_files += 1

                return f"Repositorio {repo_name} actualizado. Nuevos: {new_files}, Actualizados: {updated_files}, Eliminados: {deleted_files}."
        except Exception as e:
            logger.error(f"Error actualizando documentos: {e}")
            return f"Error: {e}"

    async def _update_knowledge_collection(self, repo_url: str, collection_topic: Optional[str] = None, vectorize: bool = False) -> str:
        """
        Actualiza una colección de conocimientos.
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
            repo_info_response = self._make_request(api_url)
            repo_info_response.raise_for_status()
            repo_info = repo_info_response.json()
            repo_name = repo_info["name"]
            default_branch = repo_info.get("default_branch", "main")
            
            async with DBSession(SessionLocal) as db_session:
                updated_files = 0
                new_files = 0
                deleted_files = 0
                vectorized_count = 0
                
                if self.account_id is None:
                    return "Error: Account ID required."

                rag_tool = DocumentRAGTool(account_id=self.account_id, workspace_id=self.workspace_id, telegram_id=self.telegram_id, thread_id=self.thread_id)
                
                response = self._make_request(f"{api_url}/git/trees/{default_branch}?recursive=1")
                response.raise_for_status()
                github_files = {item['path']: item['sha'] for item in response.json()["tree"] if item['type'] == 'blob'}
                
                query = select(GitHubDocument).where(
                    GitHubDocument.repo_url == repo_url,
                    GitHubDocument.account_id == self.account_id,
                    GitHubDocument.topic == collection_topic
                )
                result = await db_session.execute(query)
                existing_db_docs = {doc.file_path: doc for doc in result.scalars().all()}

                for file_path, db_doc in existing_db_docs.items():
                    if file_path not in github_files:
                        try:
                            await remove_document_from_rag(self.account_id, file_path, collection_topic or "repositorio")
                        except: pass
                        await db_session.delete(db_doc)
                        deleted_files += 1
                
                for file_path, github_sha in github_files.items():
                    if self._is_temporary_file(file_path) or self._is_binary_file(file_path):
                        continue

                    if file_path in existing_db_docs and existing_db_docs[file_path].sha == github_sha:
                        continue

                    content_data = self._get_content_with_retry(f"{api_url}/contents/{file_path}")
                    if not content_data or 'content' not in content_data:
                        continue

                    decoded_content = base64.b64decode(content_data["content"]).decode("utf-8", errors="ignore")
                    clean_content = decoded_content.replace('\x00', '')
                    
                    if file_path in existing_db_docs:
                        db_doc = existing_db_docs[file_path]
                        try:
                            await remove_document_from_rag(self.account_id, file_path, collection_topic or "repositorio")
                        except: pass
                        db_doc.content = clean_content
                        db_doc.sha = github_sha
                        db_doc.updated_at = datetime.now()
                        updated_files += 1
                    else:
                        db_doc = GitHubDocument(
                            repo_url=repo_url, file_path=file_path, sha=github_sha, content=clean_content,
                            account_id=self.account_id, workspace_id=self.workspace_id, topic=collection_topic,
                            created_at=datetime.now(), updated_at=datetime.now()
                        )
                        db_session.add(db_doc)
                        new_files += 1
                    
                    if vectorize:
                        try:
                            res = await rag_tool._arun(
                                extracted_text=clean_content, file_name=file_path,
                                topic=collection_topic or "repositorio", workspace_id=self.workspace_id,
                                metadata={"repo_url": repo_url, "repo_name": repo_name}
                            )
                            if "chunks added" in res.context_for_llm: vectorized_count += 1
                        except: pass

                return f"Actualizado {repo_name}. Nuevos: {new_files}, Actualizados: {updated_files}, Eliminados: {deleted_files}. Vectorizados: {vectorized_count}."
        except Exception as e:
            logger.error(f"Error: {e}")
            return f"Error: {e}"

    def _is_temporary_file(self, file_path: str) -> bool:
        import os
        file_name = os.path.basename(file_path)
        temp_patterns = [
            file_name.startswith('.~lock.'),
            file_name.startswith('~$'),
            file_name.endswith(('.tmp', '.temp', '.bak', '.swp', '.swo')),
            file_name.startswith('._'),
            file_name.startswith('auto-save'),
            file_name.startswith('#') and file_name.endswith('#'),
            file_name.lower().startswith('temp'),
        ]
        return any(temp_patterns)

    def _is_binary_file(self, file_path: str) -> bool:
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg', '.webp',
            '.pdf', '.epub', '.mobi',
            '.zip', '.tar', '.gz', '.7z', '.rar', '.xz',
            '.exe', '.dll', '.so', '.dylib', '.bin',
            '.mp3', '.mp4', '.mkv', '.avi', '.mov', '.flv',
            '.ttf', '.otf', '.woff', '.woff2',
            '.pyc', '.pyo', '.db', '.sqlite', '.class', '.node'
        }
        _, ext = os.path.splitext(file_path.lower())
        return ext in binary_extensions

    def _make_request(self, url: str) -> requests.Response:
        """
        Realiza una petición GET a la API de GitHub. Si devuelve 401 y hay un token,
        reintenta la petición sin el token para permitir el acceso a repositorios públicos.
        """
        if self.session is None:
            self.session = requests.Session()
            
        auth_header = self.session.headers.get('Authorization', 'None')
        logger.debug(f"Making request to {url} with auth: {auth_header[:15]}...")
        
        response = self.session.get(url)
        
        # Any 401 could mean an invalid token was passed, either in headers or env.
        if response.status_code == 401:
            logger.warning(f"401 Unauthorized for {url}. Retrying explicitly without any token...")
            if 'Authorization' in self.session.headers:
                self.session.headers.pop('Authorization', None)
            
            # Explicitly force an unauthenticated request by bypassing the session's auth entirely
            # We use a raw requests.get without the Authorization header.
            headers_without_auth = {k: v for k, v in self.session.headers.items() if k.lower() != 'authorization'}
            response = requests.get(url, headers=headers_without_auth)
            logger.info(f"Retry status for {url} (forced non-auth): {response.status_code}")
        
        return response

    def _get_content_with_retry(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el contenido de un archivo usando _make_request (con reintento por 401)
        y manejo de 403 para archivos binarios o rate limit.
        """
        try:
            response = self._make_request(url)
            if response.status_code >= 400:
                logger.warning(f"Error {response.status_code} accessing {url}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Exception fetching {url}: {e}")
            return None

    def _get_api_url(self, repo_url: str) -> str:
        parsed_url = urlparse(repo_url)
        path_segments = parsed_url.path.strip("/").split("/")
        if len(path_segments) != 2:
            raise ValueError("Invalid GitHub repository URL")
        username, repo_name = path_segments
        return f"https://api.github.com/repos/{username}/{repo_name}"