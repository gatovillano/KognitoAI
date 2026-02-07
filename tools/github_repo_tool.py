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
        self.github_token = kwargs.get("github_token") or os.environ.get("GITHUB_TOKEN")
        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
        logger.debug("GitHubRepoTool initialized. Version: 2025-07-24_04:42") # Añadir log de versión
    
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
            # Las acciones de knowledge collection suelen ser async, pero si se llaman desde sync, 
            # tendríamos que usar asyncio.run() o advertir. Por simplicidad devolvemos mensaje de error o intentamos una versión sync si existiera (no existe).
            elif action in ["add_as_knowledge_collection", "update_knowledge_collection"]:
                 return "Error: Las acciones de knowledge collection solo están disponibles en modo asíncrono."
            else:
                return f"Error: Acción no válida. Las acciones válidas son: list_tree, read_file, navigate, read_directory, read_directory_recursively"
            
            # Construir la fuente
            full_url = repo_url
            if path:
                if action == "read_file":
                    branch = "main"
                    full_url = f"{repo_url}/blob/{branch}/{path}"
                elif action in ["navigate", "read_directory", "read_directory_recursively"]:
                    branch = "main"
                    full_url = f"{repo_url}/tree/{branch}/{path}"
            
            source = create_github_source(
                file_path=path if path else repo_url,
                repo_url=full_url,
                content=str(result_content),
                node_id=None
            )
            source.title = f"{path} ({action})" if path else f"Repo: {repo_url}"
            source.snippet = f"Result of {action}: " + (str(result_content)[:200] + "..." if len(str(result_content)) > 200 else str(result_content))
            
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
        self.github_token = github_token or self.github_token or os.environ.get("GITHUB_TOKEN")
        if self.github_token:
            self.session.headers.update({'Authorization': f'Bearer {self.github_token}'})
            logger.info("Using github_token to access repo")
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
                # Este método ya devuelve un string descriptivo, lo tratamos igual
                result_content = await self._add_as_knowledge_collection(repo_url, collection_topic, vectorize=vectorize or False)
            elif action == "update_knowledge_collection":
                result_content = await self._update_knowledge_collection(repo_url, collection_topic, vectorize=vectorize or False)
            else:
                return f"Error: Acción no válida. Las acciones válidas son: list_tree, read_file, navigate, read_directory, read_directory_recursively, add_as_knowledge_collection, update_knowledge_collection"
            
            # Construir la fuente
            full_url = repo_url
            if path:
                # Construir URL web visible (blob para archivos, tree para directorios)
                if action == "read_file":
                    # Intentar inferir si es main o master
                    branch = "main" # Por defecto
                    full_url = f"{repo_url}/blob/{branch}/{path}"
                elif action in ["navigate", "read_directory", "read_directory_recursively"]:
                    branch = "main"
                    full_url = f"{repo_url}/tree/{branch}/{path}"
            
            # Crear objeto Source explícito
            source = create_github_source(
                file_path=path if path else repo_url,
                repo_url=full_url,
                content=str(result_content), # Asegurar string
                node_id=None
            )
            # Personalizar título y snippet
            source.title = f"{path} ({action})" if path else f"Repo: {repo_url}"
            source.snippet = f"Result of {action}: " + (str(result_content)[:200] + "..." if len(str(result_content)) > 200 else str(result_content))
            
            # Devolver objeto enriquecido
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
            # First, get the default branch
            api_url = self._get_api_url(repo_url)
            repo_info_response = self.session.get(api_url)
            repo_info_response.raise_for_status()
            repo_info = repo_info_response.json()
            default_branch = repo_info.get("default_branch", "main")
            
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
                decoded_content = base64.b64decode(content)
                try:
                    content = decoded_content.decode("utf-8")
                except UnicodeDecodeError:
                    # Si falla la decodificación, es un archivo binario.
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
            repo_info = repo_info_response.json()
            default_branch = repo_info.get("default_branch", "main")
            
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



    async def _add_as_knowledge_collection(self, repo_url: str, collection_topic: Optional[str] = None, vectorize: bool = False) -> str:
        """
        Añade un repositorio de GitHub como colección de conocimientos, ya sea en una colección RAG específica o como conocimiento general de una cuenta.
        Controla la vectorización con el parámetro 'vectorize'.
        """
        try:
            from core.database import SessionLocal, GitHubDocument
            from sqlalchemy import select
            import uuid
            import base64
            from datetime import datetime
            import hashlib
            from tools.document_rag_tool import DocumentRAGTool
            
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
            async with DBSession(SessionLocal) as db_session:
                file_count = 0
                vectorized_count = 0
                
                if self.account_id is None:
                    raise ValueError("Account ID must be provided.")

                logger.info(f"DEBUG: _add_as_knowledge_collection - account_id: {self.account_id}, collection_topic: {collection_topic}, vectorize: {vectorize}")
                rag_tool = DocumentRAGTool(account_id=self.account_id, workspace_id=self.workspace_id, telegram_id=self.telegram_id, thread_id=self.thread_id)

                for item in tree:
                    if item['type'] == 'blob':
                        file_path = item['path']

                        # Omitir archivos temporales
                        if self._is_temporary_file(file_path):
                            logger.info(f"⏩ Omitiendo archivo temporal: {file_path}")
                            continue

                        # Check if document already exists
                        existing_doc_query = select(GitHubDocument).where(
                            GitHubDocument.repo_url == repo_url,
                            GitHubDocument.file_path == file_path,
                            GitHubDocument.account_id == self.account_id
                        )
                        existing_doc_result = await db_session.execute(existing_doc_query)
                        existing_doc = existing_doc_result.scalars().first()

                        content_response = self.session.get(f"{api_url}/contents/{file_path}")
                        content_response.raise_for_status()
                        content_data = content_response.json()

                        # Omitir enlaces simbólicos ya que no tienen contenido directo
                        if content_data.get('type') == 'symlink':
                            logger.info(f"⏩ Omitiendo enlace simbólico: {file_path}")
                            continue

                        content_base64 = content_data["content"]
                        encoding = content_data["encoding"]
                        
                        if encoding == "base64":
                            decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                        else:
                            decoded_content = content_base64
                        
                        # Eliminar caracteres nulos
                        clean_content = decoded_content.replace('\x00', '')

                        content_sha = hashlib.sha256(clean_content.encode('utf-8')).hexdigest()

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
                                content=clean_content, # Guardar contenido limpio
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
                                    extracted_text=clean_content, # Vectorizar contenido limpio
                                    file_name=file_path,
                                    topic=collection_topic if collection_topic else "repositorio",
                                    workspace_id=self.workspace_id,
                                    metadata=repo_metadata
                                )
                                
                                if "chunks added" in result.context_for_llm:
                                    vectorized_count += 1
                                    logger.info(f"✅ Archivo {file_path} vectorizado correctamente")
                                else:
                                    logger.warning(f"⚠️ Archivo {file_path} no se vectorizó: {result.context_for_llm}")
                                    
                            except Exception as vec_error:
                                logger.error(f"❌ Error vectorizando {file_path}: {vec_error}", exc_info=True)
                        else:
                            logger.info(f"⏩ Archivo {file_path} no vectorizado (vectorize=False).")
                
                logger.info(f"DEBUG: Antes del commit en _add_as_knowledge_collection. Archivos a añadir/actualizar: {file_count}")
                # Commit is handled by DBSession context manager if no exception
                logger.info(f"DEBUG: Después del commit en _add_as_knowledge_collection.")
                return f"Repositorio {repo_name} añadido/actualizado con {file_count} archivos. {vectorized_count} archivos vectorizados correctamente para la cuenta {self.account_id} con tema '{collection_topic if collection_topic else 'repositorio'}'."

        except Exception as e:
            logger.error(f"Error al añadir el repositorio {repo_url} como colección de conocimientos: {e}", exc_info=True)
            return f"Error al añadir el repositorio como colección de conocimientos: {e}"

    async def _update_repository_documents(self, repo_url: str, account_id: str, workspace_id: Optional[str] = None, collection_topic: Optional[str] = "repositorio", vectorize: bool = False) -> str:
        """
        Actualiza los documentos textuales de un repositorio de GitHub, con opción a vectorizar los cambios.
        """
        try:
            from core.database import SessionLocal, GitHubDocument
            from sqlalchemy import select, delete
            import uuid
            import base64
            from datetime import datetime
            # Eliminar imports relacionados con RAG que no se usarán
            # from tools.document_rag_tool import DocumentRAGTool
            # from core.memory_manager import remove_document_from_rag
            
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
            async with DBSession(SessionLocal) as db_session:
                updated_files = 0
                new_files = 0
                deleted_files = 0
                # vectorized_count = 0 # Ya no es necesario

                if account_id is None:
                    return "Error: Account ID must be provided to update repository documents."

                # rag_tool = DocumentRAGTool(account_id=account_id, workspace_id=self.workspace_id, telegram_id=self.telegram_id, thread_id=self.thread_id) # Ya no es necesario

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
                result = await db_session.execute(existing_github_docs_query)
                existing_db_docs = {doc.file_path: doc for doc in result.scalars().all()}

                # 1. Eliminar archivos que ya no existen en GitHub
                for file_path, db_doc in existing_db_docs.items():
                    if file_path not in github_files:
                        # if vectorize: # Ya no es necesario
                        #     try:
                        #         await remove_document_from_rag(
                        #             account_id=account_id,
                        #             file_name=file_path,
                        #             topic=collection_topic
                        #         )
                        #         logger.info(f"🗑️ Embeddings eliminados para {file_path}")
                        #     except Exception as del_error:
                        #         logger.error(f"❌ Error eliminando embeddings de {file_path}: {del_error}")
                        
                        await db_session.delete(db_doc) # type: ignore
                        deleted_files += 1
                        logger.info(f"🗑️ Documento eliminado: {file_path}")

                # 2. Añadir nuevos archivos o actualizar modificados
                for file_path, github_sha in github_files.items():
                    # Omitir archivos temporales
                    if self._is_temporary_file(file_path):
                        logger.info(f"⏩ Omitiendo archivo temporal: {file_path}")
                        continue

                    content_response = self.session.get(f"{api_url}/contents/{file_path}")
                    content_response.raise_for_status()
                    content_data = content_response.json()
                    content_base64 = content_data["content"]
                    encoding = content_data["encoding"]

                    if encoding == "base64":
                        decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                    else:
                        decoded_content = content_base64

                    # Limpiar NUL bytes
                    clean_content = decoded_content.replace('\x00', '')

                    # Preparar metadatos para vectorización (ya no es necesario aquí)
                    # repo_metadata = {
                    #     "repo_url": repo_url,
                    #     "repo_name": repo_name,
                    #     "file_extension": file_path.split('.')[-1] if '.' in file_path else '',
                    #     "directory": '/'.join(file_path.split('/')[:-1]) if '/' in file_path else ''
                    # }

                    if file_path in existing_db_docs:
                        db_doc = existing_db_docs[file_path]
                        if db_doc.sha != github_sha:
                            # Contenido modificado, actualizar
                            db_doc.content = clean_content
                            db_doc.sha = github_sha
                            db_doc.topic = collection_topic
                            db_doc.updated_at = datetime.now()
                            updated_files += 1
                            logger.info(f"📝 Documento actualizado: {file_path}")

                            # if vectorize: # Ya no es necesario
                            #     try:
                            #         await remove_document_from_rag(
                            #             account_id=account_id,
                            #             file_name=file_path,
                            #             topic=collection_topic
                            #         )
                            #         logger.info(f"🗑️ Embeddings antiguos eliminados para {file_path}")
                                    
                            #         result = await rag_tool._arun(
                            #             extracted_text=clean_content,
                            #             file_name=file_path,
                            #             topic=collection_topic,
                            #             workspace_id=self.workspace_id,
                            #             metadata=repo_metadata
                            #         )
                            #         if "chunks added" in result.context_for_llm:
                            #             vectorized_count += 1
                            #             logger.info(f"✅ Archivo {file_path} re-vectorizado correctamente")
                            #     except Exception as vec_error:
                            #         logger.error(f"❌ Error re-vectorizando {file_path}: {vec_error}", exc_info=True)
                        else:
                            logger.info(f"⏩ Archivo {file_path} sin cambios.")
                    else:
                        # Nuevo archivo, añadir
                        github_doc = GitHubDocument(
                            repo_url=repo_url,
                            file_path=file_path,
                            sha=github_sha,
                            content=clean_content,
                            account_id=account_id,
                            workspace_id=workspace_id if workspace_id else None,
                            topic=collection_topic,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        db_session.add(github_doc)
                        new_files += 1
                        logger.info(f"📄 Nuevo documento añadido: {file_path} con topic: {github_doc.topic}")
                        
                        # if vectorize: # Ya no es necesario
                        #     try:
                        #         result = await rag_tool._arun(
                        #             extracted_text=clean_content,
                        #             file_name=file_path,
                        #             topic=collection_topic,
                        #             workspace_id=self.workspace_id,
                        #             metadata=repo_metadata
                        #         )
                        #         if "chunks added" in result.context_for_llm:
                        #             vectorized_count += 1
                        #             logger.info(f"✅ Nuevo archivo {file_path} vectorizado correctamente")
                        #     except Exception as vec_error:
                        #         logger.error(f"❌ Error vectorizando nuevo archivo {file_path}: {vec_error}", exc_info=True)

                logger.info(f"DEBUG: Antes del commit en _update_repository_documents. Nuevos: {new_files}, Actualizados: {updated_files}, Eliminados: {deleted_files}")
                # Commit is handled by DBSession context manager
                logger.info(f"DEBUG: Después del commit en _update_repository_documents.")
                
                return f"Repositorio {repo_name} actualizado. Archivos nuevos: {new_files}, Archivos actualizados: {updated_files}, Archivos eliminados: {deleted_files}." # Eliminar referencia a archivos vectorizados

        except Exception as e:
            logger.error(f"Error al actualizar documentos del repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al actualizar documentos del repositorio: {e}"

    async def _update_knowledge_collection(self, repo_url: str, collection_topic: Optional[str] = None, vectorize: bool = False) -> str:
        """
        Actualiza una colección de conocimientos existente desde un repositorio de GitHub, ya sea en una colección RAG específica o como conocimiento general de una cuenta.
        Controla la re-vectorización con el parámetro 'vectorize'.
        """
        try:
            from core.database import SessionLocal, GitHubDocument
            from sqlalchemy import select, delete
            import uuid
            import base64
            from datetime import datetime
            import hashlib
            from tools.document_rag_tool import DocumentRAGTool
            from core.memory_manager import remove_document_from_rag
            
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
            async with DBSession(SessionLocal) as db_session:
                updated_files = 0
                new_files = 0
                deleted_files = 0
                vectorized_count = 0
                
                if self.account_id is None:
                    return "Error: Debes especificar un ID de cuenta para actualizar la colección de conocimientos."

                # Instanciar DocumentRAGTool para vectorización (después de la verificación de account_id)
                rag_tool = DocumentRAGTool(account_id=self.account_id, workspace_id=self.workspace_id, telegram_id=self.telegram_id, thread_id=self.thread_id)
                
                # Obtener el árbol actual del repositorio de GitHub
                tree_url = f"{api_url}/git/trees/{default_branch}?recursive=1"
                response = self.session.get(tree_url)
                response.raise_for_status()
                github_tree = response.json()["tree"]
                
                # Mapear archivos de GitHub por path y SHA
                github_files = {item['path']: item['sha'] for item in github_tree if item['type'] == 'blob'}
                
                # Obtener los documentos de GitHub existentes en la base de datos para este repositorio y cuenta
                if collection_topic:
                    existing_github_docs_query = select(GitHubDocument).where(
                        GitHubDocument.repo_url == repo_url,
                        GitHubDocument.account_id == self.account_id,
                        GitHubDocument.topic == collection_topic
                    )
                else:
                    existing_github_docs_query = select(GitHubDocument).where(
                        GitHubDocument.repo_url == repo_url,
                        GitHubDocument.account_id == self.account_id,
                        GitHubDocument.topic == None
                    )
                result = await db_session.execute(existing_github_docs_query)
                existing_db_docs = {doc.file_path: doc for doc in result.scalars().all()}
                
                # 1. Eliminar archivos que ya no existen en GitHub
                for file_path, db_doc in existing_db_docs.items():
                    if file_path not in github_files:
                        # Eliminar embeddings del archivo
                        try:
                            await remove_document_from_rag(
                                account_id=self.account_id,
                                file_name=file_path,
                                topic=collection_topic if collection_topic else "repositorio"
                            )
                            logger.info(f"🗑️ Embeddings eliminados para {file_path}")
                        except Exception as del_error:
                            logger.error(f"❌ Error eliminando embeddings de {file_path}: {del_error}")
                        
                        await db_session.delete(db_doc) # type: ignore
                        deleted_files += 1
                
                # 2. Añadir nuevos archivos o actualizar modificados
                for file_path, github_sha in github_files.items():
                    # Omitir archivos temporales
                    if self._is_temporary_file(file_path):
                        logger.info(f"⏩ Omitiendo archivo temporal: {file_path}")
                        continue

                    content_response = self.session.get(f"{api_url}/contents/{file_path}")
                    content_response.raise_for_status()
                    content_data = content_response.json()
                    content_base64 = content_data["content"]
                    encoding = content_data["encoding"]
                    
                    if encoding == "base64":
                        decoded_content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")
                    else:
                        decoded_content = content_base64
                    
                    # Preparar metadatos para vectorización
                    repo_metadata = {
                        "repo_url": repo_url,
                        "repo_name": repo_name,
                        "file_extension": file_path.split('.')[-1] if '.' in file_path else '',
                        "directory": '/'.join(file_path.split('/')[:-1]) if '/' in file_path else ''
                    }
                    
                    if file_path in existing_db_docs:
                        db_doc = existing_db_docs[file_path]
                        if db_doc.sha != github_sha:
                            # Contenido modificado, actualizar
                            
                            # Eliminar embeddings antiguos
                            try:
                                await remove_document_from_rag(
                                    account_id=self.account_id,
                                    file_name=file_path,
                                    topic=collection_topic if collection_topic else "repositorio"
                                )
                                logger.info(f"🗑️ Embeddings antiguos eliminados para {file_path}")
                            except Exception as del_error:
                                logger.error(f"❌ Error eliminando embeddings antiguos de {file_path}: {del_error}")
                            
                            # Actualizar documento
                            db_doc.content = decoded_content
                            db_doc.sha = github_sha
                            db_doc.updated_at = datetime.now()
                            updated_files += 1
                            
                            # Opcionalmente, re-vectorizar
                            if vectorize:
                                try:
                                    result = await rag_tool._arun(
                                        extracted_text=decoded_content,
                                        file_name=file_path,
                                        topic=collection_topic if collection_topic else "repositorio",
                                        workspace_id=self.workspace_id,
                                        metadata=repo_metadata
                                    )
                                    
                                    if "chunks added" in result.context_for_llm:
                                        vectorized_count += 1
                                        logger.info(f"✅ Archivo {file_path} re-vectorizado correctamente")
                                except Exception as vec_error:
                                    logger.error(f"❌ Error re-vectorizando {file_path}: {vec_error}")
                            else:
                                logger.info(f"⏩ Archivo {file_path} modificado, no re-vectorizado (vectorize=False).")
                    else:
                        # Nuevo archivo, añadir
                        github_doc = GitHubDocument(
                            repo_url=repo_url,
                            file_path=file_path,
                            sha=github_sha,
                            content=decoded_content,
                            account_id=self.account_id,
                            workspace_id=self.workspace_id if self.workspace_id else None,
                            topic=collection_topic, # Usamos collection_topic directamente aquí
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        db_session.add(github_doc)
                        new_files += 1
                        logger.info(f"📄 Nuevo archivo añadido: {file_path} con topic: {github_doc.topic}")
                        
                        if vectorize:
                            try:
                                result = await rag_tool._arun(
                                    extracted_text=decoded_content,
                                    file_name=file_path,
                                    topic=collection_topic if collection_topic else "repositorio",
                                    workspace_id=self.workspace_id,
                                    metadata=repo_metadata
                                )
                                
                                if "chunks added" in result.context_for_llm:
                                    vectorized_count += 1
                                    logger.info(f"✅ Nuevo archivo {file_path} vectorizado correctamente")
                            except Exception as vec_error:
                                logger.error(f"❌ Error vectorizando nuevo archivo {file_path}: {vec_error}")
                        else:
                            logger.info(f"⏩ Nuevo archivo {file_path} añadido, no vectorizado (vectorize=False).")
                
                # Commit is handled by DBSession context manager
                if collection_topic:
                    return f"Colección con tema '{collection_topic}' actualizada desde {repo_name}. Archivos nuevos: {new_files}, Archivos actualizados: {updated_files}, Archivos eliminados: {deleted_files}. {vectorized_count} archivos vectorizados."
                else:
                    return f"Colección de conocimientos generales para {repo_name} actualizada. Archivos nuevos: {new_files}, Archivos actualizados: {updated_files}, Archivos eliminados: {deleted_files}. {vectorized_count} archivos vectorizados."

        except Exception as e:
            logger.error(f"Error al actualizar la colección de conocimientos para el repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al actualizar la colección de conocimientos: {e}"
    
    def _is_temporary_file(self, file_path: str) -> bool:
        """
        Determina si un archivo es temporal y debería ser omitido del procesamiento.
        """
        import os

        # Obtener solo el nombre del archivo (sin directorios)
        file_name = os.path.basename(file_path)

        # Patrones de archivos temporales comunes
        temp_patterns = [
            # LibreOffice lock files
            file_name.startswith('.~lock.'),
            # Microsoft Office temporary files
            file_name.startswith('~$'),
            # Common temporary file extensions
            file_name.endswith(('.tmp', '.temp', '.bak', '.swp', '.swo')),
            # Hidden files that are typically temporary
            file_name.startswith('._'),
            # Auto-save files
            file_name.startswith('auto-save'),
            # Vim swap files
            file_name.endswith('.swp') or file_name.endswith('.swo'),
            # Emacs lock files
            file_name.startswith('#') and file_name.endswith('#'),
            # System temporary files
            file_name.startswith('~$') or file_name.lower().startswith('temp'),
        ]

        return any(temp_patterns)

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