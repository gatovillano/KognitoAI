# knowledge_graph/cognee_integration.py
"""
Integración real con Cognee para grafos de conocimiento.
Utiliza la biblioteca cognee instalada via pip.
"""

import logging
import os
import numpy as np
from typing import Dict, Any, List, Optional, Literal
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

# Usar Neo4jAdapter directamente (más confiable que HybridCogneeAdapter)
logger.info("✅ Usando Neo4jAdapter para pipeline híbrido")

from core.config import settings
from knowledge_graph.graph_database import GraphDB
from core.llm_manager import get_main_llm, get_fast_llm
from utils.embeddings import get_embedding_model
from core.memory_manager import get_full_document_content
from knowledge_graph.hybrid_graph_processor import HybridGraphProcessor

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
        self.hybrid_processor = HybridGraphProcessor()

        if self.cognee_available:
            logger.info("✅ CogneeIntegration inicializada con Cognee real")
            # Configurar Cognee con las credenciales del proyecto
            self._configure_cognee()
            
            # Asegurarse de que el dataset exista antes de usarlo
            # try:
            #     import cognee.modules.data as data
            #     # Esta es una llamada síncrona, pero la ejecutamos en el constructor
            #     # que es síncrono. Si se mueve a un método asíncrono, usar asyncio.to_thread
            #     data.add_dataset("default")
            #     logger.info("✅ Dataset 'default' de Cognee asegurado.")
            # except Exception as e:
            #     # Es posible que la función falle si el dataset ya existe,
            #     # lo cual es un comportamiento esperado y no un error crítico.
            #     logger.warning(f"⚠️ No se pudo asegurar el dataset 'default' de Cognee (puede que ya exista): {e}")

        else:
            logger.warning("⚠️ CogneeIntegration inicializada en modo fallback (sin Cognee)")

        # Usar Neo4jAdapter directamente (más confiable)
        from knowledge_graph.neo4j_adapter import Neo4jAdapter
        self.hybrid_adapter = Neo4jAdapter(graph_db)
        logger.info("✅ Neo4jAdapter inicializado para pipeline híbrido")

    async def _create_fulltext_indexes(self):
        """Asegura que los índices full-text necesarios existan en Neo4j."""
        try:
            logger.info("🔍 Verificando y creando índices full-text en Neo4j...")

            # Índice para nodos (CONCEPTUAL_QUOTE y IDEA_PROFILE)
            node_index_query = """
            CREATE FULLTEXT INDEX node_fulltext_index IF NOT EXISTS
            FOR (n:CONCEPTUAL_QUOTE | IDEA_PROFILE)
            ON EACH [n.name, n.description, n.concept, n.full_text, n.category]
            """
            await self.graph_db.execute_query(node_index_query)
            logger.info("✅ Índice 'node_fulltext_index' para nodos asegurado.")

            # Índice para relaciones (THEMATIC_RELATIONSHIP y CONTAINS_IDEA)
            relationship_index_query = """
            CREATE FULLTEXT INDEX relationship_fulltext_index IF NOT EXISTS
            FOR ()-[r:THEMATIC_RELATIONSHIP | CONTAINS_IDEA]-()
            ON EACH [r.description]
            """
            await self.graph_db.execute_query(relationship_index_query)
            logger.info("✅ Índice 'relationship_fulltext_index' para relaciones asegurado.")

        except Exception as e:
            logger.error(f"❌ Error creando índices full-text: {e}", exc_info=True)
            # No relanzar la excepción para no detener la inicialización

    def _configure_cognee(self):
        """Configura Cognee con las credenciales y configuración del proyecto."""
        try:
            # Usar el LLM manager de Kognito en lugar de configurar Cognee directamente
            main_llm = get_main_llm()
            if main_llm:
                logger.info("✅ Usando LLM manager de Kognito para Cognee")
                # Configurar Cognee para usar Google AI Studio (no Vertex AI)
                if hasattr(settings, 'google_api_key') and settings.google_api_key:
                    # Configurar LLM para Google AI Studio con formato correcto de LiteLLM
                    cognee.config.set_llm_provider("gemini")  # Correcto para Google AI Studio
                    cognee.config.set_llm_api_key(settings.google_api_key)
                    cognee.config.set_llm_model(f"gemini/{settings.google_main_model_name}")  # Prefijo para Google AI Studio

                    # Configurar embeddings para usar Ollama según la documentación oficial de Cognee
                    try:
                        # Configuración de embeddings para Ollama según docs oficiales
                        os.environ["EMBEDDING_PROVIDER"] = "ollama"
                        os.environ["EMBEDDING_MODEL"] = settings.ollama_embedding_model
                        os.environ["EMBEDDING_ENDPOINT"] = f"{settings.ollama_api_url}/api/embeddings"
                        os.environ["EMBEDDING_DIMENSIONS"] = "384"  # Para all-minilm:latest
                        os.environ["HUGGINGFACE_TOKENIZER"] = "sentence-transformers/all-MiniLM-L6-v2"

                        # Configuración para evitar problemas de permisos
                        os.environ["COGNEE_ENV"] = "local"
                        os.environ["COGNEE_AUTH_DISABLED"] = "true"

                        # Variables adicionales para Google AI Studio (no Vertex AI)
                        # Usar el formato correcto de LiteLLM para Google AI Studio
                        os.environ["LLM_PROVIDER"] = "gemini"
                        os.environ["LLM_API_KEY"] = settings.google_api_key
                        os.environ["LLM_MODEL"] = f"gemini/{settings.google_main_model_name}"  # Prefijo para Google AI Studio

                        # Variables específicas de LiteLLM para Google AI Studio
                        os.environ["GEMINI_API_KEY"] = settings.google_api_key
                        os.environ["GOOGLE_AI_STUDIO_API_KEY"] = settings.google_api_key

                        # Configurar timeouts más largos para documentos grandes
                        os.environ["LITELLM_REQUEST_TIMEOUT"] = "300"  # 5 minutos
                        os.environ["LITELLM_MAX_RETRIES"] = "3"
                        os.environ["LITELLM_RETRY_DELAY"] = "10"  # 10 segundos entre reintentos

                        # Configurar rate limiting para Google AI Studio (tier gratuito)
                        os.environ["LITELLM_RPM"] = "10"  # 10 requests por minuto (bajo el límite de 15)
                        os.environ["LITELLM_TPM"] = "50000"  # 50k tokens por minuto
                        os.environ["LITELLM_REQUEST_DELAY"] = "6"  # 6 segundos entre requests (10 req/min)

                        # Configurar límites de respuesta para evitar JSON truncado
                        os.environ["LITELLM_MAX_TOKENS"] = "5000"  # Limitar respuesta a 2k tokens
                        os.environ["COGNEE_MAX_OUTPUT_LENGTH"] = "40000"  # Máximo 4k caracteres de salida

                        logger.info(f"✅ Cognee configurado con Google AI Studio")
                        logger.info(f"📱 Modelo LLM: {settings.google_main_model_name}")
                        logger.info(f"✅ Embeddings configurados para Ollama: {settings.ollama_embedding_model}")
                        logger.info(f"📝 Endpoint de embeddings: {settings.ollama_api_url}/api/embeddings")
                        logger.info(f"🔓 Autenticación de Cognee deshabilitada para uso local")
                    except Exception as embed_error:
                        logger.warning(f"⚠️ Error configurando embeddings de Cognee: {embed_error}")
                else:
                    logger.warning("⚠️ No se encontró API key de Gemini")
            else:
                logger.warning("⚠️ LLM manager no inicializado, usando configuración por defecto")

            # Verificar que el modelo de embeddings global esté disponible
            embedding_model = get_embedding_model()
            if embedding_model:
                logger.info("✅ Modelo de embeddings global disponible para Cognee")
            else:
                logger.warning("⚠️ Modelo de embeddings global no inicializado")

            # Añadir log para verificar la configuración de Neo4j de Cognee
            logger.info(f"DEBUG Cognee Neo4j Config: URI={os.environ.get('NEO4J_URI')}, User={os.environ.get('NEO4J_USER')}, Password set={bool(os.environ.get('NEO4J_PASSWORD'))}")

            logger.info("✅ Cognee configurado correctamente")
        except Exception as e:
            logger.error(f"❌ Error configurando Cognee: {e}")
            self.cognee_available = False

    async def process_documents(self, documents: List[Dict[str, Any]], dataset_name: str = "default", account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Procesa documentos usando un enfoque híbrido donde el LLM es el principal analista
        para crear grafos conceptuales.

        Prioriza el procesamiento conceptual basado en LLM (ConceptualGraphProcessor).

        Args:
            documents: Lista de documentos a procesar.
            dataset_name: Nombre del dataset.
            account_id: ID del usuario o cuenta propietaria de los documentos.

        Returns:
            Dict con el resultado del procesamiento conceptual.
        """
        logger.info(f"🧠 Iniciando procesamiento conceptual (LLM-driven) para {len(documents)} documentos.")

        try:
            # Reconstruir contenido completo desde chunks vectorizados
            # Esta función ya está implementada y es necesaria para obtener el texto completo
            processed_documents = await self._reconstruct_document_content(documents, account_id=account_id)

            if not processed_documents:
                raise ValueError("No se pudo reconstruir contenido de documentos para procesamiento conceptual.")

            # Inicializar procesador conceptual (que usa LLM)
            from knowledge_graph.conceptual_graph_processor import ConceptualGraphProcessor
            from core.llm_manager import get_main_llm

            llm = get_main_llm()
            if not llm:
                raise ValueError("LLM principal no disponible para procesamiento conceptual.")

            conceptual_processor = ConceptualGraphProcessor(llm=llm)

            # Procesar documentos conceptualmente
            conceptual_result = await conceptual_processor.process_documents_conceptually(
                processed_documents, dataset_name
            )

            # Guardar en Neo4j usando el adaptador
            if self.hybrid_adapter:
                # Convertir formato conceptual a formato compatible con Neo4j
                neo4j_data = await self._convert_conceptual_to_neo4j_format(conceptual_result)

                # Guardar nodos conceptuales
                await self.hybrid_adapter.add_cognee_results_to_graph(neo4j_data["entities"], [])
                logger.info(f"✅ {len(neo4j_data['entities'])} citas conceptuales guardadas.")

                # Guardar relaciones temáticas
                await self.hybrid_adapter.add_cognee_results_to_graph([], neo4j_data["relationships"])
                logger.info(f"✅ {len(neo4j_data['relationships'])} relaciones temáticas guardadas.")

                # Guardar perfiles de ideas como nodos especiales
                if neo4j_data.get("profiles"):
                    await self.hybrid_adapter.add_cognee_results_to_graph(neo4j_data["profiles"], [])
                    logger.info(f"✅ {len(neo4j_data['profiles'])} perfiles de ideas guardados.")

                # Guardar relaciones de perfiles
                if neo4j_data.get("profile_relationships"):
                    await self.hybrid_adapter.add_cognee_results_to_graph([], neo4j_data["profile_relationships"])
                    logger.info(f"✅ {len(neo4j_data['profile_relationships'])} relaciones de perfiles guardadas.")

            logger.info("🎉 Procesamiento conceptual LLM-driven completado exitosamente.")

            return {
                "success": True,
                "processing_type": "conceptual_llm_driven",
                "conceptual_quotes": len(conceptual_result.get("conceptual_nodes", [])),
                "thematic_relationships": len(conceptual_result.get("thematic_relationships", [])),
                "idea_profiles": len(conceptual_result.get("idea_profiles", [])),
                "metadata": conceptual_result.get("metadata", {})
            }

        except Exception as e:
            logger.error(f"❌ Error en procesamiento conceptual (LLM-driven): {e}", exc_info=True)
            # Fallback al procesamiento básico si el LLM-driven falla
            return await self._fallback_processing(documents, dataset_name)

    def _clean_malformed_json(self, json_str: str) -> Optional[str]:
        """
        Intenta limpiar un JSON malformado de forma más agresiva y extraer el primer objeto/array JSON válido de cualquier texto.
        Mejorada para eliminar comentarios, líneas basura y extraer el mayor bloque JSON posible.
        """
        try:
            import json
            import re

            logger.info(f"🔧 Intentando reparar JSON truncado (longitud: {len(json_str)} caracteres)")

            # 1. Eliminar comentarios tipo // y /* ... */
            json_str = re.sub(r'//.*', '', json_str)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

            # 2. Eliminar líneas basura que no parezcan JSON
            lines = json_str.splitlines()
            json_lines = [line for line in lines if any(c in line for c in '{[":,')]  # líneas con {, [, ", :, ,
            json_str = '\n'.join(json_lines)

            # 3. Buscar el mayor bloque JSON posible entre { ... } o [ ... ]
            first_curly = json_str.find('{')
            last_curly = json_str.rfind('}')
            first_square = json_str.find('[')
            last_square = json_str.rfind(']')
            candidates = []
            if first_curly != -1 and last_curly != -1 and last_curly > first_curly:
                candidates.append(json_str[first_curly:last_curly+1])
            if first_square != -1 and last_square != -1 and last_square > first_square:
                candidates.append(json_str[first_square:last_square+1])

            # 4. Buscar también todos los objetos/arrays internos
            for match in re.finditer(r'\{(?:[^{}]|(?R))*\}', json_str, re.DOTALL):
                candidates.append(match.group())
            for match in re.finditer(r'\[(?:[^\[\]]|(?R))*\]', json_str, re.DOTALL):
                candidates.append(match.group())

            # 5. Probar cada candidato
            for candidate in candidates:
                try:
                    parsed = json.loads(candidate)
                    logger.info(f"✅ JSON extraído y parseado correctamente (longitud: {len(candidate)})")
                    return candidate
                except Exception:
                    continue

            # Si todo falla, crear JSON mínimo válido
            logger.warning("⚠️ No se pudo reparar JSON, creando estructura mínima")
            minimal_json = {
                "nodes": [],
                "edges": [],
                "metadata": {"status": "partial_recovery", "original_length": len(json_str)}
            }
            return json.dumps(minimal_json)

        except Exception as clean_error:
            logger.error(f"❌ Error limpiando JSON: {clean_error}")
            return None

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

    async def _process_with_hybrid_pipeline(self, documents: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
        """Procesa documentos usando el pipeline híbrido de modelos especializados."""
        logger.info(f"🧠 Procesando con pipeline híbrido (spaCy + SentenceTransformers)")

        # Reconstruir contenido completo desde chunks vectorizados
        processed_documents = await self._reconstruct_document_content(documents)

        if not processed_documents:
            raise ValueError("No se pudo reconstruir contenido de documentos")

        # El adapter ya está inicializado en __init__
        if not self.hybrid_adapter:
            from knowledge_graph.neo4j_adapter import Neo4jAdapter
            self.hybrid_adapter = Neo4jAdapter(self.graph_db)

        # Configurar callback de guardado inmediato
        async def save_immediately(entities, relationships):
            logger.info("💾 GUARDANDO INMEDIATAMENTE en Neo4j con Neo4jAdapter...")
            if self.hybrid_adapter:
                # Usar Neo4jAdapter que maneja formato híbrido correctamente
                await self.hybrid_adapter.add_cognee_results_to_graph(entities, relationships)
                logger.info(f"✅ GUARDADO INMEDIATO: {len(entities)} entidades, {len(relationships)} relaciones")
            else:
                logger.error("❌ hybrid_adapter no está disponible para guardado inmediato")

        self.hybrid_processor.set_save_callback(save_immediately)

        # Procesar con pipeline híbrido (con guardado automático después de Fase 2)
        result = await self.hybrid_processor.process_documents(processed_documents, dataset_name)

        # Convertir formato para compatibilidad con el resto del sistema
        entities, relationships = self._convert_hybrid_result(result)

        logger.info(f"✅ Pipeline híbrido completado con guardado automático:")
        logger.info(f"   📊 Entidades: {len(entities)}")
        logger.info(f"   🔗 Relaciones: {len(relationships)}")
        logger.info(f"   💾 Datos ya guardados en Neo4j durante el procesamiento")

        return {
            "entities": entities,
            "relationships": relationships,
            "metadata": result.get("metadata", {}),
            "processing_method": "hybrid_pipeline"
        }

    async def _reconstruct_document_content(self, documents: List[Dict[str, Any]], account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Reconstruye el contenido completo de documentos desde chunks vectorizados."""
        processed_documents = []

        # Si no se proporciona account_id, intentar extraerlo del primer documento
        if not account_id and documents:
            account_id = documents[0].get("metadata", {}).get("account_id")

        if not account_id:
            logger.error("❌ No se encontró account_id ni en los parámetros ni en los documentos")
            return []

        for i, doc in enumerate(documents):
            # Obtener el nombre del archivo
            file_name = doc.get("title") or doc.get("metadata", {}).get("file_name")

            if not file_name:
                logger.warning(f"⚠️ Documento {i} sin nombre de archivo: {doc}")
                continue

            logger.info(f"🔄 Reconstruyendo contenido para: {file_name}")

            # Reconstruir contenido completo desde chunks vectorizados
            try:
                full_content = await get_full_document_content(
                    account_id=account_id,
                    file_name=file_name
                )

                if full_content and len(full_content.strip()) > 0:
                    processed_documents.append({
                        "title": file_name,
                        "content": full_content.strip(),
                        "metadata": doc.get("metadata", {})
                    })
                    logger.info(f"✅ Contenido reconstruido para {file_name}: {len(full_content)} caracteres")
                else:
                    logger.warning(f"⚠️ No se pudo reconstruir contenido para: {file_name}")

            except Exception as content_error:
                logger.error(f"❌ Error reconstruyendo contenido para {file_name}: {content_error}")

        return processed_documents

    def _convert_hybrid_result(self, result: Dict[str, Any]) -> tuple[List[Dict], List[Dict]]:
        """Convierte el resultado del pipeline híbrido al formato estándar."""
        entities = []
        relationships = []

        # Convertir entidades
        for entity in result.get("entities", []):
            entities.append({
                "type": entity.get("type", "Entity"),
                "properties": {
                    "name": entity.get("name", "Unknown"),
                    "description": entity.get("description", ""),
                    "confidence": entity.get("confidence", 0.8),
                    "extraction_method": entity.get("extraction_method", "hybrid"),
                    "source": "hybrid_pipeline",
                    "created_at": datetime.now().isoformat(),
                }
            })

        # Convertir relaciones
        for rel in result.get("relationships", []):
            relationships.append({
                "type": rel.get("relationship_type", "RELATED"),
                "properties": {
                    "description": rel.get("description", ""),
                    "confidence": rel.get("confidence", 0.8),
                    "extraction_method": rel.get("extraction_method", "hybrid"),
                    "source": "hybrid_pipeline",
                    "created_at": datetime.now().isoformat(),
                },
                "source_entity": rel.get("source_entity_id", ""),
                "target_entity": rel.get("target_entity_id", "")
            })

        return entities, relationships

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

    async def search_knowledge_graph(
        self,
        query: str,
        dataset_name: str = "default",
        relationship_types: Optional[List[str]] = None,
        source_concept: Optional[str] = None,
        target_concept: Optional[str] = None,
        max_hops: Optional[int] = None,
        pattern_description: Optional[str] = None,
        return_type: Optional[Literal["nodes", "relationships", "paths", "summary"]] = "summary"
    ) -> Dict[str, Any]:
        # ... (código de cognee_available y try-except)

        # 1. Lógica para Búsquedas Relacionales y de Caminos (si se especifican parámetros estructurados)
        # ESTA ES LA PRIORIDAD MÁS ALTA SI EL LLM YA HA ESTRUCTURADO LA CONSULTA.
        if not self.cognee_available:
            return {
                "query": query, "dataset_name": dataset_name, "results": [],
                "status": "search_unavailable", "method": "fallback",
                "searched_at": datetime.now().isoformat()
            }

        try:
            if source_concept or target_concept or relationship_types or max_hops:
                logger.info(f"🧠 Ejecutando búsqueda relacional/de caminos con: source={source_concept}, target={target_concept}, rels={relationship_types}, hops={max_hops}")
                
                # --- Construcción dinámica de la consulta Cypher para paths ---
                # (Tu código existente aquí, que está bien)
                parts = []
                params = {"dataset_name": dataset_name}

                source_match = f"(s {{name: $source_concept, dataset_name: $dataset_name}})" if source_concept else "(s)"
                target_match = f"(t {{name: $target_concept, dataset_name: $dataset_name}})" if target_concept else "(t)"
                
                if source_concept:
                    params["source_concept"] = source_concept
                if target_concept:
                    params["target_concept"] = target_concept

                rel_spec = ""
                if relationship_types:
                    rel_spec = ":" + "|".join(relationship_types)
                
                # Ajustar hop_spec para el caso de max_hops=1 o ilimitado si no se da
                hop_spec = f"*{1 if max_hops == 1 else ''}..{max_hops}" if max_hops else "*"

                cypher_query = f"MATCH path = {source_match}-[{rel_spec}{hop_spec}]-{target_match} "
                
                # Asegurar que todos los nodos en el camino pertenezcan al dataset
                cypher_query += "WHERE all(n IN nodes(path) WHERE n.dataset_name = $dataset_name) "
                cypher_query += "RETURN path"

                raw_results = await self.graph_db.execute_query(cypher_query, parameters=params)
                
                formatted_results = self._format_advanced_search_results(raw_results, return_type)

                return {
                    "query": f"Advanced search: source={source_concept}, target={target_concept}, rels={relationship_types}, hops={max_hops}",
                    "dataset_name": dataset_name,
                    "results": formatted_results,
                    "status": "search_completed_advanced_graph",
                    "method": "advanced_cypher",
                    "searched_at": datetime.now().isoformat()
                }

            # 2. Lógica para Búsqueda de Patrones Específicos usando pattern_description (NUEVA PRIORIDAD)
            # Esto intenta ser más inteligente que solo full-text si hay una descripción de patrón.
            if pattern_description:
                logger.info(f"🔍 Ejecutando búsqueda de patrón específica con: {pattern_description}")
                
                # --- Intento de traducir pattern_description a Cypher (simplificado) ---
                # Esto es un placeholder y el punto más complejo.
                # Aquí la idea es que un LLM interno o una lógica de NLP avanzada
                # convierta "conceptos y relaciones que describen desafíos de la IA"
                # en un patrón Cypher como:
                # MATCH (n:CONCEPTUAL_QUOTE)-[r]->(m:CONCEPTUAL_QUOTE)
                # WHERE n.description CONTAINS 'desafíos' AND r.type = 'DESAFIO_DE'
                # (Esto es muy difícil de hacer de forma genérica sin un LLM interno)
                
                # POR AHORA, usaremos una búsqueda full-text mejorada que devuelva los nodos/rels
                # directamente, y no solo conteos.

                # La query para full-text ahora incluye el pattern_description para ser más específico
                search_text_for_pattern = f"{query} {pattern_description}" if query else pattern_description

                cypher_query = """
                CALL db.index.fulltext.queryNodes('node_fulltext_index', $search_text_for_pattern) YIELD node AS n, score AS nodeScore
                WHERE n.dataset_name = $dataset_name
                WITH n, nodeScore
                OPTIONAL MATCH (n)-[r]-(m)
                RETURN DISTINCT n, r, m, nodeScore AS score
                UNION ALL
                CALL db.index.fulltext.queryRelationships('relationship_fulltext_index', $search_text_for_pattern) YIELD relationship AS r, score AS relScore
                MATCH (n)-[r]-(m)
                WHERE n.dataset_name = $dataset_name AND m.dataset_name = $dataset_name
                RETURN DISTINCT n, r, m, relScore AS score
                ORDER BY score DESC LIMIT 10
                """
                params = {"search_text_for_pattern": search_text_for_pattern, "dataset_name": dataset_name}
                
                raw_results = await self.graph_db.execute_query(cypher_query, parameters=params)
                
                formatted_results = self._format_advanced_search_results(raw_results, return_type) # Usar el nuevo formateador

                if formatted_results:
                    return {
                        "query": query,
                        "dataset_name": dataset_name,
                        "results": formatted_results, # Devolver los nodos/rels formateados
                        "status": "search_completed_pattern",
                        "method": "pattern_search_fulltext",
                        "searched_at": datetime.now().isoformat(),
                        "summary": f"Se encontraron elementos relacionados con el patrón '{pattern_description}'. Estos son algunos de los resultados clave."
                    }
                else:
                    return {
                        "query": query,
                        "dataset_name": dataset_name,
                        "results": [],
                        "status": "search_completed_no_patterns",
                        "method": "pattern_search_fulltext",
                        "searched_at": datetime.now().isoformat(),
                        "summary": "No se encontraron elementos que coincidan con el patrón descrito."
                    }

            # 3. Lógica para Insights Generales/Estadísticas (si la query contiene "insights", "patrones", pero no hay pattern_description específica)
            # Esto es para cuando el LLM pide "insights" pero no especifica un patrón concreto.
            if "tematicas" in query.lower() or "insights" in query.lower() or "patrones" in query.lower():
                logger.info(f"📊 Ejecutando búsqueda de insights generales/estadísticas para: {query}")
                
                node_stats_query = f"""
                MATCH (n:CONCEPTUAL_QUOTE {{dataset_name: $dataset_name}})
                RETURN DISTINCT n.category AS category, COUNT(n) AS count
                ORDER BY count DESC LIMIT 5
                """
                rels_stats_query = f"""
                MATCH ()-[r]->() WHERE r.dataset_name = $dataset_name
                RETURN DISTINCT type(r) AS rel_type, COUNT(r) AS count
                ORDER BY count DESC LIMIT 5
                """
                
                node_stats = await self.graph_db.execute_query(node_stats_query, parameters={"dataset_name": dataset_name})
                rels_stats = await self.graph_db.execute_query(rels_stats_query, parameters={"dataset_name": dataset_name})

                summary_items = []
                if node_stats:
                    summary_items.append({"type": "node_stats", "content": "Categorías de nodos más comunes:\n" + "\n".join([f"- {item['category']}: {item['count']} nodos" for item in node_stats])})
                if rels_stats:
                    summary_items.append({"type": "rel_stats", "content": "Tipos de relaciones más comunes:\n" + "\n".join([f"- {item['rel_type']}: {item['count']} relaciones" for item in rels_stats])})
                
                if summary_items:
                    return {
                        "query": query, "dataset_name": dataset_name, "results": summary_items,
                        "status": "search_completed_general_insights", "method": "general_insights",
                        "searched_at": datetime.now().isoformat(),
                        "summary": "Se encontraron estadísticas generales del grafo."
                    }
                else:
                     return {
                        "query": query, "dataset_name": dataset_name, "results": [],
                        "status": "search_completed_no_general_insights", "method": "general_insights",
                        "searched_at": datetime.now().isoformat(),
                        "summary": "No se encontraron estadísticas o patrones generales significativos en el grafo."
                    }

            # 4. Lógica de Búsqueda Full-Text (como última opción si nada más específico aplica)
            logger.info(f"📝 Ejecutando búsqueda full-text para: {query}")
            cypher_query = """
            CALL db.index.fulltext.queryNodes('node_fulltext_index', $query) YIELD node AS n, score AS nodeScore
            WHERE n.dataset_name = $dataset_name
            WITH n, nodeScore
            OPTIONAL MATCH (n)-[r]-(m)
            RETURN DISTINCT n, r, m, nodeScore AS score
            UNION ALL
            CALL db.index.fulltext.queryRelationships('relationship_fulltext_index', $query) YIELD relationship AS r, score AS relScore
            MATCH (n)-[r]-(m)
            WHERE n.dataset_name = $dataset_name AND m.dataset_name = $dataset_name
            RETURN DISTINCT n, r, m, relScore AS score
            ORDER BY score DESC LIMIT 20
            """
            search_results_raw = await self.graph_db.execute_query(cypher_query, parameters={"query": query, "dataset_name": dataset_name})
            
            # Formatear resultados full-text (puedes usar _format_advanced_search_results con return_type="summary" si quieres)
            formatted_results = self._format_advanced_search_results(search_results_raw, return_type="summary")

            return {
                "query": query, "dataset_name": dataset_name, "results": formatted_results,
                "status": "search_completed", "method": "fulltext_cypher",
                "searched_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}", exc_info=True)
            return {
                "query": query, "dataset_name": dataset_name, "results": [],
                "status": "search_error", "error": str(e),
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

    async def process_documents_conceptually(self, documents: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
        """
        Procesa documentos usando el nuevo enfoque conceptual de citas e ideas.

        Args:
            documents: Lista de documentos
            dataset_name: Nombre del dataset

        Returns:
            Dict con resultado del procesamiento conceptual
        """
        try:
            logger.info(f"🧠 Iniciando procesamiento conceptual para {len(documents)} documentos")

            # Inicializar procesador conceptual
            from knowledge_graph.conceptual_graph_processor import ConceptualGraphProcessor
            from core.llm_manager import get_main_llm

            llm = get_main_llm()
            conceptual_processor = ConceptualGraphProcessor(llm=llm)

            # Reconstruir contenido completo desde chunks vectorizados
            processed_documents = await self._reconstruct_document_content(documents)

            if not processed_documents:
                raise ValueError("No se pudo reconstruir contenido de documentos")

            # Procesar documentos conceptualmente
            conceptual_result = await conceptual_processor.process_documents_conceptually(
                processed_documents, dataset_name
            )

            # Guardar en Neo4j usando el adapter
            if self.hybrid_adapter:
                # Convertir formato conceptual a formato compatible con Neo4j
                neo4j_data = await self._convert_conceptual_to_neo4j_format(conceptual_result)

                # Guardar nodos conceptuales
                await self.hybrid_adapter.add_cognee_results_to_graph(neo4j_data["entities"], [])
                logger.info(f"✅ {len(neo4j_data['entities'])} citas conceptuales guardadas")

                # Guardar relaciones temáticas
                await self.hybrid_adapter.add_cognee_results_to_graph([], neo4j_data["relationships"])
                logger.info(f"✅ {len(neo4j_data['relationships'])} relaciones temáticas guardadas")

                # Guardar perfiles de ideas como nodos especiales
                if neo4j_data.get("profiles"):
                    await self.hybrid_adapter.add_cognee_results_to_graph(neo4j_data["profiles"], [])
                    logger.info(f"✅ {len(neo4j_data['profiles'])} perfiles de ideas guardados")

                # Guardar relaciones de perfiles
                if neo4j_data.get("profile_relationships"):
                    await self.hybrid_adapter.add_cognee_results_to_graph([], neo4j_data["profile_relationships"])
                    logger.info(f"✅ {len(neo4j_data['profile_relationships'])} relaciones de perfiles guardadas")

            logger.info("🎉 Procesamiento conceptual completado exitosamente")

            return {
                "success": True,
                "processing_type": "conceptual",
                "conceptual_quotes": len(conceptual_result["conceptual_nodes"]),
                "thematic_relationships": len(conceptual_result["thematic_relationships"]),
                "idea_profiles": len(conceptual_result["idea_profiles"]),
                "metadata": conceptual_result["metadata"]
            }

        except Exception as e:
            logger.error(f"❌ Error en procesamiento conceptual: {e}")
            raise

    
    async def _convert_conceptual_to_neo4j_format(self, conceptual_result: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte el resultado conceptual al formato compatible con Neo4j."""

        # Convertir citas conceptuales a entidades
        entities = []
        conceptual_nodes = conceptual_result.get("conceptual_nodes", [])
        for quote in conceptual_nodes:
            entity = {
                "type": "CONCEPTUAL_QUOTE",
                "properties": {
                    "name": quote.get("concept", "Unknown"),
                    "cognee_id": quote["id"],
                    "description": quote["text"][:500] + "..." if len(quote["text"]) > 500 else quote["text"],
                    "full_text": quote["text"],
                    "concept": quote.get("concept", "Unknown"),
                    "importance": quote["importance"],
                    "category": quote["category"],
                    "confidence": quote["confidence"],
                    "source_document": quote["source_document"],
                    "extraction_method": quote["extraction_method"],
                    "created_at": datetime.now().isoformat()
                }
            }
            entities.append(entity)

        # Convertir relaciones temáticas
        relationships = []
        thematic_relationships = conceptual_result.get("thematic_relationships", [])
        for rel in thematic_relationships:
            relationship = {
                # CAMBIO: Usar 'source_entity' y 'target_entity' para compatibilidad con el adaptador
                "source_entity": rel.get("source_id", ""),
                "target_entity": rel.get("target_id", ""),
                "source_type": "CONCEPTUAL_QUOTE", # source_type y target_type son opcionales si el adaptador los infiere
                "target_type": "CONCEPTUAL_QUOTE",
                "type": rel["type"],
                "confidence": rel["confidence"],
                "cognee_id": rel["id"],
                "properties": {
                    "description": rel["description"],
                    "similarity_score": rel.get("similarity_score", 0),
                    "extraction_method": rel["extraction_method"],
                    "created_at": datetime.now().isoformat()
                }
            }
            relationships.append(relationship)

        # Convertir perfiles de ideas a entidades especiales
        profiles = []
        profile_relationships = []

        idea_profiles = conceptual_result.get("idea_profiles", [])
        for profile in idea_profiles:
            profile_entity = {
                "type": "IDEA_PROFILE",
                "properties": {
                    "name": profile["central_concept"],
                    "cognee_id": profile["id"],
                    "description": profile["description"],
                    "quotes_count": profile["quotes_count"],
                    "categories": ", ".join(profile["categories"]),
                    "importance_score": profile["importance_score"],
                    "coherence_score": profile["coherence_score"],
                    "documents_span": ", ".join(profile["documents_span"]),
                    "confidence": profile["coherence_score"],  # Usar coherencia como confianza
                    "extraction_method": "idea_profile_clustering",
                    "created_at": datetime.now().isoformat()
                }
            }
            profiles.append(profile_entity)

            # Crear relaciones entre el perfil y sus citas
            for quote_id in profile["quote_ids"]:
                profile_rel = {
                    # CAMBIO: Usar 'source_entity' y 'target_entity' también aquí
                    "source_entity": profile["id"],
                    "target_entity": quote_id,
                    "source_type": "IDEA_PROFILE",
                    "target_type": "CONCEPTUAL_QUOTE",
                    "type": "CONTAINS_IDEA",
                    "confidence": 0.9,
                    "cognee_id": f"profile_contains_{profile['id']}_{quote_id}",
                    "properties": {
                        "description": f"El perfil '{profile['central_concept']}' contiene esta idea",
                        "extraction_method": "profile_membership",
                        "created_at": datetime.now().isoformat()
                    }
                }
                profile_relationships.append(profile_rel)

        return {
            "entities": entities,
            "relationships": relationships,
            "profiles": profiles,
            "profile_relationships": profile_relationships
        }

    async def detect_trends(
        self,
        dataset_name: str,
        time_window: str = "last_6_months",
        trend_threshold: float = 0.7,
        granularity: str = "weekly"
    ) -> Dict[str, Any]:
        """
        Detecta tendencias emergentes en el dataset usando análisis temporal.

        Args:
            dataset_name: Nombre del dataset
            time_window: Ventana temporal (ej: "last_6_months", "last_1_year")
            trend_threshold: Umbral para considerar una tendencia (0.0-1.0)
            granularity: Granularidad temporal ("daily", "weekly", "monthly")

        Returns:
            Dict con tendencias detectadas
        """
        try:
            logger.info(f"📈 Detectando tendencias en dataset '{dataset_name}'")

            # Inicializar analizador de tendencias
            from knowledge_graph.trend_analyzer import TrendAnalyzer

            trend_analyzer = TrendAnalyzer(
                graph_db=self.graph_db,
                sentence_transformer=None  # Se puede agregar después
            )

            # Detectar tendencias
            trends_result = await trend_analyzer.detect_trends(
                dataset_name=dataset_name,
                time_window=time_window,
                trend_threshold=trend_threshold,
                granularity=granularity
            )

            logger.info(f"✅ Análisis de tendencias completado: {trends_result['trend_metrics']['total_trends']} tendencias detectadas")

            return trends_result

        except Exception as e:
            logger.error(f"❌ Error detectando tendencias: {e}")
            raise

    async def analyze_temporal_patterns(
        self,
        dataset_name: str,
        analysis_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Realiza análisis temporal completo del dataset.

        Args:
            dataset_name: Nombre del dataset
            analysis_types: Tipos de análisis a realizar

        Returns:
            Dict con resultados del análisis temporal
        """
        if analysis_types is None:
            analysis_types = ["trends", "evolution", "patterns"]

        try:
            logger.info(f"🕒 Iniciando análisis temporal completo para '{dataset_name}'")

            results = {
                "dataset_name": dataset_name,
                "analysis_timestamp": datetime.now().isoformat(),
                "analysis_types": analysis_types
            }

            # Análisis de tendencias
            if "trends" in analysis_types:
                logger.info("📈 Analizando tendencias...")
                trends = await self.detect_trends(
                    dataset_name=dataset_name,
                    time_window="last_6_months",
                    trend_threshold=0.6,
                    granularity="weekly"
                )
                results["trends_analysis"] = trends

            # Análisis de evolución (diferentes ventanas temporales)
            if "evolution" in analysis_types:
                logger.info("🔄 Analizando evolución temporal...")
                evolution_results = {}

                time_windows = ["last_1_month", "last_3_months", "last_6_months"]
                for window in time_windows:
                    evolution = await self.detect_trends(
                        dataset_name=dataset_name,
                        time_window=window,
                        trend_threshold=0.5,
                        granularity="weekly"
                    )
                    evolution_results[window] = evolution["trend_metrics"]

                results["evolution_analysis"] = evolution_results

            # Análisis de patrones (granularidades diferentes)
            if "patterns" in analysis_types:
                logger.info("🔍 Analizando patrones temporales...")
                pattern_results = {}

                granularities = ["daily", "weekly", "monthly"]
                for granularity in granularities:
                    patterns = await self.detect_trends(
                        dataset_name=dataset_name,
                        time_window="last_3_months",
                        trend_threshold=0.7,
                        granularity=granularity
                    )
                    pattern_results[granularity] = {
                        "trends_count": patterns["trend_metrics"]["total_trends"],
                        "strongest_trend": patterns["summary"].get("strongest_trend")
                    }

                results["patterns_analysis"] = pattern_results

            # Generar resumen consolidado
            results["consolidated_summary"] = await self._generate_temporal_summary(results)

            logger.info("✅ Análisis temporal completo finalizado")
            return results

        except Exception as e:
            logger.error(f"❌ Error en análisis temporal: {e}")
            raise

    async def _generate_temporal_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Genera un resumen consolidado del análisis temporal."""

        summary = {
            "analysis_date": analysis_results["analysis_timestamp"],
            "dataset": analysis_results["dataset_name"]
        }

        # Resumen de tendencias
        if "trends_analysis" in analysis_results:
            trends = analysis_results["trends_analysis"]
            summary["trends_summary"] = {
                "total_trends": trends["trend_metrics"]["total_trends"],
                "strongest_trend_score": trends["trend_metrics"].get("max_trend_score", 0),
                "growth_trends": trends["trend_metrics"]["trends_by_direction"].get("creciente", 0),
                "decline_trends": trends["trend_metrics"]["trends_by_direction"].get("decreciente", 0)
            }

        # Resumen de evolución
        if "evolution_analysis" in analysis_results:
            evolution = analysis_results["evolution_analysis"]
            summary["evolution_summary"] = {
                "time_windows_analyzed": len(evolution),
                "trend_consistency": self._calculate_trend_consistency(evolution)
            }

        # Recomendaciones generales
        summary["recommendations"] = self._generate_temporal_recommendations(analysis_results)

        return summary

    def _calculate_trend_consistency(self, evolution_data: Dict[str, Any]) -> float:
        """Calcula la consistencia de tendencias entre diferentes ventanas temporales."""

        if not evolution_data:
            return 0.0

        # Obtener número de tendencias por ventana
        trend_counts = [data.get("total_trends", 0) for data in evolution_data.values()]

        if not trend_counts or max(trend_counts) == 0:
            return 0.0

        # Calcular consistencia como varianza normalizada
        mean_trends = np.mean(trend_counts)
        variance = np.var(trend_counts)
        consistency = 1.0 - (variance / (mean_trends + 1))  # +1 para evitar división por 0

        return round(max(0.0, float(consistency)), 3)

    def _generate_temporal_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en el análisis temporal."""

        recommendations = []

        # Recomendaciones basadas en tendencias
        if "trends_analysis" in analysis_results:
            trends = analysis_results["trends_analysis"]
            total_trends = trends["trend_metrics"]["total_trends"]

            if total_trends == 0:
                recommendations.append("No se detectaron tendencias significativas. Considerar reducir el umbral o aumentar el volumen de datos.")
            elif total_trends > 20:
                recommendations.append("Se detectaron muchas tendencias. Considerar filtrar por relevancia o aumentar el umbral.")
            else:
                recommendations.append(f"Se detectaron {total_trends} tendencias. Analizar las más fuertes para insights estratégicos.")

        # Recomendaciones basadas en evolución
        if "evolution_analysis" in analysis_results:
            evolution = analysis_results["evolution_analysis"]
            consistency = self._calculate_trend_consistency(evolution)

            if consistency > 0.8:
                recommendations.append("Las tendencias son consistentes entre diferentes períodos. Buena señal para predicciones.")
            elif consistency < 0.5:
                recommendations.append("Las tendencias varían mucho entre períodos. Investigar factores externos que puedan influir.")

        return recommendations

    def _format_advanced_search_results(self, raw_results: List[Dict[str, Any]], return_type: str) -> List[Dict[str, Any]]:
        """Formatea los resultados crudos de Cypher según el tipo de retorno solicitado."""
        if return_type == "paths":
            return [self._format_path(record["path"]) for record in raw_results]
        
        nodes = {}
        relationships = {}
        
        for record in raw_results:
            path = record["path"]
            for node in path.nodes:
                nodes[node.element_id] = dict(node)
            for rel in path.relationships:
                relationships[rel.element_id] = {
                    "type": rel.type,
                    "properties": dict(rel),
                    "start_node": rel.start_node.element_id,
                    "end_node": rel.end_node.element_id
                }

        if return_type == "nodes":
            return list(nodes.values())
        if return_type == "relationships":
            return list(relationships.values())
        if return_type == "summary":
            return {
                "node_count": len(nodes),
                "relationship_count": len(relationships),
                "path_count": len(raw_results)
            }
        return []

    def _format_path(self, path_object: Any) -> str:
        """Convierte un objeto Path de Neo4j en una cadena legible."""
        nodes_str = [f"({node.get('name', 'Unnamed')}:{list(node.labels)[0]})" for node in path_object.nodes]
        rels_str = [f"-[{rel.type}]->" for rel in path_object.relationships]
        
        path_str = nodes_str[0]
        for i, rel_str in enumerate(rels_str):
            path_str += rel_str + nodes_str[i+1]
            
        return path_str

# Ejemplo de uso (puedes mover esto a otro archivo para pruebas):
if __name__ == '__main__':
    #  Configura las variables de entorno
    cognee_api_url = settings.cognee_api_url
    neo4j_uri = settings.neo4j_uri
    neo4j_user = settings.neo4j_user
    neo4j_password = settings.neo4j_password

    # Validar que las configuraciones de Neo4j estén presentes
    if not neo4j_uri or not neo4j_user or not neo4j_password:
        print("❌ Error: Las configuraciones de Neo4j no están completas.")
        print("Asegúrate de que NEO4J_URI, NEO4J_USER y NEO4J_PASSWORD estén definidos en tu archivo .env")
        exit(1)

    #  Inicializa la base de datos de grafos
    graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
    try:

        graph_db.connect()
        #  Inicializa la integración con Cognee
        cognee_integration = CogneeIntegration(graph_db)

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


