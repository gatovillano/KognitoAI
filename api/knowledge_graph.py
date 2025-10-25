# api/knowledge_graph.py

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from core.database import get_db_session
from core.config import settings
from knowledge_graph.cognee_integration import CogneeIntegration
from knowledge_graph.langchain_cognee_adapter import LangChainCogneeAdapter
from knowledge_graph.graph_database import GraphDB
from utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Modelos Pydantic
class ProcessGraphRequest(BaseModel):
    workspace_id: Optional[str] = None
    force_reprocess: bool = False

class SearchGraphRequest(BaseModel):
    workspace_id: Optional[str] = None
    query: str
    limit: int = 50

class EntityConnectionsRequest(BaseModel):
    workspace_id: Optional[str] = None
    entity_id: str
    max_depth: int = 2

class GraphResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None

# Inicializar componentes de forma lazy (solo cuando se necesiten)
graph_db = None
cognee_integration = None

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

def get_cognee_integration():
    """Obtiene la instancia de CogneeIntegration, creándola si es necesario."""
    global cognee_integration
    if cognee_integration is None:
        cognee_integration = CogneeIntegration(get_graph_db())
    return cognee_integration

def get_langchain_cognee_adapter():
    """Obtiene la instancia de LangChainCogneeAdapter."""
    from core.llm_manager import get_main_llm
    return LangChainCogneeAdapter(get_graph_db(), get_main_llm())



@router.get("/knowledge-graph/{workspace_id}", response_model=GraphResponse)
async def get_knowledge_graph(
    workspace_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el grafo de conocimiento existente para un workspace.
    """
    try:
        # Aquí podrías implementar la lógica para recuperar un grafo guardado
        # Por ahora, devolvemos que no hay datos guardados
        
        return GraphResponse(
            success=False,
            error="Grafo no encontrado. Procesa los documentos primero."
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo grafo: {e}")
        return GraphResponse(
            success=False,
            error=str(e)
        )

@router.get("/knowledge-graph/status", response_model=GraphResponse)
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
    current_user: dict = Depends(get_current_user)
):
    """
    Procesa documentos con el pipeline OPTIMIZADO (sin Fase 3 pesada).
    Garantiza que el procesamiento complete exitosamente.
    """
    try:
        logger.info(f"⚡ Iniciando procesamiento OPTIMIZADO para workspace: {request.workspace_id}")

        # Obtener documentos del workspace
        async with get_db_session() as session:
            # Query para obtener documentos únicos del workspace
            # CORREGIDO: Usar document_id en lugar de file_name para evitar pérdida de documentos
            query = """
                SELECT DISTINCT ON (cmetadata->>'document_id')
                       cmetadata->>'file_name' AS file_name,
                       topic AS topic,
                       cmetadata->>'title' AS title,
                       cmetadata->>'author' AS author,
                       cmetadata->>'document_id' AS document_id,
                       workspace_id::text AS workspace_id,
                       team_id::text AS team_id,
                       CASE WHEN team_id IS NOT NULL THEN true ELSE false END AS team_shared,
                       document AS content
                FROM langchain_pg_embedding
                WHERE account_id = :account_id
                  AND cmetadata->>'type' = 'document_chunk'
                  {f"AND workspace_id::text = '{request.workspace_id}'" if request.workspace_id else "AND workspace_id IS NULL"}
                ORDER BY cmetadata->>'document_id', id
                LIMIT 100;
            """
 
            result = await session.execute(query, {'account_id': current_user['account_id']})
 
            documents = []
            for row in result.fetchall():
                doc_dict = dict(row)
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
 
        logger.info(f"📄 Encontrados {len(documents)} documentos para procesamiento optimizado en {'workspace ' + request.workspace_id if request.workspace_id else 'contexto general'}")
 
        # Procesar con pipeline híbrido optimizado
        from knowledge_graph.hybrid_graph_processor import HybridGraphProcessor
 
        processor = HybridGraphProcessor()
        await processor.initialize()
 
        dataset_name = f"workspace_{request.workspace_id}_optimized" if request.workspace_id else "global_context_optimized"
        graph_data = await processor.process_documents(
            documents,
            dataset_name
        )
 
        # Guardar en Neo4j
        from knowledge_graph.neo4j_adapter import Neo4jAdapter
        db = get_graph_db()
        adapter = Neo4jAdapter(db)
 
        await adapter.add_cognee_results_to_graph(
            graph_data.get('entities', []),
            graph_data.get('relationships', []),
            workspace_id=request.workspace_id # Pasar workspace_id
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
                       team_id::text AS team_id,
                       CASE WHEN team_id IS NOT NULL THEN true ELSE false END AS team_shared,
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
            # Aquí también debemos pasar el workspace_id al adapter si queremos que los nodos se asocien al workspace
            await adapter.add_cognee_results_to_graph(entities, relationships, workspace_id=request.workspace_id)
            logger.info(f"✅ Guardado Fase 2: {len(entities)} entidades, {len(relationships)} relaciones")
 
        processor.set_save_callback(save_after_phase2)
 
        dataset_name = f"workspace_{request.workspace_id}_with_cooccurrence" if request.workspace_id else "global_context_with_cooccurrence"
        # Procesar documentos
        graph_data = await processor.process_documents(
            documents,
            dataset_name
        )
 
        # Guardar resultado final también
        await adapter.add_cognee_results_to_graph(
            graph_data.get('entities', []),
            graph_data.get('relationships', []),
            workspace_id=request.workspace_id # Pasar workspace_id
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

@router.get("/knowledge-graph/stats", response_model=GraphResponse)
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
                  {f"AND workspace_id::text = '{workspace_id}'" if workspace_id else "AND workspace_id IS NULL"}
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

@router.post("/process-knowledge-graph-langchain-cognee", response_model=GraphResponse)
async def process_knowledge_graph_langchain_cognee(
    request: ProcessGraphRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    PRUEBA: Procesa documentos usando langchain-cognee en lugar de nuestra implementación.
    """
    try:
        logger.info(f"🧪 PRUEBA langchain-cognee para workspace: {request.workspace_id if request.workspace_id else 'contexto general'}")
 
        # Obtener documentos del workspace
        async with get_db_session() as session:
            # CORREGIDO: Usar document_id en lugar de file_name para evitar pérdida de documentos
            query = f"""
                SELECT DISTINCT ON (cmetadata->>'document_id')
                       cmetadata->>'file_name' AS file_name,
                       topic AS topic,
                       cmetadata->>'title' AS title,
                       cmetadata->>'author' AS author,
                       document AS content
                FROM langchain_pg_embedding
                WHERE account_id = :account_id
                  AND cmetadata->>'type' = 'document_chunk'
                  {f"AND workspace_id::text = '{request.workspace_id}'" if request.workspace_id else "AND workspace_id IS NULL"}
                ORDER BY cmetadata->>'document_id', id
                LIMIT 10;
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
 
        logger.info(f"📄 Procesando {len(documents)} documentos con langchain-cognee en {'workspace ' + request.workspace_id if request.workspace_id else 'contexto general'}")
 
        # Usar langchain-cognee
        adapter = get_langchain_cognee_adapter()
        dataset_name = f"workspace_{request.workspace_id}" if request.workspace_id else "global_context"
        result = await adapter.process_documents_with_langchain_cognee(
            documents,
            dataset_name
        )
 
        logger.info(f"✅ Procesamiento con langchain-cognee completado para {'workspace ' + request.workspace_id if request.workspace_id else 'contexto general'}")
 
        return GraphResponse(
            success=True,
            data=result,
            message=f"Procesado con langchain-cognee: {result.get('entities_processed', 0)} entidades"
        )

    except Exception as e:
        logger.error(f"❌ Error con langchain-cognee: {e}")
        return GraphResponse(
            success=False,
            error=f"Error langchain-cognee: {str(e)}"
        )

@router.post("/clear-neo4j", response_model=GraphResponse)
async def clear_neo4j(
    current_user: dict = Depends(get_current_user)
):
    """
    Limpia completamente la base de datos Neo4j.
    ⚠️ CUIDADO: Esta acción elimina TODOS los datos.
    """
    try:
        logger.info("🧹 Iniciando limpieza completa de Neo4j...")

        db = get_graph_db()

        # Query para eliminar todo
        clear_query = "MATCH (n) DETACH DELETE n"
        await db.execute_query(clear_query)

        # Verificar que se limpió
        count_query = "MATCH (n) RETURN count(n) as total"
        result = await db.execute_query(count_query)
        total_nodes = result[0]["total"] if result else 0

        logger.info(f"✅ Neo4j limpiado. Nodos restantes: {total_nodes}")

        return GraphResponse(
            success=True,
            data={
                "nodes_deleted": "all",
                "relationships_deleted": "all",
                "remaining_nodes": total_nodes
            },
            message="Neo4j limpiado completamente"
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

@router.get("/knowledge-graph/data", response_model=GraphResponse)
async def get_knowledge_graph_data(
    workspace_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene los nodos y aristas del grafo de conocimiento, opcionalmente filtrado por workspace_id,
    en un formato compatible con vis.js/vis-network.
    """
    try:
        db = get_graph_db()

        # Consulta Cypher base para obtener nodos y relaciones
        query = """
        MATCH (n)-[r]-(m)
        """
        
        # Modificar cláusula WHERE para manejar workspace_id opcional
        if workspace_id:
            if workspace_id.lower() == "all":
                # Si es "all", no se añade ninguna cláusula WHERE de workspace_id
                pass
            elif workspace_id.lower() == "global_context":
                # Si es "global_context", incluir solo nodos sin workspace_id
                query += """
                WHERE n.workspace_id IS NULL AND m.workspace_id IS NULL
                """
            else:
                # Para un workspace_id específico, ambos nodos deben pertenecer a ese workspace.
                query += f"""
                WHERE n.workspace_id = '{workspace_id}' AND m.workspace_id = '{workspace_id}'
                """
        else:
            # Por defecto, si no se especifica workspace_id, mostrar solo el contexto global
            query += """
            WHERE n.workspace_id IS NULL AND m.workspace_id IS NULL
            """
        
        query += """
        RETURN n, r, m
        """
        
        logger.info(f"Executing Cypher Query: {query}")
        result = await db.execute_query(query)
        logger.info(f"Cypher Query Result (first 5 records): {result[:5]}")
 
        nodes_map = {}
        edges_list = []

        for record in result:
            n = record["n"]
            m = record["m"]
            r = record["r"]

            # Función auxiliar para obtener propiedades de forma segura
            def get_node_properties(node):
                node_id_str = str(node.id)
                node_label = node.get("name", node.get("label", node_id_str))
                node_type = node.get('type', 'Desconocido')
                node_name_for_title = node.get('name', node.get('label', ''))
                
                return {
                    "id": node_id_str,
                    "label": node_label,
                    "title": f"Tipo: {node_type}\nNombre: {node_name_for_title}\nID: {node_id_str}"
                }

            # Añadir nodo 'n'
            if str(n.id) not in nodes_map:
                nodes_map[str(n.id)] = get_node_properties(n)
            
            # Añadir nodo 'm'
            if str(m.id) not in nodes_map:
                nodes_map[str(m.id)] = get_node_properties(m)
            
            # Asegurarse de que el ID de la relación sea único
            edge_id = f"{str(n.id)}-{r.type}-{str(m.id)}"
            edges_list.append({
                "id": edge_id,
                "from": str(n.id),
                "to": str(m.id),
                "label": r.type,
                "arrows": "to", # Asumimos flechas direccionales para visualización
                "title": f"Tipo de relación: {r.type}\nDesde: {nodes_map[str(n.id)]['label']}\nHacia: {nodes_map[str(m.id)]['label']}"
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
