# tools/text_to_knowledge_graph_tool.py

"""
Herramienta híbrida que combina análisis de texto con generación de grafos de conocimiento.
Adapta la funcionalidad existente de AnalyzeTextForInsightsTool para también crear grafos.
"""

import logging
import asyncio
import json
from typing import Any, Type, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importaciones existentes
from utils.advanced_text_analyzer import text_analyzer, SingleTextAnalysis
from tools.knowledge_graph_tool import knowledge_graph_tool, extract_entities_from_text_analysis
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.knowledge_models import Node, Relationship
from core.config import settings

logger = logging.getLogger(__name__)

class TextToKnowledgeGraphInput(BaseModel):
    """Define el esquema de entrada para la herramienta híbrida."""
    text: str = Field(
        ...,
        description="El texto que se va a analizar y convertir en grafo de conocimiento."
    )
    workspace_id: str = Field(
        default="general",
        description="ID del workspace donde almacenar el grafo."
    )
    graph_name: str = Field(
        default="",
        description="Nombre opcional para el grafo. Si no se proporciona, se genera automáticamente."
    )
    create_graph: bool = Field(
        default=True,
        description="Si crear el grafo de conocimiento además del análisis de texto."
    )
    use_cognee: bool = Field(
        default=False,
        description="Si usar Cognee para procesamiento semántico avanzado."
    )

class TextToKnowledgeGraphTool(BaseTool):
    """
    Herramienta híbrida que realiza análisis de texto Y genera grafos de conocimiento.
    Combina la funcionalidad de AnalyzeTextForInsightsTool con generación de grafos.
    """
    name: str = "text_to_knowledge_graph"
    description: str = (
        "Herramienta avanzada que analiza texto en profundidad Y crea un grafo de conocimiento. "
        "Extrae resumen, temas, sentimiento, entidades y relaciones. Almacena todo en Neo4j. "
        "Ideal para procesar documentos importantes y crear memoria estructurada."
    )
    args_schema: Type[BaseModel] = TextToKnowledgeGraphInput
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
        text: str,
        workspace_id: str = "general",
        graph_name: str = "",
        create_graph: bool = True,
        use_cognee: bool = False,
        **kwargs: Any
    ) -> str:
        """Ejecuta el análisis híbrido de texto y creación de grafo."""
        logger.info(f"Iniciando análisis híbrido de texto y creación de grafo...")
        
        try:
            # 1. Análisis de texto tradicional
            logger.info("Paso 1: Analizando texto con AdvancedTextAnalyzer...")
            analysis_result = await text_analyzer.analyze_single_text(
                text, 
                document_title=f"Texto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            result = {
                "text_analysis": self._format_text_analysis(analysis_result),
                "knowledge_graph": None
            }
            
            # 2. Crear grafo de conocimiento si se solicita
            if create_graph:
                logger.info("Paso 2: Creando grafo de conocimiento...")
                
                if not graph_name:
                    graph_name = f"text_graph_{self.account_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                if use_cognee:
                    # Usar Cognee para procesamiento avanzado
                    graph_result = await self._create_graph_with_cognee(
                        text, graph_name, workspace_id
                    )
                else:
                    # Usar extracción directa de entidades
                    graph_result = await self._create_graph_direct(
                        analysis_result, graph_name, workspace_id
                    )
                
                result["knowledge_graph"] = graph_result
            
            return self._format_final_result(result)
            
        except Exception as e:
            logger.error(f"Error en análisis híbrido: {e}", exc_info=True)
            return f"Error en el análisis híbrido: {str(e)}"

    def _run(self, **kwargs) -> str:
        """Ejecuta la herramienta de forma síncrona."""
        try:
            return asyncio.run(self._arun(**kwargs))
        except RuntimeError as e:
            logger.warning(f"RuntimeError en _run: {e}")
            return "Error: No se pudo ejecutar en modo síncrono. Use contexto asíncrono."
        except Exception as e:
            logger.error(f"Error en ejecución síncrona: {e}", exc_info=True)
            return f"Error en el análisis: {str(e)}"

    async def _create_graph_with_cognee(
        self, 
        text: str, 
        graph_name: str, 
        workspace_id: str
    ) -> Dict[str, Any]:
        """Crea grafo usando Cognee para procesamiento semántico."""
        try:
            # Simular documento para Cognee
            documents = [{
                "id": f"text_{datetime.now().timestamp()}",
                "content": text,
                "metadata": {
                    "account_id": self.account_id,
                    "workspace_id": workspace_id,
                    "type": "text_input"
                }
            }]
            
            # Usar la herramienta de knowledge_graph existente
            result = await knowledge_graph_tool.create_knowledge_graph_from_documents(
                document_ids=[documents[0]["id"]],
                workspace_id=workspace_id,
                account_id=self.account_id,
                graph_name=graph_name
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error creando grafo con Cognee: {e}")
            return {"status": "error", "error": str(e)}

    async def _create_graph_direct(
        self, 
        analysis_result: SingleTextAnalysis, 
        graph_name: str, 
        workspace_id: str
    ) -> Dict[str, Any]:
        """Crea grafo directamente desde el análisis de texto."""
        try:
            # Convertir análisis a formato de entidades
            analysis_dict = {
                "key_themes": getattr(analysis_result, 'key_themes', []),
                "summary": getattr(analysis_result, 'summary', ''),
                "sentiment": getattr(analysis_result, 'sentiment', 'neutral'),
                "tone": getattr(analysis_result, 'tone', 'neutral')
            }
            
            entities_relations = await extract_entities_from_text_analysis(analysis_dict)
            
            # Almacenar en Neo4j
            self.graph_db.connect()
            nodes_created = 0
            relationships_created = 0
            
            try:
                # Crear nodos
                for entity in entities_relations.get("entities", []):
                    node = Node(
                        label=entity.get("type", "Entity"),
                        properties={
                            **entity.get("properties", {}),
                            "workspace_id": workspace_id,
                            "account_id": self.account_id,
                            "graph_name": graph_name,
                            "created_at": datetime.now().isoformat(),
                            "source": "direct_analysis"
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
                            "account_id": self.account_id,
                            "graph_name": graph_name,
                            "created_at": datetime.now().isoformat()
                        }
                    )
                    relationships_created += 1
                
                return {
                    "status": "success",
                    "method": "direct_analysis",
                    "graph_name": graph_name,
                    "nodes_created": nodes_created,
                    "relationships_created": relationships_created,
                    "entities": entities_relations.get("entities", []),
                    "relationships": entities_relations.get("relationships", [])
                }
                
            finally:
                self.graph_db.close()
                
        except Exception as e:
            logger.error(f"Error creando grafo directo: {e}")
            return {"status": "error", "error": str(e)}

    def _format_text_analysis(self, analysis_result: SingleTextAnalysis) -> Dict[str, Any]:
        """Formatea el resultado del análisis de texto."""
        return {
            "summary": getattr(analysis_result, 'summary', ''),
            "key_themes": getattr(analysis_result, 'key_themes', []),
            "sentiment": getattr(analysis_result, 'sentiment', 'neutral'),
            "tone": getattr(analysis_result, 'tone', 'neutral'),
            "knowledge_gaps": getattr(analysis_result, 'knowledge_gaps', []),
            "word_count": len(getattr(analysis_result, 'original_text', '').split()) if hasattr(analysis_result, 'original_text') else 0
        }

    def _format_final_result(self, result: Dict[str, Any]) -> str:
        """Formatea el resultado final para el usuario."""
        output = []
        
        # Análisis de texto
        text_analysis = result.get("text_analysis", {})
        output.append("📊 **ANÁLISIS DE TEXTO COMPLETADO**")
        output.append(f"📝 **Resumen:** {text_analysis.get('summary', 'N/A')}")
        output.append(f"🎯 **Temas Clave:** {', '.join(text_analysis.get('key_themes', []))}")
        output.append(f"😊 **Sentimiento:** {text_analysis.get('sentiment', 'N/A')}")
        output.append(f"🎵 **Tono:** {text_analysis.get('tone', 'N/A')}")
        
        # Grafo de conocimiento
        graph_result = result.get("knowledge_graph")
        if graph_result:
            output.append("\n🕸️ **GRAFO DE CONOCIMIENTO CREADO**")
            if graph_result.get("status") == "success":
                output.append(f"📊 **Nombre del Grafo:** {graph_result.get('graph_name', 'N/A')}")
                output.append(f"🔗 **Nodos Creados:** {graph_result.get('nodes_created', 0)}")
                output.append(f"↔️ **Relaciones Creadas:** {graph_result.get('relationships_created', 0)}")
                output.append(f"⚙️ **Método:** {graph_result.get('method', 'N/A')}")
            else:
                output.append(f"❌ **Error:** {graph_result.get('error', 'Error desconocido')}")
        
        output.append("\n✅ **Análisis híbrido completado exitosamente!**")
        return "\n".join(output)
