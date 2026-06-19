import os
import importlib
import inspect
import logging
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

# Embedding and async
import asyncio
from core.embedding_manager import aembed_query, aembed_documents
import numpy as np

from langchain_core.tools import BaseTool
from core.config import settings

logger = logging.getLogger(__name__)

import contextvars
_in_tool_logging = contextvars.ContextVar('_in_tool_logging', default=False)

# Categorías que siempre se cargan independientemente del filtro dinámico
ALWAYS_ON_CATEGORIES = {"core_skills", "search_and_research_skill", "knowledge_and_memory_skill"}

_skill_manager_instance = None

def get_skill_manager(skills_dir: str = "skills") -> 'SkillManager':
    """Retorna una instancia única (singleton) del SkillManager."""
    global _skill_manager_instance
    if _skill_manager_instance is None:
        _skill_manager_instance = SkillManager(skills_dir)
    return _skill_manager_instance

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

        # Cache for skill markdowns and embeddings
        self._skill_md_cache: Optional[List[Dict[str, Any]]] = None
        self._skill_md_embeddings: Optional[np.ndarray] = None
    async def _load_skill_markdowns(self) -> List[Dict[str, Any]]:
        """
        Load all SKILL.md (or .md) files for all skills and return a list of dicts:
        [{ 'id': skill_id, 'description': ..., 'markdown': ... }]
        Robust to missing/deleted skill directories.
        """
        if self._skill_md_cache is not None:
            return self._skill_md_cache
        metadata = await self.get_skills_metadata()
        skill_mds = []
        for entry in metadata:
            skill_id = entry["id"]
            try:
                # Try to find the markdown file for this skill
                # Native
                native_path = os.path.join(self.skills_dir, skill_id)
                if os.path.exists(native_path):
                    md = self._read_markdown_description(native_path, skill_id)
                    if md:
                        skill_mds.append({"id": skill_id, "description": entry.get("description", ""), "markdown": md})
                        continue
                # User/global
                user_global_path = os.path.join(self.skills_dir, "user_global", skill_id)
                if os.path.exists(user_global_path):
                    md = self._read_markdown_description(user_global_path, skill_id)
                    if md:
                        skill_mds.append({"id": skill_id, "description": entry.get("description", ""), "markdown": md})
            except Exception as e:
                logger.warning(f"[SKILL.md loader] Ignoring missing or broken skill '{skill_id}': {e}")
                continue
        self._skill_md_cache = skill_mds
        return skill_mds

    async def _ensure_skill_md_embeddings(self):
        """
        Ensure that embeddings for all SKILL.md files are computed and cached.
        """
        if self._skill_md_embeddings is not None:
            return
        skill_mds = await self._load_skill_markdowns()
        texts = [s["markdown"] for s in skill_mds]
        if not texts:
            self._skill_md_embeddings = np.zeros((0, 384), dtype=np.float32)
            return
        # Compute embeddings
        embeddings = await aembed_documents(texts)
        self._skill_md_embeddings = np.array(embeddings)

    async def search_skills_semantic(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Perform semantic search over all SKILL.md files and return the top-k most relevant skills.
        Returns a list of dicts: [{ 'id': ..., 'description': ..., 'markdown': ... }]
        """
        await self._ensure_skill_md_embeddings()
        skill_mds = await self._load_skill_markdowns()
        if not skill_mds or self._skill_md_embeddings.shape[0] == 0:
            return []
        # Embed the query
        query_emb = await aembed_query(query)
        query_emb = np.array(query_emb)
        # Compute cosine similarity
        skill_embs = self._skill_md_embeddings
        # Normalize
        skill_embs_norm = skill_embs / (np.linalg.norm(skill_embs, axis=1, keepdims=True) + 1e-8)
        query_emb_norm = query_emb / (np.linalg.norm(query_emb) + 1e-8)
        sims = np.dot(skill_embs_norm, query_emb_norm)
        # Get top-k
        top_idx = np.argsort(sims)[::-1][:top_k]
        return [skill_mds[i] for i in top_idx]

    def clear_skill_md_cache(self):
        self._skill_md_cache = None
        self._skill_md_embeddings = None

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

    def _get_tool_classes_from_module(self, module) -> List[Any]:
        """
        Extrae todas las clases que heredan de BaseTool en un módulo dado,
        y también funciones públicas estándar (run, main, execute) como herramientas ejecutables.
        """
        tools = []
        # Clases BaseTool
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseTool) and obj != BaseTool and obj.__module__ == module.__name__:
                tools.append(obj)
        # Funciones públicas estándar
        for fname in ("run", "main", "execute"):
            func = getattr(module, fname, None)
            if callable(func):
                # Envolver la función en una clase simple para compatibilidad
                tool_name = getattr(module, "name", module.__name__)
                tool_desc = getattr(module, "description", func.__doc__ or "Función ejecutable expuesta por el script.")
                class FunctionTool:
                    name = tool_name
                    description = tool_desc
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return func(*args, **kwargs)
                tools.append(FunctionTool)
        return tools

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
            
            # Envuelve la herramienta para logging automático de ejecuciones
            instance = self._wrap_tool_with_logging(instance)
            return instance

        except Exception as e:
            logger.error(f"Error instantiating skill {ToolClass.__name__}: {e}", exc_info=True)
            return None

    def _wrap_tool_with_logging(self, tool_instance: Any) -> Any:
        """
        Envuelve la ejecución de los puntos de entrada (invoke, ainvoke, run, arun, __call__)
        de la herramienta usando un recursion guard para que siempre se registren logs
        (al iniciar, en éxito y en error) exactamente una vez por ejecución.
        """
        import functools
        import types
        import time
        import json

        tool_name = getattr(tool_instance, 'name', tool_instance.__class__.__name__)

        def format_args(args, kwargs):
            try:
                combined = {}
                if args:
                    combined["args"] = args
                if kwargs:
                    combined.update(kwargs)
                if not combined:
                    return "None"
                # Eliminar self de los args posicionales si aparece
                if "args" in combined and combined["args"] and combined["args"][0] == tool_instance:
                    if len(combined["args"]) > 1:
                        combined["args"] = combined["args"][1:]
                    else:
                        del combined["args"]
                if not combined:
                    return "None"
                args_str = json.dumps(combined, ensure_ascii=False)
                if len(args_str) > 500:
                    return args_str[:497] + "..."
                return args_str
            except Exception:
                return f"args: {args}, kwargs: {kwargs}"

        def format_result(result):
            try:
                from core.citation_models import ToolOutputWithSources
                if isinstance(result, ToolOutputWithSources):
                    res_str = str(result.context_for_llm)
                else:
                    res_str = str(result)
                if len(res_str) > 500:
                    return res_str[:497] + "..."
                return res_str
            except Exception:
                return str(result)[:500]

        def make_async_wrapper(orig_func):
            @functools.wraps(orig_func)
            async def async_wrapper(self, *args, **kwargs):
                if _in_tool_logging.get():
                    return await orig_func(self, *args, **kwargs)
                
                token = _in_tool_logging.set(True)
                start_time = time.time()
                inputs = format_args(args, kwargs)
                logger.info(f"🛠️ [TOOL START] Executing async tool '{tool_name}' | Args: {inputs}")
                try:
                    res = await orig_func(self, *args, **kwargs)
                    elapsed = time.time() - start_time
                    logger.info(f"✅ [TOOL SUCCESS] Tool '{tool_name}' completed in {elapsed:.3f}s | Result: {format_result(res)}")
                    return res
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(f"❌ [TOOL ERROR] Tool '{tool_name}' failed after {elapsed:.3f}s: {e}", exc_info=True)
                    raise
                finally:
                    _in_tool_logging.reset(token)
            return async_wrapper

        def make_sync_wrapper(orig_func):
            @functools.wraps(orig_func)
            def sync_wrapper(self, *args, **kwargs):
                if _in_tool_logging.get():
                    return orig_func(self, *args, **kwargs)
                
                token = _in_tool_logging.set(True)
                start_time = time.time()
                inputs = format_args(args, kwargs)
                logger.info(f"🛠️ [TOOL START] Executing sync tool '{tool_name}' | Args: {inputs}")
                try:
                    res = orig_func(self, *args, **kwargs)
                    elapsed = time.time() - start_time
                    logger.info(f"✅ [TOOL SUCCESS] Tool '{tool_name}' completed in {elapsed:.3f}s | Result: {format_result(res)}")
                    return res
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(f"❌ [TOOL ERROR] Tool '{tool_name}' failed after {elapsed:.3f}s: {e}", exc_info=True)
                    raise
                finally:
                    _in_tool_logging.reset(token)
            return sync_wrapper

        for attr in ('invoke', 'ainvoke', 'run', 'arun', '__call__'):
            original = getattr(tool_instance, attr, None)
            if not original or not callable(original):
                continue
                
            if getattr(original, '__wrapped_by_skill_manager__', False):
                continue
                
            original_func = getattr(original, '__func__', original)
            
            if inspect.iscoroutinefunction(original_func):
                wrapper = make_async_wrapper(original_func)
            else:
                wrapper = make_sync_wrapper(original_func)
                
            wrapper.__wrapped_by_skill_manager__ = True
            bound_method = types.MethodType(wrapper, tool_instance)
            try:
                tool_instance.__dict__[attr] = bound_method
            except Exception as e:
                logger.warning(f"Could not wrap method '{attr}' for tool '{tool_name}': {e}")
                
        return tool_instance

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
        disabled_skills: Optional[List[str]] = None,
        relevant_categories: Optional[List[str]] = None,
    ) -> List[BaseTool]:
        """
        Escanea el directorio skills/ cargando skills nativas (categorias directas)
        y skills de usuario (user_global y user_workspace_{workspace_name}).
        """
        await self.initialize_dependencies()
        
        # Invalidate import caches to ensure newly created skills are discoverable
        importlib.invalidate_caches()
        logger.info(f"🔄 Scanning for skills. Account: {account_id}, Workspace: {workspace_name}")
        
        loaded_tools = []
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory {self.skills_dir} does not exist.")
            return loaded_tools

        # 1. Identificar categorías nativas
        native_categories = []
        for item in os.listdir(self.skills_dir):
            item_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(item_path) and not item.startswith("user_") and not item.startswith("__"):
                native_categories.append(item)

        # 2. Identificar scopes de usuario
        user_scopes = ["user_global"]
        if account_id:
            user_scopes.append(f"user_account_{account_id}")
        if workspace_name:
            user_scopes.append(f"user_workspace_{workspace_name}")

        # --- CARGAR SKILLS NATIVAS ---
        for category in native_categories:
            if disabled_skills and category in disabled_skills:
                continue

            if relevant_categories is not None:
                allowed = set(relevant_categories) | ALWAYS_ON_CATEGORIES
                if category not in allowed:
                    continue
                
            category_path = os.path.join(self.skills_dir, category)
            scripts_path = os.path.join(category_path, "scripts")
            if not os.path.exists(scripts_path): continue
            
            skill_description = self._read_markdown_description(category_path, category)
            
            for file in os.listdir(scripts_path):
                if file.endswith(".py") and not file.startswith("__"):
                    module_name = file[:-3]
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
                    continue
                    
                skill_folder_path = os.path.join(scope_path, skill_folder)
                if not os.path.isdir(skill_folder_path) or skill_folder.startswith("__"):
                    continue

                skill_description = self._read_markdown_description(skill_folder_path, skill_folder)
                scripts_path = os.path.join(skill_folder_path, "scripts")
                if not os.path.exists(scripts_path):
                    continue

                for file in os.listdir(scripts_path):
                    if file.endswith(".py") and not file.startswith("__"):
                        module_name = file[:-3]
                        # Path: skills.[scope].[skill_folder].scripts.[module_name]
                        module_path = f"skills.{scope}.{skill_folder}.scripts.{module_name}"
                        logger.info(f"🧪 Found user skill script: {file} in {scope}/{skill_folder}")
                        await self._load_module_and_instantiate(
                            module_path, account_id, telegram_id, thread_id, 
                            workspace_id, workspace_name, progress_callback, 
                            skill_description, loaded_tools
                        )

        logger.info(f"✅ Total skills loaded in this session: {len(loaded_tools)}")
        return loaded_tools

    async def reload_user_skills(self, account_id: str, workspace_name: Optional[str] = None):
        """
        Limpia caches y asegura que las habilidades del usuario sean re-escaneadas.
        """
        importlib.invalidate_caches()
        # Limpiar el registro interno de herramientas para forzar re-instanciación
        self._loaded_tools = {}
        logger.info(f"🔄 Caches de importación y registro de herramientas invalidados para recarga de skills (account: {account_id})")

    async def _load_module_and_instantiate(
        self, module_path, account_id, telegram_id, thread_id, 
        workspace_id, workspace_name, progress_callback, 
        skill_description, loaded_tools
    ):
        try:
            import sys
            
            # --- Robustez para paquetes dinámicos ---
            # Si el path tiene varios puntos (ej: skills.user_account_X.myskill...),
            # nos aseguramos de que cada nivel intermedio esté en sys.modules si existe __init__.py
            parts = module_path.split('.')
            for i in range(1, len(parts)):
                parent_path = '.'.join(parts[:i])
                if parent_path not in sys.modules:
                    try:
                        importlib.import_module(parent_path)
                    except Exception as e:
                        logger.debug(f"Could not preemptively import parent package {parent_path}: {e}")

            is_reload = module_path in sys.modules
            
            # Forzar recarga del sistema de importación
            importlib.invalidate_caches()
            
            if is_reload:
                module = sys.modules[module_path]
                importlib.reload(module)
                logger.debug(f"🔄 Module reloaded: {module_path}")
            else:
                module = importlib.import_module(module_path)
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
                    
                    # Marcar si es una skill de usuario para priorización en el agente
                    if ".user_" in module_path:
                        try:
                            setattr(instance, 'is_user_skill', True)
                        except:
                            if hasattr(instance, "__dict__"):
                                instance.__dict__['is_user_skill'] = True
                        logger.info(f"✅ User Skill loaded: {instance.name} (from {module_path})")
                    else:
                        logger.info(f"✅ Native Skill loaded: {instance.name} (from {module_path})")
        except Exception as e:
            logger.error(f"Failed to load module {module_path}: {e}")
