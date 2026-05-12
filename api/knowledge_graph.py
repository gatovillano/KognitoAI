# api/knowledge_graph.py

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Literal
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.database import get_db_session
from core.config import settings
from knowledge_graph.graph_integration import GraphIntegration
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.entity_quality_reviewer import EntityQualityReviewer
from knowledge_graph.trend_analyzer import TrendAnalyzer
from utils.security import get_current_user
from utils.knowledge_graph_service import KnowledgeGraphService
from utils.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Modelos Pydantic
class ProcessGraphRequest(BaseModel):
    workspace_id: Optional[str] = None
    force_reprocess: bool = False
    dataset_name: Optional[str] = None
    topic: Optional[str] = None  # Filtrar por colección específica
    processing_mode: Optional[Literal["hybrid", "conceptual"]] = "hybrid"  # Modo de procesamiento

class SearchGraphRequest(BaseModel):
    workspace_id: Optional[str] = None
    query: str
    limit: int = 50

class EntityConnectionsRequest(BaseModel):
    workspace_id: Optional[str] = None
    entity_id: str
    depth: int = 1

class ClearGraphRequest(BaseModel):
    workspace_id: Optional[str] = None
    confirm_delete_all: bool = False

class GraphResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None

# Inicializar componentes de forma lazy (solo cuando se necesiten)
graph_db = None
graph_integration = None

def get_graph_db():
    """Obtiene la instancia de GraphDB, creándola si es necesario."""
    global graph_db
    if graph_db is None:
        assert settings.neo4j_uri is not None, "Neo4j URI no configurado"
        assert settings.neo4j_user is not None, "Neo4j User no configurado"
        assert settings.neo4j_password is not None, "Neo4j Password no configurado"

        graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        try:
            graph_db.connect()
            logger.info("✅ Conexión a Neo4j establecida")
        except Exception as e:
            logger.error(f"❌ Error conectando a Neo4j: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"No se puede conectar a Neo4j: {str(e)}"
            )
    return graph_db

def get_graph_integration():
    """Obtiene la instancia de GraphIntegration, creándola si es necesario."""
    global graph_integration
    if graph_integration is None:
        graph_integration = GraphIntegration(get_graph_db())
    return graph_integration


def get_knowledge_graph_service():
    """Obtiene la instancia de KnowledgeGraphService, creándola si es necesario."""
    return KnowledgeGraphService(get_graph_db(), get_graph_integration())





@router.get("/status", response_model=GraphResponse)
async def get_graph_status(
    workspace_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el estado del procesamiento del grafo para un workspace específico o el contexto general.
    """
    try:
        async with get_db_session() as session:
            query = f"""
                SELECT COUNT(DISTINCT cmetadata->>'file_name') as document_count
                FROM langchain_pg_embedding
                WHERE account_id = :account_id
                  AND (cmetadata->>'type' = 'document_chunk' OR cmetadata->>'type' = 'user_memory_proactive_llm' OR cmetadata->>'type' = 'thread_summary')
                  {f"AND workspace_id::text = '{workspace_id}'" if workspace_id else "AND workspace_id IS NULL"}
            """
            
            result = await session.execute(query, {'account_id': current_user['account_id']})
            
            row = result.fetchone()
            document_count = row[0] if row else 0
        
        if document_count == 0:
            status_message = "no_documents"
        else:
            status_message = "not_processed" # O podrías verificar si hay un grafo procesado guardado
        
        return GraphResponse(
            success=True,
            data={
                "status": status_message,
                "document_count": document_count,
                "workspace_id": workspace_id # Puede ser None
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado del grafo: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.post("/search-graph", response_model=GraphResponse)
async def search_graph(
    request: SearchGraphRequest,
    current_user: dict = Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service) # Added dependency
):
    """
    Busca entidades en el grafo de conocimiento.
    """
    try:
        results = await kg_service.search_graph_flow(
            query=request.query,
            workspace_id=request.workspace_id,
            limit=request.limit,
            account_id=current_user['account_id']
        )
        return GraphResponse(
            success=True,
            data={
                "results": results,
                "query": request.query,
                "total": len(results)
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error buscando en grafo: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.post("/entity-connections", response_model=GraphResponse)
async def get_entity_connections(
    request: EntityConnectionsRequest,
    current_user: dict = Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service) # Added dependency
):
    """
    Obtiene las conexiones de una entidad específica.
    """
    try:
        connections = await kg_service.get_entity_connections_flow(
            entity_id=request.entity_id,
            workspace_id=request.workspace_id,
            depth=request.depth,
            account_id=current_user['account_id']
        )
        return GraphResponse(
            success=True,
            data={
                "entity_id": request.entity_id,
                "connections": connections,
                "depth": request.depth
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo conexiones: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.post("/test-neo4j-connection", response_model=GraphResponse)
async def test_neo4j_connection(
    current_user: dict = Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    """
    Prueba la conexión con Neo4j y muestra estadísticas básicas.
    """
    try:
        result = await kg_service.test_neo4j_connection_flow(
            account_id=current_user['account_id']
        )
        return GraphResponse(
            success=True,
            data=result,
            message="Conexión con Neo4j exitosa"
        )

    except Exception as e:
        logger.error(f"❌ Error probando conexión Neo4j: {e}")
        return GraphResponse(
            success=False,
            error=f"Error de conexión: {str(e)}",
            message="No se pudo conectar con Neo4j"
        )

@router.post("/process-knowledge-graph-optimized", response_model=GraphResponse)
async def process_knowledge_graph_optimized(
    request: ProcessGraphRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    """
    Procesa documentos con el pipeline OPTIMIZADO (sin Fase 3 pesada).
    Garantiza que el procesamiento complete exitosamente.
    """
    try:
        # Si no se proporciona dataset_name pero hay un topic, usar el topic como dataset_name
        # Esto asegura que el dataset tenga el nombre de la colección
        if request.topic:
            # Decodificar el topic si viene encodeado
            from urllib.parse import unquote
            decoded_topic = unquote(request.topic)
            request.dataset_name = decoded_topic
            logger.info(f"🏷️ Usando topic '{decoded_topic}' como dataset_name para procesamiento optimizado")

        result = await kg_service.process_documents_flow(
            db_session=db,
            request=request,
            account_id=current_user['account_id'],
            background_tasks=background_tasks,
        )
        return GraphResponse(
            success=True,
            data=result,
            message="Procesamiento de grafo iniciado exitosamente."
        )

    except Exception as e:
        logger.error(f"❌ Error en procesamiento optimizado: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.post("/process-knowledge-graph-with-cooccurrence", response_model=GraphResponse)
async def process_knowledge_graph_with_cooccurrence(
    request: ProcessGraphRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    """
    Procesa documentos con co-ocurrencias OPTIMIZADAS.
    Más lento pero más completo que la versión optimizada básica.
    """
    try:
        # Si no se proporciona dataset_name pero hay un topic, usar el topic como dataset_name
        # Esto asegura que el dataset tenga el nombre de la colección
        if request.topic:
            # Decodificar el topic si viene encodeado
            from urllib.parse import unquote
            decoded_topic = unquote(request.topic)
            request.dataset_name = decoded_topic
            logger.info(f"🏷️ Usando topic '{decoded_topic}' como dataset_name para procesamiento con co-ocurrencia")

        result = await kg_service.process_documents_flow( # Assuming process_documents_flow handles co-occurrence
            db_session=db,
            request=request,
            account_id=current_user['account_id'],
            background_tasks=background_tasks,
        )
        return GraphResponse(
            success=True,
            data=result,
            message="Procesamiento de grafo con co-ocurrencias iniciado exitosamente."
        )

    except Exception as e:
        logger.error(f"❌ Error en procesamiento con co-ocurrencias: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.get("/stats", response_model=GraphResponse)
async def get_graph_stats(
    workspace_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    """
    Obtiene estadísticas del grafo de conocimiento para un workspace específico o el contexto general.
    """
    try:
        stats = await kg_service.get_graph_stats_flow(
            workspace_id=workspace_id,
            account_id=current_user['account_id']
        )
        return GraphResponse(
            success=True,
            data=stats
        )

    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas del grafo: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.delete("/datasets/{dataset_name}", response_model=GraphResponse)
async def delete_dataset(
    dataset_name: str,
    current_user: dict = Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    """
    Elimina un dataset específico del grafo de conocimiento.
    """
    try:
        result = await kg_service.delete_dataset_flow(
            dataset_name=dataset_name,
            account_id=current_user['account_id']
        )
        return GraphResponse(
            success=result["success"],
            data=result if result["success"] else None,
            error=result.get("error") if not result["success"] else None,
            message=result.get("message")
        )
    except Exception as e:
        logger.error(f"❌ Error eliminando dataset '{dataset_name}': {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )


@router.post("/clear-neo4j", response_model=GraphResponse)
async def clear_neo4j(
    request: ClearGraphRequest = ClearGraphRequest(),
    current_user: dict = Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    """
    Limpia la base de datos Neo4j.

    - Si se proporciona `workspace_id`, solo elimina los nodos de ese workspace.
    - Si NO se proporciona `workspace_id`, requiere `confirm_delete_all=True` para eliminar TODO.
    """
    try:
        result = await kg_service.clear_graph_flow(
            workspace_id=request.workspace_id,
            confirm_delete_all=request.confirm_delete_all,
            account_id=current_user['account_id']
        )
        return GraphResponse(
            success=True,
            data=result,
            message="Limpieza de Neo4j completada."
        )

    except Exception as e:
        logger.error(f"❌ Error limpiando Neo4j: {e}")
        return GraphResponse(
            success=False,
            error=f"Error limpiando Neo4j: {str(e)}"
        )

# New endpoint for memories, as per instructions
@router.post("/memories", response_model=GraphResponse)
async def fetch_user_memories(
    request: dict, # Assuming a request body for filtering, etc.
    current_user: dict = Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    """
    Obtiene las memorias del usuario.
    """
    try:
        # Extract parameters from request body as needed by fetch_memories_flow
        # For now, assuming it might take workspace_id and optionally other filters
        workspace_id: Optional[str] = request.get("workspace_id")
        memories = await kg_service.fetch_memories_flow(
            workspace_id=workspace_id,
            account_id=current_user['account_id']
            # Add other parameters as needed by fetch_memories_flow
        )
        return GraphResponse(
            success=True,
            data=memories,
            message="Memorias del usuario obtenidas exitosamente."
        )
    except Exception as e:
        logger.error(f"❌ Error obteniendo memorias del usuario: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.post("/enhanced-chat", response_model=GraphResponse)
async def enhanced_chat(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat enriquecido que usa el grafo de conocimiento para mejorar las respuestas del LLM.
    """
    try:
        user_message: Optional[str] = request.get("message")
        workspace_id: Optional[str] = request.get("workspace_id")
        use_knowledge_graph: bool = request.get("use_knowledge_graph", True)

        if not user_message:
            return GraphResponse(
                success=False,
                error="Mensaje requerido"
            )
        
        # Pylance puede quejarse si workspace_id es None, pero la lógica de la aplicación
        # puede manejarlo o se espera que el frontend lo proporcione.
        # Por ahora, se asume que si no es None, es str para el resto de la función.
        # Si se necesita un valor por defecto para el entorno general, se puede añadir aquí.

        logger.info(f"🧠 Chat enriquecido: '{user_message[:50]}...'")

        # Usar el LLM enriquecido
        from core.llm_manager import get_enhanced_llm_response

        enhanced_response = await get_enhanced_llm_response(
            user_message=user_message,
            user_id=current_user['user_id'],
            workspace_id=workspace_id or "", # Asegura que workspace_id sea str
            use_knowledge_graph=use_knowledge_graph
        )

        return GraphResponse(
            success=True,
            data=enhanced_response,
            message="Respuesta enriquecida generada"
        )

    except Exception as e:
        logger.error(f"❌ Error en chat enriquecido: {e}")
        return GraphResponse(
            success=False,
            error=f"Error en chat enriquecido: {str(e)}"
        )

@router.post("/review-entities", response_model=GraphResponse)
async def review_entities(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Revisa la calidad de las entidades en el grafo y sugiere correcciones.
    """
    try:
        workspace_id: Optional[str] = request.get("workspace_id")

        # Asumimos que workspace_id será un str si se usa, o se maneja como opcional en las funciones llamadas.
        # Si la lógica de la aplicación permite un entorno general sin workspace_id,
        # se debe modificar la firma de la función o proveer un valor por defecto aquí.

        logger.info("🔍 Iniciando revisión de calidad de entidades...")

        # Inicializar revisor
        from knowledge_graph.entity_quality_reviewer import EntityQualityReviewer
        from core.llm_manager import get_main_llm

        db = get_graph_db()
        llm = get_main_llm()

        reviewer = EntityQualityReviewer(graph_db=db, llm=llm)

        # Realizar revisión
        review_results = await reviewer.review_all_entities(workspace_id or "") # Asegura que workspace_id sea str

        return GraphResponse(
            success=True,
            data=review_results,
            message=f"Revisión completada: {review_results['summary']['issues_found']} problemas encontrados"
        )

    except Exception as e:
        logger.error(f"❌ Error en revisión de entidades: {e}")
        return GraphResponse(
            success=False,
            error=f"Error en revisión: {str(e)}"
        )

@router.post("/apply-corrections", response_model=GraphResponse)
async def apply_corrections(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Aplica las correcciones sugeridas por la revisión de calidad.
    """
    try:
        corrections = request.get("corrections", [])
        auto_apply = request.get("auto_apply", False)

        if not corrections:
            return GraphResponse(
                success=False,
                error="No se proporcionaron correcciones"
            )

        logger.info(f"🔧 Aplicando {len(corrections)} correcciones...")

        # Inicializar revisor
        from knowledge_graph.entity_quality_reviewer import EntityQualityReviewer

        db = get_graph_db()
        reviewer = EntityQualityReviewer(graph_db=db)

        # Aplicar correcciones
        results = await reviewer.apply_corrections(corrections, auto_apply, account_id=current_user['account_id'])

        return GraphResponse(
            success=True,
            data=results,
            message=f"Correcciones aplicadas: {results['applied']} exitosas, {results['failed']} fallidas"
        )

    except Exception as e:
        logger.error(f"❌ Error aplicando correcciones: {e}")
        return GraphResponse(
            success=False,
            error=f"Error aplicando correcciones: {str(e)}"
        )

@router.get("/entity-statistics", response_model=GraphResponse)
async def get_entity_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene estadísticas detalladas de las entidades en el grafo.
    """
    try:
        logger.info("📊 Obteniendo estadísticas de entidades...")

        db = get_graph_db()

        # Query para estadísticas por tipo
        stats_query = """
        MATCH (n)
        RETURN n.type as type,
               count(n) as count,
               avg(n.confidence) as avg_confidence,
               collect(DISTINCT n.extraction_method) as methods
        ORDER BY count DESC
        """

        type_stats = await db.execute_query(stats_query)

        # Query para estadísticas de relaciones
        rel_stats_query = """
        MATCH ()-[r]->()
        RETURN type(r) as relationship_type,
               count(r) as count,
               avg(r.confidence) as avg_confidence
        ORDER BY count DESC
        """

        rel_stats = await db.execute_query(rel_stats_query)

        # Query para nodos más conectados
        connected_query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]-()
        RETURN n.name as name, n.type as type, count(r) as connections
        ORDER BY connections DESC
        LIMIT 20
        """

        most_connected = await db.execute_query(connected_query)

        statistics = {
            "entity_types": type_stats,
            "relationship_types": rel_stats,
            "most_connected": most_connected,
            "summary": {
                "total_entities": sum(stat["count"] for stat in type_stats),
                "total_relationships": sum(stat["count"] for stat in rel_stats),
                "entity_types_count": len(type_stats),
                "relationship_types_count": len(rel_stats)
            }
        }

        return GraphResponse(
            success=True,
            data=statistics,
            message="Estadísticas obtenidas exitosamente"
        )

    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}")
        return GraphResponse(
            success=False,
            error=f"Error obteniendo estadísticas: {str(e)}"
        )

@router.post("/process-conceptually", response_model=GraphResponse)
async def process_documents_conceptually(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Procesa documentos usando el enfoque conceptual de citas e ideas interrelacionadas.
    """
    try:
        documents = request.get("documents", [])
        dataset_name = request.get("dataset_name", "conceptual_dataset")

        if not documents:
            return GraphResponse(
                success=False,
                error="No se proporcionaron documentos para procesar"
            )

        logger.info(f"🧠 Iniciando procesamiento conceptual de {len(documents)} documentos")

        # Inicializar servicio
        from utils.knowledge_graph_service import KnowledgeGraphService
        from knowledge_graph.graph_integration import GraphIntegration
        
        db = get_graph_db()
        graph_integration = GraphIntegration(db)
        kg_service = KnowledgeGraphService(db, graph_integration)

        # Usar el servicio para procesar conceptualmente
        # Nota: process_documents_flow maneja conceptual vs hybrid via processing_mode
        # Pero aquí estamos llamando directamente a una ruta específica.
        # Lo ideal es reutilizar process_documents_flow con processing_mode="conceptual"
        
        # Simular request object para compatibilidad con process_documents_flow
        class MockRequest:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        mock_req = MockRequest(
            documents=documents,
            dataset_name=dataset_name,
            processing_mode="conceptual"
        )

        result = await kg_service.process_documents_flow(
            db_session=None, # No se necesita para docs directos
            request=mock_req,
            account_id=current_user['account_id'],
            processing_mode="conceptual"
        )

        return GraphResponse(
            success=True,
            data=result,
            message=f"Procesamiento conceptual completado: {result.get('conceptual_quotes', 0)} citas, {result.get('idea_profiles', 0)} perfiles"
        )

    except Exception as e:
        logger.error(f"❌ Error en procesamiento conceptual: {e}")
        return GraphResponse(
            success=False,
            error=f"Error en procesamiento conceptual: {str(e)}"
        )

@router.post("/detect-trends", response_model=GraphResponse)
async def detect_trends(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Detecta tendencias emergentes en el grafo de conocimiento.
    """
    try:
        dataset_name = request.get("dataset_name", "default")
        time_window = request.get("time_window", "last_6_months")
        trend_threshold = request.get("trend_threshold", 0.7)
        granularity = request.get("granularity", "weekly")

        logger.info(f"📈 Detectando tendencias en '{dataset_name}' para {time_window}")

        # Inicializar integración
        graph_integration = get_graph_integration()

        # Detectar tendencias
        trends_result = await graph_integration.detect_trends(
            dataset_name=dataset_name,
            time_window=time_window,
            trend_threshold=trend_threshold,
            granularity=granularity
        )

        return GraphResponse(
            success=True,
            data=trends_result,
            message=f"Análisis de tendencias completado: {trends_result['trend_metrics']['total_trends']} tendencias detectadas"
        )

    except Exception as e:
        logger.error(f"❌ Error detectando tendencias: {e}")
        return GraphResponse(
            success=False,
            error=f"Error detectando tendencias: {str(e)}"
        )

@router.post("/temporal-analysis", response_model=GraphResponse)
async def temporal_analysis(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Realiza análisis temporal completo del grafo de conocimiento.
    """
    try:
        dataset_name = request.get("dataset_name", "default")
        analysis_types = request.get("analysis_types", ["trends", "evolution", "patterns"])

        logger.info(f"🕒 Iniciando análisis temporal completo para '{dataset_name}'")

        # Inicializar integración
        graph_integration = get_graph_integration()

        # Realizar análisis temporal
        temporal_result = await graph_integration.analyze_temporal_patterns(
            dataset_name=dataset_name,
            analysis_types=analysis_types
        )

        return GraphResponse(
            success=True,
            data=temporal_result,
            message=f"Análisis temporal completado para {len(analysis_types)} tipos de análisis"
        )

    except Exception as e:
        logger.error(f"❌ Error en análisis temporal: {e}")
        return GraphResponse(
            success=False,
            error=f"Error en análisis temporal: {str(e)}"
        )

@router.get("/trend-summary/{dataset_name}", response_model=GraphResponse)
async def get_trend_summary(
    dataset_name: str,
    time_window: str = "last_6_months",
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene un resumen rápido de tendencias para un dataset.
    """
    try:
        logger.info(f"📊 Obteniendo resumen de tendencias para '{dataset_name}'")

        # Inicializar integración
        graph_integration = get_graph_integration()

        # Obtener tendencias con umbral bajo para resumen
        trends_result = await graph_integration.detect_trends(
            dataset_name=dataset_name,
            time_window=time_window,
            trend_threshold=0.5,  # Umbral más bajo para resumen
            granularity="weekly"
        )

        # Crear resumen simplificado
        summary = {
            "dataset_name": dataset_name,
            "time_window": time_window,
            "total_trends": trends_result["trend_metrics"]["total_trends"],
            "strongest_trends": trends_result["emerging_trends"][:5],  # Top 5
            "trend_distribution": trends_result["trend_metrics"]["trends_by_direction"],
            "summary_message": trends_result["summary"]["message"] if "message" in trends_result["summary"] else "Tendencias detectadas",
            "recommendations": trends_result["summary"].get("recommendations", [])
        }

        return GraphResponse(
            success=True,
            data=summary,
            message=f"Resumen de tendencias obtenido: {summary['total_trends']} tendencias"
        )

    except Exception as e:
        logger.error(f"❌ Error obteniendo resumen de tendencias: {e}")
        return GraphResponse(
            success=False,
            error=f"Error obteniendo resumen: {str(e)}"
        )

@router.get("/datasets", response_model=GraphResponse)
async def get_available_datasets(
    workspace_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene la lista de datasets únicos disponibles en Neo4j para el usuario actual.
    Opcionalmente filtra por workspace_id.
    """
    try:
        db = get_graph_db()
        
        # Construir query para obtener datasets únicos
        params = {'account_id': current_user['account_id']}
        where_clauses = ["n.account_id = $account_id", "n.dataset_name IS NOT NULL"]

        if workspace_id and workspace_id.lower() != "all":
            if workspace_id.lower() == "global_context":
                where_clauses.append("n.workspace_id IS NULL")
            else:
                where_clauses.append("n.workspace_id = $workspace_id")
                params['workspace_id'] = workspace_id

        where_statement = " WHERE " + " AND ".join(where_clauses)

        query = f"""
        MATCH (n)
        {where_statement}
        RETURN DISTINCT n.dataset_name as dataset_name, count(n) as node_count
        ORDER BY dataset_name
        """
        
        logger.info(f"Executing datasets query: {query}")
        result = await db.execute_query(query, params)
        
        datasets = [
            {
                "name": record["dataset_name"],
                "node_count": record["node_count"]
            }
            for record in result
        ]
        
        return GraphResponse(
            success=True,
            data={"datasets": datasets},
            message=f"Encontrados {len(datasets)} datasets"
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datasets: {e}", exc_info=True)
        return GraphResponse(
            success=False,
            error=f"Error obteniendo datasets: {str(e)}"
        )


@router.get("/data", response_model=GraphResponse)
@limiter.limit("1000/minute")
async def get_knowledge_graph_data(
    request: Request,
    workspace_id: Optional[str] = None,
    dataset_name: Optional[str] = None,
    limit: int = 100,
    max_hops: int = 2,
    node_types: Optional[List[str]] = Query(None),
    edge_types: Optional[List[str]] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene los nodos y aristas del grafo de conocimiento, opcionalmente filtrado por workspace_id y/o dataset_name,
    en un formato compatible con vis.js/vis-network.
    """
    try:
        db = get_graph_db()
        
        # Parámetros iniciales siempre incluyen el account_id
        params = {'account_id': current_user['account_id'], 'limit': limit}

        # Construir la cláusula WHERE dinámicamente
        where_clauses = ["n.account_id = $account_id"]

        if workspace_id and workspace_id.lower() != "all":
            if workspace_id.lower() == "global_context":
                where_clauses.append("n.workspace_id IS NULL")
            else:
                where_clauses.append("n.workspace_id = $workspace_id")
                params['workspace_id'] = workspace_id

        # Agregar filtro por dataset_name si se proporciona
        if dataset_name and dataset_name.lower() != "all":
            where_clauses.append("n.dataset_name = $dataset_name")
            params['dataset_name'] = dataset_name

        # Filtros por tipo de nodo
        if node_types:
            where_clauses.append("n.type IN $node_types")
            params['node_types'] = node_types

        # Unir cláusulas
        where_statement = " WHERE " + " AND ".join(where_clauses)

        # Filtros por tipo de relación
        rel_where_clause = ""
        if edge_types:
            rel_where_clause = " AND type(r) IN $edge_types"
            params['edge_types'] = edge_types

        # Consulta Cypher para obtener nodos y relaciones del usuario
        # Si hay filtros de tipos de nodo, aplicarlos a ambos nodos conectados
        node_type_filter = ""
        if node_types:
            node_type_filter = " AND (m.type IN $node_types OR m IS NULL)"

        query = f"""
        MATCH (n)
        {where_statement}
        OPTIONAL MATCH (n)-[r]-(m)
        WHERE m.account_id = $account_id
        {rel_where_clause}
        {node_type_filter}
        RETURN n, r, m
        LIMIT $limit
        """
        
        logger.info(f"Executing Cypher Query: {query}")
        result = await db.execute_query(query, params)
        logger.info(f"Cypher Query Result (first 5 records): {result[:5]}")
 
        nodes_map = {}
        edges_list = []
        added_edge_ids = set()

        for record in result:
            n = record["n"]
            r = record["r"]
            m = record["m"]

            # Función auxiliar para obtener propiedades de forma segura
            def get_node_properties(node):
                node_id_str = ""
                node_label = ""
                node_type = "Desconocido" # Valor por defecto
                node_name_for_title = ""
                all_properties = {}

                if isinstance(node, dict):
                    node_id_str = str(node.get('id'))
                    node_label = node.get("name") or node.get("title") or node.get("label") or node_id_str
                    # Preferir 'type', luego 'node_type' (nodos MEMORY), luego primer label Neo4j
                    node_type = node.get('type') or node.get('node_type', 'Desconocido')
                    if (not node_type or node_type == 'Desconocido') and node.get('labels'):
                        labels = node['labels']
                        # Para nodos multi-label (ej: MEMORY + USER_MEMORY), preferir el más específico
                        node_type = next((l for l in labels if l != 'MEMORY'), labels[0]) if labels else 'Desconocido'
                    node_name_for_title = node.get("name") or node.get("title") or node.get("label", "")
                    all_properties = node
                elif hasattr(node, 'id') and hasattr(node, 'labels') and hasattr(node, 'items'): # neo4j.graph.Node object
                    node_id_str = str(node.id)
                    node_props = dict(node)
                    # Preferir propiedad 'type' o 'node_type', luego labels (priorizando sublabels sobre 'MEMORY')
                    node_type = node_props.get('type') or node_props.get('node_type')
                    if not node_type and node.labels:
                        labels = list(node.labels)
                        node_type = next((l for l in labels if l != 'MEMORY'), labels[0])
                    if not node_type:
                        node_type = 'Desconocido'

                    node_label = getattr(node, 'name', getattr(node, 'title', getattr(node, 'label', node_id_str)))
                    node_name_for_title = getattr(node, 'name', getattr(node, 'title', getattr(node, 'label', '')))
                    all_properties = node_props

                # Lógica para generar etiquetas más descriptivas
                if node_type == "IDEA_PROFILE":
                    # Para IDEA_PROFILE, priorizar el central_concept
                    node_label = all_properties.get("central_concept") or all_properties.get("name") or node_label
                    node_name_for_title = node_label # Usar el label como nombre para el título
                return {
                    "id": node_id_str,
                    "label": node_label,
                    "type": node_type,
                    "title": f"Tipo: {node_type}\nNombre: {node_name_for_title}\nID: {node_id_str}",
                    "properties": all_properties
                }

            # Añadir nodo 'n'
            n_id = str(n.get('id')) if isinstance(n, dict) else str(n.id)
            if n_id not in nodes_map:
                nodes_map[n_id] = get_node_properties(n)
            
            # Añadir nodo 'm' si existe (para relaciones)
            m_id = None
            if m:
                m_id = str(m.get('id')) if isinstance(m, dict) else str(m.id)
                if m_id not in nodes_map:
                    nodes_map[m_id] = get_node_properties(m)
            
            # Añadir relación si existe
            if r and m_id:
                # Determinar tipo de relación
                rel_type = "RELATED"
                if isinstance(r, tuple) or isinstance(r, list):
                    if len(r) > 1:
                        rel_type = str(r[1])
                elif hasattr(r, 'type'):
                    rel_type = r.type
                elif isinstance(r, dict):
                    rel_type = r.get('type', 'RELATED')

                edge_id = f"{n_id}-{rel_type}-{m_id}"
                
                # Evitar duplicados
                if edge_id not in added_edge_ids:
                    added_edge_ids.add(edge_id)
                    edges_list.append({
                        "id": edge_id,
                        "from": n_id,
                        "to": m_id,
                        "label": rel_type,
                        "arrows": "to", # Asumimos flechas direccionales para visualización
                        "title": f"Tipo de relación: {rel_type}\nDesde: {nodes_map[n_id]['label']}\nHacia: {nodes_map[m_id]['label']}"
                    })
        
        nodes_list = list(nodes_map.values())

        logger.info(f"Prepared Graph Data: {len(nodes_list)} nodes, {len(edges_list)} edges.")
        return GraphResponse(
            success=True,
            data={
                "nodes": nodes_list,
                "edges": edges_list
            },
            message=f"Grafo obtenido: {len(nodes_list)} nodos y {len(edges_list)} aristas."
        )

    except Exception as e:
        logger.error(f"❌ Error obteniendo datos del grafo: {e}", exc_info=True)
        return GraphResponse(
            success=False,
            error=f"Error obteniendo datos del grafo: {str(e)}"
        )

@router.get("/metadata", response_model=GraphResponse)
@limiter.limit("1000/minute")
async def get_graph_metadata(
    request: Request,
    workspace_id: Optional[str] = None,
    dataset_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene metadata del grafo: tipos de nodos y relaciones disponibles.
    """
    try:
        db = get_graph_db()
        params = {'account_id': current_user['account_id']}
        
        # Construir cláusula WHERE base
        where_clauses = ["n.account_id = $account_id"]

        if workspace_id and workspace_id.lower() != "all":
            if workspace_id.lower() == "global_context":
                where_clauses.append("n.workspace_id IS NULL")
            else:
                where_clauses.append("n.workspace_id = $workspace_id")
                params['workspace_id'] = workspace_id

        if dataset_name and dataset_name.lower() != "all":
            where_clauses.append("n.dataset_name = $dataset_name")
            params['dataset_name'] = dataset_name

        where_statement = " WHERE " + " AND ".join(where_clauses)

        # Query para tipos de nodos
        node_query = f"""
        MATCH (n)
        {where_statement}
        WITH n, 
             CASE 
                WHEN n.type IS NOT NULL AND n.type <> '' THEN n.type 
                WHEN size(labels(n)) > 0 THEN labels(n)[0] 
                ELSE 'Unknown' 
             END AS node_type
        RETURN DISTINCT node_type as type, count(n) as count
        ORDER BY count DESC
        """

        # Query para tipos de relaciones
        # Nota: Para relaciones, verificamos que el nodo origen cumpla los filtros
        edge_query = f"""
        MATCH (n)-[r]->()
        {where_statement}
        RETURN DISTINCT type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        
        node_results = await db.execute_query(node_query, params)
        edge_results = await db.execute_query(edge_query, params)
        
        metadata = {
            "nodeTypes": [
                {"type": r["type"] or "Unknown", "count": r["count"]} 
                for r in node_results
            ],
            "edgeTypes": [
                {"type": r["type"] or "Unknown", "count": r["count"]} 
                for r in edge_results
            ]
        }
        
        return GraphResponse(
            success=True,
            data=metadata,
            message="Metadata del grafo obtenida exitosamente"
        )

    except Exception as e:
        logger.error(f"❌ Error obteniendo metadata del grafo: {e}", exc_info=True)
        return GraphResponse(
            success=False,
            error=f"Error obteniendo metadata: {str(e)}"
        )

# Modelos para análisis de calidad y tendencias
class EntityCorrection(BaseModel):
    entity_id: str
    correction_type: str  # 'type_change', 'merge', 'delete'
    new_type: Optional[str] = None
    target_entity_id: Optional[str] = None  # Para merges

class ApplyCorrectionsRequest(BaseModel):
    corrections: List[Dict[str, Any]]
    auto_apply: bool = False

class TrendAnalysisRequest(BaseModel):
    dataset_name: str
    time_window: str = "last_6_months"
    workspace_id: Optional[str] = None

@router.post("/review-entities")
async def review_entities(
    workspace_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    """
    Revisa la calidad de las entidades en el grafo y sugiere correcciones.
    Detecta entidades mal clasificadas, duplicados y anomalías.
    """
    try:
        results = await kg_service.review_entities_flow(
            workspace_id=workspace_id,
            account_id=current_user['account_id']
        )
        return GraphResponse(
            success=True,
            data=results,
            message="Revisión de entidades completada"
        )
    except Exception as e:
        logger.error(f"❌ Error revisando entidades: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.post("/apply-entity-corrections")
async def apply_entity_corrections(
    request: ApplyCorrectionsRequest,
    current_user: dict = Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    """
    Aplica las correcciones sugeridas a las entidades.
    """
    try:
        results = await kg_service.apply_corrections_flow(
            corrections=request.corrections,
            auto_apply=request.auto_apply,
            account_id=current_user['account_id']
        )
        
        return GraphResponse(
            success=True,
            data=results,
            message="Correcciones aplicadas exitosamente"
        )
    except Exception as e:
        logger.error(f"❌ Error aplicando correcciones: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.post("/detect-trends")
async def detect_trends(
    request: TrendAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Detecta tendencias emergentes y patrones temporales en el grafo.
    """
    try:
        db = get_graph_db()
        
        # Inicializar embeddings (necesario para análisis semántico)
        from utils.embeddings import get_embedding_model, initialize_embeddings
        
        # Asegurar que el modelo esté inicializado
        embedding_model = get_embedding_model()
        if not embedding_model:
            await initialize_embeddings()
            embedding_model = get_embedding_model()
            
        analyzer = TrendAnalyzer(db, embedding_model)
        
        trends = await analyzer.detect_trends(
            dataset_name=request.dataset_name,
            time_window=request.time_window
        )
        
        return GraphResponse(
            success=True,
            data=trends,
            message="Análisis de tendencias completado"
        )
    except Exception as e:
        logger.error(f"❌ Error detectando tendencias: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

# IMPORTANTE: Esta ruta dinámica DEBE estar al final del archivo
# para evitar que capture las rutas estáticas como /data, /status, etc.
@router.get("/{workspace_id}", response_model=GraphResponse)
async def get_knowledge_graph(
    workspace_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el grafo de conocimiento existente para un workspace.
    """
    try:
        # Reutilizar la lógica de get_knowledge_graph_data para obtener los datos del grafo
        graph_data_response = await get_knowledge_graph_data(workspace_id, current_user)
        
        if graph_data_response.success:
            if graph_data_response.data and (graph_data_response.data.get("nodes") or graph_data_response.data.get("edges")):
                return GraphResponse(
                    success=True,
                    data=graph_data_response.data,
                    message=f"Grafo obtenido: {len(graph_data_response.data.get('nodes', []))} nodos y {len(graph_data_response.data.get('edges', []))} aristas."
                )
            else:
                return GraphResponse(
                    success=False,
                    error="Grafo vacío. Procesa los documentos primero para generar el grafo."
                )
        else:
            return GraphResponse(
                success=False,
                error=graph_data_response.error,
                message="Error al obtener los datos del grafo."
            )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo grafo: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE PROGRESO DE PROCESAMIENTO
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/progress/{task_id}", response_model=GraphResponse)
async def get_processing_progress(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el estado de progreso de una tarea de procesamiento de grafo.
    
    Args:
        task_id: ID de la tarea de procesamiento
        
    Returns:
        Estado actual del progreso: fase, porcentaje, mensaje, métricas
    """
    try:
        from knowledge_graph.progress_tracker import get_progress
        
        progress = get_progress(task_id)
        
        if progress is None:
            return GraphResponse(
                success=False,
                error=f"Tarea '{task_id}' no encontrada. Puede que haya expirado o no exista.",
                message="Tarea no encontrada"
            )
        
        return GraphResponse(
            success=True,
            data=progress,
            message=f"Progreso: {progress.get('progress_percent', 0):.0f}% - {progress.get('message', '')}"
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo progreso: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )


@router.get("/progress", response_model=GraphResponse)
async def get_all_active_progress(
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el progreso de todas las tareas de procesamiento activas.
    
    Returns:
        Lista de estados de progreso de todas las tareas activas
    """
    try:
        from knowledge_graph.progress_tracker import get_all_active_progress
        
        active_tasks = get_all_active_progress()
        
        return GraphResponse(
            success=True,
            data={
                "active_tasks": active_tasks,
                "count": len(active_tasks)
            },
            message=f"{len(active_tasks)} tareas activas"
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo progreso activo: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )
@router.post("/process-memories", response_model=GraphResponse)
async def process_memories_endpoint(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    force: bool = False,
):
    """
    Dispara manualmente el procesamiento de memorias del usuario actual.
    Usa ?force=true para resetear el flag y reprocesar todas las memorias.
    """
    try:
        account_id = current_user.get("account_id")
        if not account_id:
            raise HTTPException(status_code=400, detail="Usuario no identificado")

        from knowledge_graph.memory_graph_processor import process_memory_batches
        from knowledge_graph.progress_tracker import create_progress_tracker
        import uuid as _uuid

        task_id = str(_uuid.uuid4())[:8]
        # Registrar el tracker antes del background task para que el polling
        # lo encuentre de inmediato
        create_progress_tracker(task_id=task_id, processing_mode="memory", total_phases=5)

        # Ejecutar en background para no bloquear
        background_tasks.add_task(process_memory_batches, account_id=account_id, task_id=task_id, force=force)

        return GraphResponse(
            success=True,
            message=f"Procesamiento de memorias iniciado {'(forzado)' if force else 'en segundo plano'}.",
            data={"account_id": account_id, "task_id": task_id, "force": force}
        )
    except Exception as e:
        logger.error(f"Error al iniciar procesamiento de memorias: {e}")
        return GraphResponse(
            success=False,
            error=str(e),
            message="Error al iniciar el procesamiento."
        )
