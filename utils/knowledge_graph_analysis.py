import logging
import asyncio
import uuid
from typing import Optional, Dict, Any, List
from core.database import SessionLocal
from utils.db_session import DBSession
from sqlalchemy import text
from core.websocket_manager import send_personal_message
import json

# Importaciones para el análisis de grafo real
from core.llm_manager import get_fast_llm
from langchain_core.messages import HumanMessage
from knowledge_graph.neo4j_adapter import Neo4jAdapter
from knowledge_graph.graph_database import GraphDB # Importar GraphDB
from core.memory_manager import list_user_documents, get_full_document_content
from core.config import settings # Importar settings para credenciales de Neo4j

logger = logging.getLogger(__name__)

async def perform_knowledge_graph_analysis_task(
    task_id: str,
    account_id: str,
    topic: str,
    workspace_id: Optional[str] = None
):
    """
    Realiza el análisis de grafo de conocimiento en segundo plano.
    """
    logger.info(f"Iniciando tarea de análisis de grafo de conocimiento {task_id} para el topic '{topic}' en workspace '{workspace_id}'")

    graph_db = None # Inicializar a None
    async with DBSession(SessionLocal) as db:
        try:
            # Actualizar estado a 'processing'
            update_query = text("""
                UPDATE analysis_tasks
                SET status = 'processing', updated_at = NOW()
                WHERE id = :task_id
            """)
            await db.execute(update_query, {"task_id": task_id})
            await db.commit()

            # --- Lógica real del análisis de grafo de conocimiento ---
            # Inicializar GraphDB y Neo4jAdapter
            graph_db = GraphDB(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=settings.neo4j_password
            )
            graph_db.connect()
            neo4j_adapter = Neo4jAdapter(graph_db)
            llm = get_fast_llm()

            if not llm:
                raise ValueError("LLM no disponible para el análisis de grafo de conocimiento.")

            # 1. Recuperar documentos de la colección
            documents = await list_user_documents(
                account_id=account_id,
                topic=topic,
                workspace_id=workspace_id
            )

            if not documents:
                raise ValueError(f"No se encontraron documentos para el topic '{topic}' en el workspace '{workspace_id}'.")

            all_extracted_nodes = []
            all_extracted_relationships = []

            for doc in documents:
                full_content = await get_full_document_content(account_id, doc['file_name'])
                if not full_content:
                    logger.warning(f"No se pudo obtener el contenido completo para el documento {doc['file_name']}. Saltando.")
                    continue

                # 2. Usar LLM para extraer entidades y relaciones
                # Ajustar el prompt para que el LLM devuelva el formato esperado por add_cognee_results_to_graph
                prompt = f"""
                Del siguiente texto, extrae entidades (personas, organizaciones, lugares, conceptos clave) y las relaciones entre ellas.
                Cada entidad debe tener un 'id' único, 'name' y 'type' (ej. Person, Organization, Concept).
                Cada relación debe tener 'source_entity' (id del nodo origen), 'target_entity' (id del nodo destino) y 'relationship_type' (ej. KNOWS, WORKS_AT, RELATED_TO).
                Asegúrate de que los 'id' de las entidades en las relaciones coincidan con los 'id' de las entidades en la lista de nodos.
                El 'name' de la entidad debe ser el texto exacto de la entidad.

                Formato de salida JSON: {{
                    "entities": [{{"id": "unique_id_1", "name": "Nombre Entidad 1", "type": "Tipo Entidad"}}],
                    "relationships": [{{"source_entity": "unique_id_1", "target_entity": "unique_id_2", "relationship_type": "TIPO_RELACION"}}]
                }}

                Texto: {full_content[:4000]} # Aumentar el límite de texto para el LLM si es posible
                """
                try:
                    llm_response = await llm.ainvoke([HumanMessage(content=prompt)])
                    raw_llm_output = llm_response.content

                    # Limpiar la respuesta del LLM para extraer solo el JSON
                    if raw_llm_output.startswith('```json'):
                        raw_llm_output = raw_llm_output.replace('```json', '').strip()
                    if raw_llm_output.endswith('```'):
                        raw_llm_output = raw_llm_output.replace('```', '').strip()
                    
                    llm_output = json.loads(raw_llm_output)

                    # Recolectar nodos y relaciones
                    for entity in llm_output.get("entities", []):
                        # Mapear 'id' a 'cognee_id' para el Neo4jAdapter
                        entity["cognee_id"] = entity.pop("id")
                        all_extracted_nodes.append(entity)
                    for rel in llm_output.get("relationships", []):
                        all_extracted_relationships.append(rel)

                except Exception as llm_e:
                    logger.error(f"Error al extraer entidades/relaciones con LLM para {doc['file_name']}: {llm_e}", exc_info=True)

            # 3. Añadir todas las entidades y relaciones al grafo en un solo lote
            if all_extracted_nodes or all_extracted_relationships:
                await neo4j_adapter.add_cognee_results_to_graph(
                    entities=all_extracted_nodes,
                    relationships=all_extracted_relationships,
                    workspace_id=workspace_id
                )

            # 4. Consultar Neo4j para obtener un resumen del grafo
            graph_stats = await neo4j_adapter.get_graph_stats()
            total_nodes = graph_stats.get("total_nodes", 0)
            total_relationships = graph_stats.get("total_relationships", 0)
            
            graph_summary = f"Análisis de grafo de conocimiento completado para la colección '{topic}'. Se identificaron {total_nodes} nodos y {total_relationships} relaciones clave."

            result_payload = {
                "analysis_type": "knowledge_graph_analysis",
                "graph_summary": graph_summary,
                "nodes": all_extracted_nodes, # Devolver los nodos extraídos por el LLM
                "relationships": all_extracted_relationships # Devolver las relaciones extraídas por el LLM
            }
            # --- Fin de la lógica real ---

            status = "completed"
            # Serializar el diccionario a JSON string
            result_payload_json = json.dumps(result_payload)
            # Actualizar estado y resultado de la tarea
            update_result_query = text("""
                UPDATE analysis_tasks
                SET status = :status, result_payload = CAST(:result_payload AS jsonb), updated_at = NOW()
                WHERE id = :task_id
            """)
            await db.execute(update_result_query, {
                "task_id": task_id,
                "status": status,
                "result_payload": result_payload_json
            })
            await db.commit()

            logger.info(f"Tarea de análisis de grafo de conocimiento {task_id} completada con estado '{status}'")

            # Notificar al frontend a través de WebSocket
            await send_personal_message(
                account_id,
                {
                    "type": "collection_analysis_completed",
                    "task_id": task_id,
                    "status": status,
                    "result": result_payload
                }
            )

        except Exception as e:
            logger.error(f"Error durante la tarea de análisis de grafo de conocimiento {task_id}: {e}", exc_info=True)
            await db.rollback()
            # Actualizar estado a 'failed' en caso de error
            update_error_query = text("""
                UPDATE analysis_tasks
                SET status = 'failed', error_message = :error_message, updated_at = NOW()
                WHERE id = :task_id
            """)
            await db.execute(update_error_query, {
                "task_id": task_id,
                "error_message": str(e)
            })
            await db.commit()

            # Notificar al frontend a través de WebSocket
            await send_personal_message(
                account_id,
                {
                    "type": "collection_analysis_failed",
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e)
                }
            )
        finally:
            if graph_db:
                graph_db.close()

async def start_knowledge_graph_analysis(
    account_id: str,
    topic: str,
    workspace_id: Optional[str] = None
) -> str:
    """
    Inicia el proceso de análisis de grafo de conocimiento en segundo plano.
    """
    task_id = str(uuid.uuid4())
    logger.info(f"Programando análisis de grafo de conocimiento para account '{account_id}', topic '{topic}', workspace '{workspace_id}' con task_id '{task_id}'")

    async with DBSession(SessionLocal) as db:
        try:
            # Registrar la tarea en la base de datos
            insert_query = text("""
                INSERT INTO analysis_tasks (id, account_id, file_name, status, analysis_type, created_at, updated_at)
                VALUES (:task_id, :account_id, :file_name, 'pending', 'knowledge_graph_analysis', NOW(), NOW())
            """)
            await db.execute(insert_query, {
                "task_id": task_id,
                "account_id": account_id,
                "file_name": f"Análisis de Grafo de Conocimiento: {topic}"
            })
            await db.commit()

            # Iniciar la tarea en segundo plano
            asyncio.create_task(perform_knowledge_graph_analysis_task(
                task_id, account_id, topic, workspace_id
            ))

            return task_id
        except Exception as e:
            logger.error(f"Error al registrar la tarea de análisis de grafo de conocimiento: {e}", exc_info=True)
            await db.rollback()
            raise