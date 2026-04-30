import os
import importlib
import inspect
import logging
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

from langchain_core.tools import BaseTool
from core.config import settings

logger = logging.getLogger(__name__)

class SkillManager:
    """
    Gestor dinámico de Skills para Kognito AI.
    Escanea el directorio de skills, empareja archivos .py con sus correspondientes .md,
    y carga dinámicamente las herramientas listas para ser usadas por el agente.
    """
    
    def __init__(self, skills_dir: str = "skills"):
        # Resolvemos el directorio relativo al directorio principal de KognitoAI
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.skills_dir = os.path.join(project_root, skills_dir)
        self.skills_module_prefix = skills_dir.replace("/", ".")
        self._loaded_tools: Dict[str, BaseTool] = {}
        
        # Shared instances
        self._graph_db = None
        self._enhanced_memory_manager = None
        self._knowledge_graph_service = None

    async def initialize_dependencies(self):
        """Inicializa despendenicss globales necesarias para las tools (ej: base de datos Neo4j)"""
        try:
            from core.agent import get_shared_graph_dependencies
            self._graph_db, self._enhanced_memory_manager = await get_shared_graph_dependencies()
        except Exception as e:
            logger.warning(f"No se pudieron cargar as dependencias globales compartidas para las skills: {e}")

    def _read_markdown_description(self, skill_folder_path: str, skill_name: str) -> Optional[str]:
        """
        Lee el archivo .md asociado a la skill.
        Busca primero uno con el nombre de la carpeta (ej: notes_skill/notes_skill.md),
        y si no, toma el primer .md que encuentre en la raíz de dicha carpeta.
        """
        md_path = os.path.join(skill_folder_path, f"{skill_name}.md")
            
        if not os.path.exists(md_path):
            # Buscar cualquier archivo .md si no existe el específico
            md_files = [f for f in os.listdir(skill_folder_path) if f.endswith(".md")]
            if md_files:
                md_path = os.path.join(skill_folder_path, md_files[0])
            else:
                return None

        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error reading markdown file {md_path}: {e}")
        return None

    def _get_tool_classes_from_module(self, module) -> List[type]:
        """Extrae todas las clases que heredan de BaseTool en un módulo dado."""
        classes = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseTool) and obj != BaseTool and obj.__module__ == module.__name__:
                classes.append(obj)
        return classes

    async def _instantiate_skill(
        self,
        ToolClass: type,
        account_id: str,
        telegram_id: Optional[int] = None,
        thread_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        workspace_name: Optional[str] = None,
        progress_callback: Optional[Any] = None
    ) -> Optional[BaseTool]:
        """Instancia una Tool Class inyectándole las dependencias requeridas basándose en las propiedades que acepta."""
        try:
            tool_name = getattr(ToolClass, 'name', ToolClass.__name__)
            fields = set()
            
            # Detectar propiedades (Pydantic v1/v2 compatibility)
            if hasattr(ToolClass, 'model_fields'):
                fields = set(ToolClass.model_fields.keys())
            elif hasattr(ToolClass, '__fields__'):
                fields = set(ToolClass.__fields__.keys())
            if not fields and hasattr(ToolClass, '__annotations__'):
                fields = set(ToolClass.__annotations__.keys())

            kwargs = {}
            if 'account_id' in fields:
                kwargs['account_id'] = account_id
            if 'telegram_id' in fields and telegram_id is not None:
                kwargs['telegram_id'] = str(telegram_id)
            if 'thread_id' in fields and thread_id is not None:
                kwargs['thread_id'] = thread_id
            if 'workspace_id' in fields and workspace_id is not None:
                kwargs['workspace_id'] = workspace_id
            if 'workspace_name' in fields and workspace_name is not None:
                kwargs['workspace_name'] = workspace_name
            
            if 'github_token' in fields:
                kwargs['github_token'] = os.environ.get("GITHUB_TOKEN")
            if 'progress_callback' in fields:
                kwargs['progress_callback'] = progress_callback

            # Dependencias de Grafo (si la skill las requiere)
            if 'graph_db' in fields and self._graph_db is not None:
                kwargs['graph_db'] = self._graph_db
            if 'enhanced_memory_manager' in fields and self._enhanced_memory_manager is not None:
                 kwargs['enhanced_memory_manager'] = self._enhanced_memory_manager
            
            # Neo4j Knowledge Graph Service (si aplica)
            if 'knowledge_graph_service' in fields:
                 try:
                     from knowledge_graph.neo4j_adapter import Neo4jGraphAdapter
                     kwargs['knowledge_graph_service'] = Neo4jGraphAdapter()
                 except Exception as e:
                     logger.warning(f"Could not inject knowledge_graph_service into {tool_name}: {e}")

            # Permitir instanciar herramientas sin kwargs si no esperan nada
            try:
                instance = ToolClass(**kwargs)
            except Exception as e:
                logger.warning(f"Error instantiating {tool_name} with kwargs {kwargs}. Falling back to empty constructor. Error: {e}")
                try:
                    instance = ToolClass()
                except:
                    return None
            
            # Re-asignar explicitly a la instancia final si existía el field y no se inyectó bien
            if 'account_id' in fields and not hasattr(instance, 'account_id'): instance.account_id = account_id
            if 'workspace_id' in fields and not hasattr(instance, 'workspace_id'): instance.workspace_id = workspace_id
            
            return instance

        except Exception as e:
            logger.error(f"Error instantiating skill {ToolClass.__name__}: {e}", exc_info=True)
            return None

    async def get_skills_metadata(self) -> List[Dict[str, str]]:
        """
        Escanea el directorio de skills y devuelve una lista de diccionarios con
        el nombre base de la skill y su descripción (si existe).
        """
        # Nota: Este método podría necesitar refinarse para devolver metadatos de las carpetas de skills
        metadata = []
        if not os.path.exists(self.skills_dir):
            return metadata

        # 1. Identificar categorías nativas (todos los subdirectorios excepto user_*)
        native_categories = []
        for item in os.listdir(self.skills_dir):
            item_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(item_path) and not item.startswith("user_") and not item.startswith("__"):
                native_categories.append(item)

        # 2. Agregar metadatos de categorías nativas
        for category in native_categories:
            category_path = os.path.join(self.skills_dir, category)
            description = self._read_markdown_description(category_path, category)
            metadata.append({
                "id": category,
                "description": description or "Sin descripción disponible."
            })

        # 3. Ahora buscamos en user_global y user_workspace_*
        for scope in ["user_global"]: # Por ahora solo global para metadatos generales
            scope_dir = os.path.join(self.skills_dir, scope)
            if not os.path.exists(scope_dir): continue
            
            for skill_folder in os.listdir(scope_dir):
                skill_path = os.path.join(scope_dir, skill_folder)
                if os.path.isdir(skill_path) and not skill_folder.startswith("__"):
                    description = self._read_markdown_description(skill_path, skill_folder)
                    metadata.append({
                        "id": skill_folder,
                        "description": description or "Sin descripción disponible."
                    })
        return metadata

    async def load_skills(
        self,
        account_id: str,
        telegram_id: Optional[int] = None,
        thread_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        workspace_name: Optional[str] = None,
        progress_callback: Optional[Any] = None,
        disabled_skills: Optional[List[str]] = None
    ) -> List[BaseTool]:
        """
        Escanea el directorio skills/ cargando skills nativas (categorias directas)
        y skills de usuario (user_global y user_workspace_{workspace_name}).
        """
        await self.initialize_dependencies()
        
        # Invalidate import caches to ensure newly created skills are discoverable
        importlib.invalidate_caches()
        logger.debug("Import caches invalidated before loading skills.")
        
        loaded_tools = []
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory {self.skills_dir} does not exist.")
            return loaded_tools

        # 1. Identificar categorías nativas (todos los subdirectorios excepto user_*)
        native_categories = []
        for item in os.listdir(self.skills_dir):
            item_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(item_path) and not item.startswith("user_") and not item.startswith("__"):
                native_categories.append(item)

        # 2. Identificar scopes de usuario
        user_scopes = ["user_global"]
        
        # Scope por cuenta (privado del usuario)
        if account_id:
            user_scopes.append(f"user_account_{account_id}")
            
        # Scope por espacio de trabajo (compartido en el workspace)
        if workspace_name:
            user_scopes.append(f"user_workspace_{workspace_name}")

        # --- CARGAR SKILLS NATIVAS ---
        for category in native_categories:
            if disabled_skills and category in disabled_skills:
                logger.info(f"Habilidad nativa '{category}' está desactivada. Saltando.")
                continue
                
            category_path = os.path.join(self.skills_dir, category)
            scripts_path = os.path.join(category_path, "scripts")
            if not os.path.exists(scripts_path): continue
            
            skill_description = self._read_markdown_description(category_path, category)
            
            for file in os.listdir(scripts_path):
                if file.endswith(".py") and not file.startswith("__"):
                    module_name = file[:-3]
                    # Path: skills.[category].scripts.[module_name]
                    module_path = f"skills.{category}.scripts.{module_name}"
                    await self._load_module_and_instantiate(
                        module_path, account_id, telegram_id, thread_id, 
                        workspace_id, workspace_name, progress_callback, 
                        skill_description, loaded_tools
                    )

        # --- CARGAR SKILLS DE USUARIO ---
        for scope in user_scopes:
            scope_path = os.path.join(self.skills_dir, scope)
            if not os.path.exists(scope_path): continue

            for skill_folder in os.listdir(scope_path):
                if disabled_skills and skill_folder in disabled_skills:
                    logger.info(f"Habilidad de usuario '{skill_folder}' está desactivada en scope {scope}. Saltando.")
                    continue
                    
                skill_folder_path = os.path.join(scope_path, skill_folder)
                if not os.path.isdir(skill_folder_path) or skill_folder.startswith("__"):
                    continue

                skill_description = self._read_markdown_description(skill_folder_path, skill_folder)
                scripts_path = os.path.join(skill_folder_path, "scripts")
                if not os.path.exists(scripts_path): continue

                for file in os.listdir(scripts_path):
                    if file.endswith(".py") and not file.startswith("__"):
                        module_name = file[:-3]
                        # Path: skills.[scope].[skill_folder].scripts.[module_name]
                        module_path = f"skills.{scope}.{skill_folder}.scripts.{module_name}"
                        await self._load_module_and_instantiate(
                            module_path, account_id, telegram_id, thread_id, 
                            workspace_id, workspace_name, progress_callback, 
                            skill_description, loaded_tools
                        )

        return loaded_tools

    async def _load_module_and_instantiate(
        self, module_path, account_id, telegram_id, thread_id, 
        workspace_id, workspace_name, progress_callback, 
        skill_description, loaded_tools
    ):
        try:
            import sys
            is_reload = module_path in sys.modules
            
            module = importlib.import_module(module_path)
            if is_reload:
                importlib.reload(module)
                logger.debug(f"🔄 Module reloaded: {module_path}")
            else:
                logger.debug(f"🆕 Module imported for the first time: {module_path}")
                
            tool_classes = self._get_tool_classes_from_module(module)
            
            for ToolClass in tool_classes:
                instance = await self._instantiate_skill(
                    ToolClass, account_id, telegram_id, thread_id, 
                    workspace_id, workspace_name, progress_callback
                )
                
                if instance:
                    if skill_description:
                        try:
                            instance.description = skill_description
                        except:
                            if hasattr(instance, "__dict__"):
                                instance.__dict__['description'] = skill_description
                    
                    loaded_tools.append(instance)
                    self._loaded_tools[instance.name] = instance
                    logger.info(f"✅ Skill loaded: {instance.name} (from {module_path})")
        except Exception as e:
            logger.error(f"Failed to load module {module_path}: {e}")
