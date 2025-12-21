# core/tools.py

"""
Módulo de Ensamblaje de Herramientas de LangChain.
"""

import logging
import os
from typing import List, Optional, Any

from langchain_core.tools import Tool

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# Importaciones explícitas para las clases de herramientas
from tools.add_note_tool import AddNoteTool
from tools.add_web_to_rag_tool import AddWebToRAGTool
from tools.analyze_code_for_insights_tool import AnalyzeCodeForInsightsTool
from tools.analyze_text_for_insights_tool import AnalyzeTextForInsightsTool
from tools.cancel_event_tool import CancelEventTool
from tools.conceptual_processing_tool import ConceptualProcessingTool
from tools.knowledge_graph_tool import KnowledgeGraphTool
from tools.comprehensive_web_analysis_tool import ComprehensiveWebAnalysisTool
from tools.deep_research_tool import DeepResearchTool
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

# Lista de todas las clases de herramientas a instanciar directamente.
tool_classes_to_instantiate = [
    AddNoteTool, AddWebToRAGTool, AnalyzeCodeForInsightsTool, AnalyzeTextForInsightsTool,
    CancelEventTool, ConceptualProcessingTool, KnowledgeGraphTool,
    InsightGenerationTool, ComprehensiveWebAnalysisTool, ConversationContextAnalyzerTool,
    ConversationHistoryAnalyzerTool, DeleteDocumentTool, DeleteNoteTool, DocumentRAGTool,
    ExtractDocumentTitlesTool, GetAgendaTool, GetAnalysisResultsTool, GetDocumentContentTool,
    GetDocumentListTool, GetNotesTool, GetFormResponsesTool, GetProactiveInsightsTool,
    GitHubRepoTool, ImageBackgroundEraserTool, ImageGenerationTool, InternalKnowledgeSearchTool,
    MemoryAddTool, KnowledgeSearchTool, MindmapGeneratorTool, MultiQuerySearchTool,
    NaturalQueryInterpreterTool, ScheduleEventTool, ScopedRagAnalysisTool, SearchNotesTool,
    SetReminderTool, UpdateDocumentMetadataTool, UpdateNoteTool, UpdateProfileTool,
    WebScraperTool, ScheduleToolExecutionTool, ListScheduledToolsTool, ContactProfileTool,
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

async def _instantiate_tool(
    ToolClass,
    account_id: str,
    telegram_id: Optional[int] = None,
    thread_id: Optional[str] = None,
    workspace_id: Optional[str] = None, # Añadir workspace_id aquí
    graph_db: Optional[Any] = None,
    enhanced_memory_manager: Optional[Any] = None
) -> Optional[Tool]:
    """
    Helper to instantiate a tool class with dependencies.
    """
    try:
        tool_instance = None
        tool_name = getattr(ToolClass, 'name', ToolClass.__name__)

        # --- Dependency Injection for Graph Tools ---
        if ToolClass in [KnowledgeGraphTool, ConceptualProcessingTool]:
            _graph_db, _graph_integration = await get_shared_dependencies()

            if _graph_db and _graph_integration:
                tool_kwargs = {
                    'account_id': account_id,
                    'graph_integration': _graph_integration,
                    'graph_db': _graph_db
                }
                if telegram_id is not None:
                    tool_kwargs['telegram_id'] = str(telegram_id)
                if workspace_id is not None: # Pasar workspace_id a herramientas de grafo
                    tool_kwargs['workspace_id'] = workspace_id
                tool_instance = ToolClass(**tool_kwargs)
            else:
                logger.warning(f"Skipping {tool_name} due to missing graph dependencies.")
                return None
        
        # --- GitHubRepoTool ---
        elif ToolClass.__name__ == "GitHubRepoTool":
            token = os.environ.get("GITHUB_TOKEN")
            github_kwargs = {"account_id": account_id}
            if token:
                github_kwargs["github_token"] = token
            if telegram_id is not None:
                github_kwargs["telegram_id"] = str(telegram_id)
            if thread_id is not None:
                github_kwargs["thread_id"] = thread_id
            if workspace_id is not None: # Pasar workspace_id a GitHubRepoTool
                github_kwargs["workspace_id"] = workspace_id
            tool_instance = ToolClass(**github_kwargs)

        # --- Standard Tools ---
        elif hasattr(ToolClass, 'model_fields') and 'account_id' in ToolClass.model_fields:
            tool_kwargs = {'account_id': account_id}
            if 'telegram_id' in ToolClass.model_fields and telegram_id is not None:
                tool_kwargs['telegram_id'] = str(telegram_id)
            if 'thread_id' in ToolClass.model_fields and thread_id is not None:
                tool_kwargs['thread_id'] = thread_id # Pasar thread_id a herramientas estándar
            if 'workspace_id' in ToolClass.model_fields and workspace_id is not None:
                tool_kwargs['workspace_id'] = workspace_id # Pasar workspace_id a herramientas estándar
            tool_instance = ToolClass(**tool_kwargs)
        
        # --- No-Args Tools ---
        else:
            tool_instance = ToolClass()

        return tool_instance
    except Exception as e:
        logger.error(f"❌ Failed to instantiate tool '{ToolClass.__name__}': {e}", exc_info=True)
        return None

async def get_all_langchain_tools(
    account_id: str,
    telegram_id: Optional[int] = None,
    thread_id: Optional[str] = None,
    workspace_id: Optional[str] = None # Añadir workspace_id aquí
) -> List[Tool]:
    """
    Recoge, instancia y devuelve una lista de todas las herramientas LangChain disponibles.
    """
    logger.info("⚙️ Assembling agent toolbox...")
    available_tools: List[Tool] = []
    failed_tools: List[str] = []

    await get_shared_dependencies()

    for ToolClass in tool_classes_to_instantiate:
        tool_name = getattr(ToolClass, 'name', ToolClass.__name__)
        tool_instance = await _instantiate_tool(ToolClass, account_id, telegram_id, thread_id, workspace_id) # Pasar workspace_id
        if tool_instance:
            available_tools.append(tool_instance)
        else:
            failed_tools.append(tool_name)

    # Instantiate factory tools
    try:
        from tools.ddg_search_tool import create_ddg_search_tool
        ddg_search_tool_instance = create_ddg_search_tool(account_id=account_id)
        available_tools.append(ddg_search_tool_instance)
    except Exception as e:
        failed_tools.append("DuckDuckGoSearchTool")

    try:
        from tools.deep_research_tool import DeepResearchTool
        from tools.add_web_to_rag_tool import AddWebToRAGTool
        
        add_web_to_rag_instance = AddWebToRAGTool(account_id=account_id)
        ws_tool = next((t for t in available_tools if t.name == "web_search"), None)
        if ws_tool:
            deep_research_instance = DeepResearchTool(
                web_search_tool=ws_tool,
                add_web_to_rag_tool=add_web_to_rag_instance,
                account_id=account_id,
                telegram_id=telegram_id,
                thread_id=thread_id,
                workspace_id=workspace_id
            )
            if deep_research_instance:
                available_tools.append(deep_research_instance)
    except Exception as e:
        failed_tools.append("DeepResearchTool")


    logger.info(f"--- 🧰 Toolbox Assembled ({len(available_tools)} tools) ---")
    if failed_tools:
        logger.warning(f"⚠️ Failed to instantiate ({len(failed_tools)}): {', '.join(failed_tools)}")
    
    return available_tools