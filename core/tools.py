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
from typing import List, Optional

from langchain_core.tools import Tool
from langchain_core.utils.function_calling import convert_to_openai_tool

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)




import logging
import os
from typing import List, Optional

from langchain_core.tools import Tool
from langchain_core.utils.function_calling import convert_to_openai_tool

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# Explicit imports for tool classes
from tools.add_note_tool import AddNoteTool
from tools.add_web_to_rag_tool import AddWebToRAGTool
from tools.analyze_code_for_insights_tool import AnalyzeCodeForInsightsTool
from tools.analyze_text_for_insights_tool import AnalyzeTextForInsightsTool
from tools.cancel_event_tool import CancelEventTool
from tools.cognee_conceptual_processing_tool import CogneeConceptualProcessingTool
from tools.cognee_knowledge_graph_tool import CogneeKnowledgeGraphTool
from tools.comprehensive_web_analysis_tool import ComprehensiveWebAnalysisTool
from tools.conversation_context_analyzer_tool import ConversationContextAnalyzerTool
from tools.conversation_history_analyzer_tool import ConversationHistoryAnalyzerTool
from tools.delete_document_tool import DeleteDocumentTool
from tools.delete_note_tool import DeleteNoteTool
from tools.document_rag_tool import DocumentRAGTool
from tools.extract_document_titles_tool import ExtractDocumentTitlesTool
from tools.get_agenda_tool import GetAgendaTool
from tools.get_analysis_results_tool import GetAnalysisResultsTool
from tools.get_document_content_tool import GetDocumentContentTool
from tools.get_document_list_tool import GetDocumentListTool
from tools.get_notes_tool import GetNotesTool
from tools.get_proactive_insights_tool import GetProactiveInsightsTool
from tools.github_repo_tool import GitHubRepoTool
from tools.image_background_eraser_tool import ImageBackgroundEraserTool
from tools.image_generation_tool import ImageGenerationTool
from tools.internal_knowledge_search_tool import InternalKnowledgeSearchTool
from tools.knowledge_analysis_tool import KnowledgeAnalysisTool
from tools.memory_add_tool import MemoryAddTool
from tools.knowledge_search_tool import KnowledgeSearchTool
from tools.mindmap_generator_tool import MindmapGeneratorTool
from tools.multi_query_search_tool import MultiQuerySearchTool
from tools.natural_query_interpreter_tool import NaturalQueryInterpreterTool
from tools.proactive_knowledge_linker_tool import ProactiveKnowledgeLinkerTool
from tools.schedule_event_tool import ScheduleEventTool
from tools.scoped_rag_analysis_tool import ScopedRagAnalysisTool
from tools.set_reminder_tool import SetReminderTool
from tools.update_document_metadata_tool import UpdateDocumentMetadataTool
from tools.update_note_tool import UpdateNoteTool
from tools.update_user_profile import UpdateProfileTool
from tools.contact_profile_tool import ContactProfileTool


from tools.web_scraper_tool import WebScraperTool
from tools.schedule_tool_execution import ScheduleToolExecutionTool, ListScheduledToolsTool
from tools.search_notes_tool import SearchNotesTool

# List of all tool classes to instantiate directly.
tool_classes_to_instantiate = [
    AddNoteTool,
    AddWebToRAGTool,
    AnalyzeCodeForInsightsTool,
    AnalyzeTextForInsightsTool,
    CancelEventTool,
    CogneeConceptualProcessingTool,
    CogneeKnowledgeGraphTool,
    ComprehensiveWebAnalysisTool,
    ConversationContextAnalyzerTool,
    ConversationHistoryAnalyzerTool,
    DeleteDocumentTool,
    DeleteNoteTool,
    DocumentRAGTool,
    ExtractDocumentTitlesTool,
    GetAgendaTool,
    GetAnalysisResultsTool,
    GetDocumentContentTool,
    GetDocumentListTool,
    GetNotesTool,
    GetProactiveInsightsTool,
    GitHubRepoTool,
    ImageBackgroundEraserTool,
    ImageGenerationTool,
    InternalKnowledgeSearchTool,
    KnowledgeAnalysisTool,
    MemoryAddTool,
    KnowledgeSearchTool,
    MindmapGeneratorTool,
    MultiQuerySearchTool,
    NaturalQueryInterpreterTool,
    ProactiveKnowledgeLinkerTool,
    ScheduleEventTool,
    ScopedRagAnalysisTool,
    SearchNotesTool,
    SetReminderTool,
    UpdateDocumentMetadataTool,
    UpdateNoteTool,
    UpdateProfileTool,
    WebScraperTool,
    ScheduleToolExecutionTool,
    ListScheduledToolsTool,
    ContactProfileTool, # ¡NUEVA HERRAMIENTA!
]

def get_all_langchain_tools(account_id: str, telegram_id: Optional[int] = None, thread_id: Optional[str] = None) -> List[Tool]:
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

    # Instanciar herramientas cargadas explícitamente
    for ToolClass in tool_classes_to_instantiate:
        try:
            tool_instance = None
            tool_name = getattr(ToolClass, 'name', ToolClass.__name__) # Default to class name for logging

            # Special handling for GitHubRepoTool (due to optional github_token and required account_id)
            if ToolClass.__name__ == "GitHubRepoTool":
                import os
                token = os.environ.get("GITHUB_TOKEN")
                github_kwargs = {"account_id": account_id} # account_id is always required for GitHubRepoTool
                if token: # Only add github_token if it exists
                    github_kwargs["github_token"] = token
                if telegram_id is not None: # Pass telegram_id if it's not None
                    github_kwargs["telegram_id"] = str(telegram_id)
                if thread_id is not None: # Pass thread_id if it's not None
                    github_kwargs["thread_id"] = thread_id
                # Assuming workspace_id is also passed to get_all_langchain_tools if needed
                # if workspace_id is not None: 
                #     github_kwargs["workspace_id"] = workspace_id
                tool_instance = ToolClass(**github_kwargs)
            # Tools requiring account_id and optionally telegram_id and thread_id
            elif hasattr(ToolClass, 'model_fields') and 'account_id' in ToolClass.model_fields:
                tool_kwargs = {}

                if 'account_id' in ToolClass.model_fields:
                    tool_kwargs['account_id'] = account_id

                if 'telegram_id' in ToolClass.model_fields and telegram_id is not None:
                    tool_kwargs['telegram_id'] = str(telegram_id)

                # Define a list of tools that should NOT receive thread_id
                tools_to_exclude_thread_id = [
                    "KnowledgeSearchTool",
                    "WebSearchTool",
                    "DuckDuckGoSearchTool",
                    "UpdateProfileTool",
                    "InternalKnowledgeSearchTool",
                    "GetDocumentListTool",
                    "GetDocumentContentTool",
                    "GetNotesTool",
                    "GetAgendaTool",
                    "CancelEventTool",
                    "SetReminderTool",
                    "ScheduleEventTool",
                    "UpdateNoteTool",
                    "DeleteNoteTool",
                    "DeleteDocumentTool",
                    "ExtractDocumentTitlesTool",
                    "UpdateDocumentMetadataTool",
                    "ImageGenerationTool",
                    "ImageBackgroundEraserTool",
                    "WebScraperTool",
                    "AddWebToRAGTool",
                    "AnalyzeTextForInsightsTool",
                    "AnalyzeCodeForInsightsTool",
                    "KnowledgeAnalysisTool",
                    "ComprehensiveWebAnalysisTool",
                    "GetAnalysisResultsTool",
                    "ScopedRagAnalysisTool",
                    "MultiQuerySearchTool",
                    "CogneeKnowledgeGraphTool",
                    "CogneeConceptualProcessingTool",
                    "ScheduleToolExecutionTool",
                    "ListScheduledToolsTool",
                    
                    "NaturalQueryInterpreterTool",
                    "ProactiveKnowledgeLinkerTool",
                    "GetProactiveInsightsTool",
                    "MindmapGeneratorTool",
                    "ConversationHistoryAnalyzerTool",
                    "ConversationContextAnalyzerTool",
                    "DocumentRAGTool",
                    "ContactProfileTool", # NUEVA HERRAMIENTA
                ]

                # Add thread_id ONLY if the tool explicitly has the field AND is NOT in the exclusion list
                if 'thread_id' in ToolClass.model_fields and thread_id is not None and \
                   ToolClass.__name__ not in tools_to_exclude_thread_id:
                    tool_kwargs['thread_id'] = thread_id

                tool_instance = ToolClass(**tool_kwargs)
            # General tools that do not require account_id or telegram_id in constructor
            else:
                tool_instance = ToolClass()

            if tool_instance:
                available_tools.append(tool_instance)
                logger.info(f"  [+] Herramienta cargada: {tool_instance.name}")
        except Exception as e:
            # Use tool_name obtained safely for error logging
            logger.error(f"❌ Fallo al instanciar la herramienta '{tool_name}': {e}", exc_info=True)

    # Instanciar herramientas que provienen de funciones de fábrica.
    try:
        # Importar la FÁBRICA de la herramienta de búsqueda web
        from tools.ddg_search_tool import create_ddg_search_tool
        ddg_search_tool_instance = create_ddg_search_tool(account_id=account_id)
        available_tools.append(ddg_search_tool_instance)
        logger.info(f"  [+] Herramienta de fábrica cargada: {ddg_search_tool_instance.name}")
    except Exception as e:
        logger.error(f"❌ Fallo al instanciar DuckDuckGoSearchTool desde su fábrica: {e}", exc_info=True)

    try:
        # Importar la FÁBRICA de la herramienta de búsqueda web
        from tools.web_search_tool import get_web_search_tool
        web_search_tool_instance = get_web_search_tool(account_id=account_id)
        available_tools.append(web_search_tool_instance)
        logger.info(f"  [+] Herramienta de fábrica cargada: {web_search_tool_instance.name}")
    except Exception as e:
        logger.error(f"❌ Fallo al instanciar WebSearchTool desde su fábrica: {e}", exc_info=True)

    # --- Resumen Final de Herramientas Cargadas ---
    logger.info("--- 🧰 Caja de Herramientas Ensamblada ---")
    for tool in available_tools:
        logger.info(f"  ✅ {tool.name}")
    logger.info(f"  Total de herramientas operativas: {len(available_tools)}")
    logger.info("-------------------------------------------")

    return available_tools
