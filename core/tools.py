# core/tools.py

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
from tools.document_rag_tool import DocumentRAGTool

# Módulo de Creación de Contenido y Búsqueda
from tools.image_generation_tool import ImageGenerationTool
from tools.web_scraper_tool import WebScraperTool
# Importar la FÁBRICA de la herramienta de búsqueda web
from tools.web_search_tool import get_web_search_tool
from tools.analyze_text_for_insights_tool import AnalyzeTextForInsightsTool
from tools.github_repo_tool import GitHubRepoTool
from tools.mindmap_tool import MindmapTool
# Módulo de Insights Proactivos
from tools.get_proactive_insights_tool import GetProactiveInsightsTool
from tools.proactive_knowledge_linker_tool import ProactiveKnowledgeLinkerTool
from tools.knowledge_analysis_tool import KnowledgeAnalysisTool
from tools.comprehensive_web_analysis_tool import ComprehensiveWebAnalysisTool
from tools.get_analysis_results_tool import GetAnalysisResultsTool
# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


def get_all_langchain_tools(account_id: str = "", telegram_id: str = "") -> List[Tool]:
    """
    Recoge, instancia y devuelve una lista de todas las herramientas LangChain disponibles.

    Args:
        account_id (str): The account ID of the user, used for tools that require user-specific data.
        telegram_id (str): The Telegram ID of the user, used for specific tools that interact with Telegram.

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
        GetDocumentListTool, GetDocumentContentTool, DeleteDocumentTool, DocumentRAGTool,
        # Creación de Contenido y Búsqueda (excepto WebSearchTool que usa fábrica)
        ImageGenerationTool, WebScraperTool, AnalyzeTextForInsightsTool,
        # Herramienta de GitHub
        GitHubRepoTool,
        # Mapa Mental
        MindmapTool,
        # Insights Proactivos
        GetProactiveInsightsTool,
        ProactiveKnowledgeLinkerTool,
        KnowledgeAnalysisTool,
        ComprehensiveWebAnalysisTool,
        GetAnalysisResultsTool
    ]

    for ToolClass in tool_classes_to_instantiate:
        try:
            tool_instance = None # Inicializar a None

            # Manejo especial para GitHubRepoTool (por el github_token)
            if ToolClass.__name__ == "GitHubRepoTool":
                import os
                token = os.environ.get("GITHUB_TOKEN")
                tool_instance = ToolClass(github_token=token) if token else ToolClass()
            # Manejo para herramientas que requieren account_id y/o telegram_id en su constructor
            elif ToolClass in [
                AddNoteTool, GetNotesTool, UpdateNoteTool, DeleteNoteTool,
                ScheduleEventTool, GetAgendaTool, CancelEventTool, SetReminderTool,
                UpdateProfileTool, MemoryAddTool, GetDocumentListTool,
                GetDocumentContentTool, DeleteDocumentTool, DocumentRAGTool,
                ImageGenerationTool, GetProactiveInsightsTool,
                ProactiveKnowledgeLinkerTool, KnowledgeAnalysisTool, ComprehensiveWebAnalysisTool,
                GetAnalysisResultsTool
            ]:
                kwargs = {"account_id": account_id}
                if ToolClass in [SetReminderTool, ImageGenerationTool, GetDocumentContentTool]:
                    kwargs["telegram_id"] = telegram_id
                tool_instance = ToolClass(**kwargs)
                if ToolClass.__name__ == "KnowledgeAnalysisTool":
                    logger.debug(f"  [DEBUG] Intentando instanciar KnowledgeAnalysisTool con kwargs: {kwargs}")
                elif ToolClass.__name__ == "ProactiveKnowledgeLinkerTool":
                    logger.debug(f"  [DEBUG] Intentando instanciar ProactiveKnowledgeLinkerTool con kwargs: {kwargs}")
            # Para herramientas generales que no requieren argumentos específicos de usuario en su constructor
            else:
                tool_instance = ToolClass()
            
            if tool_instance: # Asegúrate de que la instancia se creó
                try:
                    # Check if the tool supports synchronous execution
                    if hasattr(tool_instance, '_run') and callable(getattr(tool_instance, '_run')):
                        available_tools.append(tool_instance)
                        logger.debug(f"  [+] Herramienta de clase cargada: {tool_instance.name}")
                        if ToolClass.__name__ == "KnowledgeAnalysisTool":
                            logger.debug(f"  [DEBUG] KnowledgeAnalysisTool añadida a la lista de herramientas disponibles")
                        elif ToolClass.__name__ == "ProactiveKnowledgeLinkerTool":
                            logger.debug(f"  [DEBUG] ProactiveKnowledgeLinkerTool añadida a la lista de herramientas disponibles")
                    else:
                        logger.error(f"  [ERROR] Herramienta {tool_instance.name} no soporta ejecución síncrona y no será añadida")
                        if ToolClass.__name__ == "KnowledgeAnalysisTool":
                            logger.error(f"  [ERROR] KnowledgeAnalysisTool no soporta ejecución síncrona")
                        elif ToolClass.__name__ == "ProactiveKnowledgeLinkerTool":
                            logger.error(f"  [ERROR] ProactiveKnowledgeLinkerTool no soporta ejecución síncrona")
                except Exception as e:
                    logger.error(f"  [ERROR] Error al verificar soporte síncrono para {tool_instance.name}: {e}")
            else:
                logger.debug(f"  [DEBUG] No se creó instancia para {ToolClass.__name__}")

        except Exception as e:
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
