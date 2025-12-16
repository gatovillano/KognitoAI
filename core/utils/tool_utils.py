# core/utils/tool_utils.py
import logging
from typing import Optional, Any
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

# Almacenamiento temporal para herramientas cacheadas por account_id
_tool_cache = {}

async def get_tool_by_name(
    tool_name: str, 
    account_id: str, 
    telegram_id: Optional[str] = None,
    **kwargs: Any  # Acepta y ignora otros argumentos para evitar caídas
) -> Optional[BaseTool]:
    """
    Obtiene una instancia de herramienta por su nombre, utilizando un caché para optimizar.
    Esta función ahora es más robusta para manejar argumentos adicionales.
    """
    cache_key = f"{account_id}:{telegram_id}:{tool_name}" if telegram_id else f"{account_id}:{tool_name}"
    if cache_key in _tool_cache:
        return _tool_cache[cache_key]

    try:
        tool_instance = None
        # Prepara los kwargs que se pasarán al constructor de la herramienta
        tool_kwargs = {'account_id': account_id}
        if telegram_id:
            tool_kwargs['telegram_id'] = str(telegram_id)

        # Lógica de instanciación específica para cada herramienta
        if tool_name == "web_search":
            from tools.web_search_tool import WebSearchTool
            tool_instance = WebSearchTool(**tool_kwargs)
        elif tool_name == "knowledge_search":
            from tools.knowledge_search_tool import KnowledgeSearchTool
            tool_instance = KnowledgeSearchTool(**tool_kwargs)
        elif tool_name == "deep_research":
            from tools.deep_research_tool import DeepResearchTool
            tool_instance = DeepResearchTool(**tool_kwargs)
        elif tool_name == "duckduckgo_search":
            from tools.ddg_search_tool import create_ddg_search_tool
            tool_instance = create_ddg_search_tool(account_id=account_id)
        else:
            # Lógica de fallback para otras herramientas (si es necesario)
            # Esto puede necesitar ser expandido si otras herramientas son llamadas dinámicamente
            logger.warning(f"Herramienta '{tool_name}' no reconocida en la lógica principal de get_tool_by_name.")
            return None
        
        if tool_instance:
            _tool_cache[cache_key] = tool_instance
        return tool_instance

    except ImportError as e:
        logger.error(f"No se pudo importar el módulo para la herramienta '{tool_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error al instanciar la herramienta '{tool_name}': {e}", exc_info=True)
        return None