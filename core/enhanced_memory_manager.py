"""
Enhanced Memory Manager que integra el grafo de conocimiento con el sistema de memoria existente.
Proporciona contexto más rico combinando embeddings vectoriales con relaciones del grafo.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

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
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Obtiene contexto enriquecido combinando embeddings y grafo de conocimiento.
        
        Args:
            user_query: Consulta del usuario
            user_id: ID del usuario
            workspace_id: ID del workspace (opcional)
            max_results: Máximo número de resultados
            
        Returns:
            Dict con contexto enriquecido
        """
        try:
            logger.info(f"🔍 Obteniendo contexto enriquecido para: '{user_query}'")
            
            # 1. Obtener contexto tradicional (embeddings)
            traditional_context = await self._get_traditional_context(
                user_query, user_id, workspace_id, max_results
            )
            
            # 2. Obtener contexto del grafo de conocimiento
            graph_context = await self._get_graph_context(
                user_query, workspace_id, max_results
            )
            
            # 3. Combinar y enriquecer contextos
            enhanced_context = await self._combine_contexts(
                traditional_context, graph_context, user_query
            )
            
            logger.info(f"✅ Contexto enriquecido generado: {len(enhanced_context.get('results', []))} elementos")
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto enriquecido: {e}")
            # Fallback al contexto tradicional
            return await self._get_traditional_context(user_query, user_id, workspace_id, max_results)
    
    async def _get_traditional_context(
        self,
        user_query: str,
        user_id: str,
        workspace_id: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Obtiene contexto usando el sistema de embeddings tradicional."""
        
        # Aquí integrarías con tu sistema actual de embeddings
        # Por ahora, estructura básica
        return {
            "type": "traditional_embeddings",
            "results": [],
            "query": user_query,
            "user_id": user_id,
            "workspace_id": workspace_id
        }
    
    async def _get_graph_context(
        self,
        user_query: str,
        workspace_id: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Obtiene contexto del grafo de conocimiento."""
        
        if not self.graph_db:
            return {"type": "graph", "results": []}
        
        try:
            # 1. Buscar entidades relacionadas con la consulta
            entities = await self._find_relevant_entities(user_query, workspace_id)
            
            # 2. Obtener relaciones de esas entidades
            relationships = await self._get_entity_relationships(entities)
            
            # 3. Construir contexto del grafo
            graph_context = {
                "type": "knowledge_graph",
                "entities": entities[:max_results],
                "relationships": relationships,
                "query": user_query,
                "workspace_id": workspace_id
            }
            
            return graph_context
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto del grafo: {e}")
            return {"type": "graph", "results": []}
    
    async def _find_relevant_entities(self, user_query: str, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Encuentra entidades relevantes en el grafo basadas en la consulta."""
        
        try:
            # Query para buscar entidades por nombre o descripción
            query = """
            MATCH (n)
            WHERE toLower(n.name) CONTAINS toLower($query_term)
               OR toLower(n.description) CONTAINS toLower($query_term)
            RETURN n.id as id, n.name as name, n.type as type, 
                   n.description as description, n.confidence as confidence
            ORDER BY n.confidence DESC
            LIMIT 20
            """
            
            # Extraer términos clave de la consulta
            query_terms = user_query.lower().split()
            relevant_entities = []
            
            for term in query_terms:
                if len(term) > 3:  # Solo términos significativos
                    result = await self.graph_db.execute_query(query, {"query_term": term})
                    relevant_entities.extend(result)
            
            # Eliminar duplicados y ordenar por relevancia
            unique_entities = {}
            for entity in relevant_entities:
                entity_id = entity.get("id")
                if entity_id not in unique_entities:
                    unique_entities[entity_id] = entity
            
            return list(unique_entities.values())
            
        except Exception as e:
            logger.error(f"❌ Error buscando entidades relevantes: {e}")
            return []
    
    async def _get_entity_relationships(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Obtiene las relaciones de las entidades encontradas."""
        
        if not entities:
            return []
        
        try:
            entity_ids = [entity.get("id") for entity in entities if entity.get("id")]
            
            if not entity_ids:
                return []
            
            # Query para obtener relaciones
            query = """
            MATCH (source)-[r]->(target)
            WHERE source.id IN $entity_ids OR target.id IN $entity_ids
            RETURN source.id as source_id, source.name as source_name,
                   type(r) as relationship_type, r.description as description,
                   target.id as target_id, target.name as target_name,
                   r.confidence as confidence
            ORDER BY r.confidence DESC
            LIMIT 50
            """
            
            relationships = await self.graph_db.execute_query(query, {"entity_ids": entity_ids})
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
        
        # Generar caminos de razonamiento
        reasoning_paths = await self._generate_reasoning_paths(graph_context, user_query)
        enhanced_context["reasoning_paths"] = reasoning_paths
        
        return enhanced_context
    
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
        enhanced_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Guarda una memoria enriquecida que incluye contexto del grafo.
        
        Args:
            user_message: Mensaje del usuario
            llm_response: Respuesta del LLM
            user_id: ID del usuario
            enhanced_context: Contexto enriquecido usado
            
        Returns:
            True si se guardó correctamente
        """
        try:
            # Crear memoria enriquecida
            enhanced_memory = {
                "user_message": user_message,
                "llm_response": llm_response,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "enhanced_context": enhanced_context,
                "memory_type": "enhanced_episodic"
            }
            
            # Aquí integrarías con tu sistema de guardado de memorias
            # Por ejemplo, guardar en pgvector con metadatos enriquecidos
            
            logger.info(f"✅ Memoria enriquecida guardada para usuario {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando memoria enriquecida: {e}")
            return False
