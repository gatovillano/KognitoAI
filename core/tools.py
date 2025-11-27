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
from tools.conceptual_processing_tool import ConceptualProcessingTool
from tools.knowledge_graph_tool import KnowledgeGraphTool
from tools.comprehensive_web_analysis_tool import ComprehensiveWebAnalysisTool
from tools.insight_generation_tool import InsightGenerationTool
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
from tools.get_form_responses_tool import GetFormResponsesTool
from tools.get_proactive_insights_tool import GetProactiveInsightsTool
from tools.github_repo_tool import GitHubRepoTool
from tools.image_background_eraser_tool import ImageBackgroundEraserTool
from tools.image_generation_tool import ImageGenerationTool
from tools.insight_generation_tool import InsightGenerationTool
from tools.internal_knowledge_search_tool import InternalKnowledgeSearchTool
from tools.memory_add_tool import MemoryAddTool
from tools.knowledge_search_tool import KnowledgeSearchTool
from tools.mindmap_generator_tool import MindmapGeneratorTool
from tools.multi_query_search_tool import MultiQuerySearchTool
from tools.natural_query_interpreter_tool import NaturalQueryInterpreterTool

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
    ConceptualProcessingTool,
    KnowledgeGraphTool,
    InsightGenerationTool,
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
    GetFormResponsesTool,
    GetProactiveInsightsTool,
    GitHubRepoTool,
    ImageBackgroundEraserTool,
    ImageGenerationTool,
    InternalKnowledgeSearchTool,
    MemoryAddTool,
    KnowledgeSearchTool,
    MindmapGeneratorTool,
    MultiQuerySearchTool,
    NaturalQueryInterpreterTool,
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
    ContactProfileTool,
]

# Global singletons for shared dependencies
_graph_db_instance = None
_graph_integration_instance = None

async def get_shared_dependencies():
    """
    Returns shared instances of GraphDB and GraphIntegration, initializing them if necessary.
    """
    global _graph_db_instance, _graph_integration_instance
    
    if _graph_db_instance and _graph_integration_instance:
        return _graph_db_instance, _graph_integration_instance

    try:
        from knowledge_graph.graph_database import GraphDB
        from knowledge_graph.graph_integration import GraphIntegration
        from core.config import settings

        if settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password:
            if not _graph_db_instance:
                _graph_db_instance = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
                _graph_db_instance.connect()
                logger.info("✅ Shared GraphDB instance created.")
            
            if not _graph_integration_instance:
                _graph_integration_instance = GraphIntegration(_graph_db_instance)
                logger.info("✅ Shared GraphIntegration instance created.")
                
            return _graph_db_instance, _graph_integration_instance
        else:
            logger.warning("⚠️ Missing Neo4j credentials, graph tools will not be initialized.")
            return None, None
    except Exception as e:
        logger.error(f"❌ Error initializing shared dependencies: {e}", exc_info=True)
        return None, None

async def get_tool_by_name(tool_name: str, account_id: str, telegram_id: Optional[int] = None, thread_id: Optional[str] = None) -> Optional[Tool]:
    """
    Instantiates and returns a single tool by its name.
    """
    logger.info(f"🔍 Buscando herramienta: {tool_name}")
    
    target_class = None
    for ToolClass in tool_classes_to_instantiate:
        # Try multiple ways to get the name attribute
        class_name = None
        
        # Method 1: Direct attribute access
        if hasattr(ToolClass, 'name'):
            class_name = getattr(ToolClass, 'name', None)
        
        # Method 2: Check __fields__ for Pydantic models
        if not class_name and hasattr(ToolClass, '__fields__'):
            name_field = ToolClass.__fields__.get('name')
            if name_field and hasattr(name_field, 'default'):
                class_name = name_field.default
        
        # Method 3: Check __dict__
        if not class_name:
            class_name = ToolClass.__dict__.get('name', ToolClass.__name__)
        
        logger.debug(f"  Comparando '{class_name}' con '{tool_name}' para {ToolClass.__name__}")
        
        if class_name == tool_name:
            target_class = ToolClass
            logger.info(f"✅ Herramienta encontrada: {ToolClass.__name__}")
            break
    
    if not target_class:
        # Check factory tools
        if tool_name == "duckduckgo_search":
             from tools.ddg_search_tool import create_ddg_search_tool
             logger.info(f"✅ Herramienta factory encontrada: DuckDuckGoSearchTool")
             return create_ddg_search_tool(account_id=account_id)
        if tool_name == "web_search":
             from tools.web_search_tool import get_web_search_tool
             logger.info(f"✅ Herramienta factory encontrada: WebSearchTool")
             return get_web_search_tool(account_id=account_id)
        
        logger.error(f"❌ Herramienta '{tool_name}' no encontrada en tool_classes_to_instantiate")
        return None

    return await _instantiate_tool(target_class, account_id, telegram_id, thread_id)


async def _instantiate_tool(ToolClass, account_id: str, telegram_id: Optional[int] = None, thread_id: Optional[str] = None) -> Optional[Tool]:
    """
    Helper to instantiate a tool class with dependencies.
    """
    try:
        tool_instance = None
        tool_name = getattr(ToolClass, 'name', ToolClass.__name__)

        # --- Dependency Injection for Graph Tools ---
        if ToolClass in [KnowledgeGraphTool, ConceptualProcessingTool]:
            graph_db, graph_integration = await get_shared_dependencies()
            if graph_db and graph_integration:
                tool_kwargs = {
                    'account_id': account_id,
                    'graph_integration': graph_integration,
                    'graph_db': graph_db
                }
                if telegram_id is not None:
                    tool_kwargs['telegram_id'] = str(telegram_id)
                tool_instance = ToolClass(**tool_kwargs)
            else:
                logger.warning(f"Skipping {tool_name} due to missing graph dependencies.")
                return None
        
        # --- GitHubRepoTool ---
        elif ToolClass.__name__ == "GitHubRepoTool":
            import os
            token = os.environ.get("GITHUB_TOKEN")
            github_kwargs = {"account_id": account_id}
            if token:
                github_kwargs["github_token"] = token
            if telegram_id is not None:
                github_kwargs["telegram_id"] = str(telegram_id)
            if thread_id is not None:
                github_kwargs["thread_id"] = thread_id
            tool_instance = ToolClass(**github_kwargs)

        # --- Standard Tools ---
        elif hasattr(ToolClass, 'model_fields') and 'account_id' in ToolClass.model_fields:
            tool_kwargs = {}
            if 'account_id' in ToolClass.model_fields:
                tool_kwargs['account_id'] = account_id
            if 'telegram_id' in ToolClass.model_fields and telegram_id is not None:
                tool_kwargs['telegram_id'] = str(telegram_id)
            
            tools_to_exclude_thread_id = [
                "KnowledgeSearchTool", "WebSearchTool", "DuckDuckGoSearchTool", "UpdateProfileTool",
                "InternalKnowledgeSearchTool", "GetDocumentListTool", "GetDocumentContentTool", "GetNotesTool",
                "GetAgendaTool", "CancelEventTool", "SetReminderTool", "ScheduleEventTool", "UpdateNoteTool",
                "DeleteNoteTool", "DeleteDocumentTool", "ExtractDocumentTitlesTool", "UpdateDocumentMetadataTool",
                "ImageGenerationTool", "ImageBackgroundEraserTool", "WebScraperTool", "AddWebToRAGTool",
                "AnalyzeTextForInsightsTool", "AnalyzeCodeForInsightsTool", "ComprehensiveWebAnalysisTool",
                "GetAnalysisResultsTool", "ScopedRagAnalysisTool", "MultiQuerySearchTool", "KnowledgeGraphTool",
                "ConceptualProcessingTool", "ScheduleToolExecutionTool", "ListScheduledToolsTool",
                "NaturalQueryInterpreterTool", "GetProactiveInsightsTool", "MindmapGeneratorTool",
                "ConversationHistoryAnalyzerTool", "ConversationContextAnalyzerTool", "DocumentRAGTool",
                "ContactProfileTool", "GetFormResponsesTool", "AddNoteTool"
            ]

            if 'thread_id' in ToolClass.model_fields and thread_id is not None and \
               ToolClass.__name__ not in tools_to_exclude_thread_id:
                tool_kwargs['thread_id'] = thread_id

            logger.info(f"Instanciando {ToolClass.__name__} con kwargs: {tool_kwargs}")
            tool_instance = ToolClass(**tool_kwargs)
        
        # --- No-Args Tools ---
        else:
            logger.info(f"Instanciando {ToolClass.__name__} sin kwargs.")
            tool_instance = ToolClass()

        return tool_instance
    except Exception as e:
        logger.error(f"❌ Failed to instantiate tool '{ToolClass.__name__}': {e}", exc_info=True)
        return None

async def get_all_langchain_tools(account_id: str, telegram_id: Optional[int] = None, thread_id: Optional[str] = None) -> List[Tool]:
    """
    Recoge, instancia y devuelve una lista de todas las herramientas LangChain disponibles.
    """
    logger.info("⚙️ Ensamblando la caja de herramientas del agente...")
    available_tools: List[Tool] = []
    failed_tools: List[str] = []

    # Ensure shared dependencies are ready
    await get_shared_dependencies()

    # Instantiate explicit tool classes
    for ToolClass in tool_classes_to_instantiate:
        tool_name = getattr(ToolClass, 'name', ToolClass.__name__)
        logger.info(f"🔧 Intentando instanciar: {tool_name} ({ToolClass.__name__})")
        tool_instance = await _instantiate_tool(ToolClass, account_id, telegram_id, thread_id)
        if tool_instance:
            available_tools.append(tool_instance)
            logger.info(f"✅ {tool_name} instanciada correctamente")
        else:
            failed_tools.append(tool_name)
            logger.warning(f"❌ {tool_name} falló al instanciarse")

    # Instantiate factory tools
    try:
        from tools.ddg_search_tool import create_ddg_search_tool
        ddg_search_tool_instance = create_ddg_search_tool(account_id=account_id)
        available_tools.append(ddg_search_tool_instance)
        logger.info("✅ DuckDuckGoSearchTool instanciada correctamente")
    except Exception as e:
        logger.error(f"❌ Fallo al instanciar DuckDuckGoSearchTool: {e}", exc_info=True)
        failed_tools.append("DuckDuckGoSearchTool")

    try:
        from tools.web_search_tool import get_web_search_tool
        web_search_tool_instance = get_web_search_tool(account_id=account_id)
        available_tools.append(web_search_tool_instance)
        logger.info("✅ WebSearchTool instanciada correctamente")
    except Exception as e:
        logger.error(f"❌ Fallo al instanciar WebSearchTool: {e}", exc_info=True)
        failed_tools.append("WebSearchTool")

    logger.info(f"--- 🧰 Caja de Herramientas Ensamblada ({len(available_tools)} herramientas) ---")
    if failed_tools:
        logger.warning(f"⚠️ Herramientas que fallaron al instanciarse ({len(failed_tools)}): {', '.join(failed_tools)}")
    
    return available_tools
