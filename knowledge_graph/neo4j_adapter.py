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
    
    async def add_cognee_results_to_graph(self, entities: List[Dict], relationships: List[Dict], workspace_id: Optional[str] = None, account_id: Optional[str] = None, dataset_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Agrega entidades y relaciones del pipeline híbrido a Neo4j.
        
        Args:
            entities: Lista de entidades extraídas
            relationships: Lista de relaciones extraídas
            workspace_id: ID del workspace actual
            account_id: ID de la cuenta del usuario
            dataset_name: Nombre del dataset (opcional, para sobrescribir/asegurar)
            
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
            stats["entities_added"] = await self._add_entities_to_neo4j(entities, workspace_id, account_id, dataset_name)
            
            # Agregar relaciones
            stats["relationships_added"] = await self._add_relationships_to_neo4j(relationships, workspace_id, account_id, dataset_name)
            
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
    
    async def _add_entities_to_neo4j(self, entities: List[Dict], workspace_id: Optional[str], account_id: Optional[str], dataset_name: Optional[str] = None) -> int:
        """
        Agrega entidades a Neo4j.
        
        Args:
            entities: Lista de entidades
            workspace_id: ID del workspace
            account_id: ID de la cuenta
            dataset_name: Nombre del dataset (opcional)
            
        Returns:
            Número de entidades agregadas
        """
        try:
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', False):
                logger.warning("🔄 GraphDB no conectado en Neo4jAdapter, intentando reconectar...")
                self.graph_db.connect()

            if not entities:
                logger.info("📝 No hay entidades para agregar a Neo4j")
                return 0

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
                    
                    # Prioridad: 1. Entidad, 2. Argumento global
                    final_dataset_name = entity.get("dataset_name") or dataset_name
                    
                    concept = props.get("concept") or entity.get("concept") # Extraer concept
                    category = props.get("category") or entity.get("category") # Extraer category

                    entity_data = {
                        "id": entity_id,
                        "name": name,
                        "type": entity_type,
                        "description": description,
                        "confidence": confidence,
                        "source": source,
                        "created_at": created_at,
                        "extraction_method": extraction_method,
                        "concept": concept, # Incluir concept
                        "category": category, # Incluir category
                        "source_document_id": entity.get("source_document_id"),
                        "dataset_name": final_dataset_name
                    }
                    entity_data["workspace_id"] = workspace_id
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
                    # Query estática para cada tipo, incluyendo todos los campos opcionales.
                    # Neo4j manejará los valores nulos si no están presentes en la entidad.
                    type_query = f"""
                    UNWIND $entities AS entity
                    MERGE (n:{entity_type} {{id: entity.id}})
                    SET n.name = entity.name,
                        n.type = entity.type,
                        n.description = entity.description,
                        n.confidence = entity.confidence,
                        n.source = entity.source,
                        n.created_at = entity.created_at,
                        n.extraction_method = entity.extraction_method,
                        n.workspace_id = entity.workspace_id,
                        n.account_id = entity.account_id,
                        n.dataset_name = entity.dataset_name,
                        n.concept = entity.concept,
                        n.category = entity.category
                    RETURN count(n) as created
                    """

                    result = await self.graph_db.execute_query(type_query, {"entities": type_entities})
                    created_count = result[0]["created"] if result else 0
                    total_created += created_count

                    logger.debug(f"✅ Creados {created_count} nodos de tipo {entity_type}")

                logger.debug(f"✅ Total nodos creados en lote: {total_created}")
                entities_added += total_created

                # Crear relaciones MENTIONS con los documentos de origen para este lote
                await self._add_document_mentions(batch_data)

                logger.debug(f"✅ Lote procesado: {len(batch)} entidades")
            
            logger.info(f"✅ {entities_added} entidades agregadas a Neo4j")
            
            return entities_added
            
        except Exception as e:
            logger.error(f"❌ Error agregando entidades: {e}")
            raise
    
    async def _add_relationships_to_neo4j(self, relationships: List[Dict], workspace_id: Optional[str], account_id: Optional[str], dataset_name: Optional[str] = None) -> int:
        """
        Agrega relaciones a Neo4j.
        
        Args:
            relationships: Lista de relaciones
            workspace_id: ID del workspace
            account_id: ID de la cuenta
            dataset_name: Nombre del dataset (opcional)
            
        Returns:
            Número de relaciones agregadas
        """
        try:
            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', False):
                logger.warning("🔄 GraphDB no conectado en Neo4jAdapter, intentando reconectar...")
                self.graph_db.connect()

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
                    # Soportar múltiples convenciones de nombres de claves
                    source_id = (relationship.get("source_id") or 
                               relationship.get("source_entity_id") or 
                               relationship.get("source_entity") or 
                               relationship.get("head"))
                               
                    target_id = (relationship.get("target_id") or 
                               relationship.get("target_entity_id") or 
                               relationship.get("target_entity") or 
                               relationship.get("tail"))

                    if j < 3:
                        logger.info(f"   🎯 Source ID: '{source_id}'")
                        logger.info(f"   🎯 Target ID: '{target_id}'")

                    if source_id and target_id:  # Solo agregar si ambas entidades existen
                        # El pipeline híbrido usa 'relationship_type', no 'type'
                        rel_type = (relationship.get("relationship_type") or
                                   relationship.get("type") or
                                   "RELATED")

                        # Prioridad: 1. Relación, 2. Argumento global
                        final_dataset_name = relationship.get("dataset_name") or dataset_name
                        
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
                        rel_data["workspace_id"] = workspace_id
                        rel_data["account_id"] = account_id
                        rel_data["dataset_name"] = final_dataset_name # Already extracted, default to None if not present
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
                    safe_rel_type = f"`{rel_type}`"
                    
                    # Filtrar relaciones para evitar duplicados inversos
                    filtered_relationships = []
                    for rel in type_relationships:
                        source_id = rel["source_id"]
                        target_id = rel["target_id"]
                        
                        # Verificar si la relación (o su inversa) ya existe en la base de datos
                        if await self._relationship_exists_in_db(source_id, target_id, rel_type):
                            logger.debug(f"⚠️ Relación inversa ya existente o duplicada omitida: {source_id}-[:{rel_type}]->{target_id}")
                            continue
                        filtered_relationships.append(rel)

                    if not filtered_relationships:
                        continue # No hay relaciones para agregar en este tipo

                    # Query estática para cada tipo de relación, incluyendo todos los campos opcionales.
                    type_query = f"""
                    UNWIND $relationships AS rel
                    MATCH (source {{id: rel.source_id}})
                    MATCH (target {{id: rel.target_id}})
                    MERGE (source)-[r:{safe_rel_type}]->(target)
                    SET r.description = rel.description,
                        r.confidence = rel.confidence,
                        r.source = rel.source,
                        r.created_at = rel.created_at,
                        r.extraction_method = rel.extraction_method,
                        r.type = rel.type,
                        r.workspace_id = rel.workspace_id,
                        r.account_id = rel.account_id,
                        r.dataset_name = rel.dataset_name
                    RETURN count(r) as created
                    """

                    result = await self.graph_db.execute_query(type_query, {"relationships": filtered_relationships})
                    created_count = result[0]["created"] if result else 0
                    relationships_added += created_count
                    logger.info(f"✅ Creadas {created_count} relaciones de tipo {rel_type}")
                logger.debug(f"✅ Lote procesado: {len(filtered_relationships)} relaciones")
            
            logger.info(f"✅ {relationships_added} relaciones agregadas a Neo4j")
            return relationships_added
            
        except Exception as e:
            logger.error(f"❌ Error agregando relaciones: {e}")
            raise

    async def _relationship_exists_in_db(self, source_id: str, target_id: str, rel_type: str) -> bool:
        """
        Verifica si una relación (o su inversa) ya existe en la base de datos.
        
        Args:
            source_id: ID del nodo de origen
            target_id: ID del nodo de destino
            rel_type: Tipo de la relación
            
        Returns:
            True si la relación (o su inversa) existe, False en caso contrario.
        """
        query = f"""
        MATCH (s {{id: $source_id}})-[r:`{rel_type}`]->(t {{id: $target_id}})
        RETURN count(r) > 0 AS exists
        """
        params = {"source_id": source_id, "target_id": target_id}
        result = await self.graph_db.execute_query(query, params)
        if result and result[0]["exists"]:
            return True

        # Verificar si la relación inversa existe
        query_inverse = f"""
        MATCH (s {{id: $target_id}})-[r:`{rel_type}`]->(t {{id: $source_id}})
        RETURN count(r) > 0 AS exists
        """
        params_inverse = {"source_id": source_id, "target_id": target_id} # Los IDs se invierten en la consulta, no en los parámetros
        result_inverse = await self.graph_db.execute_query(query_inverse, params_inverse)
        return result_inverse and result_inverse[0]["exists"]

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
    async def create_document_nodes(self, document_nodes: List[Dict[str, Any]]) -> int:
        """
        Persiste nodos de tipo DOCUMENT en Neo4j.
        
        Args:
            document_nodes: Lista de diccionarios con datos de documentos
            
        Returns:
            Número de nodos creados
        """
        try:
            if not document_nodes:
                return 0

            if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', False):
                self.graph_db.connect()

            logger.info(f"📄 Persistiendo {len(document_nodes)} nodos DOCUMENT en Neo4j...")
            
            # Preparar los datos para Neo4j
            formatted_docs = []
            for doc in document_nodes:
                formatted_doc = {
                    "id": doc.get("id"),
                    "title": doc.get("title", "Sin título"),
                    "url": doc.get("url", ""),
                    "content": doc.get("summary") or (doc.get("content", "")[:500] + "..." if len(doc.get("content", "")) > 500 else doc.get("content", "")),
                    "content_hash": doc.get("content_hash", ""),
                    "summary": doc.get("summary", ""),
                    "keywords": doc.get("keywords", []),
                    "publication_date": doc.get("publication_date"),
                    "author": doc.get("author", "Desconocido"),
                    "source_type": doc.get("source_type", "unknown"),
                    "topic": doc.get("topic", "general"),
                    "created_at": doc.get("created_at", datetime.now().isoformat()),
                    "updated_at": doc.get("updated_at", datetime.now().isoformat()),
                    "workspace_id": doc.get("workspace_id"),
                    "account_id": doc.get("account_id"),
                    "dataset_name": doc.get("dataset_name"),
                    "type": "DOCUMENT"
                }
                formatted_docs.append(formatted_doc)

            # Query para crear/actualizar nodos DOCUMENT
            query = """
            UNWIND $docs AS doc
            MERGE (d:DOCUMENT {id: doc.id})
            SET d.title = doc.title,
                d.url = doc.url,
                d.content = doc.content,
                d.content_hash = doc.content_hash,
                d.summary = doc.summary,
                d.keywords = doc.keywords,
                d.publication_date = doc.publication_date,
                d.author = doc.author,
                d.source_type = doc.source_type,
                d.topic = doc.topic,
                d.created_at = doc.created_at,
                d.updated_at = doc.updated_at,
                d.workspace_id = doc.workspace_id,
                d.account_id = doc.account_id,
                d.dataset_name = doc.dataset_name,
                d.type = doc.type
            RETURN count(d) as created
            """

            result = await self.graph_db.execute_query(query, {"docs": formatted_docs})
            created_count = result[0]["created"] if result else 0
            
            logger.info(f"✅ {created_count} nodos DOCUMENT persistidos en Neo4j.")
            return created_count

        except Exception as e:
            logger.error(f"❌ Error persistiendo nodos DOCUMENT: {e}")
            raise

    async def _add_document_mentions(self, entities: List[Dict], dataset_name: Optional[str] = None):
        """Crea relaciones MENTIONS entre documentos y entidades."""
        try:
            mentions = [
                {
                    "source_id": ent["source_document_id"],
                    "target_id": ent["id"],
                    "dataset_name": dataset_name or ent.get("dataset_name")
                }
                for ent in entities if ent.get("source_document_id")
            ]
            
            if not mentions:
                return

            query = """
            UNWIND $mentions AS mention
            MATCH (d:DOCUMENT {id: mention.source_id})
            MATCH (e {id: mention.target_id})
            MERGE (d)-[r:MENTIONS]->(e)
            SET r.dataset_name = mention.dataset_name,
                r.created_at = datetime().isoformat(),
                r.extraction_method = 'hybrid_mention'
            """
            await self.graph_db.execute_query(query, {"mentions": mentions})
            logger.info(f"🔗 Creadas {len(mentions)} relaciones MENTIONS entre documentos y entidades")
            
        except Exception as e:
            logger.warning(f"⚠️ Error creando relaciones MENTIONS: {e}")

