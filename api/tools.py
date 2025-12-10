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

    try:
        # Inicializar dependencias de grafo si son necesarias
        graph_db = None
        graph_integration = None
        if "graph" in tool_name or "conceptual" in tool_name:
             if settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password:
                graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
                graph_db.connect()
                graph_integration = GraphIntegration(graph_db)

        if tool_name == "cognee_knowledge_graph" or tool_name == "knowledge_graph":
            # Mapear cognee_knowledge_graph a KnowledgeGraphTool con modo conceptual si es necesario
            tool = KnowledgeGraphTool(
                graph_integration=graph_integration, 
                graph_db=graph_db,
                account_id=current_user['account_id'],
                workspace_id=request.get("workspace_id")
            )
            
            # Preparar argumentos
            logger.info(f"🔍 DEBUG: Raw request received: {request}")
            args = request.copy()
            if "tool_name" in args:
                del args["tool_name"]
            
            # Forzar modo conceptual si el nombre de la herramienta lo sugiere
            if tool_name == "cognee_knowledge_graph":
                args["processing_mode"] = "conceptual"

            # Si documents está vacío pero tenemos workspace_id o dataset_name (que podría ser el topic),
            # intentamos recuperar documentos de la base de datos.
            if not args.get("documents") and (args.get("workspace_id") or args.get("dataset_name")):
                logger.info("Lista de documentos vacía. Intentando recuperar documentos de la base de datos...")
                logger.info(f"🔍 DEBUG: args received: {args}")
                logger.info(f"🔍 DEBUG: dataset_name: {args.get('dataset_name')}")
                logger.info(f"🔍 DEBUG: workspace_id: {args.get('workspace_id')}")
                from sqlalchemy import text
                
                # Construir query para obtener documentos
                filters = ["account_id = :account_id", "cmetadata->>'type' = 'document_chunk'"]
                params = {'account_id': current_user['account_id']}
                
                if args.get("workspace_id"):
                    # Si buscamos un topic específico, permitimos documentos personales (workspace_id NULL)
                    # o del workspace actual.
                    if args.get("topic") and args.get("topic") != "default":
                        filters.append(f"(workspace_id::text = :workspace_id OR workspace_id IS NULL)")
                    else:
                        filters.append(f"workspace_id::text = :workspace_id")
                    params['workspace_id'] = args.get("workspace_id")
                else:
                    filters.append("workspace_id IS NULL")

                # Filtrar por topic (nombre de la colección) si se proporciona
                # dataset_name es solo para organizar el grafo, NO para filtrar documentos
                topic_filter = args.get("topic")  # El nombre real de la colección
                if topic_filter and topic_filter != "default":
                     # Smart Topic Matching: Intentar encontrar el topic correcto en la DB
                     from sqlalchemy import text
                     import unicodedata
                     from urllib.parse import unquote

                     # 1. Obtener todos los topics existentes para este usuario
                     topics_query = text("SELECT DISTINCT topic FROM langchain_pg_embedding WHERE account_id = :account_id")
                     topics_result = await db.execute(topics_query, {'account_id': current_user['account_id']})
                     db_topics = [row[0] for row in topics_result.fetchall() if row[0]]

                     matched_topic = topic_filter
                     
                     # Helper para normalizar strings
                     def normalize_str(s):
                         if not s: return ""
                         # Normalizar unicode, quitar acentos, minúsculas
                         normalized = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8').lower().strip()
                         # Quitar espacios y guiones bajos para comparación
                         return normalized.replace(" ", "").replace("_", "")

                     # 2. Estrategias de coincidencia
                     if topic_filter in db_topics:
                         matched_topic = topic_filter # Coincidencia exacta
                     elif unquote(topic_filter) in db_topics:
                         matched_topic = unquote(topic_filter) # Coincidencia URL decoded
                     else:
                         # Coincidencia aproximada/normalizada
                         norm_candidate = normalize_str(topic_filter)
                         # Manejar posible prefijo 'topic_' que a veces envía el frontend/dialog
                         if norm_candidate.startswith("topic"):
                             norm_candidate_noprefix = norm_candidate[5:]  # Quitar 'topic' (ya sin _)
                         else:
                             norm_candidate_noprefix = norm_candidate

                         for db_topic in db_topics:
                             norm_db = normalize_str(db_topic)
                             # Chequear igualdad normalizada (sin espacios ni guiones bajos)
                             if norm_db == norm_candidate or norm_db == norm_candidate_noprefix:
                                 matched_topic = db_topic
                                 logger.info(f"🔄 Topic match: '{topic_filter}' -> '{db_topic}'")
                                 break
                     
                     filters.append("topic = :topic")
                     params['topic'] = matched_topic
                else:
                     # Si no hay topic específico, procesar TODOS los documentos del usuario
                     logger.info("📚 No topic filter - processing all user documents")

                logger.info(f"🔍 DEBUG: Filters before join: {filters}")
                logger.info(f"🔍 DEBUG: Params before execute: {params}")
                where_clause = " AND ".join(filters)
                
                query = text(f"""
                    SELECT DISTINCT ON (cmetadata->>'document_id')
                           cmetadata->>'file_name' AS file_name,
                           topic AS topic,
                           cmetadata->>'title' AS title,
                           cmetadata->>'author' AS author,
                           cmetadata->>'document_id' AS document_id,
                           document AS content
                    FROM langchain_pg_embedding
                    WHERE {where_clause}
                    ORDER BY cmetadata->>'document_id', id
                    LIMIT 50;
                """)
                
                result_docs = await db.execute(query, params)
                fetched_documents = []
                for row in result_docs.fetchall():
                    doc_dict = dict(row._mapping)
                    if not doc_dict.get('content'):
                         doc_dict['content'] = f"Documento: {doc_dict.get('title', 'Sin título')}"
                    fetched_documents.append(doc_dict)
                
                if fetched_documents:
                    logger.info(f"Recuperados {len(fetched_documents)} documentos de la base de datos.")
                    args["documents"] = fetched_documents
                else:
                    logger.warning("No se encontraron documentos en la base de datos para procesar.")

            result = await tool._arun(**args)
            return {"result": result, "status": "success"}

        elif tool_name == "conceptual_processing":
            tool = ConceptualProcessingTool(
                graph_integration=graph_integration,
                graph_db=graph_db,
                account_id=current_user['account_id'],
                workspace_id=request.get("workspace_id")
            )
            args = request.copy()
            if "tool_name" in args:
                del args["tool_name"]
            
            result = await tool._arun(**args)
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
