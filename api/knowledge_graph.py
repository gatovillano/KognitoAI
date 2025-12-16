# api/knowledge_graph.py

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
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
                  AND cmetadata->>'type' = 'document_chunk'
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
    current_user: dict = Depends(get_current_user)
):
    """
    Busca entidades en el grafo de conocimiento.
    """
    try:
        # Implementar búsqueda en el grafo
        # Por ahora devolvemos resultados vacíos
        
        return GraphResponse(
            success=True,
            data={
                "results": [],
                "query": request.query,
                "total": 0
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
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene las conexiones de una entidad específica.
    """
    try:
        # Implementar búsqueda de conexiones
        # Por ahora devolvemos conexiones vacías
        
        return GraphResponse(
            success=True,
            data={
                "entity_id": request.entity_id,
                "connections": [],
                "depth": request.max_depth
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
    current_user: dict = Depends(get_current_user)
):
    """
    Prueba la conexión con Neo4j y muestra estadísticas básicas.
    """
    try:
        # Probar conexión básica
        db = get_graph_db()
        test_query = "RETURN 'Neo4j conectado correctamente' as message"
        result = await db.execute_query(test_query)

        # Obtener estadísticas
        stats_query = """
        MATCH (n)
        OPTIONAL MATCH ()-[r]-()
        RETURN count(DISTINCT n) as nodes, count(DISTINCT r) as relationships
        """
        stats_result = await db.execute_query(stats_query)

        stats = stats_result[0] if stats_result else {"nodes": 0, "relationships": 0}

        return GraphResponse(
            success=True,
            data={
                "connection": "OK",
                "message": result[0]["message"] if result else "Conectado",
                "stats": stats,
                "neo4j_uri": settings.neo4j_uri,
                "neo4j_user": settings.neo4j_user
            },
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
    db: AsyncSession = Depends(get_db_session)
):
    """
    Procesa documentos con el pipeline OPTIMIZADO (sin Fase 3 pesada).
    Garantiza que el procesamiento complete exitosamente.
    """
    try:
        logger.info(f"⚡ Iniciando procesamiento OPTIMIZADO para workspace: {request.workspace_id}")

        # Obtener documentos del workspace
        # Query para obtener documentos únicos del workspace
        # CORREGIDO: Usar document_id en lugar de file_name para evitar pérdida de documentos
        # Construir filtros dinámicamente
        filters = ["account_id = :account_id", "cmetadata->>'type' = 'document_chunk'"]
        
        if request.workspace_id:
            filters.append(f"workspace_id::text = '{request.workspace_id}'")
        else:
            filters.append("workspace_id IS NULL")
        
        # NUEVO: Filtrar por topic si se especifica
        if request.topic:
            filters.append(f"topic = :topic")
        
        where_clause = " AND ".join(filters)
        
        query = text(f"""
            SELECT DISTINCT ON (cmetadata->>'document_id')
                   cmetadata->>'file_name' AS file_name,
                   topic AS topic,
                   cmetadata->>'title' AS title,
                   cmetadata->>'author' AS author,
                   cmetadata->>'document_id' AS document_id,
                   workspace_id::text AS workspace_id,
                   document AS content
            FROM langchain_pg_embedding
            WHERE {where_clause}
            ORDER BY cmetadata->>'document_id', id
            LIMIT 100;
        """)

        params = {'account_id': current_user['account_id']}
        if request.topic:
            params['topic'] = request.topic
        
        result = await db.execute(query, params)

        documents = []
        for row in result.fetchall():
            doc_dict = dict(row._mapping)
            # Agregar contenido si está disponible
            if doc_dict.get('content'):
                doc_dict['content'] = doc_dict['content']
            else:
                doc_dict['content'] = f"Documento: {doc_dict.get('title', 'Sin título')}"
            documents.append(doc_dict)
 
        if not documents:
            detail_msg = "No se encontraron documentos en este workspace" if request.workspace_id else "No se encontraron documentos en el contexto general"
            return GraphResponse(
                success=False,
                error=detail_msg
            )
 
        context_desc = f"colección '{request.topic}'" if request.topic else (f"workspace {request.workspace_id}" if request.workspace_id else "contexto general")
        logger.info(f"📄 Encontrados {len(documents)} documentos para procesamiento optimizado en {context_desc}")
 
        # Determinar el modo de procesamiento
        processing_mode = request.processing_mode or "hybrid"

        if processing_mode == "conceptual":
            # Procesar con pipeline conceptual
            logger.info("🧠 Procesando con modo conceptual...")

            # Inicializar integración
            graph_integration = get_graph_integration()

            # Usar dataset_name proporcionado o generar uno por defecto
            if request.dataset_name:
                dataset_name = request.dataset_name
            else:
                dataset_name = f"workspace_{request.workspace_id}_conceptual" if request.workspace_id else "global_context_conceptual"

            # Procesar documentos conceptualmente
            result = await graph_integration.process_documents(
                documents=documents,
                dataset_name=dataset_name,
                account_id=current_user['account_id'],
                processing_mode="conceptual"
            )

            logger.info(f"✅ Procesamiento conceptual completado para {'workspace ' + request.workspace_id if request.workspace_id else 'contexto general'}")

            return GraphResponse(
                success=True,
                data=result,
                message=f"Grafo procesado conceptualmente: {result.get('conceptual_quotes', 0)} citas conceptuales, {result.get('thematic_relationships', 0)} relaciones temáticas, {result.get('idea_profiles', 0)} perfiles de ideas"
            )

        else:
            # Procesar con pipeline híbrido optimizado (modo por defecto)
            logger.info("⚙️ Procesando con modo híbrido...")

            from knowledge_graph.hybrid_graph_processor import HybridGraphProcessor

            processor = HybridGraphProcessor()
            await processor.initialize()

            # Usar dataset_name proporcionado o generar uno por defecto
            if request.dataset_name:
                dataset_name = request.dataset_name
            else:
                dataset_name = f"workspace_{request.workspace_id}_hybrid" if request.workspace_id else "global_context_hybrid"

            graph_data = await processor.process_documents(
                documents,
                dataset_name,
                account_id=current_user['account_id'],
                workspace_id=request.workspace_id
            )

            # Guardar en Neo4j
            from knowledge_graph.neo4j_adapter import Neo4jAdapter
            db = get_graph_db()
            adapter = Neo4jAdapter(db)

            await adapter.add_cognee_results_to_graph(
                graph_data.get('entities', []),
                graph_data.get('relationships', []),
                workspace_id=request.workspace_id, # Pasar workspace_id
                account_id=current_user['account_id']
            )
 
        logger.info(f"✅ Procesamiento optimizado completado para {'workspace ' + request.workspace_id if request.workspace_id else 'contexto general'}")
 
        return GraphResponse(
            success=True,
            data=graph_data,
            message=f"Grafo procesado con pipeline optimizado: {len(graph_data.get('entities', []))} entidades, {len(graph_data.get('relationships', []))} relaciones"
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
    current_user: dict = Depends(get_current_user)
):
    """
    Procesa documentos con co-ocurrencias OPTIMIZADAS.
    Más lento pero más completo que la versión optimizada básica.
    """
    try:
        logger.info(f"🔗 Iniciando procesamiento CON co-ocurrencias optimizadas para workspace: {request.workspace_id}")

        # Obtener documentos del workspace
        async with get_db_session() as session:
            # CORREGIDO: Usar document_id en lugar de file_name para evitar pérdida de documentos
            query = """
                SELECT DISTINCT ON (cmetadata->>'document_id')
                       cmetadata->>'file_name' AS file_name,
                       topic AS topic,
                       cmetadata->>'title' AS title,
                       cmetadata->>'author' AS author,
                       cmetadata->>'document_id' AS document_id,
                       workspace_id::text AS workspace_id,
                       NULL::text AS team_id,
                       false AS team_shared,
                       document AS content
                FROM langchain_pg_embedding
                WHERE account_id = :account_id
                  AND cmetadata->>'type' = 'document_chunk'
                  {f"AND workspace_id::text = '{request.workspace_id}'" if request.workspace_id else "AND workspace_id IS NULL"}
                ORDER BY cmetadata->>'document_id', id
                LIMIT 50;
            """
 
            result = await session.execute(query, {'account_id': current_user['account_id']})
 
            documents = []
            for row in result.fetchall():
                doc_dict = dict(row)
                if doc_dict.get('content'):
                    doc_dict['content'] = doc_dict['content']
                else:
                    doc_dict['content'] = f"Documento: {doc_dict.get('title', 'Sin título')}"
                documents.append(doc_dict)
 
        if not documents:
            detail_msg = "No se encontraron documentos en este workspace" if request.workspace_id else "No se encontraron documentos en el contexto general"
            return GraphResponse(
                success=False,
                error=detail_msg
            )
 
        logger.info(f"📄 Encontrados {len(documents)} documentos para procesamiento con co-ocurrencias en {'workspace ' + request.workspace_id if request.workspace_id else 'contexto general'}")
 
        # Procesar con pipeline híbrido + co-ocurrencias optimizadas
        from knowledge_graph.hybrid_graph_processor import HybridGraphProcessor
 
        processor = HybridGraphProcessor()
        await processor.initialize()
 
        # Configurar callback para guardar después de Fase 2
        from knowledge_graph.neo4j_adapter import Neo4jAdapter
        db = get_graph_db()
        adapter = Neo4jAdapter(db)
 
        async def save_after_phase2(entities, relationships):
            logger.info("💾 Guardando después de Fase 2...")
            # Aquí también debemos pasar el workspace_id y account_id al adapter
            await adapter.add_cognee_results_to_graph(
                entities,
                relationships,
                workspace_id=request.workspace_id,
                account_id=current_user['account_id']
            )
            logger.info(f"✅ Guardado Fase 2: {len(entities)} entidades, {len(relationships)} relaciones")
 
        processor.set_save_callback(save_after_phase2)
 
        dataset_name = f"workspace_{request.workspace_id}_with_cooccurrence" if request.workspace_id else "global_context_with_cooccurrence"
        # Procesar documentos
        graph_data = await processor.process_documents(
            documents,
            dataset_name,
            account_id=current_user['account_id'],
            workspace_id=request.workspace_id
        )
 
        # Guardar resultado final también
        await adapter.add_cognee_results_to_graph(
            graph_data.get('entities', []),
            graph_data.get('relationships', []),
            workspace_id=request.workspace_id,
            account_id=current_user['account_id']
        )
 
        logger.info(f"✅ Procesamiento con co-ocurrencias completado para {'workspace ' + request.workspace_id if request.workspace_id else 'contexto general'}")
 
        return GraphResponse(
            success=True,
            data=graph_data,
            message=f"Grafo procesado con co-ocurrencias optimizadas: {len(graph_data.get('entities', []))} entidades, {len(graph_data.get('relationships', []))} relaciones"
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
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene estadísticas del grafo de conocimiento para un workspace específico o el contexto general.
    """
    try:
        async with get_db_session() as session:
            query = f"""
                SELECT
                    COUNT(DISTINCT cmetadata->>'file_name') as document_count,
                    COUNT(*) as chunk_count,
                    AVG(LENGTH(document)) as avg_chunk_length
                FROM langchain_pg_embedding
                WHERE account_id = :account_id
                  AND cmetadata->>'type' = 'document_chunk'
                  {f"AND workspace_id::text = '{workspace_id}'" if workspace_id else ""}
            """
            
            result = await session.execute(query, {'account_id': current_user['account_id']})
            
            row = result.fetchone()
            
            stats = {
                "document_count": row[0] if row else 0,
                "chunk_count": row[1] if row else 0,
                "avg_chunk_length": round(row[2]) if row and row[2] else 0,
                "workspace_id": workspace_id, # Puede ser None
                "last_updated": datetime.now().isoformat()
            }
        
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



@router.post("/clear-neo4j", response_model=GraphResponse)
async def clear_neo4j(
    request: ClearGraphRequest = ClearGraphRequest(),
    current_user: dict = Depends(get_current_user)
):
    """
    Limpia la base de datos Neo4j.
    
    - Si se proporciona `workspace_id`, solo elimina los nodos de ese workspace.
    - Si NO se proporciona `workspace_id`, requiere `confirm_delete_all=True` para eliminar TODO.
    """
    try:
        db = get_graph_db()
        
        if request.workspace_id:
            logger.info(f"🧹 Iniciando limpieza de Neo4j para workspace: {request.workspace_id}...")
            # Eliminar solo nodos del workspace
            clear_query = "MATCH (n) WHERE n.workspace_id = $workspace_id DETACH DELETE n"
            await db.execute_query(clear_query, {"workspace_id": request.workspace_id})
            message = f"Datos del workspace {request.workspace_id} eliminados"
            
        else:
            if not request.confirm_delete_all:
                raise HTTPException(
                    status_code=400, 
                    detail="Para eliminar TODA la base de datos, debes establecer confirm_delete_all=True"
                )
                
            logger.info("🧹 Iniciando limpieza COMPLETA de Neo4j...")
            # Eliminar todo
            clear_query = "MATCH (n) DETACH DELETE n"
            await db.execute_query(clear_query)
            message = "Neo4j limpiado completamente (todos los datos)"

        # Verificar nodos restantes (global o por workspace)
        if request.workspace_id:
            count_query = "MATCH (n) WHERE n.workspace_id = $workspace_id RETURN count(n) as total"
            result = await db.execute_query(count_query, {"workspace_id": request.workspace_id})
        else:
            count_query = "MATCH (n) RETURN count(n) as total"
            result = await db.execute_query(count_query)
            
        total_nodes = result[0]["total"] if result else 0

        logger.info(f"✅ Limpieza completada. Nodos restantes: {total_nodes}")

        return GraphResponse(
            success=True,
            data={
                "nodes_deleted": "workspace" if request.workspace_id else "all",
                "remaining_nodes": total_nodes
            },
            message=message
        )

    except Exception as e:
        logger.error(f"❌ Error limpiando Neo4j: {e}")
        return GraphResponse(
            success=False,
            error=f"Error limpiando Neo4j: {str(e)}"
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
        results = await reviewer.apply_corrections(corrections, auto_apply)

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

        # Inicializar integración
        db = get_graph_db()
        cognee_integration = CogneeIntegration(db)

        # Procesar conceptualmente
        result = await cognee_integration.process_documents_conceptually(documents, dataset_name)

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
        db = get_graph_db()
        cognee_integration = CogneeIntegration(db)

        # Detectar tendencias
        trends_result = await cognee_integration.detect_trends(
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
        db = get_graph_db()
        cognee_integration = CogneeIntegration(db)

        # Realizar análisis temporal
        temporal_result = await cognee_integration.analyze_temporal_patterns(
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
        db = get_graph_db()
        cognee_integration = CogneeIntegration(db)

        # Obtener tendencias con umbral bajo para resumen
        trends_result = await cognee_integration.detect_trends(
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
        where_clauses = ["(n.account_id = $account_id OR n.account_id IS NULL)", "n.dataset_name IS NOT NULL"]

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
async def get_knowledge_graph_data(
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
        where_clauses = ["(n.account_id = $account_id OR n.account_id IS NULL)"]

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
        WHERE (m.account_id = $account_id OR m.account_id IS NULL OR m IS NULL)
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
                    node_label = node.get("name", node.get("label", node_id_str))
                    node_type = node.get('type', 'Desconocido') # Preferir la propiedad 'type'
                    if node_type == 'Desconocido' and node.get('labels'): # Si no hay propiedad 'type', intentar con las etiquetas de Neo4j
                         node_type = node['labels'][0] if node['labels'] else 'Desconocido'
                    node_name_for_title = node.get('name', node.get('label', ''))
                    all_properties = node
                elif hasattr(node, 'id') and hasattr(node, 'labels') and hasattr(node, 'items'): # neo4j.graph.Node object
                    node_id_str = str(node.id)
                    # Tomar el primer label de Neo4j como el tipo principal
                    if node.labels:
                        node_type = list(node.labels)[0]
                    else:
                        node_type = getattr(node, 'type', 'Desconocido') # Fallback a la propiedad 'type' si no hay labels

                    node_label = getattr(node, 'name', getattr(node, 'label', node_id_str))
                    node_name_for_title = getattr(node, 'name', getattr(node, 'label', ''))
                    all_properties = dict(node) # Convertir a dict para propiedades

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
async def get_graph_metadata(
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
        where_clauses = ["(n.account_id = $account_id OR n.account_id IS NULL)"]

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
        RETURN DISTINCT n.type as type, count(n) as count
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
    current_user: dict = Depends(get_current_user)
):
    """
    Revisa la calidad de las entidades en el grafo y sugiere correcciones.
    Detecta entidades mal clasificadas, duplicados y anomalías.
    """
    try:
        db = get_graph_db()
        # Inicializar LLM (necesario para validación contextual)
        from core.llm_manager import LLMManager
        llm_manager = LLMManager()
        # Usar un modelo rápido para validación
        llm = llm_manager.get_llm(model_name="gemini-1.5-flash") 
        
        reviewer = EntityQualityReviewer(db, llm)
        results = await reviewer.review_all_entities(workspace_id)
        
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
    current_user: dict = Depends(get_current_user)
):
    """
    Aplica las correcciones sugeridas a las entidades.
    """
    try:
        db = get_graph_db()
        reviewer = EntityQualityReviewer(db)
        
        results = await reviewer.apply_corrections(request.corrections, request.auto_apply)
        
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

