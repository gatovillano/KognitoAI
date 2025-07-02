# tools/github_repo_tool.py
import logging
import os
from typing import List, Any, Dict, Optional
import requests
from bs4 import BeautifulSoup
import urllib3
from urllib.parse import urlparse, urljoin
import json
import hashlib # Importar hashlib para calcular SHA

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class GitHubRepoTool(BaseTool):
    name: str = "github_repository_explorer"
    description: str = (
        "Este tool permite explorar repositorios de GitHub y gestionarlos como colecciones de conocimientos. Debes proporcionar la URL del repositorio en el parámetro 'repo_url', la acción a realizar (list_tree, read_file, navigate, read_directory, read_directory_recursively, add_as_knowledge_collection, update_knowledge_collection) en el parámetro 'action', y, opcionalmente, la ruta al archivo o directorio en el parámetro 'path', el token de GitHub en el parámetro 'github_token', el ID del workspace en 'workspace_id' y el ID de la cuenta en 'account_id' si es necesario. Asegúrate de proporcionar la URL completa del repositorio y de utilizar los nombres de parámetro y acción correctos."
    )
    github_token: Optional[str] = Field(
        None,
        description="El token de GitHub a utilizar para acceder a repositorios privados. Si no se proporciona, se utilizará la variable de entorno GITHUB_TOKEN."
    )
    session: Optional[requests.Session] = Field(
        default_factory=requests.Session,
        description="La sesión HTTP a utilizar para realizar las solicitudes."
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.session = requests.Session()
        self.github_token = kwargs.get("github_token") or os.environ.get("GITHUB_TOKEN")
        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
        logger.debug("GitHubRepoTool initialized.")
    
    def _run(self, repo_url: str, action: str, path: Optional[str] = None, github_token: Optional[str] = None, collection_topic: Optional[str] = None, account_id: Optional[str] = None) -> str:
        """
        Ejecuta la acción especificada en el repositorio de GitHub.
        Esta es la versión síncrona y no debe usar await.
        """
        if self.session is None:
            self.session = requests.Session()
        self.github_token = github_token or self.github_token or os.environ.get("GITHUB_TOKEN")
        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
            logger.info("Using github_token to access repo")
        try:
            if action == "list_tree":
                return self._list_tree(repo_url)
            elif action == "read_file":
                if not path:
                    return "Error: Debes especificar la ruta del archivo para leer."
                return self._read_file(repo_url, path)
            elif action == "navigate":
                if not path:
                    return "Error: Debes especificar la ruta para navegar."
                return self._navigate(repo_url, path)
            elif action == "read_directory":
                if not path:
                    return "Error: Debes especificar la ruta del directorio para leer los documentos."
                return self._read_directory(repo_url, path)
            elif action == "read_directory_recursively":
                return self._read_directory_recursively(repo_url, path or "")
            elif action == "add_as_knowledge_collection":
                # No se puede llamar a una función async desde una sync directamente sin un loop de eventos.
                # Esto se manejará en _arun.
                return "Error: La acción 'add_as_knowledge_collection' solo puede ser ejecutada de forma asíncrona."
            elif action == "update_knowledge_collection":
                # No se puede llamar a una función async desde una sync directamente sin un loop de eventos.
                # Esto se manejará en _arun.
                return "Error: La acción 'update_knowledge_collection' solo puede ser ejecutada de forma asíncrona."
            else:
                return f"Error: Acción no válida. Las acciones válidas son: list_tree, read_file, navigate, read_directory, read_directory_recursively, add_as_knowledge_collection, update_knowledge_collection"
        except Exception as e:
            logger.error(f"Error al ejecutar la acción {action} en el repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al ejecutar la acción: {e}"
    
    async def _arun(self, repo_url: str, action: str, path: Optional[str] = None, github_token: Optional[str] = None, collection_topic: Optional[str] = None, account_id: Optional[str] = None) -> str:
        """
        Ejecuta la acción especificada en el repositorio de GitHub (asíncrono).
        """
        if self.session is None:
            self.session = requests.Session()
        self.github_token = github_token or self.github_token or os.environ.get("GITHUB_TOKEN")
        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
            logger.info("Using github_token to access repo")
        try:
            if action == "list_tree":
                return self._list_tree(repo_url)
            elif action == "read_file":
                if not path:
                    return "Error: Debes especificar la ruta del archivo para leer."
                return self._read_file(repo_url, path)
            elif action == "navigate":
                if not path:
                    return "Error: Debes especificar la ruta para navegar."
                return self._navigate(repo_url, path)
            elif action == "read_directory":
                if not path:
                    return "Error: Debes especificar la ruta del directorio para leer los documentos."
                return self._read_directory(repo_url, path)
            elif action == "read_directory_recursively":
                return self._read_directory_recursively(repo_url, path or "")
            elif action == "add_as_knowledge_collection":
                return await self._add_as_knowledge_collection(repo_url, collection_topic, account_id)
            elif action == "update_knowledge_collection":
                return await self._update_knowledge_collection(repo_url, collection_topic, account_id)
            else:
                return f"Error: Acción no válida. Las acciones válidas son: list_tree, read_file, navigate, read_directory, read_directory_recursively, add_as_knowledge_collection, update_knowledge_collection"
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
            # First, get the default branch
            api_url = self._get_api_url(repo_url)
            repo_info_response = self.session.get(api_url)
            repo_info_response.raise_for_status()
            default_branch = repo_info_response.json().get("default_branch", "main")
            
            # Now, get the tree for the default branch
            tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
            response = self.session.get(tree_url)
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
            response = self.session.get(api_url)
            response.raise_for_status()
            content = response.json()["content"]
            encoding = response.json()["encoding"]
            if encoding == "base64":
                import base64
                content = base64.b64decode(content).decode("utf-8")
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
            response = self.session.get(api_url)
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
            response = self.session.get(api_url)
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
            repo_info_response = self.session.get(api_url)
            repo_info_response.raise_for_status()
            default_branch = repo_info_response.json().get("default_branch", "main")
            
            tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
            response = self.session.get(tree_url)
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

    async def _add_as_knowledge_collection(self, repo_url: str, collection_topic: Optional[str] = None, account_id: Optional[str] = None) -> str:
        """
        Añade un repositorio de GitHub como colección de conocimientos, ya sea en una colección RAG específica o como conocimiento general de una cuenta.
        """
        try:
            from core.database import SessionLocal, LangchainPgCollection, WorkspaceCollectionAssociation, GitHubDocument
            from sqlalchemy import select
            import uuid
            import base64
            from datetime import datetime
            
            if self.session is None:
                self.session = requests.Session()
            
            # Obtener información del repositorio
            api_url = self._get_api_url(repo_url)
            repo_info_response = self.session.get(api_url)
            repo_info_response.raise_for_status()
            repo_info = repo_info_response.json()
            default_branch = repo_info.get("default_branch", "main")
            repo_name = repo_info["name"]
            
            # Obtener el árbol del repositorio
            tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
            response = self.session.get(tree_url)
            response.raise_for_status()
            tree = response.json()["tree"]
            
            # Conectar a la base de datos
            db_session = SessionLocal()
            try:
                file_count = 0
                if collection_topic:
                    # Añadir a una colección RAG existente
                    collection_query = select(LangchainPgCollection).where(LangchainPgCollection.name == collection_topic)
                    result = await db_session.execute(collection_query)
                    existing_collection = result.scalars().first()

                    if not existing_collection:
                        return f"Error: No se encontró la colección RAG con el tema '{collection_topic}'."

                    # Añadir documentos de GitHub a la tabla github_documents
                    for item in tree:
                        if item['type'] == 'blob':
                            file_path = item['path']
                            content_response = self.session.get(f"{api_url}/contents/{file_path}")
                            content_response.raise_for_status()
                            content_data = content_response.json()
                            content_base64 = content_data["content"]
                            encoding = content_data["encoding"]
                            
                            if encoding == "base64":
                                decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                            else:
                                decoded_content = content_base64 # Si no es base64, usar directamente
                            
                            # Calcular SHA del contenido
                            content_sha = hashlib.sha256(decoded_content.encode('utf-8')).hexdigest()
                            
                            github_doc = GitHubDocument(
                                repo_url=repo_url,
                                file_path=file_path,
                                sha=content_sha,
                                content=decoded_content,
                                account_id=account_id,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            db_session.add(github_doc)
                            file_count += 1
                    
                    await db_session.commit()
                    return f"Repositorio {repo_name} añadido a la colección '{collection_topic}' con {file_count} archivos."
                elif account_id:
                    # Añadir como conocimiento general de la cuenta
                    for item in tree:
                        if item['type'] == 'blob':
                            file_path = item['path']
                            content_response = self.session.get(f"{api_url}/contents/{file_path}")
                            content_response.raise_for_status()
                            content_data = content_response.json()
                            content_base64 = content_data["content"]
                            encoding = content_data["encoding"]
                            
                            if encoding == "base64":
                                decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                            else:
                                decoded_content = content_base64
                            
                            # Calcular SHA del contenido
                            content_sha = hashlib.sha256(decoded_content.encode('utf-8')).hexdigest()
                            
                            github_doc = GitHubDocument(
                                repo_url=repo_url,
                                file_path=file_path,
                                sha=content_sha,
                                content=decoded_content,
                                account_id=account_id,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            db_session.add(github_doc)
                            file_count += 1
                    
                    db_session.commit()
                    return f"Repositorio {repo_name} añadido como conocimiento general de la cuenta {account_id} con {file_count} archivos."
                else:
                    return "Error: Debes especificar un ID de workspace o un ID de cuenta para añadir la colección de conocimientos."
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error al añadir el repositorio {repo_url} como colección de conocimientos: {e}", exc_info=True)
            return f"Error al añadir el repositorio como colección de conocimientos: {e}"

    async def _update_knowledge_collection(self, repo_url: str, collection_topic: Optional[str] = None, account_id: Optional[str] = None) -> str:
        """
        Actualiza una colección de conocimientos existente desde un repositorio de GitHub, ya sea en una colección RAG específica o como conocimiento general de una cuenta.
        """
        try:
            from core.database import SessionLocal, GitHubDocument, LangchainPgCollection, WorkspaceCollectionAssociation
            from sqlalchemy import select, delete
            import uuid
            import base64
            from datetime import datetime
            import hashlib
            
            if self.session is None:
                self.session = requests.Session()
            
            # Obtener información del repositorio
            api_url = self._get_api_url(repo_url)
            repo_info_response = self.session.get(api_url)
            repo_info_response.raise_for_status()
            repo_info = repo_info_response.json()
            repo_name = repo_info["name"]
            default_branch = repo_info.get("default_branch", "main")
            
            # Conectar a la base de datos
            db_session = SessionLocal()
            try:
                updated_files = 0
                new_files = 0
                deleted_files = 0
                
                if collection_topic:
                    # Actualizar colección RAG existente
                    collection_query = select(LangchainPgCollection).where(LangchainPgCollection.name == collection_topic)
                    result = await db_session.execute(collection_query)
                    existing_collection = result.scalars().first()

                    if not existing_collection:
                        return f"Error: No se encontró la colección RAG con el tema '{collection_topic}'."

                    # Obtener el árbol actual del repositorio de GitHub
                    tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
                    response = self.session.get(tree_url)
                    response.raise_for_status()
                    github_tree = response.json()["tree"]
                    
                    # Mapear archivos de GitHub por path y SHA
                    github_files = {item['path']: item['sha'] for item in github_tree if item['type'] == 'blob'}
                    
                    # Obtener los documentos de GitHub existentes en la base de datos para este repositorio y colección
                    existing_github_docs_query = select(GitHubDocument).where(
                        GitHubDocument.repo_url == repo_url,
                        GitHubDocument.account_id == account_id
                    )
                    result = await db_session.execute(existing_github_docs_query)
                    existing_db_docs = {doc.file_path: doc for doc in result.scalars().all()}
                    
                    # 1. Eliminar archivos que ya no existen en GitHub
                    for file_path, db_doc in existing_db_docs.items():
                        if file_path not in github_files:
                            await db_session.delete(db_doc)
                            deleted_files += 1
                    
                    # 2. Añadir nuevos archivos o actualizar modificados
                    for file_path, github_sha in github_files.items():
                        if file_path in existing_db_docs:
                            db_doc = existing_db_docs[file_path]
                            if db_doc.sha != github_sha:
                                # Contenido modificado, actualizar
                                content_response = self.session.get(f"{api_url}/contents/{file_path}")
                                content_response.raise_for_status()
                                content_data = content_response.json()
                                content_base64 = content_data["content"]
                                encoding = content_data["encoding"]
                                
                                if encoding == "base64":
                                    decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                                else:
                                    decoded_content = content_base64
                                
                                db_doc.content = decoded_content
                                db_doc.sha = github_sha
                                db_doc.updated_at = datetime.now()
                                updated_files += 1
                        else:
                            # Nuevo archivo, añadir
                            content_response = self.session.get(f"{api_url}/contents/{file_path}")
                            content_response.raise_for_status()
                            content_data = content_response.json()
                            content_base64 = content_data["content"]
                            encoding = content_data["encoding"]
                            
                            if encoding == "base64":
                                decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                            else:
                                decoded_content = content_base64
                            
                            github_doc = GitHubDocument(
                                repo_url=repo_url,
                                file_path=file_path,
                                sha=github_sha,
                                content=decoded_content,
                                account_id=account_id,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            db_session.add(github_doc)
                            new_files += 1
                    
                    await db_session.commit()
                    return f"Colección '{collection_topic}' actualizada desde {repo_name}. Archivos nuevos: {new_files}, Archivos actualizados: {updated_files}, Archivos eliminados: {deleted_files}."
                
                elif account_id:
                    # Actualizar conocimiento general de la cuenta
                    # Obtener el árbol actual del repositorio de GitHub
                    tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
                    response = self.session.get(tree_url)
                    response.raise_for_status()
                    github_tree = response.json()["tree"]
                    
                    # Mapear archivos de GitHub por path y SHA
                    github_files = {item['path']: item['sha'] for item in github_tree if item['type'] == 'blob'}
                    
                    # Obtener los documentos de GitHub existentes en la base de datos para este repositorio y cuenta
                    existing_github_docs_query = select(GitHubDocument).where(
                        GitHubDocument.repo_url == repo_url,
                        GitHubDocument.account_id == account_id
                    )
                    result = db_session.execute(existing_github_docs_query)
                    existing_db_docs = {doc.file_path: doc for doc in result.scalars().all()}
                    
                    # 1. Eliminar archivos que ya no existen en GitHub
                    for file_path, db_doc in existing_db_docs.items():
                        if file_path not in github_files:
                            await db_session.delete(db_doc)
                            deleted_files += 1
                    
                    # 2. Añadir nuevos archivos o actualizar modificados
                    for file_path, github_sha in github_files.items():
                        if file_path in existing_db_docs:
                            db_doc = existing_db_docs[file_path]
                            if db_doc.sha != github_sha:
                                # Contenido modificado, actualizar
                                content_response = self.session.get(f"{api_url}/contents/{file_path}")
                                content_response.raise_for_status()
                                content_data = content_response.json()
                                content_base64 = content_data["content"]
                                encoding = content_data["encoding"]
                                
                                if encoding == "base64":
                                    decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                                else:
                                    decoded_content = content_base64
                                
                                db_doc.content = decoded_content
                                db_doc.sha = github_sha
                                db_doc.updated_at = datetime.now()
                                updated_files += 1
                        else:
                            # Nuevo archivo, añadir
                            content_response = self.session.get(f"{api_url}/contents/{file_path}")
                            content_response.raise_for_status()
                            content_data = content_response.json()
                            content_base64 = content_data["content"]
                            encoding = content_data["encoding"]
                            
                            if encoding == "base64":
                                decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                            else:
                                decoded_content = content_base64
                            
                            github_doc = GitHubDocument(
                                repo_url=repo_url,
                                file_path=file_path,
                                sha=github_sha,
                                content=decoded_content,
                                account_id=account_id,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            db_session.add(github_doc)
                            new_files += 1
                    
                    db_session.commit()
                    return f"Colección de conocimientos para {repo_name} como conocimiento general de la cuenta {account_id} actualizada. Archivos nuevos: {new_files}, Archivos actualizados: {updated_files}, Archivos eliminados: {deleted_files}."
                else:
                    return "Error: Debes especificar un ID de workspace o un ID de cuenta para actualizar la colección de conocimientos."
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error al actualizar la colección de conocimientos para el repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al actualizar la colección de conocimientos: {e}"
    
    def _get_api_url(self, repo_url: str) -> str:
        """
        Convierte la URL del repositorio a la URL de la API de GitHub.
        """
        parsed_url = urlparse(repo_url)
        path_segments = parsed_url.path.strip("/").split("/")
        if len(path_segments) != 2:
            raise ValueError("Invalid GitHub repository URL")
        username, repo_name = path_segments
        return f"https://api.github.com/repos/{username}/{repo_name}"

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
    account_id: Optional[str] = Field(
        None,
        description="ID de la cuenta a la que se asociará la colección de conocimientos general. Requerido si no se proporciona un collection_topic para las acciones 'add_as_knowledge_collection' y 'update_knowledge_collection'."
    )

# Asignar el esquema de entrada a la herramienta
GitHubRepoTool.args_schema = GitHubRepoInput

# Nota: Esta herramienta debe ser instanciada en la función get_all_langchain_tools() en telegram_client/tools.py
