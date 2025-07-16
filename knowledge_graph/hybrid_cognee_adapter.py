# knowledge_graph/hybrid_cognee_adapter.py

import logging
from typing import List, Dict, Any
from knowledge_graph.graph_database import GraphDB

logger = logging.getLogger(__name__)

class HybridCogneeAdapter:
    """
    Adaptador para integrar los resultados de Cognee con la base de datos de grafos existente (GraphDB).
    Actúa como un puente, permitiendo que el sistema utilice las capacidades de Cognee
    mientras mantiene la consistencia con la estructura de datos del grafo actual.
    """

    def __init__(self, graph_db: GraphDB):
        """
        Inicializa el adaptador.

        Args:
            graph_db (GraphDB): Una instancia de la clase GraphDB para interactuar con Neo4j.
        """
        self.graph_db = graph_db
        logger.info("✅ HybridCogneeAdapter inicializado y conectado a GraphDB.")

    async def add_cognee_results_to_graph(self, entities: List[Dict[str, Any]], relationships: List[Dict[str, Any]]):
        """
        Toma las entidades y relaciones extraídas por Cognee y las añade a la base de datos de grafos.

        Args:
            entities: Una lista de entidades extraídas por Cognee.
            relationships: Una lista de relaciones extraídas por Cognee.
        """
        logger.info(f"Integrando {len(entities)} entidades y {len(relationships)} relaciones al grafo Neo4j...")

        # Primero, añadir o actualizar todas las entidades
        for entity in entities:
            try:
                node_type = entity.get("type", "Entity")

                # El pipeline híbrido pone los datos directamente en entity, no en properties
                properties = {
                    "id": entity.get("id", ""),
                    "name": entity.get("name", "Unknown"),
                    "type": entity.get("type", "Entity"),
                    "description": entity.get("description", ""),
                    "confidence": entity.get("confidence", 0.8),
                    "source_document": entity.get("source_document", ""),
                    "extraction_method": entity.get("extraction_method", "hybrid")
                }

                # Usar 'id' en lugar de 'cognee_id' para el pipeline híbrido
                await self.graph_db.add_node(node_type, properties)
                logger.debug(f"✅ Nodo creado: {properties['name']} ({node_type})")
            except Exception as e:
                logger.error(f"❌ Error añadiendo entidad {entity}: {e}", exc_info=True)

        # Segundo, crear las relaciones
        for rel in relationships:
            try:
                # El pipeline híbrido usa source_entity_id y target_entity_id
                source_id = rel.get("source_entity_id", "")
                target_id = rel.get("target_entity_id", "")
                rel_type = rel.get("type", "RELATED_TO")

                # Propiedades de la relación
                properties = {
                    "description": rel.get("description", ""),
                    "confidence": rel.get("confidence", 0.8),
                    "extraction_method": rel.get("extraction_method", "hybrid")
                }

                if source_id and target_id:
                    # Usar 'id' en lugar de 'cognee_id' para el pipeline híbrido
                    await self.graph_db.add_relationship_by_property("id", source_id, "id", target_id, rel_type, properties)
                    logger.debug(f"✅ Relación creada: {source_id} -> {target_id} ({rel_type})")
                else:
                    logger.warning(f"⚠️ Relación omitida: source_id='{source_id}', target_id='{target_id}'")
            except Exception as e:
                logger.error(f"❌ Error añadiendo relación {rel}: {e}", exc_info=True)
        
        logger.info("✅ Resultados de Cognee integrados en el grafo Neo4j.")