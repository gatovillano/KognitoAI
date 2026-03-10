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

    def _read_markdown_description(self, skill_name: str, subdirectory: str = "") -> Optional[str]:
        """Lee el archivo .md asociado a la skill y devuelve su contenido."""
        if subdirectory:
            md_path = os.path.join(self.skills_dir, subdirectory, f"{skill_name}.md")
        else:
            md_path = os.path.join(self.skills_dir, f"{skill_name}.md")
            
        if os.path.exists(md_path):
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
                # Filtrar kwargs para pasar solo los que la clase acepta si no usa **kwargs
                # Aunque Pydantic suele ignorar extra si se configura, seremos precavidos.
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
        metadata = []
        if not os.path.exists(self.skills_dir):
            return metadata

        for root, _, files in os.walk(self.skills_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    skill_id = file[:-3]
                    # Relativo a root
                    subdirectory = os.path.relpath(root, self.skills_dir) if root != self.skills_dir else ""
                    description = self._read_markdown_description(skill_id, subdirectory)
                    
                    # Intentar obtener el nombre amigable de la clase si es posible sin cargar todo el sistema
                    # Por ahora usamos el ID del archivo como nombre identificador
                    metadata.append({
                        "id": skill_id,
                        "description": description or "Sin descripción disponible."
                    })
        return metadata

    async def load_skills(
        self,
        account_id: str,
        telegram_id: Optional[int] = None,
        thread_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        progress_callback: Optional[Any] = None,
        disabled_skills: Optional[List[str]] = None
    ) -> List[BaseTool]:
        """
        Escanea el directorio skills/ (y subdirectorios 1 nivel deep), 
        descubre las clases BaseTool, carga su respectivo .md como description, 
        y las instancia con los kwargs provistos.
        """
        await self.initialize_dependencies()
        
        loaded_tools = []
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory {self.skills_dir} does not exist.")
            return loaded_tools

        # Escanear el directorio
        for root, _, files in os.walk(self.skills_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    module_name = file[:-3]
                    
                    # Check if skill is disabled
                    if disabled_skills and module_name in disabled_skills:
                        logger.info(f"🚫 Skill {module_name} is disabled for this user. Skipping.")
                        continue

                    # Relativo a KognitoAI root (ej: "skills.terminal_executor")
                    rel_dir = os.path.relpath(root, os.path.dirname(self.skills_dir))
                    module_path = f"{rel_dir.replace('/', '.')}.{module_name}"
                    
                    try:
                        module = importlib.import_module(module_path)
                        importlib.reload(module) # Reload modules always to allow hot-reloading new skills
                        
                        tool_classes = self._get_tool_classes_from_module(module)
                        
                        for ToolClass in tool_classes:
                            # 1. Instanciar clase
                            instance = await self._instantiate_skill(ToolClass, account_id, telegram_id, thread_id, workspace_id, progress_callback)
                            
                            if instance:
                                # 2. Buscar archivo markdown homónimo al archivo o subdirectorio para overridear la description
                                md_desc = self._read_markdown_description(module_name, os.path.relpath(root, self.skills_dir) if root != self.skills_dir else "")
                                
                                if md_desc:
                                    logger.debug(f"Loaded Markdown description for skill: {instance.name}")
                                    try:
                                         # Pydantic v1 vs v2 workaround para sobrescribir campos protegidos
                                         instance.description = md_desc
                                    except Exception as p_err:
                                         logger.warning(f"Failed to set description on {instance.name} using standard attr. Retrying. {p_err}")
                                         # Forced dict update occasionally needed in older Pydantic strictly typed BaseModel
                                         if hasattr(instance, "__dict__"):
                                             instance.__dict__['description'] = md_desc
                                
                                loaded_tools.append(instance)
                                self._loaded_tools[instance.name] = instance
                                logger.info(f"✅ Skill loaded: {instance.name}")
                                
                    except Exception as e:
                        logger.error(f"Failed to load module {module_path}: {e}")

        return loaded_tools
