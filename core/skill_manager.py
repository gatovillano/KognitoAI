import os
import importlib
import importlib.util
import inspect
import logging
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
import yaml

# Embedding and async
import asyncio

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

from langchain_core.tools import BaseTool

# Lazy imports – resolved at runtime to avoid heavy deps at import time
# (needed for test environments without sentence_transformers / DB)
_aembed_query = None
_aembed_documents = None
_settings = None


def _get_embed_fns():
    global _aembed_query, _aembed_documents
    if _aembed_query is None:
        from core.embedding_manager import aembed_query, aembed_documents
        _aembed_query = aembed_query
        _aembed_documents = aembed_documents
    return _aembed_query, _aembed_documents


def _get_settings():
    global _settings
    if _settings is None:
        from core.config import settings
        _settings = settings
    return _settings

logger = logging.getLogger(__name__)

import contextvars
_in_tool_logging = contextvars.ContextVar('_in_tool_logging', default=False)

# Categorías que siempre se cargan independientemente del filtro dinámico
ALWAYS_ON_CATEGORIES = {"core_skills", "search_and_research_skill", "knowledge_and_memory_skill", "developer_tools_skill"}

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
        self.user_skills_dir = os.getenv("KOGNITO_USER_SKILLS_DIR", os.path.expanduser("~/.kognito/skills"))
        self.skills_module_prefix = skills_dir.replace("/", ".")
        self._loaded_tools: Dict[str, BaseTool] = {}
        
        # Shared instances
        self._graph_db = None
        self._enhanced_memory_manager = None
        self._knowledge_graph_service = None

        # Cache dictionaries by (account_id, workspace_name)
        self._skill_md_cache_dict: Dict[tuple, List[Dict[str, Any]]] = {}
        self._skill_md_embeddings_dict: Dict[tuple, Any] = {}  # np.ndarray when np available

    def parse_skill_markdown(self, content: str) -> Dict[str, Any]:
        """
        Parsea el contenido de un SKILL.md/markdown separando frontmatter y cuerpo.
        Soporta frontmatter YAML delimitado por '---'.
        """
        content = content.strip()
        if not content.startswith("---"):
            return {
                "name": "",
                "description": content,
                "instructions": content,
                "metadata": {}
            }
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {
                "name": "",
                "description": content,
                "instructions": content,
                "metadata": {}
            }
        
        try:
            frontmatter = yaml.safe_load(parts[1]) or {}
        except Exception as e:
            logger.warning(f"Error parsing YAML frontmatter: {e}")
            frontmatter = {}
            
        if not isinstance(frontmatter, dict):
            frontmatter = {}
            
        description = frontmatter.get("description", "").strip()
        instructions = frontmatter.get("instructions", "").strip()
        body_content = parts[2].strip()
        if not instructions:
            instructions = body_content
        
        if not description:
            description = instructions[:200]
            if len(instructions) > 200:
                description += "..."
                
        return {
            "name": frontmatter.get("name", ""),
            "description": description,
            "instructions": instructions,
            "content": body_content,
            "metadata": frontmatter
        }

    def _read_markdown_content(self, skill_folder_path: str, skill_name: str) -> Optional[str]:
        """
        Lee el archivo markdown (.md) asociado a la skill de forma robusta.
        """
        md_path = os.path.join(skill_folder_path, f"{skill_name}.md")
        if not os.path.exists(md_path):
            md_path = os.path.join(skill_folder_path, "SKILL.md")
        if not os.path.exists(md_path):
            try:
                md_files = [f for f in os.listdir(skill_folder_path) if f.endswith(".md") and f != "README.md"]
                if md_files:
                    md_path = os.path.join(skill_folder_path, md_files[0])
                else:
                    return None
            except Exception:
                return None

        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error reading markdown file {md_path}: {e}")
        return None

    def _read_markdown_description(self, skill_folder_path: str, skill_name: str) -> Optional[str]:
        """
        Lee el archivo markdown y retorna su descripción básica.
        """
        content = self._read_markdown_content(skill_folder_path, skill_name)
        if content:
            parsed = self.parse_skill_markdown(content)
            return parsed["description"]
        return None

    async def _load_skill_markdowns(self, account_id: Optional[str] = None, workspace_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Carga todos los archivos markdown de las skills buscando en categorías nativas
        y en los scopes correspondientes al usuario y workspace.
        """
        cache_key = (account_id, workspace_name)
        if cache_key in self._skill_md_cache_dict:
            return self._skill_md_cache_dict[cache_key]
            
        metadata = await self.get_skills_metadata(account_id, workspace_name)
        skill_mds = []
        
        scopes = ["user_global"]
        if account_id:
            scopes.append(f"user_account_{account_id}")
        if workspace_name:
            scopes.append(f"user_workspace_{workspace_name}")
            
        for entry in metadata:
            skill_id = entry["id"]
            try:
                # 1. Native
                native_path = os.path.join(self.skills_dir, skill_id)
                if os.path.exists(native_path):
                    md_content = self._read_markdown_content(native_path, skill_id)
                    if md_content:
                        parsed = self.parse_skill_markdown(md_content)
                        has_scripts = os.path.exists(os.path.join(native_path, "scripts"))
                        skill_type = parsed.get("metadata", {}).get("type") or ("tool" if has_scripts else "procedural")
                        skill_mds.append({
                            "id": skill_id,
                            "name": parsed["name"] or skill_id,
                            "description": parsed["description"],
                            "instructions": parsed["instructions"],
                            "markdown": parsed["instructions"],
                            "type": skill_type,
                            "has_scripts": has_scripts
                        })
                        continue
                
                # 2. Scopes
                found = False
                for scope in scopes:
                    for base_dir in [self.user_skills_dir, self.skills_dir]:
                        if not base_dir: continue
                        scope_path = os.path.join(base_dir, scope, skill_id)
                        if os.path.exists(scope_path):
                            md_content = self._read_markdown_content(scope_path, skill_id)
                            if md_content:
                                parsed = self.parse_skill_markdown(md_content)
                                has_scripts = os.path.exists(os.path.join(scope_path, "scripts"))
                                skill_type = parsed.get("metadata", {}).get("type") or ("tool" if has_scripts else "procedural")
                                skill_mds.append({
                                    "id": skill_id,
                                    "name": parsed["name"] or skill_id,
                                    "description": parsed["description"],
                                    "instructions": parsed["instructions"],
                                    "markdown": parsed["instructions"],
                                    "type": skill_type,
                                    "has_scripts": has_scripts
                                })
                                found = True
                                break
                    if found:
                        break
            except Exception as e:
                logger.warning(f"[SKILL.md loader] Ignoring missing or broken skill '{skill_id}': {e}")
                continue
                
        self._skill_md_cache_dict[cache_key] = skill_mds
        return skill_mds

    async def _ensure_skill_md_embeddings(self, account_id: Optional[str] = None, workspace_name: Optional[str] = None):
        """
        Asegura que los embeddings para los markdowns estén calculados y cacheados.
        """
        cache_key = (account_id, workspace_name)
        if cache_key in self._skill_md_embeddings_dict:
            return
            
        skill_mds = await self._load_skill_markdowns(account_id, workspace_name)
        texts = [s["markdown"] for s in skill_mds]
        if not texts:
            import numpy as _np
            self._skill_md_embeddings_dict[cache_key] = _np.zeros((0, 384), dtype=_np.float32)
            return

        _, _aembed_docs = _get_embed_fns()
        embeddings = await _aembed_docs(texts)
        import numpy as _np2
        self._skill_md_embeddings_dict[cache_key] = _np2.array(embeddings)

    async def search_skills_semantic(self, query: str, top_k: int = 3, account_id: Optional[str] = None, workspace_name: Optional[str] = None, skill_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Realiza búsqueda semántica sobre todas las skills relevantes.
        Permite filtrar opcionalmente por skill_type ('procedural' o 'tool').
        """
        await self._ensure_skill_md_embeddings(account_id, workspace_name)
        skill_mds = await self._load_skill_markdowns(account_id, workspace_name)
        
        if skill_type:
            skill_mds = [s for s in skill_mds if s.get("type") == skill_type]

        if not skill_mds:
            return []

        cache_key = (account_id, workspace_name)
        embeddings = self._skill_md_embeddings_dict.get(cache_key)
        
        if embeddings is None or embeddings.shape[0] == 0:
            return []

        # Si filtramos por skill_type, re-calculamos/filtramos los índices sobre la lista resultante
        all_mds = await self._load_skill_markdowns(account_id, workspace_name)
        if skill_type:
            valid_indices = [i for i, s in enumerate(all_mds) if s.get("type") == skill_type]
            if not valid_indices:
                return []
            skill_mds = [all_mds[i] for i in valid_indices]
            embeddings = embeddings[valid_indices]
            
        _aembed_q, _ = _get_embed_fns()
        query_emb = await _aembed_q(query)
        import numpy as _np
        query_emb = _np.array(query_emb)

        # Normalizar y calcular similitud coseno
        skill_embs_norm = embeddings / (_np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
        query_emb_norm = query_emb / (_np.linalg.norm(query_emb) + 1e-8)
        sims = _np.dot(skill_embs_norm, query_emb_norm)

        top_idx = _np.argsort(sims)[::-1][:top_k]
        return [skill_mds[i] for i in top_idx]

    def clear_skill_md_cache(self):
        self._skill_md_cache_dict.clear()
        self._skill_md_embeddings_dict.clear()

    async def initialize_dependencies(self):
        """Inicializa despendenicss globales necesarias para las tools (ej: base de datos Neo4j)"""
        try:
            from core.agent import get_shared_graph_dependencies
            self._graph_db, self._enhanced_memory_manager = await get_shared_graph_dependencies()
        except Exception as e:
            logger.warning(f"No se pudieron cargar as dependencias globales compartidas para las skills: {e}")

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
            if 'account_id' in fields and (not hasattr(instance, 'account_id') or getattr(instance, 'account_id', None) is None): instance.account_id = account_id
            if 'workspace_id' in fields and (not hasattr(instance, 'workspace_id') or getattr(instance, 'workspace_id', None) is None): instance.workspace_id = workspace_id
            
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

    async def get_skills_metadata(self, account_id: Optional[str] = None, workspace_name: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Escanea el directorio de skills y devuelve una lista de diccionarios con
        el nombre base de la skill y su descripción (si existe).
        """
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
            has_scripts = os.path.exists(os.path.join(category_path, "scripts"))
            metadata.append({
                "id": category,
                "description": description or "Sin descripción disponible.",
                "type": "tool" if has_scripts else "procedural",
                "has_scripts": has_scripts
            })

        # 3. Ahora buscamos en user_global, user_account_*, y user_workspace_*
        scopes = ["user_global"]
        if account_id:
            scopes.append(f"user_account_{account_id}")
        if workspace_name:
            scopes.append(f"user_workspace_{workspace_name}")

        for scope in scopes:
            for base_dir in [self.user_skills_dir, self.skills_dir]:
                if not base_dir or not os.path.exists(base_dir): continue
                scope_dir = os.path.join(base_dir, scope)
                if not os.path.exists(scope_dir): continue
                
                for skill_folder in os.listdir(scope_dir):
                    skill_path = os.path.join(scope_dir, skill_folder)
                    if os.path.isdir(skill_path) and not skill_folder.startswith("__"):
                        description = self._read_markdown_description(skill_path, skill_folder)
                        has_scripts = os.path.exists(os.path.join(skill_path, "scripts"))
                        metadata.append({
                            "id": skill_folder,
                            "description": description or "Sin descripción disponible.",
                            "type": "tool" if has_scripts else "procedural",
                            "has_scripts": has_scripts
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
                    file_path = os.path.join(scripts_path, file)
                    await self._load_module_and_instantiate(
                        module_path, file_path, account_id, telegram_id, thread_id, 
                        workspace_id, workspace_name, progress_callback, 
                        skill_description, loaded_tools
                    )

        # --- CARGAR SKILLS DE USUARIO ---
        for scope in user_scopes:
            for base_dir in [self.user_skills_dir, self.skills_dir]:
                if not base_dir or not os.path.exists(base_dir): continue
                scope_path = os.path.join(base_dir, scope)
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
                            clean_scope = scope.replace("-", "_")
                            clean_folder = skill_folder.replace("-", "_")
                            module_path = f"skills.{clean_scope}.{clean_folder}.scripts.{module_name}"
                            file_path = os.path.join(scripts_path, file)
                            logger.info(f"🧪 Found user skill script: {file} in {scope}/{skill_folder}")
                            await self._load_module_and_instantiate(
                                module_path, file_path, account_id, telegram_id, thread_id, 
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
        self.clear_skill_md_cache()
        # Limpiar el registro interno de herramientas para forzar re-instanciación
        self._loaded_tools = {}
        logger.info(f"🔄 Caches de importación y registro de herramientas invalidados para recarga de skills (account: {account_id})")

    async def _load_module_and_instantiate(
        self, module_path, file_path, account_id, telegram_id, thread_id, 
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
                        if "-" in parent_path:
                            import types
                            dummy = types.ModuleType(parent_path)
                            dummy.__path__ = []
                            sys.modules[parent_path] = dummy
                        else:
                            importlib.import_module(parent_path)
                    except Exception as e:
                        logger.debug(f"Could not preemptively import parent package {parent_path}: {e}")

            is_reload = module_path in sys.modules
            
            # Forzar recarga del sistema de importación
            importlib.invalidate_caches()
            
            if is_reload:
                module = sys.modules[module_path]
                if "-" in module_path:
                    spec = importlib.util.spec_from_file_location(module_path, file_path)
                    if spec is not None and spec.loader is not None:
                        spec.loader.exec_module(module)
                        logger.debug(f"🔄 Module reloaded from file path: {module_path}")
                    else:
                        importlib.reload(module)
                else:
                    importlib.reload(module)
                logger.debug(f"🔄 Module reloaded: {module_path}")
            else:
                if "-" in module_path:
                    spec = importlib.util.spec_from_file_location(module_path, file_path)
                    if spec is None or spec.loader is None:
                        raise ImportError(f"Could not load spec for {file_path}")
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_path] = module
                    spec.loader.exec_module(module)
                    logger.debug(f"🆕 Module imported from file path (kebab-case support): {module_path}")
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
