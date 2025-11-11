# knowledge_graph/neo4j_adapter.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class Neo4jAdapter:
    """
    Adaptador para integrar resultados del pipeline híbrido con Neo4j.
    """
    
    def __init__(self, graph_db):
        """
        Inicializa el adaptador con la instancia de GraphDB.
        
        Args:
            graph_db: Instancia de GraphDB para conectar con Neo4j
        """
        self.graph_db = graph_db
        logger.info("✅ Neo4jAdapter inicializado")
    
    async def add_cognee_results_to_graph(self, entities: List[Dict], relationships: List[Dict], workspace_id: Optional[str] = None, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Agrega entidades y relaciones del pipeline híbrido a Neo4j.
        
        Args:
            entities: Lista de entidades extraídas
            relationships: Lista de relaciones extraídas
            workspace_id: ID del workspace actual
            account_id: ID de la cuenta del usuario
            
        Returns:
            Dict con estadísticas del proceso
        """
        try:
            logger.info(f"🔗 Iniciando integración con Neo4j: {len(entities)} entidades, {len(relationships)} relaciones")

            # DEBUG: Log de las primeras entidades para diagnóstico
            if entities:
                logger.info(f"🔍 DIAGNÓSTICO - Primera entidad recibida: {entities[0]}")
                logger.info(f"🔍 DIAGNÓSTICO - Claves disponibles: {list(entities[0].keys())}")
                logger.info(f"🔍 DIAGNÓSTICO - Tipo de datos: {type(entities[0])}")

            # Estadísticas
            stats = {
                "entities_added": 0,
                "relationships_added": 0,
                "entities_updated": 0,
                "relationships_updated": 0,
                "errors": 0
            }
            
            # Agregar entidades
            stats["entities_added"] = await self._add_entities_to_neo4j(entities, workspace_id, account_id)
            
            # Agregar relaciones
            stats["relationships_added"] = await self._add_relationships_to_neo4j(relationships, workspace_id, account_id)
            
            logger.info(f"✅ Integración completada: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error integrando con Neo4j: {e}")
            raise
    
    async def _clear_existing_graph(self):
        """Limpia el grafo existente en Neo4j."""
        try:
            logger.info("🧹 Limpiando grafo existente en Neo4j...")
            
            # Eliminar todas las relaciones primero
            delete_relationships_query = "MATCH ()-[r]-() DELETE r"
            await self.graph_db.execute_query(delete_relationships_query)
            
            # Luego eliminar todos los nodos
            delete_nodes_query = "MATCH (n) DELETE n"
            await self.graph_db.execute_query(delete_nodes_query)
            
            logger.info("✅ Grafo limpiado correctamente")
            
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando grafo: {e}")
    
    async def _add_entities_to_neo4j(self, entities: List[Dict], workspace_id: Optional[str], account_id: Optional[str]) -> int:
        """
        Agrega entidades a Neo4j.
        
        Args:
            entities: Lista de entidades
            workspace_id: ID del workspace
            account_id: ID de la cuenta
            
        Returns:
            Número de entidades agregadas
        """
        try:
            logger.info(f"📝 Agregando {len(entities)} entidades a Neo4j...")
            
            entities_added = 0
            batch_size = 100  # Procesar en lotes para mejor performance
            
            for i in range(0, len(entities), batch_size):
                batch = entities[i:i + batch_size]

                # Preparar datos del lote
                batch_data = []
                for j, entity in enumerate(batch):
                    # DEBUG: Log detallado de las primeras 3 entidades
                    if j < 3:
                        logger.info(f"🔍 ENTIDAD {j+1} RECIBIDA:")
                        logger.info(f"   📋 Claves: {list(entity.keys())}")
                        logger.info(f"   📝 Contenido completo: {entity}")

                    # SOPORTE: Si los datos vienen anidados bajo 'properties', extraerlos
                    props = entity.get("properties", {}) if isinstance(entity, dict) else {}
                    entity_id = props.get("cognee_id") or entity.get("id") or self._generate_entity_id(entity)
                    name = props.get("name") or entity.get("name", "Unknown")
                    description = props.get("description") or entity.get("description", "")
                    confidence = props.get("confidence") or entity.get("confidence", 0.8)
                    source = props.get("source_document") or entity.get("source_document", "hybrid_pipeline")
                    created_at = props.get("created_at") or entity.get("created_at", datetime.now().isoformat())
                    extraction_method = props.get("extraction_method") or entity.get("extraction_method", "hybrid")
                    entity_type = entity.get("type", "Entity")

                    entity_data = {
                        "id": entity_id,
                        "name": name,
                        "type": entity_type,
                        "description": description,
                        "confidence": confidence,
                        "source": source,
                        "created_at": created_at,
                        "extraction_method": extraction_method
                    }
                    if workspace_id:
                        entity_data["workspace_id"] = workspace_id
                    if account_id:
                        entity_data["account_id"] = account_id

                    if j < 3:
                        logger.info(f"📝 DATOS MAPEADOS {j+1}:")
                        logger.info(f"   🆔 ID: {entity_data['id']}")
                        logger.info(f"   📛 Name: {entity_data['name']}")
                        logger.info(f"   🏷️ Type: {entity_data['type']}")
                        logger.info(f"   📄 Description: {entity_data['description']}")

                    batch_data.append(entity_data)

                # Crear nodos por tipo específico (sin APOC, más compatible)
                entities_by_type = {}
                for entity in batch_data:
                    entity_type = entity.get("type", "Entity")
                    if entity_type not in entities_by_type:
                        entities_by_type[entity_type] = []
                    entities_by_type[entity_type].append(entity)

                total_created = 0

                # Crear nodos por cada tipo específico
                for entity_type, type_entities in entities_by_type.items():
                    # Query específica para cada tipo
                    type_query = f"""
                    UNWIND $entities AS entity
                    MERGE (n:{entity_type} {{id: entity.id}})
                    SET n.name = entity.name,
                        n.type = entity.type,
                        n.description = entity.description,
                        n.confidence = entity.confidence,
                        n.source = entity.source,
                        n.created_at = entity.created_at,
                        n.extraction_method = entity.extraction_method
                    """
                    if "workspace_id" in entity:
                        type_query += """, n.workspace_id = entity.workspace_id"""
                    if "account_id" in entity:
                        type_query += """, n.account_id = entity.account_id"""
                    type_query += """
                    RETURN count(n) as created
                    """

                    result = await self.graph_db.execute_query(type_query, {"entities": type_entities})
                    created_count = result[0]["created"] if result else 0
                    total_created += created_count

                    logger.debug(f"✅ Creados {created_count} nodos de tipo {entity_type}")

                logger.debug(f"✅ Total nodos creados en lote: {total_created}")
                entities_added += total_created

                logger.debug(f"✅ Lote procesado: {len(batch)} entidades")
            
            logger.info(f"✅ {entities_added} entidades agregadas a Neo4j")
            return entities_added
            
        except Exception as e:
            logger.error(f"❌ Error agregando entidades: {e}")
            raise
    
    async def _add_relationships_to_neo4j(self, relationships: List[Dict], workspace_id: Optional[str], account_id: Optional[str]) -> int:
        """
        Agrega relaciones a Neo4j.
        
        Args:
            relationships: Lista de relaciones
            workspace_id: ID del workspace
            account_id: ID de la cuenta
            
        Returns:
            Número de relaciones agregadas
        """
        try:
            logger.info(f"🔗 Agregando {len(relationships)} relaciones a Neo4j...")
            
            relationships_added = 0
            batch_size = 100  # Procesar en lotes
            
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i:i + batch_size]

                # Preparar datos del lote
                batch_data = []
                for j, relationship in enumerate(batch):
                    # DEBUG: Log de las primeras 3 relaciones
                    if j < 3:
                        logger.info(f"🔗 RELACIÓN {j+1} RECIBIDA:")
                        logger.info(f"   📋 Claves: {list(relationship.keys())}")
                        logger.info(f"   📝 Contenido: {relationship}")

                    # El pipeline híbrido pone los datos directamente en relationship
                    source_id = relationship.get("source_entity", "")
                    target_id = relationship.get("target_entity", "")

                    if j < 3:
                        logger.info(f"   🎯 Source ID: '{source_id}'")
                        logger.info(f"   🎯 Target ID: '{target_id}'")

                    if source_id and target_id:  # Solo agregar si ambas entidades existen
                        # El pipeline híbrido usa 'relationship_type', no 'type'
                        rel_type = (relationship.get("relationship_type") or
                                   relationship.get("type") or
                                   "RELATED")

                        rel_data = {
                            "source_id": source_id,
                            "target_id": target_id,
                            "type": rel_type,
                            "description": relationship.get("description", ""),
                            "confidence": relationship.get("confidence", 0.8),
                            "source": relationship.get("source_document", "hybrid_pipeline"),
                            "created_at": relationship.get("created_at", datetime.now().isoformat()),
                            "extraction_method": relationship.get("extraction_method", "hybrid")
                        }
                        if workspace_id:
                            rel_data["workspace_id"] = workspace_id
                        if account_id:
                            rel_data["account_id"] = account_id
                        batch_data.append(rel_data)

                        if j < 3:
                            logger.info(f"   ✅ Relación agregada al batch")
                    else:
                        if j < 3:
                            logger.warning(f"   ❌ Relación omitida: source_id='{source_id}', target_id='{target_id}'")

                # Crear relaciones por tipo específico (sin APOC)
                relationships_by_type = {}
                for rel_data in batch_data:
                    rel_type = rel_data.get("type", "RELATED")
                    if rel_type not in relationships_by_type:
                        relationships_by_type[rel_type] = []
                    relationships_by_type[rel_type].append(rel_data)

                # Crear relaciones por cada tipo específico
                for rel_type, type_relationships in relationships_by_type.items():
                    # Query específica para cada tipo de relación
                    type_query = f"""
                    UNWIND $relationships AS rel
                    MATCH (source {{id: rel.source_id}})
                    MATCH (target {{id: rel.target_id}})
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET r.description = rel.description,
                        r.confidence = rel.confidence,
                        r.source = rel.source,
                        r.created_at = rel.created_at,
                        r.extraction_method = rel.extraction_method,
                        r.type = rel.type
                    """
                    if "workspace_id" in rel_data:
                        type_query += """, r.workspace_id = rel.workspace_id"""
                    if "account_id" in rel_data:
                        type_query += """, r.account_id = rel.account_id"""
                    type_query += """
                    RETURN count(r) as created
                    """

                    result = await self.graph_db.execute_query(type_query, {"relationships": type_relationships})
                    created_count = result[0]["created"] if result else 0
                    relationships_added += created_count

                    logger.debug(f"✅ Creadas {created_count} relaciones de tipo {rel_type}")
                logger.debug(f"✅ Lote procesado: {len(batch)} relaciones")
            
            logger.info(f"✅ {relationships_added} relaciones agregadas a Neo4j")
            return relationships_added
            
        except Exception as e:
            logger.error(f"❌ Error agregando relaciones: {e}")
            raise
    
    def _generate_entity_id(self, entity: Dict) -> str:
        """
        Genera un ID único para una entidad.
        
        Args:
            entity: Diccionario de entidad
            
        Returns:
            ID único como string
        """
        props = entity.get("properties", {})
        name = props.get("name", "unknown")
        entity_type = entity.get("type", "Entity")
        
        # Crear ID basado en nombre y tipo (normalizado)
        normalized_name = name.lower().replace(" ", "_").replace("-", "_")
        return f"{entity_type.lower()}_{normalized_name}"
    
    def _extract_entity_id(self, entity_reference: str) -> Optional[str]:
        """
        Extrae el ID de una entidad desde una referencia.
        
        Args:
            entity_reference: Referencia a la entidad
            
        Returns:
            ID de la entidad o None si no se puede extraer
        """
        if not entity_reference:
            return None
        
        # Si ya es un ID válido, devolverlo
        if entity_reference.startswith(("entity_", "concept_")):
            return entity_reference
        
        # Si es un nombre, intentar generar ID
        # Esto es una aproximación - en un sistema real necesitarías un mapeo más robusto
        normalized = entity_reference.lower().replace(" ", "_").replace("-", "_")
        return f"entity_{normalized}"
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del grafo en Neo4j.
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            # Contar nodos
            nodes_query = "MATCH (n) RETURN count(n) as node_count"
            nodes_result = await self.graph_db.execute_query(nodes_query)
            node_count = nodes_result[0]["node_count"] if nodes_result else 0
            
            # Contar relaciones
            rels_query = "MATCH ()-[r]-() RETURN count(r) as rel_count"
            rels_result = await self.graph_db.execute_query(rels_query)
            rel_count = rels_result[0]["rel_count"] if rels_result else 0
            
            # Contar tipos de entidades
            types_query = "MATCH (n) RETURN DISTINCT n.type as type, count(n) as count ORDER BY count DESC"
            types_result = await self.graph_db.execute_query(types_query)
            
            return {
                "total_nodes": node_count,
                "total_relationships": rel_count,
                "entity_types": types_result or [],
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {
                "total_nodes": 0,
                "total_relationships": 0,
                "entity_types": [],
                "error": str(e)
            }
