# core/tools.py

"""
Módulo de Ensamblaje de Herramientas de LangChain.
"""

import logging
import os
from typing import List, Optional, Any
import importlib

from langchain_core.tools import Tool

# --- TOOL IMPORTS (from tools/ directory) ---

def _import_tool_class(module_name: str, class_name: str):
	"""
	Try absolute import only (tools.xxx). In Docker we require the project root / package
	to be on PYTHONPATH so absolute imports resolve reliably.
	"""
	try:
		module = importlib.import_module(f"tools.{module_name}")
	except Exception as e:
		logger.error(
			"Failed to import tools.%s. Ensure the 'tools' package is on PYTHONPATH in the Docker container. (%s)",
			module_name,
			e,
			exc_info=True
		)
		# Raise a clear ImportError so failures are visible early
		raise ImportError(
			f"Unable to import 'tools.{module_name}'. Make sure the project root is on PYTHONPATH in the container."
		) from e
	return getattr(module, class_name)

# Bind all tool classes used below.
AddNoteTool = _import_tool_class("add_note_tool", "AddNoteTool")
AddWebToRAGTool = _import_tool_class("add_web_to_rag_tool", "AddWebToRAGTool")
AnalyzeCodeForInsightsTool = _import_tool_class("analyze_code_for_insights_tool", "AnalyzeCodeForInsightsTool")
AnalyzeTextForInsightsTool = _import_tool_class("analyze_text_for_insights_tool", "AnalyzeTextForInsightsTool")
CancelEventTool = _import_tool_class("cancel_event_tool", "CancelEventTool")
ConceptualProcessingTool = _import_tool_class("conceptual_processing_tool", "ConceptualProcessingTool")
KnowledgeGraphTool = _import_tool_class("knowledge_graph_tool", "KnowledgeGraphTool")
ComprehensiveWebAnalysisTool = _import_tool_class("comprehensive_web_analysis_tool", "ComprehensiveWebAnalysisTool")
InsightGenerationTool = _import_tool_class("insight_generation_tool", "InsightGenerationTool")
ConversationContextAnalyzerTool = _import_tool_class("conversation_context_analyzer_tool", "ConversationContextAnalyzerTool")
ConversationHistoryAnalyzerTool = _import_tool_class("conversation_history_analyzer_tool", "ConversationHistoryAnalyzerTool")
DeleteDocumentTool = _import_tool_class("delete_document_tool", "DeleteDocumentTool")
DeleteNoteTool = _import_tool_class("delete_note_tool", "DeleteNoteTool")
DocumentRAGTool = _import_tool_class("document_rag_tool", "DocumentRAGTool")
ExtractDocumentTitlesTool = _import_tool_class("extract_document_titles_tool", "ExtractDocumentTitlesTool")
GetAgendaTool = _import_tool_class("get_agenda_tool", "GetAgendaTool")
GetAnalysisResultsTool = _import_tool_class("get_analysis_results_tool", "GetAnalysisResultsTool")
GetDocumentContentTool = _import_tool_class("get_document_content_tool", "GetDocumentContentTool")
GetDocumentListTool = _import_tool_class("get_document_list_tool", "GetDocumentListTool")
GetNotesTool = _import_tool_class("get_notes_tool", "GetNotesTool")
GetFormResponsesTool = _import_tool_class("get_form_responses_tool", "GetFormResponsesTool")
GetProactiveInsightsTool = _import_tool_class("get_proactive_insights_tool", "GetProactiveInsightsTool")
GitHubRepoTool = _import_tool_class("github_repo_tool", "GitHubRepoTool")
ImageBackgroundEraserTool = _import_tool_class("image_background_eraser_tool", "ImageBackgroundEraserTool")
ImageGenerationTool = _import_tool_class("image_generation_tool", "ImageGenerationTool")
InternalKnowledgeSearchTool = _import_tool_class("internal_knowledge_search_tool", "InternalKnowledgeSearchTool")
MemoryAddTool = _import_tool_class("memory_add_tool", "MemoryAddTool")
KnowledgeSearchTool = _import_tool_class("knowledge_search_tool", "KnowledgeSearchTool")
MindmapGeneratorTool = _import_tool_class("mindmap_generator_tool", "MindmapGeneratorTool")
MultiQuerySearchTool = _import_tool_class("multi_query_search_tool", "MultiQuerySearchTool")
NaturalQueryInterpreterTool = _import_tool_class("natural_query_interpreter_tool", "NaturalQueryInterpreterTool")
ScheduleEventTool = _import_tool_class("schedule_event_tool", "ScheduleEventTool")
ScopedRagAnalysisTool = _import_tool_class("scoped_rag_analysis_tool", "ScopedRagAnalysisTool")
SetReminderTool = _import_tool_class("set_reminder_tool", "SetReminderTool")
UpdateDocumentMetadataTool = _import_tool_class("update_document_metadata_tool", "UpdateDocumentMetadataTool")
UpdateNoteTool = _import_tool_class("update_note_tool", "UpdateNoteTool")
UpdateProfileTool = _import_tool_class("update_user_profile", "UpdateProfileTool")
ContactProfileTool = _import_tool_class("contact_profile_tool", "ContactProfileTool")
WebScraperTool = _import_tool_class("web_scraper_tool", "WebScraperTool")
ScheduleToolExecutionTool = _import_tool_class("schedule_tool_execution", "ScheduleToolExecutionTool")
ListScheduledToolsTool = _import_tool_class("schedule_tool_execution", "ListScheduledToolsTool")
SearchNotesTool = _import_tool_class("search_notes_tool", "SearchNotesTool")

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

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
        # duckduckgo search tool: use dynamic import (require tools package on PYTHONPATH)
        try:
            ddg_module = importlib.import_module("tools.ddg_search_tool")
            create_ddg_search_tool = getattr(ddg_module, "create_ddg_search_tool", None)
            if create_ddg_search_tool is None:
                raise AttributeError("create_ddg_search_tool not found in tools.ddg_search_tool")
            ddg_search_tool_instance = create_ddg_search_tool(account_id=account_id)
            available_tools.append(ddg_search_tool_instance)
        except Exception as inner_e:
            # Provide a clearer log than a bare ImportError; falls back to the outer except
            logger.error("DuckDuckGoSearchTool import/create failed: %s", inner_e, exc_info=True)
            raise
    except Exception as e:
        logger.error("Failed to import/create DuckDuckGoSearchTool: %s", e, exc_info=True)
        failed_tools.append("DuckDuckGoSearchTool")

    try:
        # deep research tool: use absolute import (require tools package on PYTHONPATH)
        DeepResearchToolClass = _import_tool_class("deep_research_tool", "DeepResearchTool")

        # Reutilizar la instancia de AddWebToRAGTool ya creada en el loop anterior
        add_web_to_rag_instance = next((t for t in available_tools if getattr(t, "name", None) == "add_web_to_rag"), None)

        # Si no existe, crearla (esto no debería ocurrir normalmente)
        if not add_web_to_rag_instance:
            logger.warning("AddWebToRAGTool no encontrada en available_tools, intentando crear nueva instancia vía _instantiate_tool.")
            # Use the module-level AddWebToRAGTool class and the helper to ensure proper args are passed.
            if 'AddWebToRAGTool' in globals() and AddWebToRAGTool is not None:
                add_web_to_rag_instance = await _instantiate_tool(
                    AddWebToRAGTool,
                    account_id=account_id,
                    telegram_id=telegram_id,
                    thread_id=thread_id,
                    workspace_id=workspace_id
                )
                if add_web_to_rag_instance:
                    available_tools.append(add_web_to_rag_instance)
                else:
                    logger.warning("Fallo al instanciar AddWebToRAGTool vía _instantiate_tool; DeepResearchTool no será creado.")
            else:
                logger.warning("Clase AddWebToRAGTool no disponible en globals(); DeepResearchTool no será creado.")
                add_web_to_rag_instance = None
        
        # ahora buscar la herramienta de web_search (ws_tool)
        ws_tool = next((t for t in available_tools if getattr(t, "name", None) == "web_search"), None)
        if ws_tool and add_web_to_rag_instance:
            deep_research_instance = DeepResearchToolClass(
                web_search_tool=ws_tool,
                add_web_to_rag_tool=add_web_to_rag_instance,
                account_id=account_id,
                telegram_id=telegram_id,
                thread_id=thread_id,
                workspace_id=workspace_id
            )
            if deep_research_instance:
                available_tools.append(deep_research_instance)
        else:
            if not ws_tool:
                logger.warning("web_search tool no encontrada; omitiendo creación de DeepResearchTool.")
            if not add_web_to_rag_instance:
                logger.warning("add_web_to_rag tool no disponible; omitiendo creación de DeepResearchTool.")
    except Exception as e:
        logger.error("Failed to import/create DeepResearchTool: %s", e, exc_info=True)
        failed_tools.append("DeepResearchTool")

    # --- DEDUPLICATION: Ensure no duplicate tool names ---
    seen_tool_names = set()
    deduplicated_tools = []
    for tool in available_tools:
        tool_name = tool.name if hasattr(tool, 'name') else str(tool)
        if tool_name not in seen_tool_names:
            deduplicated_tools.append(tool)
            seen_tool_names.add(tool_name)
        else:
            logger.warning(f"⚠️ Duplicate tool detected and removed: '{tool_name}'")
    
    if len(deduplicated_tools) < len(available_tools):
        logger.info(f"🔧 Deduplication: Removed {len(available_tools) - len(deduplicated_tools)} duplicate tool(s)")
        available_tools = deduplicated_tools

    logger.info(f"--- 🧰 Toolbox Assembled ({len(available_tools)} tools) ---")
    if failed_tools:
        logger.warning(f"⚠️ Failed to instantiate ({len(failed_tools)}): {', '.join(failed_tools)}")
    
    return available_tools