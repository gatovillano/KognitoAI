# core/tools/knowledge_graph_tool.py
"""
Tool para crear y gestionar grafos de conocimiento usando Cognee.
Integra tanto la base de datos relacional como la de grafos.
"""

import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from core.config import settings
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.knowledge_models import Node, Relationship
from knowledge_graph.cognee_integration import CogneeIntegration

logger = logging.getLogger(__name__)

class KnowledgeGraphTool(BaseModel):
    """
    Tool para crear grafos de conocimiento usando Cognee y Neo4j.
    Implementa un enfoque híbrido: datos relacionales + grafos.
    """
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self):
        super().__init__()
        self.cognee_url = settings.cognee_api_url
        self.graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        
    async def create_knowledge_graph_from_documents(
        self,
        document_ids: List[str],
        workspace_id: str,
        account_id: str,
        graph_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Crea un grafo de conocimiento a partir de documentos.
        
        Args:
            document_ids: IDs de documentos en la base relacional
            workspace_id: ID del workspace
            account_id: ID de la cuenta
            graph_name: Nombre del grafo a crear
            
        Returns:
            Dict con el resultado de la operación
        """
        try:
            # 1. Obtener documentos de la base relacional
            documents = await self._get_documents_from_db(document_ids, account_id)
            
            # 2. Enviar documentos a Cognee para procesamiento
            cognee_result = await self._process_with_cognee(documents, graph_name)
            
            # 3. Extraer entidades y relaciones de Cognee
            entities_relations = await self._extract_entities_from_cognee(cognee_result)
            
            # 4. Almacenar en Neo4j para consultas rápidas
            neo4j_result = await self._store_in_neo4j(entities_relations, workspace_id, account_id)
            
            # 5. Crear índices y metadatos en base relacional
            metadata_result = await self._create_graph_metadata(
                graph_name, workspace_id, account_id, document_ids
            )
            
            return {
                "status": "success",
                "graph_name": graph_name,
                "cognee_result": cognee_result,
                "neo4j_nodes": neo4j_result.get("nodes_created", 0),
                "neo4j_relationships": neo4j_result.get("relationships_created", 0),
                "metadata": metadata_result
            }
            
        except Exception as e:
            logger.error(f"Error creando grafo de conocimiento: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _get_documents_from_db(self, document_ids: List[str], account_id: str) -> List[Dict]:
        """Obtiene documentos de la base de datos relacional."""
        # Aquí conectarías con tu base PostgreSQL
        # Por ahora, simulamos la respuesta
        return [
            {
                "id": doc_id,
                "content": f"Contenido del documento {doc_id}",
                "metadata": {"account_id": account_id}
            }
            for doc_id in document_ids
        ]
    
    async def _process_with_cognee(self, documents: List[Dict], graph_name: str) -> Dict:
        """Procesa documentos usando la integración real de Cognee."""
        try:
            # Usar integración real con Cognee
            cognee_integration = CogneeIntegration(self.graph_db)

            # Procesar documentos
            result = await cognee_integration.process_documents(documents, graph_name)

            return {
                "status": "success",
                "method": result.get("method", "cognee_real"),
                "entities_count": len(result.get("entities", [])),
                "relationships_count": len(result.get("relationships", [])),
                "dataset_name": graph_name,
                "processed_at": result.get("processed_at"),
                "cognee_available": cognee_integration.cognee_available
            }

        except Exception as e:
            logger.error(f"Error procesando con Cognee: {e}")
            return {
                "status": "error",
                "error": str(e),
                "method": "cognee_real"
            }
    
    async def _extract_entities_from_cognee(self, cognee_result: Dict) -> Dict:
        """Extrae entidades y relaciones del resultado de Cognee."""
        # Si Cognee procesó correctamente, usar sus resultados
        if cognee_result.get("method") == "cognee_real":
            return {
                "entities": cognee_result.get("entities", []),
                "relationships": cognee_result.get("relationships", []),
                "source": "cognee_real"
            }

        # Si fue fallback, usar los resultados básicos
        return {
            "entities": cognee_result.get("entities", []),
            "relationships": cognee_result.get("relationships", []),
            "source": "fallback"
        }
    
    async def _store_in_neo4j(self, entities_relations: Dict, workspace_id: str, account_id: str) -> Dict:
        """Almacena entidades y relaciones en Neo4j."""
        try:
            self.graph_db.connect()
            
            nodes_created = 0
            relationships_created = 0
            
            # Crear nodos
            for entity in entities_relations.get("entities", []):
                node = Node(
                    label=entity.get("type", "Entity"),
                    properties={
                        **entity.get("properties", {}),
                        "workspace_id": workspace_id,
                        "account_id": account_id,
                        "source": "cognee"
                    }
                )
                self.graph_db.create_node(node)
                nodes_created += 1
            
            # Crear relaciones
            for relation in entities_relations.get("relationships", []):
                self.graph_db.create_relationship(
                    node1_label=relation["source_type"],
                    node1_property_name="name",
                    node1_property_value=relation["source"],
                    relationship_type=relation["type"],
                    node2_label=relation["target_type"],
                    node2_property_name="name",
                    node2_property_value=relation["target"],
                    properties={
                        "confidence": relation.get("confidence", 1.0),
                        "workspace_id": workspace_id,
                        "account_id": account_id
                    }
                )
                relationships_created += 1
            
            return {
                "nodes_created": nodes_created,
                "relationships_created": relationships_created
            }
            
        finally:
            self.graph_db.close()
    
    async def _create_graph_metadata(self, graph_name: str, workspace_id: str, account_id: str, document_ids: List[str]) -> Dict:
        """Crea metadatos del grafo en la base relacional."""
        # Aquí guardarías metadatos en PostgreSQL
        return {
            "graph_id": f"{account_id}_{workspace_id}_{graph_name}",
            "created_at": "2024-01-01T00:00:00Z",
            "document_count": len(document_ids),
            "status": "active"
        }
    
    async def search_knowledge_graph(
        self,
        query: str,
        graph_name: str,
        account_id: str,
        search_type: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Busca en el grafo de conocimiento.
        
        Args:
            query: Consulta de búsqueda
            graph_name: Nombre del grafo
            account_id: ID de la cuenta
            search_type: "cognee", "neo4j", o "hybrid"
        """
        try:
            results = {}
            
            if search_type in ["cognee", "hybrid"]:
                # Búsqueda semántica con Cognee real
                try:
                    cognee_integration = CogneeIntegration(self.graph_db)
                    cognee_results = await cognee_integration.search_knowledge_graph(query, graph_name)
                    results["cognee_results"] = cognee_results
                except Exception as e:
                    logger.warning(f"Error en búsqueda Cognee: {e}")
                    results["cognee_results"] = {"error": str(e)}
            
            if search_type in ["neo4j", "hybrid"]:
                # Búsqueda estructural con Neo4j
                self.graph_db.connect()
                try:
                    cypher_query = f"""
                    MATCH (n)-[r]-(m)
                    WHERE n.account_id = $account_id
                    AND (toLower(n.name) CONTAINS toLower($query) 
                         OR toLower(m.name) CONTAINS toLower($query))
                    RETURN n, r, m
                    LIMIT 20
                    """
                    neo4j_results = self.graph_db.execute_query(
                        cypher_query,
                        {"query": query, "account_id": account_id}
                    )
                    results["neo4j_results"] = neo4j_results
                finally:
                    self.graph_db.close()
            
            return {
                "status": "success",
                "query": query,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

# Instancia global de la tool
knowledge_graph_tool = KnowledgeGraphTool()

# Función de utilidad para integrar con herramientas existentes
async def extract_entities_from_text_analysis(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae entidades y relaciones de un resultado de análisis de texto.
    Útil para integrar con AnalyzeTextForInsightsTool.
    """
    entities = []
    relationships = []

    # Extraer entidades de los temas clave
    if "key_themes" in analysis_result:
        for theme in analysis_result["key_themes"]:
            entities.append({
                "type": "Theme",
                "properties": {
                    "name": theme,
                    "category": "key_theme",
                    "source": "text_analysis"
                }
            })

    # Extraer entidades del resumen
    if "summary" in analysis_result:
        # Aquí podrías usar NLP para extraer entidades nombradas del resumen
        # Por simplicidad, creamos una entidad del documento
        entities.append({
            "type": "Document",
            "properties": {
                "name": "Documento Analizado",
                "summary": analysis_result["summary"],
                "sentiment": analysis_result.get("sentiment", "neutral"),
                "tone": analysis_result.get("tone", "neutral"),
                "source": "text_analysis"
            }
        })

    # Crear relaciones entre el documento y los temas
    if entities:
        doc_entity = next((e for e in entities if e["type"] == "Document"), None)
        if doc_entity:
            for entity in entities:
                if entity["type"] == "Theme":
                    relationships.append({
                        "source": doc_entity["properties"]["name"],
                        "source_type": "Document",
                        "target": entity["properties"]["name"],
                        "target_type": "Theme",
                        "type": "CONTAINS_THEME",
                        "confidence": 0.8
                    })

    return {
        "entities": entities,
        "relationships": relationships
    }
