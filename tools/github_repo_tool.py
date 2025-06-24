# tools/github_repo_tool.py
import logging
import os
from typing import List, Any, Dict, Optional
import requests
from bs4 import BeautifulSoup
import urllib3
from urllib.parse import urlparse, urljoin
import json

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class GitHubRepoTool(BaseTool):
    name: str = "github_repository_explorer"
    description: str = (
        "Este tool permite explorar repositorios de GitHub. Debes proporcionar la URL del repositorio en el parámetro 'repo_url', la acción a realizar (list_tree, read_file, navigate) en el parámetro 'action', y, opcionalmente, la ruta al archivo o directorio en el parámetro 'path' y el token de GitHub en el parámetro 'github_token' si es necesario. Asegúrate de proporcionar la URL completa del repositorio y de utilizar los nombres de parámetro y acción correctos."
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
    def _run(self, repo_url: str, action: str, path: Optional[str] = None, github_token: Optional[str] = None) -> str:
        """
        Ejecuta la acción especificada en el repositorio de GitHub.
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
            else:
                return f"Error: Acción no válida. Las acciones válidas son: list_tree, read_file, navigate"
        except Exception as e:
            logger.error(f"Error al ejecutar la acción {action} en el repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al ejecutar la acción: {e}"
    async def _arun(self, repo_url: str, action: str, path: Optional[str] = None, github_token: Optional[str] = None) -> str:
        """
        Ejecuta la acción especificada en el repositorio de GitHub (asíncrono).
        """
        return self._run(repo_url, action, path, github_token)  # Llama a la versión síncrona

    def _list_tree(self, repo_url: str) -> str:
        """
        Lista el árbol de archivos del repositorio.
        """
        try:
            if self.session is None:
                self.session = requests.Session()
            api_url = self._get_api_url(repo_url) + "/git/trees/main?recursive=1"
            response = self.session.get(api_url)
            response.raise_for_status()
            tree = response.json()["tree"]
            file_list = "\n".join([f"- {item['path']} ({item['type']})" for item in tree])
            return f"Árbol de archivos:\n{file_list}"
        except Exception as e:
            logger.error(f"Error al listar el árbol de archivos del repositorio {repo_url}: {e}", exc_info=True)
            return f"Error al listar el árbol de archivos: {e}"
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
        description="La acción a realizar en el repositorio. Las opciones válidas son: 'list_tree' (listar todos los archivos), 'read_file' (leer un archivo específico), 'navigate' (listar contenido de un directorio)."
    )
    path: Optional[str] = Field(
        None,
        description="La ruta al archivo o directorio dentro del repositorio. Requerido para las acciones 'read_file' y 'navigate'."
    )
    github_token: Optional[str] = Field(
        None,
        description="Token de acceso personal de GitHub para acceder a repositorios privados. Opcional, pero puede ser necesario para repositorios privados."
    )

# Asignar el esquema de entrada a la herramienta
GitHubRepoTool.args_schema = GitHubRepoInput

# Nota: Esta herramienta debe ser instanciada en la función get_all_langchain_tools() en telegram_client/tools.py
