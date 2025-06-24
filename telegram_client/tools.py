# telegram_bot/tools.py

"""
Módulo de Ensamblaje de Herramientas de LangChain.

Este archivo actúa como el punto central de recolección para todas las herramientas
disponibles para el agente de IA. Su única responsabilidad es importar todas las
clases de herramientas individuales y las funciones de fábrica, instanciarlas
y devolver una lista completa de objetos `Tool` listos para ser utilizados por
el `AgentExecutor`.

La función `get_all_langchain_tools` está diseñada para ser robusta, utilizando
bloques `try...except` para cada herramienta. Esto asegura que si una herramienta
falla al inicializarse (por ejemplo, debido a una API key faltante), el resto del
bot pueda seguir funcionando con las herramientas que sí se cargaron correctamente.
"""

import logging
from typing import List

from langchain_core.tools import Tool

# --- Importar todas las herramientas refactorizadas desde la carpeta `tools/` ---

# Módulo de Notas
from tools.add_note_tool import AddNoteTool
from tools.get_notes_tool import GetNotesTool
from tools.update_note_tool import UpdateNoteTool
from tools.delete_note_tool import DeleteNoteTool

# Módulo de Agenda y Recordatorios
from tools.schedule_event_tool import ScheduleEventTool
from tools.get_agenda_tool import GetAgendaTool
from tools.cancel_event_tool import CancelEventTool
from tools.set_reminder_tool import SetReminderTool

# Módulo de Perfil y Memoria
from tools.update_user_profile import UpdateProfileTool
from tools.memory_add_tool import MemoryAddTool

# Módulo de Gestión de Documentos
from tools.get_document_list_tool import GetDocumentListTool
from tools.get_document_content_tool import GetDocumentContentTool
from tools.delete_document_tool import DeleteDocumentTool

# Módulo de Creación de Contenido y Búsqueda
from tools.image_generation_tool import ImageGenerationTool
from tools.web_scraper_tool import WebScraperTool
# Importar la FÁBRICA de la herramienta de búsqueda web
from tools.web_search_tool import get_web_search_tool
from tools.analyze_text_for_insights_tool import AnalyzeTextForInsightsTool
from tools.github_repo_tool import GitHubRepoTool
# Módulo de Insights Proactivos
from tools.get_proactive_insights_tool import GetProactiveInsightsTool
# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


def get_all_langchain_tools() -> List[Tool]:
    """
    Recoge, instancia y devuelve una lista de todas las herramientas LangChain disponibles.

    Returns:
        Una lista de objetos `Tool` que el agente podrá utilizar.
    """
    logger.info("⚙️ Ensamblando la caja de herramientas del agente...")
    available_tools: List[Tool] = []

    # Lista de todas las clases de herramientas que se instancian directamente.
    tool_classes_to_instantiate = [
        # Notas
        AddNoteTool, GetNotesTool, UpdateNoteTool, DeleteNoteTool,
        # Agenda y Recordatorios
        ScheduleEventTool, GetAgendaTool, CancelEventTool, SetReminderTool,
        # Perfil y Memoria
        UpdateProfileTool, MemoryAddTool,
        # Documentos
        GetDocumentListTool, GetDocumentContentTool, DeleteDocumentTool,
        # Contenido y Web (excepto las que usan fábricas)
        ImageGenerationTool, WebScraperTool, AnalyzeTextForInsightsTool,
        # Herramienta de GitHub
        GitHubRepoTool,
        # Insights Proactivos
        GetProactiveInsightsTool,  # Asegúrate de que esta herramienta esté importada correctamente
    ]

    # Instanciar cada herramienta basada en clase de forma segura.
    for ToolClass in tool_classes_to_instantiate:
        try:
            tool_instance = ToolClass()
            available_tools.append(tool_instance)
            logger.debug(f"  [+] Herramienta de clase cargada: {tool_instance.name}")
        except Exception as e:
            # Si una herramienta falla, se loguea el error pero no se detiene el proceso.
            tool_name = getattr(ToolClass, 'name', 'NombreDesconocido')
            logger.error(f"❌ Fallo al instanciar la herramienta '{tool_name}': {e}", exc_info=True)
            logger.error(f"Detalles de la excepción para '{tool_name}': {str(e)}", exc_info=True)

    # Instanciar herramientas que provienen de funciones de fábrica.
    try:
        web_search_tool_instance = get_web_search_tool()
        available_tools.append(web_search_tool_instance)
        logger.debug(f"  [+] Herramienta de fábrica cargada: {web_search_tool_instance.name}")
    except Exception as e:
        logger.error(f"❌ Fallo al instanciar WebSearchTool desde su fábrica: {e}", exc_info=True)
    
    # --- Resumen Final de Herramientas Cargadas ---
    logger.info("--- 🧰 Caja de Herramientas Ensamblada ---")
    for tool in available_tools:
        logger.info(f"  ✅ {tool.name}")
    logger.info(f"  Total de herramientas operativas: {len(available_tools)}")
    logger.info("-------------------------------------------")

    return available_tools
