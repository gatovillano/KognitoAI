# knowledge_graph/graph_integration.py
"""
Integración para grafos de conocimiento usando un enfoque híbrido (spaCy + LLM + Neo4j).
Reemplaza la integración directa con Cognee por una implementación propia más flexible.
"""

import logging
import os
import numpy as np
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import asyncio
import re
import json

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import SessionLocal
from utils.db_session import DBSession
from knowledge_graph.graph_database import GraphDB
from core.llm_manager import get_main_llm, get_fast_llm
from utils.embeddings import get_embedding_model
from core.memory_manager import get_full_document_content
from knowledge_graph.hybrid_graph_processor import HybridGraphProcessor
from knowledge_graph.neo4j_adapter import Neo4jAdapter

logger = logging.getLogger(__name__)

class GraphIntegration:
    """
    Integración de bajo nivel con Neo4j y orquestación de procesadores de grafo.
    
    Responsabilidades:
    - Integración directa con Neo4j (creación de índices, consultas Cypher)
    - Orquestación entre HybridGraphProcessor y ConceptualGraphProcessor
    - Conversión de formatos entre diferentes procesadores y Neo4j
    - Búsquedas avanzadas y análisis temporal en el grafo
    - Generación de datos para visualización
    
    Nota: Los métodos con prefijo _ son privados y solo para uso interno.
    """
    
    def __init__(self, graph_db: GraphDB):
        """
        Inicializa la integración con Neo4j y procesadores de grafo.
        
        Args:
            graph_db (GraphDB): Instancia configurada de GraphDB para Neo4j.
        """
        self.graph_db = graph_db
        # Inicializar con LLMs para permitir enriquecimiento de relaciones
        self.llm = get_main_llm()
        self.fast_llm = get_fast_llm()
        self.hybrid_processor = HybridGraphProcessor(
            llm=self.llm,
            fast_llm=self.fast_llm
        )
        self.hybrid_adapter = Neo4jAdapter(graph_db)
        
        logger.info("✅ GraphIntegration inicializada con Neo4jAdapter y HybridGraphProcessor (LLM enabled)")

    async def _create_fulltext_indexes(self):
        """
        Método privado: Crea índices full-text en Neo4j para búsquedas eficientes.
        
        Solo se ejecuta cuando es necesario para optimizar búsquedas de texto completo
        en nodos CONCEPTUAL_QUOTE e IDEA_PROFILE, y relaciones THEMATIC_RELATIONSHIP.
        """
        try:
            logger.info("🔍 Verificando y creando índices full-text en Neo4j...")

            # Índice para nodos (CONCEPTUAL_QUOTE y IDEA_PROFILE)
            node_index_query = """
            CREATE FULLTEXT INDEX node_fulltext_index IF NOT EXISTS
            FOR (n:CONCEPTUAL_QUOTE | IDEA_PROFILE | DOCUMENT | PERSON | ORGANIZATION | EVENT | LOCATION | PRODUCT | TOPIC | CHAT_MESSAGE | USER_MEMORY)
            ON EACH [n.name, n.title, n.description, n.concept, n.full_text, n.category, n.summary, n.content]
            """
            await self.graph_db.execute_query(node_index_query)
            logger.info("✅ Índice 'node_fulltext_index' para nodos asegurado.")

            # Índice para relaciones (THEMATIC_RELATIONSHIP y CONTAINS_IDEA)
            relationship_index_query = """
            CREATE FULLTEXT INDEX relationship_fulltext_index IF NOT EXISTS
            FOR ()-[r:THEMATIC_RELATIONSHIP | CONTAINS_IDEA]-()
            ON EACH [r.description, r.full_text]
            """
            await self.graph_db.execute_query(relationship_index_query)
            logger.info("✅ Índice 'relationship_fulltext_index' para relaciones asegurado.")

        except Exception as e:
            logger.error(f"❌ Error creando índices full-text: {e}", exc_info=True)

    async def process_documents(self, db_session: AsyncSession, documents: List[Dict[str, Any]], dataset_name: str = "default", account_id: Optional[str] = None, processing_mode: Literal["conceptual", "hybrid"] = "conceptual", topic: Optional[str] = None, workspace_id: Optional[str] = None, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Procesa documentos usando un enfoque híbrido o conceptual.

        Args:
            db_session: Sesión de base de datos asíncrona inyectada por FastAPI.
            documents: Lista de documentos a procesar. Si está vacía, se buscarán documentos en la base de datos.
            dataset_name: Nombre del dataset.
            account_id: ID del usuario o cuenta propietaria de los documentos.
            processing_mode: Modo de procesamiento ("conceptual" o "hybrid").
            topic: Tema/colección para filtrar documentos si no se proporcionan.
            workspace_id: ID del workspace para filtrar documentos si no se proporcionan.
            task_id: ID opcional de tarea para rastreo de progreso.

        Returns:
            Dict con el resultado del procesamiento.
        """
        # Importar y crear tracker de progreso
        from knowledge_graph.progress_tracker import (
            create_progress_tracker, 
            ProcessingPhase
        )
        
        # Determinar número de fases según el modo
        total_phases = 6 if processing_mode == "hybrid" else 5
        
        # Crear tracker de progreso
        tracker = create_progress_tracker(
            task_id=task_id,
            processing_mode=processing_mode,
            total_phases=total_phases
        )
        
        # Configurar callback de progreso para enviar mensajes vía WebSocket
        if account_id:
            from core.websocket_manager import send_personal_message
            import asyncio
            
            # Obtener el loop actual al crear el tracker
            try:
                main_loop = asyncio.get_running_loop()
            except RuntimeError:
                main_loop = None
            
            def on_progress_callback(status):
                # Crear una tarea asíncrona para enviar el mensaje sin bloquear
                try:
                    message = {
                        "type": "knowledge_graph_progress",
                        "data": status
                    }
                    
                    if main_loop and main_loop.is_running():
                        main_loop.call_soon_threadsafe(
                            lambda: asyncio.create_task(send_personal_message(
                                account_id=account_id,
                                message=message
                            ))
                        )
                    else:
                        # Fallback: intentar obtener el loop actual (si estamos en un thread con loop)
                        try:
                            current_loop = asyncio.get_event_loop()
                            if current_loop.is_running():
                                current_loop.create_task(send_personal_message(
                                    account_id=account_id,
                                    message=message
                                ))
                        except Exception:
                            logger.error(f"No se pudo obtener un loop de asyncio para enviar progreso")
                except Exception as e:
                    logger.error(f"Error enviando progreso de grafo vía WebSocket: {e}")
            
            tracker.on_progress = on_progress_callback
        
        logger.info(f"📊 Tracker de progreso creado: {tracker.task_id}")
        
        await self._create_fulltext_indexes()

        # ═══════════════════════════════════════════════════════════════
        # FASE INICIAL: Obtener documentos
        # ═══════════════════════════════════════════════════════════════
        tracker.update_phase(
            ProcessingPhase.INITIALIZING,
            "🚀 Inicializando procesamiento de grafo de conocimiento...",
            2
        )

        # Si no se proporcionaron documentos, buscarlos en la base de datos
        if not documents:
            if not account_id:
                tracker.set_error("Se requiere account_id cuando no se proporcionan documentos")
                raise ValueError("Se requiere account_id cuando no se proporcionan documentos")
            
            tracker.update_phase(
                ProcessingPhase.FETCHING_DOCUMENTS,
                f"🔍 Buscando documentos en base de datos...",
                5
            )
            
            logger.info(f"🔍 Buscando documentos en base de datos para account_id: {account_id}, topic: {topic}, workspace_id: {workspace_id}")
            documents = await self._fetch_documents_from_db(db_session, account_id, topic, workspace_id)
            
            tracker.update_phase(
                ProcessingPhase.FETCHING_DOCUMENTS,
                f"✅ Encontrados {len(documents)} documentos",
                8,
                {"documents_processed": len(documents)}
            )

        logger.info(f"🧠 Iniciando procesamiento {processing_mode} para {len(documents)} documentos.")

        try:
            # ═══════════════════════════════════════════════════════════════
            # FASE: Reconstruir contenido
            # ═══════════════════════════════════════════════════════════════
            tracker.update_phase(
                ProcessingPhase.RECONSTRUCTING_CONTENT,
                f"📄 Reconstruyendo contenido de {len(documents)} documentos...",
                10
            )
            
            # Reconstruir contenido completo desde chunks vectorizados
            processed_documents = await self._reconstruct_document_content(documents, account_id=account_id, topic=topic)

            if not processed_documents:
                tracker.set_error("No se pudo reconstruir contenido de documentos.")
                raise ValueError("No se pudo reconstruir contenido de documentos.")
            
            tracker.update_phase(
                ProcessingPhase.RECONSTRUCTING_CONTENT,
                f"✅ {len(processed_documents)} documentos reconstruidos",
                15,
                {"documents_processed": len(processed_documents)}
            )

            if processing_mode == "hybrid":
                # ═══════════════════════════════════════════════════════════════
                # MODO HÍBRIDO (spaCy + Embeddings)
                # ═══════════════════════════════════════════════════════════════
                logger.info("⚙️ Ejecutando HybridGraphProcessor (spaCy + Embeddings)...")
                
                # Crear nodos DOCUMENT (común a ambos modos para visualización)
                from knowledge_graph.conceptual_graph_processor import ConceptualGraphProcessor
                conceptual_processor = ConceptualGraphProcessor(
                    llm=self.llm, 
                    fast_llm=self.fast_llm, 
                    neo4j_adapter=self.hybrid_adapter
                )
                workspace_id = documents[0].get("metadata", {}).get("workspace_id") if documents else None
                await conceptual_processor._create_document_nodes(processed_documents, workspace_id, account_id, dataset_name)

                hybrid_result = await self.hybrid_processor.process_documents(
                    processed_documents, 
                    dataset_name=dataset_name,
                    account_id=account_id,
                    workspace_id=workspace_id,
                    progress_tracker=tracker
                )
                
                # Guardar resultados en Neo4j usando el adaptador
                stats = await self.hybrid_adapter.add_cognee_results_to_graph(
                    hybrid_result["entities"], 
                    hybrid_result["relationships"],
                    workspace_id=documents[0].get("metadata", {}).get("workspace_id") if documents else None,
                    account_id=account_id,
                    dataset_name=dataset_name
                )
                
                # Marcar como completado
                tracker.complete(
                    f"🎉 Procesamiento híbrido completado: {len(hybrid_result['entities'])} entidades, {len(hybrid_result['relationships'])} relaciones"
                )
                
                return {
                    "success": True,
                    "processing_type": "hybrid_spacy_embeddings",
                    "entities_count": len(hybrid_result["entities"]),
                    "relationships_count": len(hybrid_result["relationships"]),
                    "neo4j_stats": stats,
                    "metadata": hybrid_result.get("metadata", {}),
                    "task_id": tracker.task_id  # Incluir task_id en respuesta
                }

            else:
                # ═══════════════════════════════════════════════════════════════
                # MODO CONCEPTUAL (LLM-Driven)
                # ═══════════════════════════════════════════════════════════════
                from knowledge_graph.conceptual_graph_processor import ConceptualGraphProcessor
                from core.llm_manager import get_llm_for_user
                
                if account_id:
                    llm = await get_llm_for_user(account_id, purpose="main")
                    fast_llm = await get_llm_for_user(account_id, purpose="fast")
                else:
                    llm = get_main_llm()
                    fast_llm = get_fast_llm()

                if not llm:
                    tracker.set_error("LLM principal no disponible para procesamiento conceptual.")
                    raise ValueError("LLM principal no disponible para procesamiento conceptual.")
                
                logger.info(f"💡 LLM principal para account {account_id}: {llm is not None}. Iniciando ConceptualGraphProcessor.")
                conceptual_processor = ConceptualGraphProcessor(
                    llm=llm, 
                    fast_llm=fast_llm,
                    neo4j_adapter=self.hybrid_adapter,
                    progress_tracker=tracker
                )


                # Procesar documentos conceptualmente
                conceptual_result = await conceptual_processor.process_documents_conceptually(
                    processed_documents, 
                    dataset_name,
                    progress_tracker=tracker
                )

                # Guardar en Neo4j usando el adaptador
                if self.hybrid_adapter:
                    # Convertir formato conceptual a formato compatible con Neo4j
                    neo4j_data = await self._convert_conceptual_to_neo4j_format(conceptual_result)

                    # Guardar nodos conceptuales
                    await self.hybrid_adapter.add_cognee_results_to_graph(neo4j_data["entities"], [])
                    logger.info(f"✅ {len(neo4j_data['entities'])} citas conceptuales guardadas.")

                    # Guardar relaciones temáticas
                    await self.hybrid_adapter.add_cognee_results_to_graph([], neo4j_data["relationships"])
                    logger.info(f"✅ {len(neo4j_data['relationships'])} relaciones temáticas guardadas.")

                    # Guardar perfiles de ideas como nodos especiales
                    if neo4j_data.get("profiles"):
                        await self.hybrid_adapter.add_cognee_results_to_graph(neo4j_data["profiles"], [])
                        logger.info(f"✅ {len(neo4j_data['profiles'])} perfiles de ideas guardados.")

                    # Guardar relaciones de perfiles
                    if neo4j_data.get("profile_relationships"):
                        await self.hybrid_adapter.add_cognee_results_to_graph([], neo4j_data["profile_relationships"])
                        logger.info(f"✅ {len(neo4j_data['profile_relationships'])} relaciones de perfiles guardadas.")

                logger.info("🎉 Procesamiento conceptual LLM-driven completado exitosamente.")
                
                # Marcar como completado
                tracker.complete(
                    f"🎉 Procesamiento conceptual completado: {len(conceptual_result.get('conceptual_nodes', []))} citas, {len(conceptual_result.get('thematic_relationships', []))} relaciones"
                )

                return {
                    "success": True,
                    "processing_type": "conceptual_llm_driven",
                    "conceptual_quotes": len(conceptual_result.get("conceptual_nodes", [])),
                    "thematic_relationships": len(conceptual_result.get("thematic_relationships", [])),
                    "idea_profiles": len(conceptual_result.get("idea_profiles", [])),
                    "metadata": conceptual_result.get("metadata", {}),
                    "task_id": tracker.task_id  # Incluir task_id en respuesta
                }

        except Exception as e:
            logger.error(f"❌ Error en procesamiento {processing_mode}: {e}", exc_info=True)
            tracker.set_error(str(e))
            # Fallback al procesamiento básico
            return await self._fallback_processing(documents, dataset_name)

    async def _fallback_processing(self, documents: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
        """Procesamiento básico de fallback."""
        logger.info(f"📝 Procesando {len(documents)} documentos en modo fallback")

        entities = []
        relationships = []

        for i, doc in enumerate(documents):
            content = doc.get('content', '')

            # Crear entidad del documento
            doc_entity = {
                "type": "Document",
                "properties": {
                    "name": f"Documento_{i+1}",
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "source": "fallback_processing",
                    "created_at": datetime.now().isoformat()
                }
            }
            entities.append(doc_entity)

        return {
            "entities": entities,
            "relationships": relationships,
            "dataset_name": dataset_name,
            "status": "processed_fallback",
            "method": "fallback",
            "processed_at": datetime.now().isoformat()
        }

    async def _fetch_documents_from_db(self, db_session: AsyncSession, account_id: str, topic: Optional[str] = None, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Busca documentos en la base de datos PostgreSQL."""
        import sqlalchemy
        from urllib.parse import unquote

        try:
            # Decodificar el topic para convertir de formato URL-encoded a texto legible
            decoded_topic = unquote(topic) if topic else None
            logger.info(f"🔍 Buscando documentos con topic: '{topic}' (decodificado: '{decoded_topic}')")
            
            # Construir filtros dinámicamente
            filters = ["account_id = :account_id", "cmetadata->>'type' = 'document_chunk'"]

            if workspace_id:
                filters.append("workspace_id::text = :workspace_id")
            # Si workspace_id es None, no filtramos por workspace_id para permitir
            # encontrar documentos tanto globales como de cualquier workspace si es necesario,
            # pero list_user_documents suele filtrar por IS NULL si se quiere el contexto personal.
            # Aquí, para consistencia con memory_manager, si no hay workspace_id buscamos IS NULL.
            else:
                filters.append("workspace_id IS NULL")

            if decoded_topic:
                filters.append("topic = :topic")

            where_clause = " AND ".join(filters)

            query = sqlalchemy.text(f"""
                SELECT DISTINCT ON (cmetadata->>'document_id')
                       cmetadata->>'file_name' AS file_name,
                       topic AS topic,
                       cmetadata->>'title' AS title,
                       cmetadata->>'author' AS author,
                       cmetadata->>'document_id' AS document_id,
                       workspace_id::text AS workspace_id,
                       account_id AS account_id,
                       cmetadata AS metadata
                FROM langchain_pg_embedding
                WHERE {where_clause}
                ORDER BY cmetadata->>'document_id', id
                LIMIT 50;
            """)

            params = {'account_id': account_id}
            if workspace_id:
                params['workspace_id'] = workspace_id
            if decoded_topic:
                params['topic'] = decoded_topic

            result = await db_session.execute(query, params)
            documents = []
            for row in result.fetchall():
                doc_dict = dict(row._mapping)
                documents.append(doc_dict)

            logger.info(f"✅ Encontrados {len(documents)} documentos en base de datos")
            return documents

        except Exception as e:
            logger.error(f"❌ Error buscando documentos en base de datos: {e}")
            return []

    async def _reconstruct_document_content(self, documents: List[Dict[str, Any]], account_id: Optional[str] = None, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Reconstruye el contenido completo de documentos desde chunks vectorizados."""
        processed_documents = []

        # Si no se proporciona account_id, intentar extraerlo del primer documento
        if not account_id and documents:
            # Intentar obtenerlo del campo directo primero
            account_id = documents[0].get("account_id")
            # Si no está ahí, intentar en metadata
            if not account_id:
                account_id = documents[0].get("metadata", {}).get("account_id")

        if not account_id:
            # Levantar un error si no se encuentra el account_id para detener el proceso.
            raise ValueError("No se encontró account_id ni en los parámetros ni en los documentos. El procesamiento no puede continuar.")

        logger.info(f"🔑 Usando account_id: {account_id} para reconstrucción de contenido")

        for i, doc in enumerate(documents):
            # Obtener el nombre del archivo (priorizar file_name sobre title)
            file_name = doc.get("file_name") or doc.get("metadata", {}).get("file_name") or doc.get("title")
            workspace_id = doc.get("workspace_id") or doc.get("metadata", {}).get("workspace_id")

            if not file_name:
                logger.warning(f"⚠️ Documento {i} sin nombre de archivo: {doc}")
                continue

            logger.info(f"🔄 Reconstruyendo contenido para: {file_name}")

            # Verificar si el documento ya tiene contenido
            existing_content = doc.get("content")
            if existing_content and isinstance(existing_content, str) and len(existing_content.strip()) > 0:
                logger.info(f"✅ Usando contenido existente para: {file_name}")
                processed_documents.append({
                    "title": file_name,
                    "content": existing_content.strip(),
                    "metadata": doc.get("metadata", {})
                })
                continue

            # Reconstruir contenido completo desde chunks vectorizados
            try:
                full_content = await get_full_document_content(
                    account_id=account_id,
                    file_name=file_name,
                    topic=topic,  # Filtro por topic
                    workspace_id=workspace_id
                )

                if full_content and len(full_content.strip()) > 0:
                    processed_documents.append({
                        "title": file_name,
                        "content": full_content.strip(),
                        "metadata": doc.get("metadata", {})
                    })
                    logger.info(f"✅ Contenido reconstruido para {file_name}: {len(full_content)} caracteres")
                else:
                    logger.warning(f"⚠️ No se pudo reconstruir contenido para: {file_name}")

            except Exception as content_error:
                logger.error(f"❌ Error reconstruyendo contenido para {file_name}: {content_error}")

        return processed_documents

    async def search_knowledge_graph(
        self,
        query: str,
        dataset_name: str = "default",
        relationship_types: Optional[List[str]] = None,
        source_concept: Optional[str] = None,
        target_concept: Optional[str] = None,
        max_hops: Optional[int] = None,
        pattern_description: Optional[str] = None,
        return_type: Optional[Literal["nodes", "relationships", "paths", "summary", "cypher_query_only", "stats"]] = "summary",
        account_id: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Realiza búsquedas en el grafo de conocimiento."""
        await self._create_fulltext_indexes()
        
        try:
            # 1. Lógica para Búsquedas Relacionales y de Caminos
            if source_concept or target_concept or relationship_types or max_hops:
                logger.info(f"🧠 Ejecutando búsqueda relacional/de caminos con: source={source_concept}, target={target_concept}, rels={relationship_types}, hops={max_hops}")
                
                params = {"dataset_name": dataset_name}
                where_clauses = ["all(n IN nodes(path) WHERE n.dataset_name = $dataset_name)"]

                source_match = f"(s {{name: $source_concept, dataset_name: $dataset_name}})" if source_concept else "(s)"
                target_match = f"(t {{name: $target_concept, dataset_name: $dataset_name}})" if target_concept else "(t)"
                
                if source_concept:
                    params["source_concept"] = source_concept
                if target_concept:
                    params["target_concept"] = target_concept

                if account_id:
                    where_clauses.append("all(n IN nodes(path) WHERE n.account_id = $account_id OR n.account_id IS NULL)")
                    params["account_id"] = account_id
                
                if workspace_id:
                    where_clauses.append("all(n IN nodes(path) WHERE n.workspace_id = $workspace_id OR n.workspace_id IS NULL)")
                    params["workspace_id"] = workspace_id

                rel_spec = ""
                if relationship_types:
                    rel_spec = ":" + "|".join(relationship_types)
                
                hop_spec = f"*{1 if max_hops == 1 else ''}..{max_hops}" if max_hops else "*"

                cypher_query = f"MATCH path = {source_match}-[{rel_spec}{hop_spec}]-{target_match} "
                cypher_query += "WHERE " + " AND ".join(where_clauses) + " "
                
                if return_type == "cypher_query_only":
                    return {
                        "query": f"Advanced search: source={source_concept}, target={target_concept}, rels={relationship_types}, hops={max_hops}",
                        "dataset_name": dataset_name,
                        "cypher_query": cypher_query,
                        "parameters": params,
                        "status": "cypher_query_generated",
                        "method": "advanced_cypher",
                        "searched_at": datetime.now().isoformat()
                    }

                raw_results = await self.graph_db.execute_query(cypher_query, parameters=params)
                # Asegurar que return_type sea str
                actual_return_type = return_type if return_type is not None else "summary"
                formatted_results = self._format_advanced_search_results(raw_results, actual_return_type, dataset_name)

                return {
                    "query": f"Advanced search: source={source_concept}, target={target_concept}, rels={relationship_types}, hops={max_hops}",
                    "dataset_name": dataset_name,
                    "results": formatted_results,
                    "status": "search_completed_advanced_graph",
                    "method": "advanced_cypher",
                    "searched_at": datetime.now().isoformat()
                }

            # 2. Lógica para Búsqueda de Patrones Específicos
            if pattern_description:
                logger.info(f"🔍 Ejecutando búsqueda de patrón específica con: {pattern_description}")
                
                search_text_for_pattern = f"{query} {pattern_description}" if query else pattern_description
                
                params = {"search_text_for_pattern": search_text_for_pattern, "dataset_name": dataset_name}
                where_n = ["n.dataset_name = $dataset_name"]
                where_rel = ["n.dataset_name = $dataset_name", "m.dataset_name = $dataset_name"]

                if account_id:
                    where_n.append("(n.account_id = $account_id OR n.account_id IS NULL)")
                    where_rel.append("(n.account_id = $account_id OR n.account_id IS NULL)")
                    where_rel.append("(m.account_id = $account_id OR m.account_id IS NULL)")
                    params["account_id"] = account_id
                
                if workspace_id:
                    where_n.append("(n.workspace_id = $workspace_id OR n.workspace_id IS NULL)")
                    where_rel.append("(n.workspace_id = $workspace_id OR n.workspace_id IS NULL)")
                    where_rel.append("(m.workspace_id = $workspace_id OR m.workspace_id IS NULL)")
                    params["workspace_id"] = workspace_id

                cypher_query = f"""
                CALL db.index.fulltext.queryNodes('node_fulltext_index', $search_text_for_pattern) YIELD node AS n, score AS nodeScore
                WHERE {" AND ".join(where_n)}
                WITH n, nodeScore
                OPTIONAL MATCH (n)-[r]-(m)
                RETURN DISTINCT n, r, m, nodeScore AS score
                UNION ALL
                CALL db.index.fulltext.queryRelationships('relationship_fulltext_index', $search_text_for_pattern) YIELD relationship AS r, score AS relScore
                MATCH (n)-[r]-(m)
                WHERE {" AND ".join(where_rel)}
                RETURN DISTINCT n, r, m, relScore AS score
                ORDER BY score DESC LIMIT 10
                """
                
                if return_type == "cypher_query_only":
                    return {
                        "query": query,
                        "dataset_name": dataset_name,
                        "cypher_query": cypher_query,
                        "parameters": params,
                        "status": "cypher_query_generated",
                        "method": "pattern_search_fulltext",
                        "searched_at": datetime.now().isoformat()
                    }

                raw_results = await self.graph_db.execute_query(cypher_query, parameters=params)
                # Asegurar que return_type sea str
                actual_return_type = return_type if return_type is not None else "summary"
                formatted_results = self._format_advanced_search_results(raw_results, actual_return_type, dataset_name)

                if formatted_results:
                    return {
                        "query": query,
                        "dataset_name": dataset_name,
                        "results": formatted_results,
                        "status": "search_completed_pattern",
                        "method": "pattern_search_fulltext",
                        "searched_at": datetime.now().isoformat(),
                        "summary": f"Se encontraron elementos relacionados con el patrón '{pattern_description}'."
                    }
                else:
                    return {
                        "query": query,
                        "dataset_name": dataset_name,
                        "results": [],
                        "status": "search_completed_no_patterns",
                        "method": "pattern_search_fulltext",
                        "searched_at": datetime.now().isoformat(),
                        "summary": "No se encontraron elementos que coincidan con el patrón descrito."
                    }

            # 3. Lógica para Búsqueda Full-Text (default)
            # Esta será la opción principal si no se cumplen las condiciones anteriores
            logger.info(f"📝 Ejecutando búsqueda full-text para: {query}")
            
            params = {"query": query, "dataset_name": dataset_name}
            where_n = ["n.dataset_name = $dataset_name"]
            where_m = ["(m.dataset_name = $dataset_name OR m.dataset_name IS NULL)"]
            where_rel = ["n.dataset_name = $dataset_name", "m.dataset_name = $dataset_name"]

            if account_id:
                where_n.append("(n.account_id = $account_id OR n.account_id IS NULL)")
                where_m.append("(m.account_id = $account_id OR m.account_id IS NULL)")
                where_rel.append("(n.account_id = $account_id OR n.account_id IS NULL)")
                where_rel.append("(m.account_id = $account_id OR m.account_id IS NULL)")
                params["account_id"] = account_id
            
            if workspace_id:
                where_n.append("(n.workspace_id = $workspace_id OR n.workspace_id IS NULL)")
                where_m.append("(m.workspace_id = $workspace_id OR m.workspace_id IS NULL)")
                where_rel.append("(n.workspace_id = $workspace_id OR n.workspace_id IS NULL)")
                where_rel.append("(m.workspace_id = $workspace_id OR m.workspace_id IS NULL)")
                params["workspace_id"] = workspace_id

            cypher_query = f"""
            CALL db.index.fulltext.queryNodes('node_fulltext_index', $query) YIELD node AS n, score AS nodeScore
            WHERE {" AND ".join(where_n)}
            WITH n, nodeScore
            OPTIONAL MATCH (n)-[r]-(m)
            WHERE {" AND ".join(where_m)}
            RETURN DISTINCT n, r, m, nodeScore AS score
            UNION ALL
            CALL db.index.fulltext.queryRelationships('relationship_fulltext_index', $query) YIELD relationship AS r, score AS relScore
            MATCH (n)-[r]-(m)
            WHERE {" AND ".join(where_rel)}
            RETURN DISTINCT n, r, m, relScore AS score
            ORDER BY score DESC LIMIT 20
            """

            if return_type == "cypher_query_only":
                return {
                    "query": query,
                    "dataset_name": dataset_name,
                    "cypher_query": cypher_query,
                    "parameters": params,
                    "status": "cypher_query_generated",
                    "method": "fulltext_cypher",
                    "searched_at": datetime.now().isoformat()
                }

            search_results_raw = await self.graph_db.execute_query(cypher_query, parameters=params)
            # Asegurar que return_type sea str
            actual_return_type = return_type if return_type is not None else "summary"
            formatted_results = self._format_advanced_search_results(search_results_raw, actual_return_type, dataset_name)

            if formatted_results:
                return {
                    "query": query, "dataset_name": dataset_name, "results": formatted_results,
                    "status": "search_completed", "method": "fulltext_cypher",
                    "searched_at": datetime.now().isoformat()
                }
            else:
                # Si la búsqueda full-text no da resultados, intentar con estadísticas generales
                logger.info(f"📊 Búsqueda full-text sin resultados, intentando insights generales/estadísticas para: {query}")
                node_stats_query = f"""
                MATCH (n:CONCEPTUAL_QUOTE {{dataset_name: $dataset_name}})
                RETURN DISTINCT n.category AS category, COUNT(n) AS count
                ORDER BY count DESC LIMIT 5
                """
                rels_stats_query = f"""
                MATCH ()-[r]->() WHERE r.dataset_name = $dataset_name
                RETURN DISTINCT type(r) AS rel_type, COUNT(r) AS count
                ORDER BY count DESC LIMIT 5
                """
                
                node_stats_raw = await self.graph_db.execute_query(node_stats_query, parameters={"dataset_name": dataset_name})
                rels_stats_raw = await self.graph_db.execute_query(rels_stats_query, parameters={"dataset_name": dataset_name})

                node_stats = [self._neo4j_record_to_dict(record) for record in node_stats_raw]
                rels_stats = [self._neo4j_record_to_dict(record) for record in rels_stats_raw]

                summary_items = []
                if node_stats:
                    summary_items.append({"type": "node_stats", "content": "Categorías de nodos más comunes:", "data": node_stats})
                if rels_stats:
                    summary_items.append({"type": "rel_stats", "content": "Tipos de relaciones más comunes:", "data": rels_stats})
                
                if summary_items:
                    return {
                        "query": query, "dataset_name": dataset_name, "results": summary_items,
                        "status": "search_completed_general_insights", "method": "general_insights_fallback",
                        "searched_at": datetime.now().isoformat(),
                        "summary": "No se encontraron resultados directos, pero se encontraron estadísticas generales del grafo."
                    }
                else:
                    return {
                        "query": query, "dataset_name": dataset_name, "results": [],
                        "status": "search_completed_no_results", "method": "no_results",
                        "searched_at": datetime.now().isoformat(),
                        "summary": "No se encontraron resultados relevantes en el grafo de conocimiento."
                    }


        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}", exc_info=True)
            return {
                "query": query, "dataset_name": dataset_name, "results": [],
                "status": "search_error", "error": str(e),
                "searched_at": datetime.now().isoformat()
            }

    async def detect_trends(
        self,
        dataset_name: str,
        time_window: str = "last_6_months",
        trend_threshold: float = 0.7,
        granularity: str = "weekly"
    ) -> Dict[str, Any]:
        """Detecta tendencias emergentes en el dataset usando análisis temporal."""
        try:
            logger.info(f"📈 Detectando tendencias en dataset '{dataset_name}'")

            from knowledge_graph.trend_analyzer import TrendAnalyzer

            trend_analyzer = TrendAnalyzer(
                graph_db=self.graph_db,
                sentence_transformer=None
            )

            trends_result = await trend_analyzer.detect_trends(
                dataset_name=dataset_name,
                time_window=time_window,
                trend_threshold=trend_threshold,
                granularity=granularity
            )

            logger.info(f"✅ Análisis de tendencias completado: {trends_result['trend_metrics']['total_trends']} tendencias detectadas")

            return trends_result

        except Exception as e:
            logger.error(f"❌ Error detectando tendencias: {e}")
            raise

    async def analyze_temporal_patterns(
        self,
        dataset_name: str,
        analysis_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Realiza análisis temporal completo del dataset."""
        if analysis_types is None:
            analysis_types = ["trends", "evolution", "patterns"]

        try:
            logger.info(f"🕒 Iniciando análisis temporal completo para '{dataset_name}'")

            results = {
                "dataset_name": dataset_name,
                "analysis_timestamp": datetime.now().isoformat(),
                "analysis_types": analysis_types
            }

            # Análisis de tendencias
            if "trends" in analysis_types:
                trends = await self.detect_trends(
                    dataset_name=dataset_name,
                    time_window="last_6_months",
                    trend_threshold=0.6,
                    granularity="weekly"
                )
                results["trends_analysis"] = trends

            # Análisis de evolución
            if "evolution" in analysis_types:
                evolution_results = {}
                time_windows = ["last_1_month", "last_3_months", "last_6_months"]
                for window in time_windows:
                    evolution = await self.detect_trends(
                        dataset_name=dataset_name,
                        time_window=window,
                        trend_threshold=0.5,
                        granularity="weekly"
                    )
                    evolution_results[window] = evolution["trend_metrics"]
                results["evolution_analysis"] = evolution_results

            # Análisis de patrones
            if "patterns" in analysis_types:
                pattern_results = {}
                granularities = ["daily", "weekly", "monthly"]
                for granularity in granularities:
                    patterns = await self.detect_trends(
                        dataset_name=dataset_name,
                        time_window="last_3_months",
                        trend_threshold=0.7,
                        granularity=granularity
                    )
                    pattern_results[granularity] = {
                        "trends_count": patterns["trend_metrics"]["total_trends"],
                        "strongest_trend": patterns["summary"].get("strongest_trend")
                    }
                results["patterns_analysis"] = pattern_results

            results["consolidated_summary"] = await self._generate_temporal_summary(results)
            return results

        except Exception as e:
            logger.error(f"❌ Error en análisis temporal: {e}")
            raise

    async def _generate_temporal_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Genera un resumen consolidado del análisis temporal."""
        summary = {
            "analysis_date": analysis_results["analysis_timestamp"],
            "dataset": analysis_results["dataset_name"]
        }

        if "trends_analysis" in analysis_results:
            trends = analysis_results["trends_analysis"]
            summary["trends_summary"] = {
                "total_trends": trends["trend_metrics"]["total_trends"],
                "strongest_trend_score": trends["trend_metrics"].get("max_trend_score", 0),
                "growth_trends": trends["trend_metrics"]["trends_by_direction"].get("creciente", 0),
                "decline_trends": trends["trend_metrics"]["trends_by_direction"].get("decreciente", 0)
            }

        if "evolution_analysis" in analysis_results:
            evolution = analysis_results["evolution_analysis"]
            summary["evolution_summary"] = {
                "time_windows_analyzed": len(evolution),
                "trend_consistency": self._calculate_trend_consistency(evolution)
            }

        summary["recommendations"] = self._generate_temporal_recommendations(analysis_results)
        return summary

    def _calculate_trend_consistency(self, evolution_data: Dict[str, Any]) -> float:
        """Calcula la consistencia de tendencias."""
        if not evolution_data:
            return 0.0
        trend_counts = [data.get("total_trends", 0) for data in evolution_data.values()]
        if not trend_counts or max(trend_counts) == 0:
            return 0.0
        mean_trends = np.mean(trend_counts)
        variance = np.var(trend_counts)
        consistency = 1.0 - (variance / (mean_trends + 1))
        return round(max(0.0, float(consistency)), 3)

    def _generate_temporal_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en el análisis temporal."""
        recommendations = []
        if "trends_analysis" in analysis_results:
            trends = analysis_results["trends_analysis"]
            total_trends = trends["trend_metrics"]["total_trends"]
            if total_trends == 0:
                recommendations.append("No se detectaron tendencias significativas.")
            elif total_trends > 20:
                recommendations.append("Se detectaron muchas tendencias. Considerar filtrar por relevancia.")
            else:
                recommendations.append(f"Se detectaron {total_trends} tendencias.")
        return recommendations

    async def _convert_conceptual_to_neo4j_format(self, conceptual_result: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte el resultado conceptual al formato compatible con Neo4j."""
        dataset_name = conceptual_result.get("metadata", {}).get("dataset_name", "conceptual_dataset")

        entities = []
        relationships = []

        conceptual_nodes = conceptual_result.get("conceptual_nodes", [])
        for quote in conceptual_nodes:
            entity = {
                "type": "CONCEPTUAL_QUOTE",
                "dataset_name": dataset_name,
                "properties": {
                    "name": quote["text"],
                    "cognee_id": quote["id"],
                    "description": quote["text"][:500] + "..." if len(quote["text"]) > 500 else quote["text"],
                    "full_text": quote["text"],
                    "concept": quote.get("concept", "Unknown"),
                    "importance": quote["importance"],
                    "category": quote["category"],
                    "confidence": quote["confidence"],
                    "source_document": quote["source_document"],
                    "extraction_method": quote["extraction_method"],
                    "created_at": datetime.now().isoformat()
                }
            }
            entities.append(entity)
            
            # Crear relación con el documento de origen si existe el ID
            if quote.get("source_document_id"):
                rel = {
                    "source_id": quote["source_document_id"],
                    "target_id": quote["id"],
                    "source_type": "DOCUMENT",
                    "target_type": "CONCEPTUAL_QUOTE",
                    "relationship_type": "MENTIONS",
                    "dataset_name": dataset_name,
                    "confidence": 1.0,
                    "description": f"Documento menciona la cita conceptual",
                    "created_at": datetime.now().isoformat(),
                    "extraction_method": quote.get("extraction_method", "conceptual_link")
                }
                relationships.append(rel)


        thematic_relationships = conceptual_result.get("thematic_relationships", [])

        for rel in thematic_relationships:
            relationship = {
                "source_entity": rel.get("source_id", ""),
                "target_entity": rel.get("target_id", ""),
                "source_type": "CONCEPTUAL_QUOTE",
                "target_type": "CONCEPTUAL_QUOTE",
                "type": rel["type"],
                "dataset_name": dataset_name,
                "confidence": rel["confidence"],
                "cognee_id": rel["id"],
                "properties": {
                    "description": rel["description"],
                    "similarity_score": rel.get("similarity_score", 0),
                    "extraction_method": rel["extraction_method"],
                    "created_at": datetime.now().isoformat()
                }
            }
            relationships.append(relationship)

        profiles = []
        profile_relationships = []
        idea_profiles = conceptual_result.get("idea_profiles", [])
        for profile in idea_profiles:
            profile_entity = {
                "type": "IDEA_PROFILE",
                "dataset_name": dataset_name,
                "properties": {
                    "name": profile["central_concept"],
                    "cognee_id": profile["id"],
                    "description": profile["description"],
                    "quotes_count": profile["quotes_count"],
                    "categories": ", ".join(profile["categories"]),
                    "importance_score": profile["importance_score"],
                    "coherence_score": profile["coherence_score"],
                    "documents_span": ", ".join(profile["documents_span"]),
                    "confidence": profile["coherence_score"],
                    "extraction_method": "idea_profile_clustering",
                    "created_at": datetime.now().isoformat()
                }
            }
            profiles.append(profile_entity)

            for quote_id in profile["quote_ids"]:
                profile_rel = {
                    "source_entity": profile["id"],
                    "target_entity": quote_id,
                    "source_type": "IDEA_PROFILE",
                    "target_type": "CONCEPTUAL_QUOTE",
                    "type": "CONTAINS_IDEA",
                    "dataset_name": dataset_name,
                    "confidence": 0.9,
                    "cognee_id": f"profile_contains_{profile['id']}_{quote_id}",
                    "properties": {
                        "description": f"El perfil '{profile['central_concept']}' contiene esta idea",
                        "extraction_method": "profile_membership",
                        "created_at": datetime.now().isoformat()
                    }
                }
                profile_relationships.append(profile_rel)

        return {
            "entities": entities,
            "relationships": relationships,
            "profiles": profiles,
            "profile_relationships": profile_relationships
        }

    def _format_advanced_search_results(self, raw_results: List[Dict[str, Any]], return_type: str, dataset_name: str = "default") -> List[Dict[str, Any]]:
        """Formatea los resultados crudos de Cypher."""
        formatted_output = []

        if return_type == "cypher_query_only":
            return []

        if not raw_results:
            return []

        all_nodes = {}
        all_relationships = {}

        for record in raw_results:
            if "path" in record and record["path"] is not None:
                path_object = record["path"]
                for node in path_object.nodes:
                    all_nodes[str(node.element_id)] = self._node_to_dict(node)
                for rel in path_object.relationships:
                    all_relationships[rel.element_id] = self._relationship_to_dict(rel)
            elif "n" in record and record["n"] is not None:
                node = record["n"]
                # Asegurarse de que node_dict siempre contenga element_id, independientemente de si 'node' es un objeto o un dict.
                node_dict = self._node_to_dict(node)
                all_nodes[node_dict["element_id"]] = node_dict
            elif "r" in record and record["r"] is not None:
                rel = record["r"]
                all_relationships[rel.element_id] = self._relationship_to_dict(rel)
                if hasattr(rel, 'start_node') and rel.start_node:
                    all_nodes[rel.start_node.element_id] = self._node_to_dict(rel.start_node)
                if hasattr(rel, 'end_node') and rel.end_node:
                    all_nodes[rel.end_node.element_id] = self._node_to_dict(rel.end_node)
            formatted_output.append(self._neo4j_record_to_dict(record))

        if return_type == "nodes":
            return list(all_nodes.values())
        elif return_type == "relationships":
            return list(all_relationships.values())
        elif return_type == "paths":
            for record in raw_results:
                if "path" in record and record["path"] is not None:
                    formatted_output.append(self._format_path(record["path"]))
            return formatted_output
        elif return_type == "summary" or return_type == "stats":
            if formatted_output and not (all_nodes or all_relationships): 
                return formatted_output
            
            # Generar un resumen más descriptivo incluyendo propiedades si hay pocos resultados
            if all_nodes or all_relationships:
                summary_text = f"Resultados encontrados en el grafo para el dataset '{dataset_name}':\n"
                
                if all_nodes:
                    summary_text += f"- Nodos ({len(all_nodes)}):\n"
                    # Si hay pocos nodos, listar sus propiedades principales
                    if len(all_nodes) <= 10:
                        for node in all_nodes.values():
                            name = node.get('name') or node.get('concept') or 'Sin nombre'
                            label = node.get('labels', ['Entidad'])[0]
                            # Filtrar propiedades para el resumen
                            excluded = {"name", "concept", "labels", "element_id", "id", "dataset_name", "account_id", "workspace_id"}
                            props = {k: v for k, v in node.items() if k not in excluded and v}
                            props_str = f" ({', '.join([f'{k}: {v}' for k, v in props.items()])})" if props else ""
                            summary_text += f"  * [{label}] {name}{props_str}\n"
                    else:
                        # Agrupar por etiqueta si hay muchos
                        node_label_counts = {}
                        for node in all_nodes.values():
                            label = node.get('labels', ['Unknown'])[0]
                            node_label_counts[label] = node_label_counts.get(label, 0) + 1
                        
                        sorted_labels = sorted(node_label_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                        summary_text += "  * Tipos principales: " + ", ".join([f"{count} {label}" for label, count in sorted_labels]) + "\n"

                if all_relationships:
                    summary_text += f"- Relaciones ({len(all_relationships)}):\n"
                    if len(all_relationships) <= 10:
                        for rel in all_relationships.values():
                            rel_type = rel.get('type', 'RELATED')
                            source = all_nodes.get(rel.get('start_node_element_id'), {}).get('name', 'Nodo')
                            target = all_nodes.get(rel.get('end_node_element_id'), {}).get('name', 'Nodo')
                            desc = rel.get('description', '')
                            desc_str = f": {desc}" if desc else ""
                            summary_text += f"  * {source} -[:{rel_type}]-> {target}{desc_str}\n"
                    else:
                        rel_type_counts = {}
                        for rel in all_relationships.values():
                            rel_type = rel.get('type', 'UNKNOWN')
                            rel_type_counts[rel_type] = rel_type_counts.get(rel_type, 0) + 1
                        
                        sorted_rels = sorted(rel_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                        summary_text += "  * Tipos principales: " + ", ".join([f"{count} {rel_type}" for rel_type, count in sorted_rels]) + "\n"
                
                return [{
                    "type": "summary_text_insight",
                    "content": summary_text.strip(),
                    "node_count": len(all_nodes),
                    "relationship_count": len(all_relationships),
                    "detailed_results": list(all_nodes.values())[:20] # Incluir algunos datos crudos por si el LLM los necesita
                }]
            else:
                return [{
                    "type": "no_results_summary",
                    "content": "No se encontraron resultados relevantes en el grafo de conocimiento para la consulta.",
                    "node_count": 0,
                    "relationship_count": 0
                }]
        
        return formatted_output if formatted_output else []

    def _node_to_dict(self, node: Any) -> Dict[str, Any]:
        """Convierte un objeto Node de Neo4j o un diccionario a un diccionario serializable."""
        if hasattr(node, 'labels') and hasattr(node, 'element_id'): # Es un objeto Node de Neo4j
            properties = dict(node)
            properties["labels"] = list(node.labels)
            properties["element_id"] = node.element_id

            # Asegurar propiedades clave para el LLM sin sobrescribir si ya existen con valores útiles
            if "name" not in properties:
                properties["name"] = properties.get("concept", "Unnamed Node")
            if "description" not in properties:
                properties["description"] = properties.get("full_text", "")
            if "category" not in properties:
                properties["category"] = ""

        elif isinstance(node, dict): # Es un diccionario
            properties = node.copy()
            if "labels" not in properties:
                properties["labels"] = ["Unknown"]
            if "element_id" not in properties:
                properties["element_id"] = str(properties.get("id", "unknown_id"))

            # Asegurar que 'id' exista
            if "id" not in properties:
                properties["id"] = properties["element_id"]

        else:
            # Manejar tipos inesperados
            error_msg = f"Tipo de nodo inesperado: {type(node)}."
            logger.error(error_msg + f" Valor: {node}")
            properties = {
                "element_id": f"ERROR_NODE_{str(node)}",
                "labels": ["Error"],
                "name": error_msg,
                "original_value": str(node)
            }

        return {k: self._neo4j_value_to_python(v) for k, v in properties.items()}

    def _relationship_to_dict(self, rel: Any) -> Dict[str, Any]:
        """Convierte un objeto Relationship de Neo4j o un diccionario a un diccionario serializable."""
        if hasattr(rel, 'type') and hasattr(rel, 'element_id'): # Es un objeto Relationship de Neo4j
            properties = dict(rel)
            properties["type"] = rel.type
            properties["element_id"] = rel.element_id
            properties["start_node_element_id"] = rel.start_node.element_id
            properties["end_node_element_id"] = rel.end_node.element_id
        elif isinstance(rel, dict): # Es un diccionario
            properties = rel.copy()
            properties["type"] = rel.get("type", "UNKNOWN_RELATIONSHIP")
            properties["element_id"] = rel.get("element_id", str(rel.get("id", "unknown_id")))
            properties["start_node_element_id"] = rel.get("start_node_element_id", "unknown_start_node_id")
            properties["end_node_element_id"] = rel.get("end_node_element_id", "unknown_end_node_id")
        else:
            # Manejar tipos inesperados de forma más robusta
            error_msg = f"Tipo de relación inesperado en _relationship_to_dict: {type(rel)}."
            logger.error(error_msg + f" Valor: {rel}")
            properties = {
                "element_id": f"ERROR_REL_{str(rel)}", # Prefijo para identificar fácilmente
                "type": "ERROR_RELATIONSHIP",
                "original_value": str(rel)
            }

        return {k: self._neo4j_value_to_python(v) for k, v in properties.items()}

    def _neo4j_value_to_python(self, value: Any) -> Any:
        """Convierte tipos de datos específicos de Neo4j a tipos de Python serializables."""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, list):
            return [self._neo4j_value_to_python(item) for item in value]
        if isinstance(value, dict):
            return {k: self._neo4j_value_to_python(v) for k, v in value.items()}
        # Detectar objetos Node de Neo4j (duck typing)
        if hasattr(value, 'labels') and hasattr(value, 'element_id'):
            return self._node_to_dict(value)
        # Detectar objetos Relationship de Neo4j (duck typing)
        if hasattr(value, 'type') and hasattr(value, 'element_id') and hasattr(value, 'start_node'):
            return self._relationship_to_dict(value)
        return value

    def _neo4j_record_to_dict(self, record: Any) -> Dict[str, Any]:
        """Convierte un objeto Record de Neo4j a un diccionario serializable."""
        if isinstance(record, dict):
            return {key: self._neo4j_value_to_python(record[key]) for key in record.keys()}
        else:
            logger.warning(f"Tipo de record inesperado en _neo4j_record_to_dict: {type(record)}. Valor: {record}")
            return {"error": f"Tipo de record inesperado: {type(record)}", "original_value": str(record)}

    def _format_path(self, path_object: Any) -> Dict[str, Any]:
        """Convierte un objeto Path de Neo4j en un diccionario serializable."""
        nodes = [self._node_to_dict(node) for node in path_object.nodes]
        relationships = [self._relationship_to_dict(rel) for rel in path_object.relationships]
        
        return {
            "nodes": nodes,
            "relationships": relationships,
            "path_string": self._path_to_string(path_object)
        }

    def _path_to_string(self, path_object: Any) -> str:
        """Convierte un objeto Path de Neo4j en una cadena legible."""
        nodes_str = [f"({node.get('name', 'Unnamed')}:{':'.join(node.labels)})" for node in path_object.nodes]
        rels_str = [f"-[{rel.type}]->" for rel in path_object.relationships]

        path_str = nodes_str[0]
        for i, rel_str in enumerate(rels_str):
            path_str += rel_str + nodes_str[i+1]

        return path_str

    async def get_visualization_data(
        self,
        dataset_name: str,
        focus_query: Optional[str] = None,
        max_nodes: int = 50,
        max_hops: int = 1
    ) -> Dict[str, Any]:
        """Obtiene datos para visualización del grafo."""
        fast_llm = get_fast_llm()
        nodes_data = []
        edges_data = []
        summary = ""

        try:
            cypher_query = ""
            params = {"dataset_name": dataset_name}

            if focus_query:
                logger.info(f"⚡ Generando Cypher para visualización con focus_query: '{focus_query}' en dataset: {dataset_name}")
                cypher_generation_prompt = f"""
                Eres un experto en Cypher y en la estructura de grafos de conocimiento.
                Tu tarea es traducir la siguiente pregunta en lenguaje natural a una consulta Cypher optimizada para Neo4j.
                El objetivo es extraer un subgrafo relevante para visualización.
                El grafo contiene nodos de tipo 'CONCEPTUAL_QUOTE' y relaciones de varios tipos.
                Todos los nodos y relaciones tienen una propiedad 'dataset_name'.
                
                **Reglas estrictas:**
                1. Filtra siempre por dataset_name.
                2. Identifica nodos de interés basados en la query.
                3. Expande relaciones hasta max_hops.
                4. Limita resultados a max_nodes.
                5. Para nodos de tipo CONCEPTUAL_QUOTE, asegúrate de devolver también n.concept y n.category.
                6. Devuelve SOLO la consulta Cypher.

                Pregunta: "{focus_query}"
                Max Hops: {max_hops}
                Max Nodes: {max_nodes}
                """
                generated_cypher_query_result = fast_llm.invoke(cypher_generation_prompt).content
                generated_cypher_query = "".join(str(item) for item in generated_cypher_query_result).strip()
                
                cypher_match = re.search(r"```(?:cypher)?\s*(.*?)\s*```", generated_cypher_query, re.DOTALL)
                if cypher_match:
                    cypher_query = cypher_match.group(1).strip()
                else:
                    cypher_query = generated_cypher_query.replace("`", "")
                
                cypher_query = self._post_process_cypher_query(cypher_query, dataset_name)
            else:
                logger.info(f"🔍 Usando Cypher por defecto para visualización en dataset: {dataset_name}")
                cypher_query = f"""
                MATCH (n)
                WHERE n.dataset_name = $dataset_name
                OPTIONAL MATCH (n)-[r]-(m)
                WHERE m.dataset_name = $dataset_name
                RETURN DISTINCT n, r, m, n.concept AS concept, n.category AS category
                LIMIT {max_nodes}
                """
                params = {"dataset_name": dataset_name}
            
            raw_results = await self.graph_db.execute_query(cypher_query, parameters=params)

            unique_nodes = {}
            unique_edges = {}

            for record in raw_results:
                for value in record.values():
                    if hasattr(value, 'labels') and value.labels is not None:
                        node = value
                        node_id = node.element_id
                        if node_id not in unique_nodes:
                            properties = dict(node)
                            unique_nodes[node_id] = {
                                "id": node_id,
                                "label": properties.get('name', properties.get('concept', f"Node {node_id}")),
                                "properties": properties,
                                "type": list(node.labels)[0] if node.labels else 'Unknown'
                            }
                    elif hasattr(value, 'start_node') and value.start_node is not None:
                        rel = value
                        edge_id = rel.element_id
                        if edge_id not in unique_edges:
                            unique_edges[edge_id] = {
                                "id": edge_id,
                                "source": rel.start_node.element_id,
                                "target": rel.end_node.element_id,
                                "label": rel.type,
                                "properties": dict(rel),
                                "type": rel.type
                            }

            nodes_data = list(unique_nodes.values())
            edges_data = list(unique_edges.values())

            if focus_query or nodes_data:
                summary_prompt = f"""
                Resume brevemente la estructura del grafo visualizado ({len(nodes_data)} nodos, {len(edges_data)} relaciones).
                Foco: '{focus_query}'
                """
                summary_result = fast_llm.invoke(summary_prompt).content
                summary = "".join(str(item) for item in summary_result).strip()

            return {
                "nodes": nodes_data,
                "edges": edges_data,
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Error en get_visualization_data: {e}", exc_info=True)
            raise e

    def _post_process_cypher_query(self, cypher_query: str, dataset_name: str) -> str:
        """Post-procesamiento de la consulta Cypher."""
        pattern_where_node_m = r"(OPTIONAL MATCH\s+\((?P<node1>[a-zA-Z0-9_]+)\)-\[(?P<rel>[a-zA-Z0-9_]+)\]-\((?P<node2>[a-zA-Z0-9_]+)\))\s+WHERE\s+(?P<node_var>[a-zA-Z0-9_]+)\.dataset_name\s*=\s*\$dataset_name"
        def replace_func_node_m(match):
            node_var = match.group('node_var')
            if node_var == match.group('node2'):
                return f"OPTIONAL MATCH ({match.group('node1')})-[{match.group('rel')}]-({match.group('node2')}:CONCEPTUAL_QUOTE {{dataset_name: $dataset_name}})"
            return match.group(0)
        corrected_query = re.sub(pattern_where_node_m, replace_func_node_m, cypher_query)

        pattern_direct_node_filter = r"(OPTIONAL MATCH\s+\((?P<node1>[a-zA-Z0-9_]+)\)-\[(?P<rel>[a-zA-Z0-9_]+)\]-\((?P<node2>[a-zA-Z0-9_]+)\s*\{dataset_name:\s*\$dataset_name\}\))"
        def replace_func_direct_node_filter(match):
            node2_part = match.group(4)
            if ":CONCEPTUAL_QUOTE" not in node2_part:
                return f"OPTIONAL MATCH ({match.group('node1')})-[{match.group('rel')}]-({match.group('node2')}:CONCEPTUAL_QUOTE {{dataset_name: $dataset_name}})"
            return match.group(0)
        corrected_query = re.sub(pattern_direct_node_filter, replace_func_direct_node_filter, corrected_query)
        return corrected_query
