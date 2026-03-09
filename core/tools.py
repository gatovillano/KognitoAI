# core/tools.py

"""
Módulo de Ensamblaje de Herramientas de LangChain.
"""

import logging
import os
from typing import List, Optional, Any
import importlib
import asyncio

from langchain_core.tools import Tool

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# --- TOOL IMPORTS (from tools/ directory) ---

def _import_tool_class(module_name: str, class_name: str):
	"""
	Try absolute import only (tools.xxx). In Docker we require the project root / package
	to be on PYTHONPATH so absolute imports resolve reliably.
	"""
	try:
		module = importlib.import_module(f"tools.{module_name}")
	except Exception as e:
		logger.warning(
			"⚠️ Failed to import tools.%s. This tool will not be available. Error: %s",
			module_name,
			e
		)
		return None
	return getattr(module, class_name, None)

# Bind all tool classes used below.
CreateTableTool = _import_tool_class("create_table_tool", "CreateTableTool")
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
CreatePDFTool = _import_tool_class("create_pdf_tool", "CreatePDFTool")
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
WebSearchTool = _import_tool_class("web_search_tool", "WebSearchTool")
GraphCypherGeneratorTool = _import_tool_class("graph_cypher_generator_tool", "GraphCypherGeneratorTool")
HTMLGeneratorTool = _import_tool_class("html_generator_tool", "HTMLGeneratorTool")
ExecuteCommandTool = _import_tool_class("execute_command_tool", "ExecuteCommandTool")
TableAnalysisTool = _import_tool_class("table_analysis_tool", "TableAnalysisTool")
AnalysisInterpreterTool = _import_tool_class("analysis_interpreter_tool", "AnalysisInterpreterTool")
CypherTool = _import_tool_class("cypher_tool", "CypherTool")
StructuredDataGeneratorTool = _import_tool_class("structured_data_generator_tool", "StructuredDataGeneratorTool")
TavilySearchTool = _import_tool_class("tavily_search_tool", "TavilySearchTool")



# Global singletons for shared dependencies
_graph_db_instance = None
_graph_integration_instance = None
_knowledge_graph_service_instance = None

async def get_shared_dependencies():
    """
    Returns shared instances of GraphDB and GraphIntegration, initializing them if necessary.
    """
    global _graph_db_instance, _graph_integration_instance, _knowledge_graph_service_instance
    
    if _graph_db_instance and _graph_integration_instance and _knowledge_graph_service_instance:
        return _graph_db_instance, _graph_integration_instance, _knowledge_graph_service_instance

    try:
        from knowledge_graph.graph_database import GraphDB
        from knowledge_graph.graph_integration import GraphIntegration
        from core.config import settings

        logger.debug(f"DEBUG: Neo4j URI: {settings.neo4j_uri}")
        logger.debug(f"DEBUG: Neo4j User: {settings.neo4j_user}")
        logger.debug(f"DEBUG: Neo4j Password: {'*' * len(settings.neo4j_password) if settings.neo4j_password else 'None'}")


        if settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password:
            if not _graph_db_instance:
                _graph_db_instance = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
                _graph_db_instance.connect()
                logger.debug("✅ Shared GraphDB instance created.")
            
            if not _graph_integration_instance:
                _graph_integration_instance = GraphIntegration(_graph_db_instance)
                logger.debug("✅ Shared GraphIntegration instance created.")

            if not _knowledge_graph_service_instance:
                from utils.knowledge_graph_service import KnowledgeGraphService
                _knowledge_graph_service_instance = KnowledgeGraphService()
                logger.debug("✅ Shared KnowledgeGraphService instance created.")
                
            return _graph_db_instance, _graph_integration_instance, _knowledge_graph_service_instance
        else:
            logger.warning("⚠️ Faltan credenciales de Neo4j, las herramientas del grafo no se inicializarán.")
            return None, None, None
    except Exception as e:
        logger.error(f"❌ Error initializing shared dependencies: {e}", exc_info=True)
        return None, None, None

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

        # Detect fields for the tool class (for attribute injection later)
        fields = set()
        if hasattr(ToolClass, 'model_fields'): # Pydantic v2
            fields = set(ToolClass.model_fields.keys())
        elif hasattr(ToolClass, '__fields__'): # Pydantic v1
            fields = set(ToolClass.__fields__.keys())
        # If we didn't find fields, try inspection as fallback
        if not fields and hasattr(ToolClass, '__annotations__'):
            fields = set(ToolClass.__annotations__.keys())

        # --- Dependency Injection for Graph Tools ---
        if ToolClass == KnowledgeGraphTool:
            _graph_db, _, _knowledge_graph_service = await get_shared_dependencies()
            if _graph_db and _knowledge_graph_service:
                tool_kwargs = {
                    'account_id': account_id,
                    'knowledge_graph_service': _knowledge_graph_service # Pasar el servicio
                }
                if workspace_id is not None:
                    tool_kwargs['workspace_id'] = workspace_id
                tool_instance = ToolClass(**tool_kwargs)
            else:
                logger.warning(f"Skipping {tool_name} due to missing graph dependencies.")
                return None
        elif ToolClass == ConceptualProcessingTool:
            _graph_db, _graph_integration, _ = await get_shared_dependencies()
            if _graph_db and _graph_integration:
                tool_kwargs = {
                    'account_id': account_id,
                    'graph_integration': _graph_integration,
                    'graph_db': _graph_db
                }
                if workspace_id is not None:
                    tool_kwargs['workspace_id'] = workspace_id
                tool_instance = ToolClass(**tool_kwargs)
            else:
                logger.warning(f"Skipping {tool_name} due to missing graph dependencies.")
                return None
        elif ToolClass == GraphCypherGeneratorTool:
            _, _, _knowledge_graph_service = await get_shared_dependencies()
            if _knowledge_graph_service:
                tool_kwargs = {
                    'account_id': account_id,
                    '_cognee_integration': _knowledge_graph_service.graph_integration # Usar la integración de grafo
                }
                if workspace_id is not None:
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
        else:
            # Detect if the tool class expects these arguments
            expected_args = {}
            
            # Use Pydantic's field detection for both v1 and v2
            fields = set()
            if hasattr(ToolClass, 'model_fields'): # Pydantic v2
                fields = set(ToolClass.model_fields.keys())
            elif hasattr(ToolClass, '__fields__'): # Pydantic v1
                fields = set(ToolClass.__fields__.keys())
            
            # If we didn't find fields, try inspection as fallback
            if not fields and hasattr(ToolClass, '__annotations__'):
                fields = set(ToolClass.__annotations__.keys())

            if 'account_id' in fields:
                expected_args['account_id'] = account_id
            if 'telegram_id' in fields and telegram_id is not None:
                expected_args['telegram_id'] = str(telegram_id)
            if 'thread_id' in fields and thread_id is not None:
                expected_args['thread_id'] = thread_id
            if 'workspace_id' in fields and workspace_id is not None:
                expected_args['workspace_id'] = workspace_id
            


            if expected_args:
                try:
                    tool_instance = ToolClass(**expected_args)
                except Exception as e:
                    logger.warning(f"Failed to instantiate {tool_name} with args {expected_args}: {e}")
                    # Fallback to no-args just in case, though it will likely fail for mandatory fields
                    tool_instance = ToolClass()
            else:
                # No args tools
                tool_instance = ToolClass()

        # Ensure that account_id, workspace_id, telegram_id, thread_id are set on the instance
        # if the tool class defines these fields, even if the constructor didn't accept them.
        if tool_instance is not None:
            if 'account_id' in fields:
                tool_instance.account_id = account_id
            if 'workspace_id' in fields:
                tool_instance.workspace_id = workspace_id
            if 'telegram_id' in fields:
                tool_instance.telegram_id = telegram_id
            if 'thread_id' in fields:
                tool_instance.thread_id = thread_id

        return tool_instance
    except Exception as e:
        logger.error(f"❌ Failed to instantiate tool '{ToolClass.__name__}': {e}", exc_info=True)
        return None

async def get_all_langchain_tools(
    account_id: str,
    telegram_id: Optional[int] = None,
    thread_id: Optional[str] = None,
    workspace_id: Optional[str] = None
) -> List[Tool]:
    """
    Recoge, instancia y devuelve una lista de todas las herramientas LangChain disponibles,
    asegurando que no haya duplicados.
    """
    logger.debug("⚙️ Assembling agent toolbox...")
    
    # Lista completa de todas las clases de herramientas que se deben intentar instanciar.
    full_tool_classes_to_instantiate = [
        AddNoteTool, AddWebToRAGTool, AnalyzeCodeForInsightsTool, AnalyzeTextForInsightsTool,
        CancelEventTool, ConceptualProcessingTool, KnowledgeGraphTool, GraphCypherGeneratorTool,
        InsightGenerationTool, ComprehensiveWebAnalysisTool, ConversationContextAnalyzerTool,
        ConversationHistoryAnalyzerTool, DeleteDocumentTool, DeleteNoteTool, DocumentRAGTool,
        ExtractDocumentTitlesTool, GetAgendaTool, GetAnalysisResultsTool, GetDocumentContentTool,
        GetDocumentListTool, GetNotesTool, GetFormResponsesTool, GetProactiveInsightsTool,
        GitHubRepoTool, ImageBackgroundEraserTool, ImageGenerationTool, InternalKnowledgeSearchTool,
        MemoryAddTool, CreatePDFTool, MindmapGeneratorTool, MultiQuerySearchTool,
        NaturalQueryInterpreterTool, ScheduleEventTool, ScopedRagAnalysisTool, SearchNotesTool,
        SetReminderTool, UpdateDocumentMetadataTool, UpdateNoteTool, UpdateProfileTool,
        WebScraperTool, ScheduleToolExecutionTool, ListScheduledToolsTool, ContactProfileTool,
        WebSearchTool, HTMLGeneratorTool, ExecuteCommandTool, TableAnalysisTool,
        AnalysisInterpreterTool, CypherTool, StructuredDataGeneratorTool, TavilySearchTool,
        CreateTableTool

    ]
    
    # Filtrar herramientas que no pudieron ser importadas (son None)
    full_tool_classes_to_instantiate = [cls for cls in full_tool_classes_to_instantiate if cls is not None]

    all_instantiated_tools: List[Tool] = []
    failed_tools: List[str] = []

    await get_shared_dependencies()

    # 1. Instanciar todas las herramientas estándar de la lista en paralelo.
    tasks = [_instantiate_tool(ToolClass, account_id, telegram_id, thread_id, workspace_id) for ToolClass in full_tool_classes_to_instantiate]
    instantiated_results = await asyncio.gather(*tasks)
    
    for i, tool_instance in enumerate(instantiated_results):
        tool_cls = full_tool_classes_to_instantiate[i]
        if tool_instance:
            all_instantiated_tools.append(tool_instance)
        else:
            # Obtener un nombre de cadena válido para el fallo
            cls_name = getattr(tool_cls, 'name', None) or getattr(tool_cls, '__name__', 'UnknownTool')
            failed_tools.append(str(cls_name))

    # 2. Instanciar herramientas de fábrica (factory tools) en paralelo.
    async def get_ddg_tool():
        try:
            ddg_module = importlib.import_module("tools.ddg_search_tool")
            create_ddg_search_tool = getattr(ddg_module, "create_ddg_search_tool")
            return create_ddg_search_tool(account_id=account_id)
        except Exception as e:
            logger.error("Failed to import/create DuckDuckGoSearchTool: %s", e, exc_info=True)
            return None

    ddg_task = get_ddg_tool()
    ddg_tool = await ddg_task
    if ddg_tool:
        all_instantiated_tools.append(ddg_tool)
    else:
        failed_tools.append("DuckDuckGoSearchTool")

    try:
        DeepResearchToolClass = _import_tool_class("deep_research_tool", "DeepResearchTool")
        
        # Localizar dependencias ya instanciadas
        web_search_tool = next((t for t in all_instantiated_tools if getattr(t, "name", None) == "web_search"), None)
        add_web_to_rag_tool = next((t for t in all_instantiated_tools if getattr(t, "name", None) == "add_web_to_rag"), None)

        if web_search_tool and add_web_to_rag_tool:
            deep_research_instance = DeepResearchToolClass(
                web_search_tool=web_search_tool,
                add_web_to_rag_tool=add_web_to_rag_tool,
                account_id=account_id,
                telegram_id=str(telegram_id) if telegram_id is not None else None,
                thread_id=thread_id,
                workspace_id=workspace_id
            )
            all_instantiated_tools.append(deep_research_instance)
        else:
            logger.warning("Could not create DeepResearchTool due to missing dependencies (web_search or add_web_to_rag).")

    except Exception as e:
        logger.error("Failed to import/create DeepResearchTool: %s", e, exc_info=True)
        failed_tools.append("DeepResearchTool")

    # 3. Paso de deduplicación final y definitivo.
    final_tools: List[Tool] = []
    seen_names = set()
    for tool in all_instantiated_tools:
        if tool.name not in seen_names:
            final_tools.append(tool)
            seen_names.add(tool.name)
        else:
            logger.warning(f"Duplicate tool '{tool.name}' removed during final deduplication.")
            
    logger.debug(f"--- 🧰 Toolbox Assembled ({len(final_tools)} tools) ---")
    logger.debug(f"Final tool list: {[tool.name for tool in final_tools]}")
    if failed_tools:
        logger.warning(f"Failed to instantiate ({len(failed_tools)}): {', '.join(failed_tools)}")
    
    return final_tools