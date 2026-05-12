# knowledge_graph/neo4j_adapter.py

import logging
import json
import uuid
import re
from typing import Dict, List, Optional, Any, Union
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
    
    async def create_conceptual_quote_nodes(self, quotes: List[Dict], account_id: Optional[str] = None, workspace_id: Optional[str] = None):
        """
        Crea nodos de tipo CONCEPTUAL_QUOTE en Neo4j.
        """
        if not quotes:
            return

        query = """
        UNWIND $quotes AS quote
        MERGE (q:CONCEPTUAL_QUOTE {id: quote.id, account_id: $account_id})
        SET q += quote.properties,
            q.updated_at = datetime()
        SET q:Entity, q:CONCEPTUAL_QUOTE
        """

        # Preparar datos para UNWIND
        acc_id_str = str(account_id) if account_id else None
        batch_data = []
        for quote in quotes:
            props = quote.get("properties", {})
            props["id"] = quote["id"]
            props["type"] = "CONCEPTUAL_QUOTE"
            props["account_id"] = acc_id_str
            props["workspace_id"] = str(workspace_id) if workspace_id else None
            batch_data.append({"id": quote["id"], "properties": props})

        await self.graph_db.execute_query(query, {"quotes": batch_data, "account_id": acc_id_str})

    async def create_idea_profile_nodes(self, profiles: List[Dict], account_id: Optional[str] = None, workspace_id: Optional[str] = None):
        """
        Crea nodos de tipo IDEA_PROFILE en Neo4j.
        """
        if not profiles:
            return

        query = """
        UNWIND $profiles AS profile
        MERGE (p:IDEA_PROFILE {id: profile.id, account_id: $account_id})
        SET p += profile.properties,
            p.updated_at = datetime()
        SET p:Entity, p:IDEA_PROFILE
        """

        # Preparar datos para UNWIND
        acc_id_str = str(account_id) if account_id else None
        batch_data = []
        for profile in profiles:
            props = profile.get("properties", {})
            props["id"] = profile["id"]
            props["type"] = "IDEA_PROFILE"
            props["account_id"] = acc_id_str
            props["workspace_id"] = str(workspace_id) if workspace_id else None
            batch_data.append({"id": profile["id"], "properties": props})

        await self.graph_db.execute_query(query, {"profiles": batch_data, "account_id": acc_id_str})

    async def create_conceptual_relationships(self, relationships: List[Dict], account_id: Optional[str] = None, workspace_id: Optional[str] = None):
        """
        Crea relaciones temáticas entre nodos conceptuales en Neo4j.
        """
        if not relationships:
            return

        logger.info(f"🔗 Persistiendo {len(relationships)} relaciones conceptuales en Neo4j...")
        
        # Agrupar por tipo de relación para eficiencia (MERGE no soporta tipos dinámicos en UNWIND fácilmente sin APOC)
        rels_by_type = {}
        for rel in relationships:
            rel_type = rel.get("type") or rel.get("relationship_type") or "RELATED_TO"
            if rel_type not in rels_by_type:
                rels_by_type[rel_type] = []
            rels_by_type[rel_type].append(rel)

        for rel_type, type_rels in rels_by_type.items():
            query = f"""
            UNWIND $rels AS rel
            MATCH (s {{id: rel.source_id, account_id: $account_id}})
            MATCH (t {{id: rel.target_id, account_id: $account_id}})
            MERGE (s)-[r:`{rel_type}`]->(t)
            SET r.description = rel.description,
                r.importance = rel.importance,
                r.category = rel.category,
                r.extraction_method = rel.extraction_method,
                r.confidence = rel.confidence,
                r.similarity_score = rel.similarity_score,
                r.metadata_score = rel.metadata_score,
                r.shared_signals = rel.shared_signals,
                r.account_id = $account_id,
                r.workspace_id = $workspace_id,
                r.updated_at = datetime()
            """
            
            batch_data = []
            acc_id_str = str(account_id) if account_id else None
            ws_id_str = str(workspace_id) if workspace_id else None
            
            for rel in type_rels:
                # SOPORTE: Manejar datos anidados bajo 'properties'
                rel_props = rel.get("properties", {}) if isinstance(rel, dict) else {}
                
                batch_data.append({
                    "source_id": rel.get("source_id") or rel.get("head"),
                    "target_id": rel.get("target_id") or rel.get("tail"),
                    "description": rel_props.get("description") or rel.get("description", ""),
                    "importance": rel_props.get("importance") or rel.get("importance", 0.5),
                    "category": rel_props.get("category") or rel.get("category", "general"),
                    "extraction_method": rel_props.get("extraction_method") or rel.get("extraction_method", "conceptual"),
                    "confidence": rel_props.get("confidence") or rel.get("confidence", 0.8),
                    "similarity_score": rel_props.get("similarity_score") or rel.get("similarity_score"),
                    "metadata_score": rel_props.get("metadata_score") or rel.get("metadata_score"),
                    "shared_signals": rel_props.get("shared_signals") or rel.get("shared_signals", []),
                })
            
            await self.graph_db.execute_query(query, {
                "rels": batch_data, 
                "account_id": acc_id_str,
                "workspace_id": ws_id_str
            })
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
                    entity_id = props.get("cognee_id") or entity.get("id") or self._generate_entity_id(entity, account_id)
                    name = props.get("name") or entity.get("name", "Unknown")
                    description = props.get("description") or entity.get("description", "")
                    confidence = props.get("confidence") or entity.get("confidence", 0.8)
                    source = props.get("source_document") or entity.get("source_document", "hybrid_pipeline")
                    created_at = props.get("created_at") or entity.get("created_at", datetime.now().isoformat())
                    extraction_method = props.get("extraction_method") or entity.get("extraction_method", "hybrid")
                    entity_type = entity.get("type", "Entity")
                    
                    # Prioridad: 1. Entidad, 2. Argumento global
                    # Decodificar dataset_name si es necesario
                    raw_dataset_name = entity.get("dataset_name") or dataset_name
                    final_dataset_name = raw_dataset_name
                    if final_dataset_name and '%' in final_dataset_name:
                        from urllib.parse import unquote
                        final_dataset_name = unquote(final_dataset_name)
                    
                    concept = props.get("concept") or entity.get("concept") # Extraer concept
                    category = props.get("category") or entity.get("category") # Extraer category

                    # Asegurar IDs como strings
                    acc_id_str = str(account_id) if account_id else None
                    ws_id_str = str(workspace_id) if workspace_id else None

                    entity_data = {
                        "id": str(entity_id),
                        "name": name,
                        "type": entity_type,
                        "description": description,
                        "confidence": confidence,
                        "source": source,
                        "created_at": created_at,
                        "extraction_method": extraction_method,
                        "concept": concept, # Incluir concept
                        "category": category, # Incluir category
                        "source_document_id": str(entity.get("source_document_id")) if entity.get("source_document_id") else None,
                        "dataset_name": final_dataset_name
                    }
                    entity_data["workspace_id"] = ws_id_str
                    entity_data["account_id"] = acc_id_str

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
                    # Query mejorada para consolidar:
                    # 1. MERGE usando una etiqueta base (Entity) y el ID (basado en nombre)
                    # 2. SET para aplicar la etiqueta específica (n:{entity_type})
                    # 3. SET para actualizar propiedades
                    type_query = f"""
                    UNWIND $entities AS entity
                    MERGE (n:Entity {{id: entity.id, account_id: entity.account_id}})
                    SET n:`{entity_type}`,
                        n.name = entity.name,
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

                    logger.debug(f"✅ Consolidados/Creados {created_count} nodos con tipo {entity_type}")

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

                    # Asegurar que account_id y workspace_id sean strings para evitar problemas de tipos en Neo4j
                    final_account_id = str(account_id) if account_id else None
                    final_workspace_id = str(workspace_id) if workspace_id else None

                    if source_id and target_id:  # Solo agregar si ambas entidades existen
                        # El pipeline híbrido usa 'relationship_type', no 'type'
                        rel_type = (relationship.get("relationship_type") or
                                   relationship.get("type") or
                                   "RELATED")

                        # Prioridad: 1. Relación, 2. Argumento global
                        raw_dataset_name = relationship.get("dataset_name") or dataset_name
                        final_dataset_name = raw_dataset_name
                        if final_dataset_name and '%' in final_dataset_name:
                            from urllib.parse import unquote
                            final_dataset_name = unquote(final_dataset_name)
                        
                        # SOPORTE: Manejar datos anidados bajo 'properties' si existen (como envía ConceptualGraphProcessor)
                        rel_props = relationship.get("properties", {}) if isinstance(relationship, dict) else {}
                        description = rel_props.get("description") or relationship.get("description", "")
                        confidence = rel_props.get("confidence") or relationship.get("confidence", 0.8)
                        source = rel_props.get("source") or rel_props.get("source_document") or relationship.get("source_document") or relationship.get("source", "hybrid_pipeline")
                        created_at = rel_props.get("created_at") or relationship.get("created_at", datetime.now().isoformat())
                        extraction_method = rel_props.get("extraction_method") or relationship.get("extraction_method", "hybrid")

                        rel_data = {
                            "source_id": source_id,
                            "target_id": target_id,
                            "type": rel_type,
                            "description": description,
                            "confidence": confidence,
                            "source": source,
                            "created_at": created_at,
                            "extraction_method": extraction_method
                        }
                        rel_data["workspace_id"] = final_workspace_id
                        rel_data["account_id"] = final_account_id
                        rel_data["dataset_name"] = final_dataset_name
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
                        if await self._relationship_exists_in_db(source_id, target_id, rel_type, account_id):
                            logger.debug(f"⚠️ Relación inversa ya existente o duplicada omitida: {source_id}-[:{rel_type}]->{target_id}")
                            continue
                        filtered_relationships.append(rel)

                    if not filtered_relationships:
                        continue # No hay relaciones para agregar en este tipo

                    # Query optimizada:
                    # 1. Usar la etiqueta base (Entity) si es posible para mayor velocidad
                    # 2. MATCH robusto que funciona tanto para nodos con etiqueta Entity como sin ella
                    type_query = f"""
                    UNWIND $relationships AS rel
                    MATCH (source {{id: rel.source_id, account_id: rel.account_id}})
                    MATCH (target {{id: rel.target_id, account_id: rel.account_id}})
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

    async def _relationship_exists_in_db(self, source_id: str, target_id: str, rel_type: str, account_id: Optional[str] = None) -> bool:
        """
        Verifica si una relación (o su inversa) ya existe en la base de datos para un usuario específico.
        """
        # Asegurar account_id como string
        acc_id_str = str(account_id) if account_id else None
        
        if acc_id_str:
            query = f"""
            MATCH (s {{id: $source_id, account_id: $account_id}})-[r:`{rel_type}`]->(t {{id: $target_id, account_id: $account_id}})
            RETURN count(r) > 0 AS exists
            """
            params = {"source_id": source_id, "target_id": target_id, "account_id": acc_id_str}
        else:
            query = f"""
            MATCH (s {{id: $source_id}})-[r:`{rel_type}`]->(t {{id: $target_id}})
            RETURN count(r) > 0 AS exists
            """
            params = {"source_id": source_id, "target_id": target_id}
            
        result = await self.graph_db.execute_query(query, params)
        if result and result[0]["exists"]:
            return True

        # Verificar si la relación inversa existe
        if acc_id_str:
            query_inverse = f"""
            MATCH (s {{id: $target_id, account_id: $account_id}})-[r:`{rel_type}`]->(t {{id: $source_id, account_id: $account_id}})
            RETURN count(r) > 0 AS exists
            """
            params_inverse = {"source_id": source_id, "target_id": target_id, "account_id": acc_id_str}
        else:
            query_inverse = f"""
            MATCH (s {{id: $target_id}})-[r:`{rel_type}`]->(t {{id: $source_id}})
            RETURN count(r) > 0 AS exists
            """
            params_inverse = {"source_id": source_id, "target_id": target_id}
            
        result_inverse = await self.graph_db.execute_query(query_inverse, params_inverse)
        return result_inverse and result_inverse[0]["exists"]

    def _generate_entity_id(self, entity: Dict, account_id: Optional[str] = None) -> str:
        """
        Genera un ID único para una entidad, incluyendo el account_id para multi-tenencia.
        
        Args:
            entity: Diccionario de entidad
            account_id: ID de la cuenta del usuario
            
        Returns:
            ID único como string
        """
        # Crear ID basado en el nombre normalizado y el account_id para evitar colisiones entre usuarios
        name = entity.get("name", "unknown")
        normalized_name = re.sub(r'[^\w\s]', '', name.lower())
        normalized_name = re.sub(r'\s+', '_', normalized_name).strip('_')
        
        if not normalized_name:
            normalized_name = "unknown"
        
        prefix = f"user_{account_id}_" if account_id else ""
        return f"{prefix}entity_{normalized_name}"
    
    def _extract_entity_id(self, entity_reference: str, account_id: Optional[str] = None) -> Optional[str]:
        """
        Extrae o genera el ID de una entidad desde una referencia, respetando el account_id.
        """
        if not entity_reference:
            return None
        
        # Si ya es un ID con el prefijo de usuario, devolverlo
        if account_id and entity_reference.startswith(f"user_{account_id}_"):
            return entity_reference
        
        # Si es un ID global pero tenemos account_id, convertirlo
        if account_id and entity_reference.startswith(("entity_", "concept_")):
            return f"user_{account_id}_{entity_reference}"
            
        # Si es un nombre, generar el ID usando la lógica estándar
        return self._generate_entity_id({"name": entity_reference}, account_id)
    
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
                doc_type = doc.get("type", "DOCUMENT")
                formatted_doc = {
                    "id": doc.get("id"),
                    "name": doc.get("name") or doc.get("title", "Sin título"),
                    "title": doc.get("title", "Sin título"),
                    "url": doc.get("url", ""),
                    "content": doc.get("summary") or (doc.get("content", "")[:500] + "..." if len(doc.get("content", "")) > 500 else doc.get("content", "")),
                    "content_hash": doc.get("content_hash", ""),
                    "summary": doc.get("summary", ""),
                    "keywords": doc.get("keywords", []),
                    "publication_date": doc.get("publication_date"),
                    "author": doc.get("author", "Desconocido"),
                    "source_type": doc.get("source_type", "unknown"),
                    "memory_type": doc.get("memory_type"),
                    "topic": doc.get("topic", "general"),
                    "created_at": doc.get("created_at", datetime.now().isoformat()),
                    "updated_at": doc.get("updated_at", datetime.now().isoformat()),
                    "workspace_id": doc.get("workspace_id"),
                    "account_id": doc.get("account_id"),
                    "dataset_name": doc.get("dataset_name"),
                    "type": doc_type
                }
                formatted_docs.append(formatted_doc)

            # Query para crear/actualizar nodos fuente con etiquetas específicas para documentos o memorias
            query = """
            UNWIND $docs AS doc
            MERGE (d:SourceNode {id: doc.id})
            SET d.name = doc.name,
                d.title = doc.title,
                d.url = doc.url,
                d.content = doc.content,
                d.content_hash = doc.content_hash,
                d.summary = doc.summary,
                d.keywords = doc.keywords,
                d.publication_date = doc.publication_date,
                d.author = doc.author,
                d.source_type = doc.source_type,
                d.memory_type = doc.memory_type,
                d.topic = doc.topic,
                d.created_at = doc.created_at,
                d.updated_at = doc.updated_at,
                d.workspace_id = doc.workspace_id,
                d.account_id = doc.account_id,
                d.dataset_name = doc.dataset_name,
                d.type = doc.type

            REMOVE d:DOCUMENT
            REMOVE d:MEMORY
            REMOVE d:USER_MEMORY
            REMOVE d:USER_MEMORY_PROACTIVE_LLM
            REMOVE d:AGENT_MEMORY
            REMOVE d:CHAT_SUMMARY
            REMOVE d:GENERAL_MEMORY

            FOREACH (ignore IN CASE WHEN doc.type = 'DOCUMENT' THEN [1] ELSE [] END | SET d:DOCUMENT)
            FOREACH (ignore IN CASE WHEN doc.type <> 'DOCUMENT' THEN [1] ELSE [] END | SET d:MEMORY)
            FOREACH (ignore IN CASE WHEN doc.type = 'USER_MEMORY' THEN [1] ELSE [] END | SET d:USER_MEMORY)
            FOREACH (ignore IN CASE WHEN doc.type = 'USER_MEMORY_PROACTIVE_LLM' THEN [1] ELSE [] END | SET d:USER_MEMORY_PROACTIVE_LLM)
            FOREACH (ignore IN CASE WHEN doc.type = 'AGENT_MEMORY' THEN [1] ELSE [] END | SET d:AGENT_MEMORY)
            FOREACH (ignore IN CASE WHEN doc.type = 'CHAT_SUMMARY' THEN [1] ELSE [] END | SET d:CHAT_SUMMARY)
            FOREACH (ignore IN CASE WHEN doc.type = 'GENERAL_MEMORY' THEN [1] ELSE [] END | SET d:GENERAL_MEMORY)
             
            RETURN count(d) as created
            """

            result = await self.graph_db.execute_query(query, {"docs": formatted_docs})
            created_count = result[0]["created"] if result else 0
            
            logger.info(f"✅ {created_count} nodos DOCUMENT persistidos en Neo4j.")
            return created_count

        except Exception as e:
            logger.error(f"❌ Error persistiendo nodos DOCUMENT: {e}")
            raise

    async def create_memory_nodes(self, memory_nodes: List[Dict[str, Any]]) -> int:
        """
        Persiste nodos de memoria en Neo4j con etiquetas correctas (MEMORY + tipo específico).
        Pipeline dedicado para memorias, completamente separado del de documentos.

        Cada nodo tiene:
          - Etiqueta base :MEMORY
          - Etiqueta específica: :USER_MEMORY, :AGENT_MEMORY, :CHAT_SUMMARY, etc.
          - Contenido directo sin resumen LLM
          - Embedding vectorial
          - Metadatos completos (topic, category, workspace_id, thread_id, etc.)
        """
        if not memory_nodes:
            return 0

        if self.graph_db._driver is None or getattr(self.graph_db._driver, 'closed', False):
            self.graph_db.connect()

        logger.info(f"🧠 Persistiendo {len(memory_nodes)} nodos de memoria en Neo4j...")

        formatted = []
        for m in memory_nodes:
            node_type = m.get("node_type", "USER_MEMORY")
            formatted.append({
                "id": m["id"],
                "name": m.get("name", ""),
                "content": m.get("content", ""),
                "topic": m.get("topic", "general"),
                "category": m.get("category") or "",
                "memory_type": m.get("memory_type", ""),
                "node_type": node_type,
                "workspace_id": m.get("workspace_id") or "",
                "thread_id": m.get("thread_id") or "",
                "account_id": m.get("account_id", ""),
                "original_uuid": m.get("original_uuid", ""),
                "created_at": m.get("created_at", datetime.now().isoformat()),
                "embedding": m.get("embedding"),
            })

        query = """
        UNWIND $nodes AS mem
        MERGE (m:MEMORY {id: mem.id, account_id: mem.account_id})
        SET m.name        = mem.name,
            m.content     = mem.content,
            m.topic       = mem.topic,
            m.category    = mem.category,
            m.memory_type = mem.memory_type,
            m.node_type   = mem.node_type,
            m.type        = mem.node_type,
            m.dataset_name = 'Agent Memories',
            m.workspace_id = mem.workspace_id,
            m.thread_id   = mem.thread_id,
            m.original_uuid = mem.original_uuid,
            m.created_at  = mem.created_at,
            m.updated_at  = toString(datetime()),
            m.embedding   = mem.embedding

        REMOVE m:USER_MEMORY
        REMOVE m:USER_MEMORY_PROACTIVE_LLM
        REMOVE m:AGENT_MEMORY
        REMOVE m:CHAT_SUMMARY
        REMOVE m:GENERAL_MEMORY

        FOREACH (x IN CASE WHEN mem.node_type = 'USER_MEMORY' THEN [1] ELSE [] END | SET m:USER_MEMORY)
        FOREACH (x IN CASE WHEN mem.node_type = 'USER_MEMORY_PROACTIVE_LLM' THEN [1] ELSE [] END | SET m:USER_MEMORY_PROACTIVE_LLM)
        FOREACH (x IN CASE WHEN mem.node_type = 'AGENT_MEMORY' THEN [1] ELSE [] END | SET m:AGENT_MEMORY)
        FOREACH (x IN CASE WHEN mem.node_type = 'CHAT_SUMMARY' THEN [1] ELSE [] END | SET m:CHAT_SUMMARY)
        FOREACH (x IN CASE WHEN mem.node_type = 'GENERAL_MEMORY' THEN [1] ELSE [] END | SET m:GENERAL_MEMORY)

        RETURN count(m) AS created
        """

        try:
            result = await self.graph_db.execute_query(query, {"nodes": formatted})
            count = result[0]["created"] if result else 0
            logger.info(f"✅ {count} nodos de memoria persistidos en Neo4j.")
            return count
        except Exception as e:
            logger.error(f"❌ Error persistiendo nodos de memoria: {e}", exc_info=True)
            raise

    async def link_memories_to_entities(
        self,
        memory_id: str,
        entity_ids: List[str],
        account_id: str,
        relationship_type: str = "MEMORY_MENTIONS",
    ) -> int:
        """
        Crea relaciones MEMORY_MENTIONS entre un nodo MEMORY y entidades existentes del grafo.
        Solo crea la relación si el nodo de entidad ya existe.
        """
        if not entity_ids:
            return 0

        pairs = [{"memory_id": memory_id, "entity_id": eid} for eid in entity_ids]
        query = f"""
        UNWIND $pairs AS pair
        MATCH (m:MEMORY {{id: pair.memory_id, account_id: $account_id}})
        MATCH (e {{id: pair.entity_id, account_id: $account_id}})
        MERGE (m)-[r:{relationship_type}]->(e)
        SET r.created_at = toString(datetime()),
            r.extraction_method = 'memory_entity_linking'
        RETURN count(r) AS created
        """
        try:
            result = await self.graph_db.execute_query(
                query, {"pairs": pairs, "account_id": account_id}
            )
            return result[0]["created"] if result else 0
        except Exception as e:
            logger.warning(f"⚠️ Error enlazando memoria {memory_id} con entidades: {e}")
            return 0

    async def get_existing_entity_ids_for_account(self, account_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Devuelve id + embedding de entidades existentes del usuario para enlazar con memorias.
        Excluye nodos que ya sean memorias (label MEMORY o id con prefijo 'memory_').
        """
        query = """
        MATCH (e {account_id: $account_id})
        WHERE NOT e:MEMORY
          AND NOT e.id STARTS WITH 'memory_'
          AND e.embedding IS NOT NULL
          AND e.id IS NOT NULL
        RETURN e.id AS id, e.embedding AS embedding, e.name AS name
        LIMIT $limit
        """
        try:
            result = await self.graph_db.execute_query(
                query, {"account_id": account_id, "limit": limit}
            )
            return result or []
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo entidades existentes: {e}")
            return []

    async def strip_memory_embeddings(self, account_id: str) -> int:
        """
        Elimina la propiedad 'embedding' de todos los nodos MEMORY del usuario.
        Los embeddings ya están guardados en pgvector/Postgres — en Neo4j solo
        se necesitan durante el pipeline de enlace. Llamar después del paso 4.
        """
        query = """
        MATCH (m:MEMORY {account_id: $account_id})
        WHERE m.embedding IS NOT NULL
        WITH collect(m) AS nodes
        FOREACH (m IN nodes | REMOVE m.embedding)
        RETURN size(nodes) AS stripped
        """
        try:
            result = await self.graph_db.execute_query(query, {"account_id": account_id})
            count = result[0]["stripped"] if result else 0
            logger.info(f"🧹 Embeddings eliminados de {count} nodos MEMORY en Neo4j.")
            return count
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando embeddings de MEMORY nodes: {e}")
            return 0

    async def cleanup_orphaned_memory_documents(self, account_id: str) -> int:
        """
        Elimina nodos SourceNode/DOCUMENT del pipeline roto que tienen id con
        prefijo 'memory_' pero NO son nodos :MEMORY (doble guardado del pipeline viejo).
        Estos causaban relaciones self-loop y duplicaban datos de memoria.
        """
        query = """
        MATCH (n {account_id: $account_id})
        WHERE n.id STARTS WITH 'memory_' AND NOT n:MEMORY
        WITH collect(n) AS nodes
        FOREACH (n IN nodes | DETACH DELETE n)
        RETURN size(nodes) AS deleted
        """
        try:
            result = await self.graph_db.execute_query(query, {"account_id": account_id})
            count = result[0]["deleted"] if result else 0
            if count > 0:
                logger.info(f"🗑️ {count} nodos DOCUMENT huérfanos de memorias eliminados de Neo4j.")
            return count
        except Exception as e:
            logger.warning(f"⚠️ Error eliminando nodos DOCUMENT huérfanos: {e}")
            return 0

    async def _add_document_mentions(self, entities: List[Dict], dataset_name: Optional[str] = None):
        """Crea relaciones MENTIONS entre documentos y entidades."""
        try:
            mentions = [
                {
                    "source_id": str(ent["source_document_id"]),
                    "target_id": str(ent["id"]),
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
                r.created_at = toString(datetime()),
                r.extraction_method = 'hybrid_mention'
            """
            await self.graph_db.execute_query(query, {"mentions": mentions})
            logger.info(f"🔗 Creadas {len(mentions)} relaciones MENTIONS entre documentos y entidades")
            
        except Exception as e:
            logger.warning(f"⚠️ Error creando relaciones MENTIONS: {e}")
