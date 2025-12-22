# core/utils/tool_utils.py
import logging
from typing import Optional, Any, Dict, List, Sequence
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

# Almacenamiento temporal para herramientas cacheadas por contexto (account_id, telegram_id, workspace_id)
# Este caché ahora almacenará herramientas individuales una vez encontradas en la lista all_tools
_individual_tool_cache: Dict[str, BaseTool] = {}

async def get_tool_by_name(
    tool_name: str,
    all_tools: Sequence[BaseTool], # Ahora recibe la lista completa de herramientas
    account_id: str, # Mantener para la clave de caché
    telegram_id: Optional[str] = None, # Mantener para la clave de caché
    workspace_id: Optional[str] = None, # Mantener para la clave de caché
    **kwargs: Any
) -> Optional[BaseTool]:
    """
    Obtiene una instancia de herramienta por su nombre de una lista proporcionada,
    utilizando un caché para optimizar.
    """
    # Generar una clave de caché para el contexto actual y la herramienta individual
    context_key_parts = [account_id]
    if telegram_id:
        context_key_parts.append(telegram_id)
    if workspace_id:
        context_key_parts.append(workspace_id)
    context_key = ":".join(context_key_parts)
    individual_tool_cache_key = f"{context_key}:{tool_name}"

    # Intentar obtener la herramienta individual del caché
    if individual_tool_cache_key in _individual_tool_cache:
        return _individual_tool_cache[individual_tool_cache_key]

    # Buscar la herramienta por nombre en la lista proporcionada
    for tool in all_tools:
        if tool.name == tool_name:
            _individual_tool_cache[individual_tool_cache_key] = tool
            return tool
    
    logger.warning(f"Herramienta '{tool_name}' no encontrada en el conjunto de herramientas proporcionado para el contexto '{context_key}'.")
    return None