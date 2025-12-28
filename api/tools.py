import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from core.dependencies import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from utils.security import get_current_user
from tools.knowledge_graph_tool import KnowledgeGraphTool
from tools.conceptual_processing_tool import ConceptualProcessingTool
from core.config import settings
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration

logger = logging.getLogger(__name__)

router = APIRouter()

class ToolRunRequest(BaseModel):
    tool_name: str
    action: Optional[str] = None
    dataset_name: Optional[str] = None
    documents: Optional[List[Dict[str, Any]]] = None
    workspace_id: Optional[str] = None
    # Allow extra fields
    class Config:
        extra = "allow"

@router.post("/run", summary="Ejecutar una herramienta")
async def run_tool(
    request: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint genérico para ejecutar herramientas.
    """
    tool_name = request.get("tool_name")
    if not tool_name:
        raise HTTPException(status_code=400, detail="tool_name es requerido")

    logger.info(f"Solicitud de ejecución de herramienta: {tool_name} por usuario {current_user.get('user_id')}")

    graph_db = None
    try:
        # Inicializar dependencias de grafo si son necesarias
        graph_integration = None
        if "graph" in tool_name or "conceptual" in tool_name:
             if settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password:
                graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
                graph_db.connect()
                if tool_name != "knowledge_graph": # La nueva KGTool no necesita GraphIntegration
                    graph_integration = GraphIntegration(graph_db)

        if tool_name == "knowledge_graph":
            if not graph_db:
                raise ValueError("Las dependencias del grafo (GraphDB) no pudieron ser inicializadas.")

            tool = KnowledgeGraphTool(
                graph_db=graph_db,
                account_id=current_user['account_id'],
                workspace_id=request.get("workspace_id")
            )
            
            logger.info(f"🔍 DEBUG: Raw request received for KG Tool: {request}")
            args = request.copy()
            if "tool_name" in args:
                del args["tool_name"]

            # --- LÓGICA CORREGIDA PARA KNOWLEDGE GRAPH TOOL ---
            # Construir la consulta en lenguaje natural a partir de los argumentos existentes
            nl_query_parts = []
            if args.get("query"):
                nl_query_parts.append(args["query"])
            if args.get("pattern_description"):
                nl_query_parts.append(f"Busca el patrón: {args['pattern_description']}")
            if args.get("source_concept") and args.get("target_concept"):
                nl_query_parts.append(f"Encuentra el camino entre '{args['source_concept']}' y '{args['target_concept']}'")
            
            if not nl_query_parts:
                raise HTTPException(status_code=400, detail="Se requiere 'query', 'pattern_description' o conceptos para la herramienta knowledge_graph")

            natural_language_query = ". ".join(nl_query_parts)
            
            # Llamar a la herramienta con el argumento correcto
            result = await tool._arun(natural_language_query=natural_language_query)
            return {"result": result, "status": "success"}

        elif tool_name == "cognee_knowledge_graph":
            if not graph_db:
                raise ValueError("Las dependencias del grafo (GraphDB) no pudieron ser inicializadas.")
            
            # Instanciar ConceptualProcessingTool
            tool = ConceptualProcessingTool(
                graph_db=graph_db,
                account_id=current_user['account_id'],
                workspace_id=request.get("workspace_id")
            )
            
            logger.info(f"🔍 DEBUG: Raw request received for Cognee KG Tool: {request}")
            args = request.copy()
            if "tool_name" in args:
                del args["tool_name"]
            
            # Mapear argumentos para ConceptualProcessingTool
            documents_to_process = args.get("documents")
            document_titles_to_process = args.get("document_titles")
            topic = args.get("topic")
            dataset_name = args.get("dataset_name") or "default"
            
            # Validación más flexible: permitir documentos vacíos si hay un topic
            if not documents_to_process and not document_titles_to_process and not topic:
                raise HTTPException(status_code=400, detail="Se requiere 'documents', 'document_titles' o 'topic' para la herramienta cognee_knowledge_graph con acción 'process_documents'")

            # Construir argumentos para la herramienta
            tool_args = {"dataset_name": dataset_name}
            if topic:
                tool_args["topic"] = topic
            
            if documents_to_process:
                tool_args["documents"] = documents_to_process
                result = await tool._arun(**tool_args)
            elif document_titles_to_process:
                tool_args["document_titles"] = document_titles_to_process
                result = await tool._arun(**tool_args)
            elif topic:
                # Solo topic, sin documentos
                result = await tool._arun(**tool_args)
            return {"result": result, "status": "success"}

        elif tool_name == "conceptual_processing":
            if not graph_db or not graph_integration:
                raise ValueError("Las dependencias del grafo (GraphDB, GraphIntegration) no pudieron ser inicializadas.")
            
            tool = ConceptualProcessingTool(
                graph_integration=graph_integration,
                graph_db=graph_db,
                account_id=current_user['account_id'],
                workspace_id=request.get("workspace_id")
            )
            args = request.copy()
            if "tool_name" in args:
                del args["tool_name"]
            
            result = await tool._arun(db_session=db, **args)
            return {"result": result, "status": "success"}

        else:
            raise HTTPException(status_code=404, detail=f"Herramienta '{tool_name}' no encontrada o no soportada en este endpoint.")

    except Exception as e:
        logger.error(f"Error ejecutando herramienta {tool_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno ejecutando la herramienta: {str(e)}")
    finally:
        if graph_db:
            try:
                graph_db.close()
            except:
                pass
