# tools/mindmap_to_graph_tool.py

"""
Herramienta que adapta MindmapGeneratorTool para también crear grafos de conocimiento en Neo4j.
Genera mapas mentales visuales Y almacena la estructura como grafo persistente.
"""

import logging
import asyncio
import json
from typing import Any, Type, Dict, List
from datetime import datetime

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importaciones existentes
from utils.document_analysis import extract_concepts_from_document
from utils.generate_mind_map import generate_mindmap_data_for_frontend
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.knowledge_models import Node, Relationship
from core.config import settings

logger = logging.getLogger(__name__)

class MindmapToGraphInput(BaseModel):
    """Esquema de entrada para la herramienta de mapa mental + grafo."""
    document_content: str = Field(
        ...,
        description="Contenido del documento para generar el mapa mental y grafo."
    )
    workspace_id: str = Field(
        default="general",
        description="ID del workspace donde almacenar el grafo."
    )
    topic_hint: str = Field(
        default="",
        description="Pista sobre el tema principal del documento."
    )
    concept_query: str = Field(
        default="temas clave y conceptos principales",
        description="Consulta para extraer conceptos específicos."
    )
    save_to_graph: bool = Field(
        default=True,
        description="Si guardar la estructura del mapa mental como grafo en Neo4j."
    )

class MindmapToGraphTool(BaseTool):
    """
    Herramienta que genera mapas mentales Y los almacena como grafos de conocimiento.
    Combina visualización con persistencia estructurada.
    """
    name: str = "mindmap_to_knowledge_graph"
    description: str = (
        "Genera un mapa mental visual a partir de un documento Y lo almacena como grafo de conocimiento. "
        "Extrae conceptos, crea estructura jerárquica visual y persiste relaciones en Neo4j. "
        "Ideal para documentos complejos que necesitan visualización y memoria estructurada."
    )
    args_schema: Type[BaseModel] = MindmapToGraphInput
    account_id: str = Field(default="", description="ID de la cuenta asociada.")
    return_direct: bool = False

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id
        self.graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )

    async def _arun(
        self,
        document_content: str,
        workspace_id: str = "general",
        topic_hint: str = "",
        concept_query: str = "temas clave y conceptos principales",
        save_to_graph: bool = True,
        **kwargs: Any
    ) -> str:
        """Ejecuta la generación de mapa mental y grafo."""
        logger.info(f"Iniciando generación de mapa mental y grafo de conocimiento...")
        
        try:
            # 1. Extraer conceptos del documento
            logger.info("Paso 1: Extrayendo conceptos del documento...")
            concepts = await extract_concepts_from_document(
                document_content, 
                concept_query, 
                topic_hint
            )
            
            if not concepts:
                return "❌ No se pudieron extraer conceptos del documento."
            
            # 2. Generar datos del mapa mental
            logger.info("Paso 2: Generando estructura del mapa mental...")
            mindmap_data = await generate_mindmap_data_for_frontend(
                concepts, 
                topic_hint if topic_hint else "Documento"
            )
            
            result = {
                "mindmap_data": mindmap_data,
                "concepts_extracted": len(concepts),
                "knowledge_graph": None
            }
            
            # 3. Crear grafo de conocimiento si se solicita
            if save_to_graph:
                logger.info("Paso 3: Creando grafo de conocimiento...")
                graph_result = await self._create_knowledge_graph(
                    concepts, mindmap_data, workspace_id, topic_hint
                )
                result["knowledge_graph"] = graph_result
            
            return self._format_result(result)
            
        except Exception as e:
            logger.error(f"Error en generación de mapa mental y grafo: {e}", exc_info=True)
            return f"❌ Error: {str(e)}"

    def _run(self, **kwargs) -> str:
        """Ejecuta la herramienta de forma síncrona."""
        try:
            return asyncio.run(self._arun(**kwargs))
        except RuntimeError as e:
            logger.warning(f"RuntimeError en _run: {e}")
            return "❌ Error: No se pudo ejecutar en modo síncrono. Use contexto asíncrono."
        except Exception as e:
            logger.error(f"Error en ejecución síncrona: {e}", exc_info=True)
            return f"❌ Error: {str(e)}"

    async def _create_knowledge_graph(
        self,
        concepts: List[Dict],
        mindmap_data: Dict,
        workspace_id: str,
        topic_hint: str
    ) -> Dict[str, Any]:
        """Crea el grafo de conocimiento a partir de los conceptos y estructura del mapa mental."""
        try:
            self.graph_db.connect()
            nodes_created = 0
            relationships_created = 0
            graph_name = f"mindmap_{self.account_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Crear nodo principal (tema central)
            central_topic = topic_hint if topic_hint else "Documento Principal"
            central_node = Node(
                label="CentralTopic",
                properties={
                    "name": central_topic,
                    "type": "central_topic",
                    "workspace_id": workspace_id,
                    "account_id": self.account_id,
                    "graph_name": graph_name,
                    "created_at": datetime.now().isoformat(),
                    "source": "mindmap_generator"
                }
            )
            self.graph_db.create_node(central_node)
            nodes_created += 1
            
            # Crear nodos para conceptos principales
            main_concepts = []
            for concept in concepts:
                concept_name = concept.get("name", concept.get("concept", ""))
                if concept_name:
                    concept_node = Node(
                        label="Concept",
                        properties={
                            "name": concept_name,
                            "description": concept.get("description", ""),
                            "importance": concept.get("importance", 0.5),
                            "category": concept.get("category", "general"),
                            "workspace_id": workspace_id,
                            "account_id": self.account_id,
                            "graph_name": graph_name,
                            "created_at": datetime.now().isoformat(),
                            "source": "mindmap_generator"
                        }
                    )
                    self.graph_db.create_node(concept_node)
                    nodes_created += 1
                    main_concepts.append(concept_name)
                    
                    # Crear relación con el tema central
                    self.graph_db.create_relationship(
                        node1_label="CentralTopic",
                        node1_property_name="name",
                        node1_property_value=central_topic,
                        relationship_type="CONTAINS",
                        node2_label="Concept",
                        node2_property_name="name",
                        node2_property_value=concept_name,
                        properties={
                            "relationship_type": "hierarchical",
                            "confidence": concept.get("importance", 0.8),
                            "workspace_id": workspace_id,
                            "account_id": self.account_id,
                            "graph_name": graph_name,
                            "created_at": datetime.now().isoformat()
                        }
                    )
                    relationships_created += 1
            
            # Crear relaciones entre conceptos relacionados
            for i, concept1 in enumerate(concepts):
                for j, concept2 in enumerate(concepts[i+1:], i+1):
                    # Crear relaciones basadas en similitud semántica o co-ocurrencia
                    if self._concepts_are_related(concept1, concept2):
                        concept1_name = concept1.get("name", concept1.get("concept", ""))
                        concept2_name = concept2.get("name", concept2.get("concept", ""))
                        
                        if concept1_name and concept2_name:
                            self.graph_db.create_relationship(
                                node1_label="Concept",
                                node1_property_name="name",
                                node1_property_value=concept1_name,
                                relationship_type="RELATED_TO",
                                node2_label="Concept",
                                node2_property_name="name",
                                node2_property_value=concept2_name,
                                properties={
                                    "relationship_type": "semantic",
                                    "confidence": 0.6,
                                    "workspace_id": workspace_id,
                                    "account_id": self.account_id,
                                    "graph_name": graph_name,
                                    "created_at": datetime.now().isoformat()
                                }
                            )
                            relationships_created += 1
            
            return {
                "status": "success",
                "graph_name": graph_name,
                "central_topic": central_topic,
                "nodes_created": nodes_created,
                "relationships_created": relationships_created,
                "main_concepts": main_concepts
            }
            
        except Exception as e:
            logger.error(f"Error creando grafo de conocimiento: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            self.graph_db.close()

    def _concepts_are_related(self, concept1: Dict, concept2: Dict) -> bool:
        """Determina si dos conceptos están relacionados."""
        # Lógica simple: si comparten palabras clave o categorías
        name1 = concept1.get("name", concept1.get("concept", "")).lower()
        name2 = concept2.get("name", concept2.get("concept", "")).lower()
        
        # Si comparten palabras (más de 2 caracteres)
        words1 = set(word for word in name1.split() if len(word) > 2)
        words2 = set(word for word in name2.split() if len(word) > 2)
        
        if words1.intersection(words2):
            return True
        
        # Si tienen la misma categoría
        if concept1.get("category") == concept2.get("category") and concept1.get("category"):
            return True
        
        return False

    def _format_result(self, result: Dict[str, Any]) -> str:
        """Formatea el resultado final para el usuario."""
        output = []
        
        output.append("🧠 **MAPA MENTAL Y GRAFO DE CONOCIMIENTO GENERADOS**")
        output.append(f"📊 **Conceptos Extraídos:** {result.get('concepts_extracted', 0)}")
        
        # Información del mapa mental
        mindmap_data = result.get("mindmap_data", {})
        if mindmap_data:
            output.append(f"🎯 **Tema Central:** {mindmap_data.get('central_topic', 'N/A')}")
            output.append(f"📝 **Nodos del Mapa:** {len(mindmap_data.get('nodes', []))}")
            output.append(f"🔗 **Enlaces del Mapa:** {len(mindmap_data.get('links', []))}")
        
        # Información del grafo de conocimiento
        graph_result = result.get("knowledge_graph")
        if graph_result:
            output.append("\n🕸️ **GRAFO DE CONOCIMIENTO**")
            if graph_result.get("status") == "success":
                output.append(f"📊 **Nombre del Grafo:** {graph_result.get('graph_name', 'N/A')}")
                output.append(f"🎯 **Tema Central:** {graph_result.get('central_topic', 'N/A')}")
                output.append(f"🔗 **Nodos Creados:** {graph_result.get('nodes_created', 0)}")
                output.append(f"↔️ **Relaciones Creadas:** {graph_result.get('relationships_created', 0)}")
                
                main_concepts = graph_result.get('main_concepts', [])
                if main_concepts:
                    output.append(f"💡 **Conceptos Principales:** {', '.join(main_concepts[:5])}")
                    if len(main_concepts) > 5:
                        output.append(f"   ... y {len(main_concepts) - 5} más")
            else:
                output.append(f"❌ **Error en Grafo:** {graph_result.get('error', 'Error desconocido')}")
        
        output.append("\n✅ **Mapa mental y grafo de conocimiento listos para usar!**")
        output.append("💡 **Tip:** Puedes consultar el grafo usando herramientas de búsqueda de Neo4j")
        
        return "\n".join(output)
