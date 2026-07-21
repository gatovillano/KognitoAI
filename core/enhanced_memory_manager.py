"""
Enhanced Memory Manager que integra el grafo de conocimiento con el sistema de memoria existente.
Proporciona contexto más rico combinando embeddings vectoriales con relaciones del grafo.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from core.memory_manager import get_relevant_memories, add_memory_to_vector_db

logger = logging.getLogger(__name__)

class EnhancedMemoryManager:
    """
    Manager de memoria mejorado que combina:
    1. Sistema de embeddings existente (pgvector)
    2. Grafo de conocimiento (Neo4j)
    3. Memoria episódica y semántica
    """
    
    def __init__(self, graph_db=None, embedding_manager=None):
        """
        Inicializa el manager de memoria mejorado.
        
        Args:
            graph_db: Instancia de GraphDB para Neo4j
            embedding_manager: Manager de embeddings existente
        """
        self.graph_db = graph_db
        self.embedding_manager = embedding_manager
        logger.info("✅ EnhancedMemoryManager inicializado")
    
    async def get_enhanced_context(
        self, 
        user_query: str,
        user_id: str,
        workspace_id: Optional[str] = None,
        max_results: int = 10,
        explicit_document_ids: Optional[List[str]] = None # Nuevo parámetro
    ) -> Dict[str, Any]:
        """
        Obtiene contexto enriquecido combinando embeddings y grafo de conocimiento.
        
        Args:
            user_query: Consulta del usuario
            user_id: ID del usuario
            workspace_id: ID del workspace (opcional)
            max_results: Máximo número de resultados
            explicit_document_ids: Lista de IDs de documentos para priorizar/filtrar (opcional)
            
        Returns:
            Dict con contexto enriquecido
        """
        try:
            logger.info(f"🔍 Obteniendo contexto enriquecido para: '{user_query[:150]}...'")
            
            # Por defecto, la búsqueda en el grafo está habilitada
            enable_graph_search = True
            # Si la consulta es muy larga, desactivar la búsqueda en el grafo para evitar latencia.
            # Esto es útil para respuestas de herramientas (ej. búsquedas web) que son extensas.
            if len(user_query.split()) > 100:
                logger.warning("⚠️ La consulta es muy larga (+100 palabras), se omitirá la búsqueda en el grafo de conocimiento para evitar latencia.")
                enable_graph_search = False

            # 1. Obtener contexto tradicional (embeddings)
            traditional_context = await self._get_traditional_context(
                user_query, user_id, workspace_id, max_results, explicit_document_ids # Pasar el nuevo parámetro
            )
            
            # 2. Obtener contexto del grafo de conocimiento (si está habilitado)
            graph_context = {"type": "graph", "results": [], "reason": "Disabled"}
            if enable_graph_search:
                # 1. Buscar en el grafo de memorias del agente (aislado por account_id y workspace_id)
                agent_memory_dataset = "Agent Memories"
                
                agent_graph_context = await self._get_graph_context(
                    user_query, agent_memory_dataset, user_id, workspace_id, max_results
                )
                
                # 2. Buscar en el grafo de documentos (asumiendo un dataset por defecto o workspace)
                document_dataset = f"workspace_documents_{workspace_id.replace('-', '_')}" if workspace_id else "default_documents"
                document_graph_context = await self._get_graph_context(
                    user_query, document_dataset, user_id, workspace_id, max_results
                )

                # Combinar ambos contextos de grafo
                graph_context = {
                    "type": "combined_knowledge_graph",
                    "agent_memories": agent_graph_context,
                    "document_insights": document_graph_context
                }
            
            # 3. Combinar y enriquecer contextos
            enhanced_context = await self._combine_contexts(
                traditional_context, graph_context, user_query
            )
            
            logger.info(f"✅ Contexto enriquecido generado con {len(enhanced_context.get('enhanced_insights', []))} insights.")
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto enriquecido: {e}")
            # Fallback al contexto tradicional
            return await self._get_traditional_context(user_query, user_id, workspace_id, max_results, explicit_document_ids)
    
    async def _get_traditional_context(
        self,
        user_query: str,
        user_id: str,
        workspace_id: Optional[str] = None,
        max_results: int = 10,
        explicit_document_ids: Optional[List[str]] = None # Nuevo parámetro
    ) -> Dict[str, Any]:
        """Obtiene contexto usando el sistema de embeddings tradicional."""
        
        traditional_context_output = await get_relevant_memories(
            account_id=user_id,
            query=user_query,
            k=max_results,
            workspace_id=workspace_id,

            explicit_document_ids=explicit_document_ids # Pasar el nuevo parámetro
        )

        return {
            "type": "traditional_embeddings",
            "results": traditional_context_output.sources,
            "query": user_query,
            "user_id": user_id,
            "workspace_id": workspace_id
        }
    
    async def _get_graph_context(
        self,
        user_query: str,
        dataset_name: str,
        user_id: str,
        workspace_id: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Obtiene contexto del grafo de conocimiento para un dataset específico, filtrando por cuenta y workspace."""
        
        if not self.graph_db:
            return {"type": "graph", "results": [], "dataset": dataset_name}
        
        try:
            # 1. Buscar entidades relacionadas con la consulta en el dataset específico
            entities = await self._find_relevant_entities(user_query, dataset_name, user_id, workspace_id)
            
            # 2. Obtener relaciones de esas entidades
            relationships = await self._get_entity_relationships(entities, user_id, workspace_id)
            
            # 3. Construir contexto del grafo
            graph_context = {
                "type": "knowledge_graph",
                "dataset": dataset_name,
                "entities": entities[:max_results],
                "relationships": relationships,
                "query": user_query
            }
            
            return graph_context
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto del grafo: {e}")
            return {"type": "graph", "results": []}
    
    async def _find_relevant_entities(self, user_query: str, dataset_name: str, user_id: str, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Encuentra entidades relevantes en el grafo para un dataset específico, filtrando por cuenta y workspace."""
        
        try:
            # Extraer términos clave de la consulta
            query_terms = [term for term in user_query.lower().split() if len(term) > 3][:15]
            if not query_terms:
                return []

            workspace_filter = ""
            params = {
                "query_terms": query_terms, 
                "dataset_name": dataset_name,
                "account_id": user_id
            }

            if workspace_id:
                workspace_filter = "AND (n.workspace_id = $workspace_id OR n.workspace_id IS NULL)"
                params["workspace_id"] = workspace_id
            else:
                workspace_filter = "AND n.workspace_id IS NULL"

            # Query para buscar entidades que pertenezcan al dataset_name
            query = f"""
            MATCH (n)
            WHERE n.dataset_name = $dataset_name
              AND (n.account_id = $account_id OR n.account_id IS NULL)
              {workspace_filter}
              AND ANY(term IN $query_terms WHERE toLower(n.name) CONTAINS term OR toLower(n.description) CONTAINS term)
            RETURN n.id as id, n.name as name, n.type as type,
                   n.description as description, n.confidence as confidence
            ORDER BY n.confidence DESC
            LIMIT 20
            """
            
            result = await self.graph_db.execute_query(query, params)
            
            # Eliminar duplicados si los hubiera, manteniendo el orden de la base de datos
            unique_entities = {}
            for entity in result:
                entity_id = entity.get("id")
                if entity_id not in unique_entities:
                    unique_entities[entity_id] = entity
            
            return list(unique_entities.values())
            
        except Exception as e:
            logger.error(f"❌ Error buscando entidades relevantes: {e}")
            return []
    
    async def _get_entity_relationships(self, entities: List[Dict[str, Any]], user_id: str, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene las relaciones de las entidades encontradas, filtrando por cuenta y workspace."""
        
        if not entities:
            return []
        
        try:
            entity_ids = [entity.get("id") for entity in entities if entity.get("id")]
            
            if not entity_ids:
                return []
            
            workspace_filter = ""
            params = {
                "entity_ids": entity_ids,
                "account_id": user_id
            }

            if workspace_id:
                workspace_filter = "AND (source.workspace_id = $workspace_id OR source.workspace_id IS NULL)"
                params["workspace_id"] = workspace_id
            else:
                workspace_filter = "AND source.workspace_id IS NULL"

            # Query para obtener relaciones
            query = f"""
            MATCH (source)-[r]->(target)
            WHERE (source.id IN $entity_ids OR target.id IN $entity_ids)
              AND (source.account_id = $account_id OR source.account_id IS NULL)
              {workspace_filter}
            RETURN source.id as source_id, source.name as source_name,
                   type(r) as relationship_type, r.description as description,
                   target.id as target_id, target.name as target_name,
                   r.confidence as confidence
            ORDER BY r.confidence DESC
            LIMIT 50
            """
            
            relationships = await self.graph_db.execute_query(query, params)
            return relationships
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo relaciones: {e}")
            return []
    
    async def _combine_contexts(
        self, 
        traditional_context: Dict[str, Any], 
        graph_context: Dict[str, Any],
        user_query: str
    ) -> Dict[str, Any]:
        """Combina contextos tradicionales y del grafo para crear contexto enriquecido."""
        
        # Crear contexto combinado
        enhanced_context = {
            "query": user_query,
            "timestamp": datetime.now().isoformat(),
            "sources": {
                "traditional_embeddings": traditional_context,
                "knowledge_graph": graph_context
            },
            "enhanced_insights": [],
            "reasoning_paths": []
        }
        
        # Generar insights combinados
        insights = await self._generate_insights(traditional_context, graph_context, user_query)
        enhanced_context["enhanced_insights"] = insights
        
        # Generar resolución de conflictos entre grafo y contexto tradicional
        conflicts = await self._detect_and_resolve_conflicts(traditional_context, graph_context, user_query)
        enhanced_context["conflicts_resolved"] = conflicts

        # Generar caminos de razonamiento
        reasoning_paths = await self._generate_reasoning_paths(graph_context, user_query)
        enhanced_context["reasoning_paths"] = reasoning_paths
        
        return enhanced_context

    async def _detect_and_resolve_conflicts(
        self,
        traditional_context: Dict[str, Any],
        graph_context: Dict[str, Any],
        user_query: str
    ) -> List[Dict[str, Any]]:
        """
        Detecta y resuelve conflictos de hechos entre el Grafo de Conocimiento (Neo4j)
        y los recuerdos de la memoria tradicional/vectorial, priorizando según trust_score y validez temporal.
        """
        resolved_conflicts = []
        graph_entities = {str(e.get("name", "")).lower(): e for e in graph_context.get("entities", []) if e.get("name")}
        
        memories = traditional_context.get("memories", []) if isinstance(traditional_context, dict) else []
        for mem in memories:
            mem_text = str(mem.get("content") or mem.get("event_text") or "").lower()
            for ent_name, ent_data in graph_entities.items():
                if ent_name in mem_text:
                    trust = ent_data.get("trust_score", ent_data.get("confidence", 0.5))
                    # Si el nodo del grafo tiene alto trust_score (>= 0.7), prevalece la versión del grafo
                    if trust >= 0.7:
                        resolved_conflicts.append({
                            "entity": ent_data.get("name"),
                            "prevailed_source": "knowledge_graph",
                            "trust_score": trust,
                            "description": f"Hecho de '{ent_data.get('name')}' en Grafo prevalece (trust: {trust}) sobre memoria tradicional.",
                            "status": "resolved"
                        })
        return resolved_conflicts

    
    async def _generate_insights(
        self, 
        traditional_context: Dict[str, Any], 
        graph_context: Dict[str, Any],
        user_query: str
    ) -> List[Dict[str, Any]]:
        """Genera insights combinando información de ambas fuentes."""
        
        insights = []
        
        # Insight 1: Entidades clave identificadas
        entities = graph_context.get("entities", [])
        if entities:
            key_entities = [e for e in entities if e.get("confidence", 0) > 0.8]
            if key_entities:
                insights.append({
                    "type": "key_entities",
                    "description": f"Entidades clave identificadas: {', '.join([e.get('name', '') for e in key_entities[:5]])}",
                    "entities": key_entities[:5],
                    "confidence": "high"
                })
        
        # Insight 2: Relaciones relevantes
        relationships = graph_context.get("relationships", [])
        if relationships:
            high_conf_rels = [r for r in relationships if r.get("confidence", 0) > 0.7]
            if high_conf_rels:
                insights.append({
                    "type": "key_relationships",
                    "description": f"Relaciones importantes encontradas: {len(high_conf_rels)} conexiones",
                    "relationships": high_conf_rels[:3],
                    "confidence": "high"
                })
        
        return insights
    
    async def _generate_reasoning_paths(
        self, 
        graph_context: Dict[str, Any],
        user_query: str
    ) -> List[Dict[str, Any]]:
        """Genera caminos de razonamiento basados en el grafo de conocimiento."""
        
        reasoning_paths = []
        
        entities = graph_context.get("entities", [])
        relationships = graph_context.get("relationships", [])
        
        if len(entities) >= 2 and relationships:
            # Crear camino de razonamiento simple
            path = {
                "type": "conceptual_connection",
                "description": f"Conexión conceptual encontrada en el grafo de conocimiento",
                "steps": [],
                "confidence": "medium"
            }
            
            # Agregar pasos del razonamiento
            for i, rel in enumerate(relationships[:3]):
                step = {
                    "step": i + 1,
                    "from": rel.get("source_name", ""),
                    "to": rel.get("target_name", ""),
                    "relationship": rel.get("relationship_type", ""),
                    "description": rel.get("description", "")
                }
                path["steps"].append(step)
            
            reasoning_paths.append(path)
        
        return reasoning_paths
    
    async def save_enhanced_memory(
        self, 
        user_message: str, 
        llm_response: str, 
        user_id: str,
        enhanced_context: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> bool:
        """
        Guarda una memoria enriquecida que incluye contexto del grafo.
        
        Args:
            user_message: Mensaje del usuario
            llm_response: Respuesta del LLM
            user_id: ID del usuario
            enhanced_context: Contexto enriquecido usado
            workspace_id: ID del workspace (opcional)
            
        Returns:
            True si se guardó correctamente
        """
        try:
            # Construir el contenido de la memoria
            content = f"User: {user_message}\nAI: {llm_response}"
            
            # Si hay contexto enriquecido, podríamos querer incluir un resumen o metadatos
            # Por ahora, guardamos la interacción principal
            
            await add_memory_to_vector_db(
                account_id=user_id,
                content=content,
                type="enhanced_episodic",
                workspace_id=workspace_id
            )
            
            logger.info(f"✅ Memoria enriquecida guardada para usuario {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando memoria enriquecida: {e}")
            return False

    async def add_memory(
        self,
        user_id: str,
        content: str,
        type: str = "general_memory",
        workspace_id: Optional[str] = None,
        topic: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Wrapper para añadir una memoria directamente usando el sistema subyacente.
        Permite que EnhancedMemoryManager sea el punto de entrada único.
        """
        try:
            await add_memory_to_vector_db(
                account_id=user_id,
                content=content,
                type=type,
                workspace_id=workspace_id,
                topic=topic,
                category=category
            )
            return True
        except Exception as e:
            logger.error(f"❌ Error añadiendo memoria a través de EnhancedMemoryManager: {e}")
            return False

    async def add_episodic_memory(
        self,
        event_text: str,
        user_id: str,
        workspace_id: Optional[str] = None,
        episode_type: str = "chat",
        extra_metadata: Optional[Dict] = None
    ) -> bool:
        """
        Almacena una memoria episódica en PostgreSQL con su vector de embedding.
        """
        try:
            from core.database import SessionLocal, EpisodicMemory
            from core.embedding_manager import KognitoInternalEmbeddingService
            import uuid

            embedding_service = KognitoInternalEmbeddingService()
            embedding = await embedding_service.aembed_query(event_text)

            acc_id = uuid.UUID(user_id) if isinstance(user_id, str) and len(user_id) == 36 else user_id
            ws_id = uuid.UUID(workspace_id) if isinstance(workspace_id, str) and len(workspace_id) == 36 else workspace_id

            async with SessionLocal() as session:
                episodic_record = EpisodicMemory(
                    account_id=acc_id,
                    workspace_id=ws_id,
                    event_text=event_text,
                    embedding=embedding,
                    episode_type=episode_type,
                    extra_metadata=extra_metadata
                )
                session.add(episodic_record)
                await session.commit()

            logger.info(f"✅ Memoria episódica de tipo '{episode_type}' guardada para usuario {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando memoria episódica: {e}")
            return False

    async def get_episodic_context(
        self,
        query: str,
        user_id: str,
        workspace_id: Optional[str] = None,
        limit: int = 5,
        recency_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Obtiene recuerdos episódicos aplicando una mezcla ponderada de similitud de embedding y recencia.
        """
        try:
            from core.database import SessionLocal, EpisodicMemory
            from core.embedding_manager import KognitoInternalEmbeddingService
            from sqlalchemy import select, and_
            import uuid

            embedding_service = KognitoInternalEmbeddingService()
            query_embedding = await embedding_service.aembed_query(query)

            acc_id = uuid.UUID(user_id) if isinstance(user_id, str) and len(user_id) == 36 else user_id
            ws_id = uuid.UUID(workspace_id) if isinstance(workspace_id, str) and len(workspace_id) == 36 else workspace_id

            async with SessionLocal() as session:
                conditions = [EpisodicMemory.account_id == acc_id]
                if ws_id:
                    conditions.append(EpisodicMemory.workspace_id == ws_id)

                stmt = (
                    select(EpisodicMemory)
                    .where(and_(*conditions))
                    .order_by(EpisodicMemory.occurred_at.desc())
                    .limit(50)
                )
                res = await session.execute(stmt)
                records = res.scalars().all()

            if not records:
                return []

            # Calcular score mixto = (1 - recency_weight) * similarity + recency_weight * recency_factor
            now = datetime.now()
            scored_records = []
            for rec in records:
                # Similitud coseno aproximada entre embeddings
                sim = 0.5
                if rec.embedding is not None and len(rec.embedding) == len(query_embedding):
                    dot = sum(a * b for a, b in zip(query_embedding, rec.embedding))
                    norm_a = sum(a * a for a in query_embedding) ** 0.5
                    norm_b = sum(b * b for b in rec.embedding) ** 0.5
                    if norm_a > 0 and norm_b > 0:
                        sim = dot / (norm_a * norm_b)

                # Factor de recencia (decaimiento por días)
                age_days = (now - rec.occurred_at.replace(tzinfo=None)).total_seconds() / 86400.0
                recency_factor = max(0.0, 1.0 - (age_days / 30.0))

                final_score = (1.0 - recency_weight) * sim + recency_weight * recency_factor

                scored_records.append({
                    "id": str(rec.id),
                    "event_text": rec.event_text,
                    "episode_type": rec.episode_type,
                    "occurred_at": rec.occurred_at.isoformat() if rec.occurred_at else None,
                    "score": round(final_score, 4)
                })

            scored_records.sort(key=lambda x: x["score"], reverse=True)
            return scored_records[:limit]

        except Exception as e:
            logger.error(f"❌ Error consultando memoria episódica: {e}")
            return []

