# knowledge_graph/cognee_integration.py
"""
Integración real con Cognee para grafos de conocimiento.
Utiliza la biblioteca cognee instalada via pip.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

# Importar Cognee real
try:
    import cognee
    COGNEE_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Cognee library imported successfully")
except ImportError as e:
    COGNEE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Failed to import Cognee: {e}")

# Importar adaptador híbrido
try:
    from .hybrid_cognee_adapter import HybridCogneeAdapter
    HYBRID_ADAPTER_AVAILABLE = True
    logger.info("✅ HybridCogneeAdapter disponible")
except ImportError as e:
    HYBRID_ADAPTER_AVAILABLE = False
    logger.warning(f"⚠️ HybridCogneeAdapter no disponible: {e}")

from core.config import settings
from knowledge_graph.graph_database import GraphDB
from core.llm_manager import get_main_llm, get_fast_llm  # Comentado temporalmente

class CogneeIntegration:
    def __init__(self, graph_db: GraphDB):
        """
        Integración real con Cognee para procesamiento semántico avanzado.

        Args:
            graph_db (GraphDB): Una instancia de la clase GraphDB.
        """
        self.graph_db = graph_db
        self.cognee_available = COGNEE_AVAILABLE
        self.hybrid_adapter = None

        if self.cognee_available:
            logger.info("✅ CogneeIntegration inicializada con Cognee real")
            # Configurar Cognee con las credenciales del proyecto
            self._configure_cognee()
        else:
            logger.warning("⚠️ CogneeIntegration inicializada en modo fallback (sin Cognee)")

        # Inicializar adaptador híbrido si está disponible
        if HYBRID_ADAPTER_AVAILABLE:
            self.hybrid_adapter = HybridCogneeAdapter(graph_db)
            logger.info("✅ HybridCogneeAdapter inicializado")

    def _configure_cognee(self):
        """Configura Cognee con las credenciales y configuración del proyecto."""
        try:
            # Usar el LLM manager de Kognito en lugar de configurar Cognee directamente
            main_llm = get_main_llm()
            if main_llm:
                logger.info("✅ Usando LLM manager de Kognito para Cognee")
                # Configurar Cognee para usar Gemini a través de nuestro LLM manager
                if hasattr(settings, 'google_api_key') and settings.google_api_key:
                    cognee.config.set_llm_provider("gemini")
                    cognee.config.set_llm_api_key(settings.google_api_key)
                    cognee.config.set_llm_model("gemini-2.0-flash")
                    logger.info("✅ Cognee configurado con Gemini (gemini-2.0-flash) - LLM manager integrado")
                else:
                    logger.warning("⚠️ No se encontró API key de Gemini")
            else:
                logger.warning("⚠️ LLM manager no inicializado, usando configuración por defecto")

            logger.info("✅ Cognee configurado correctamente")
        except Exception as e:
            logger.error(f"❌ Error configurando Cognee: {e}")
            self.cognee_available = False

    async def process_documents(self, documents: List[Dict[str, Any]], dataset_name: str = "default") -> Dict[str, Any]:
        """
        Procesa documentos usando Cognee real para extraer entidades y relaciones.

        Args:
            documents: Lista de documentos a procesar
            dataset_name: Nombre del dataset

        Returns:
            Dict con entidades y relaciones extraídas
        """
        if not self.cognee_available:
            return await self._fallback_processing(documents, dataset_name)

        logger.info(f"🧠 Procesando {len(documents)} documentos con Cognee real")

        try:
            # Preparar documentos para Cognee
            cognee_docs = []
            for doc in documents:
                cognee_docs.append({
                    "id": doc.get("id", f"doc_{len(cognee_docs)}"),
                    "text": doc.get("content", ""),
                    "metadata": doc.get("metadata", {})
                })

            # Añadir documentos a Cognee
            await cognee.add(cognee_docs, dataset_name=dataset_name)

            # Procesar documentos (cognify)
            await cognee.cognify(dataset_name=dataset_name)

            # Obtener el grafo generado
            graph_data = await cognee.search.graph(dataset_name=dataset_name)

            # Convertir el formato de Cognee a nuestro formato
            entities, relationships = self._convert_cognee_graph(graph_data)

            return {
                "entities": entities,
                "relationships": relationships,
                "dataset_name": dataset_name,
                "status": "processed",
                "method": "cognee_real",
                "processed_at": datetime.now().isoformat(),
                "cognee_graph_data": graph_data
            }

        except Exception as e:
            logger.error(f"❌ Error procesando con Cognee: {e}")
            # Fallback a procesamiento básico
            return await self._fallback_processing(documents, dataset_name)

    async def _fallback_processing(self, documents: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
        """
        Procesamiento básico de fallback cuando Cognee no está disponible.
        """
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

    def _convert_cognee_graph(self, graph_data: Dict) -> tuple[List[Dict], List[Dict]]:
        """
        Convierte el formato de grafo de Cognee a nuestro formato estándar.

        Args:
            graph_data: Datos del grafo de Cognee

        Returns:
            Tupla con (entidades, relaciones)
        """
        entities = []
        relationships = []

        # Procesar nodos (entidades)
        nodes = graph_data.get("nodes", [])
        for node in nodes:
            entity = {
                "type": node.get("type", "Entity"),
                "properties": {
                    "name": node.get("name", node.get("id", "Unknown")),
                    "cognee_id": node.get("id"),
                    "source": "cognee",
                    "created_at": datetime.now().isoformat(),
                    **node.get("properties", {})
                }
            }
            entities.append(entity)

        # Procesar aristas (relaciones)
        edges = graph_data.get("edges", [])
        for edge in edges:
            relationship = {
                "source": edge.get("source"),
                "source_type": "Entity",  # Se puede mejorar con tipo específico
                "target": edge.get("target"),
                "target_type": "Entity",
                "type": edge.get("type", "RELATED_TO"),
                "confidence": edge.get("weight", 1.0),
                "cognee_id": edge.get("id"),
                "properties": edge.get("properties", {})
            }
            relationships.append(relationship)

        return entities, relationships

    async def search_knowledge_graph(self, query: str, dataset_name: str = "default") -> Dict[str, Any]:
        """
        Busca en el grafo de conocimiento usando Cognee.

        Args:
            query: Consulta de búsqueda
            dataset_name: Nombre del dataset

        Returns:
            Resultados de la búsqueda
        """
        if not self.cognee_available:
            return {
                "query": query,
                "dataset_name": dataset_name,
                "results": [],
                "status": "search_unavailable",
                "method": "fallback",
                "searched_at": datetime.now().isoformat()
            }

        try:
            # Buscar usando Cognee
            search_results = await cognee.search(query, dataset_name=dataset_name)

            return {
                "query": query,
                "dataset_name": dataset_name,
                "results": search_results,
                "status": "search_completed",
                "method": "cognee_real",
                "searched_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Error en búsqueda con Cognee: {e}")
            return {
                "query": query,
                "dataset_name": dataset_name,
                "results": [],
                "status": "search_error",
                "error": str(e),
                "method": "cognee_real",
                "searched_at": datetime.now().isoformat()
            }

    def convert_graph_to_pddl(self, domain_name="default_domain"):
        """
        Convierte el conocimiento en la base de datos de grafos a formato PDDL.

        Esta función consulta la base de datos de grafos para obtener todos los nodos y relaciones,
        y los convierte a formato PDDL para que Cognee pueda entenderlos.

        Args:
            domain_name (str): El nombre del dominio PDDL.

        Returns:
            dict: Un diccionario con las definiciones del dominio y el problema en formato PDDL.
        """
        try:
            #  Obtener todos los nodos y relaciones de la base de datos de grafos
            nodes_query = "MATCH (n) RETURN n"
            relationships_query = "MATCH (n1)-[r]->(n2) RETURN n1, type(r) as relation, n2"

            nodes = self.graph_db.execute_query(nodes_query)
            relationships = self.graph_db.execute_query(relationships_query)

            #  Construir las definiciones PDDL
            domain_definition = f"""
            (define (domain {domain_name})
                (:requirements :strips :typing)
                (:types concept) ;  Define el tipo 'concept'
                (:predicates
                    (is-a ?x - concept)
                    (related ?x - concept ?y - concept)
                )
                ; Aquí puedes agregar acciones si las tienes
            )
            """

            problem_definition = f"""
            (define (problem problem1)
                (:domain {domain_name})
                (:objects
                    ;  Lista de objetos (nodos)
                    {' '.join([f"{node['n']['properties']['nombre']} - concept" for node in nodes])}
                )
                (:init
                    ;  Hechos iniciales (relaciones y propiedades)
                    {' '.join([f"(is-a {node['n']['properties']['nombre']})" for node in nodes])}
                    {' '.join([f"(related {rel['n1']['properties']['nombre']} {rel['n2']['properties']['nombre']})" for rel in relationships])}
                )
                (:goal
                    ;  Define tu objetivo aquí
                    (and (objetivo-alcanzado)) ;  Ejemplo de objetivo
                )
            )
            """

            return {"domain": domain_definition, "problem": problem_definition}

        except Exception as e:
            logger.error(f"Error al convertir el grafo a PDDL: {e}", exc_info=True)
            raise

    def execute_plan(self, domain_file, problem_file):
        """
        Ejecuta un plan en Cognee.

        Args:
            domain_file (str): El contenido del archivo de dominio PDDL.
            problem_file (str): El contenido del archivo de problema PDDL.

        Returns:
            dict: La respuesta simulada del plan.
        """
        try:
            # Simulación de ejecución de plan - se puede implementar con Cognee real
            logger.info("🔄 Ejecutando plan PDDL (simulado)")
            return {
                "status": "ok",
                "plan": ["accion_1", "accion_2", "accion_3"],
                "message": "Plan ejecutado exitosamente (simulado)"
            }
        except Exception as e:
            logger.error(f"Error al ejecutar el plan en Cognee: {e}", exc_info=True)
            raise

    def integrate_cognee_results(self, plan_result):
        """
        Integra los resultados de Cognee en la base de datos de grafos.

        Args:
            plan_result (dict): El resultado del plan de Cognee.
        """
        try:
            #  Analizar el resultado del plan y actualizar la base de datos de grafos
            #  (Este es un ejemplo, debes adaptarlo a tus necesidades específicas)
            if plan_result and plan_result['status'] == 'ok':
                for action in plan_result['plan']:
                    logger.info(f"Ejecutando acción: {action}")
                    #  Aquí puedes agregar código para actualizar la base de datos de grafos
                    #  basado en las acciones del plan
            else:
                logger.warning("El plan no se ejecutó correctamente.")

        except Exception as e:
            logger.error(f"Error al integrar los resultados de Cognee: {e}", exc_info=True)
            raise

# Ejemplo de uso (puedes mover esto a otro archivo para pruebas):
if __name__ == '__main__':
    #  Configura las variables de entorno
    cognee_api_url = settings.cognee_api_url
    neo4j_uri = settings.neo4j_uri
    neo4j_user = settings.neo4j_user
    neo4j_password = settings.neo4j_password

    #  Inicializa la base de datos de grafos
    graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
    try:

        graph_db.connect()
        #  Inicializa la integración con Cognee
        cognee_integration = CogneeIntegration(cognee_api_url, graph_db)

        #  Convierte el grafo a PDDL
        pddl_data = cognee_integration.convert_graph_to_pddl()
        print(f"Definiciones PDDL: {pddl_data}")

        #  Ejecuta un plan (simulado)
        #  En este ejemplo, simplemente mostramos las definiciones PDDL
        #  En un caso real, enviarías estas definiciones a la API de Cognee
        # plan_result = cognee_integration.execute_plan(pddl_data['domain'], pddl_data['problem'])
        # print(f"Resultado del plan: {plan_result}")

        #  Integra los resultados de Cognee (simulado)
        #  En este ejemplo, simplemente mostramos un mensaje
        #  En un caso real, analizarías el resultado del plan y actualizarías la base de datos de grafos
        # cognee_integration.integrate_cognee_results(plan_result)
        print("Integración con Cognee completada (simulada).")

    except Exception as e:
        print(f"Ocurrió un error durante la ejecución: {e}")
    finally:
        graph_db.close()  #  Cierra la conexión a la base de datos de grafos