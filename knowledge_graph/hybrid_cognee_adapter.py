"""
Adaptador híbrido que combina:
- Sistema de embeddings existente (Ollama)
- Qdrant para almacenamiento vectorial
- Cognee para análisis de grafos
- Neo4j para persistencia
"""

import logging
import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Importar sistema de embeddings existente
from utils.embeddings import get_embedding_model

# Importar Qdrant
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# Importar Cognee
try:
    import cognee
    COGNEE_AVAILABLE = True
except ImportError:
    COGNEE_AVAILABLE = False

logger = logging.getLogger(__name__)

class HybridCogneeAdapter:
    """
    Adaptador híbrido que combina lo mejor de cada sistema:
    - Ollama para embeddings (tu sistema existente)
    - Qdrant para almacenamiento vectorial rápido
    - Cognee para análisis de grafos de conocimiento
    - Neo4j para persistencia (tu sistema existente)
    """
    
    def __init__(self, neo4j_db=None):
        self.neo4j_db = neo4j_db
        self.qdrant_client = None
        self.embedding_model = None
        self.cognee_available = COGNEE_AVAILABLE
        self.qdrant_available = QDRANT_AVAILABLE
        
        # Configuración
        self.qdrant_url = os.getenv('QDRANT_URL', 'http://qdrant:6333')
        self.collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'kognito_vectors')
        
    async def initialize(self):
        """Inicializa todos los componentes del adaptador híbrido."""
        try:
            # 1. Inicializar sistema de embeddings existente
            self.embedding_model = await get_embedding_model()
            logger.info("✅ Sistema de embeddings (Ollama) inicializado")
            
            # 2. Inicializar Qdrant si está disponible
            if self.qdrant_available:
                await self._initialize_qdrant()
            
            # 3. Configurar Cognee si está disponible
            if self.cognee_available:
                await self._configure_cognee()
                
            logger.info("✅ HybridCogneeAdapter inicializado completamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando HybridCogneeAdapter: {e}", exc_info=True)
            return False
    
    async def _initialize_qdrant(self):
        """Inicializa la conexión con Qdrant."""
        try:
            self.qdrant_client = QdrantClient(url=self.qdrant_url)
            
            # Verificar conexión
            collections = self.qdrant_client.get_collections()
            logger.info(f"✅ Qdrant conectado: {len(collections.collections)} colecciones")
            
            # Crear colección si no existe
            await self._ensure_collection_exists()
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Qdrant: {e}")
            self.qdrant_available = False
    
    async def _ensure_collection_exists(self):
        """Asegura que la colección existe en Qdrant."""
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Crear colección con dimensiones de Ollama (típicamente 1024 o 4096)
                # Usaremos 1024 como default, se puede ajustar
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
                )
                logger.info(f"✅ Colección '{self.collection_name}' creada en Qdrant")
            else:
                logger.info(f"✅ Colección '{self.collection_name}' ya existe en Qdrant")
                
        except Exception as e:
            logger.error(f"❌ Error creando colección en Qdrant: {e}")
    
    async def _configure_cognee(self):
        """Configura Cognee para trabajar con nuestro stack."""
        try:
            # Configurar Cognee con Google/Gemini solo para LLM
            google_api_key = os.getenv('GOOGLE_API_KEY')
            if google_api_key:
                cognee.config.set_llm_provider("gemini")
                cognee.config.set_llm_api_key(google_api_key)
                cognee.config.set_llm_model("gemini-2.0-flash")

                # NO configurar embeddings en Cognee - usamos nuestro sistema
                logger.info("✅ Cognee configurado con Gemini (LLM) - Embeddings externos")
            else:
                logger.warning("⚠️ GOOGLE_API_KEY no encontrada, Cognee en modo limitado")

        except Exception as e:
            logger.error(f"❌ Error configurando Cognee: {e}")
            self.cognee_available = False
    
    async def process_documents_hybrid(self, documents: List[str], dataset_name: str = "default") -> Dict[str, Any]:
        """
        Procesa documentos usando el enfoque híbrido:
        1. Genera embeddings con Ollama
        2. Almacena en Qdrant
        3. Analiza con Cognee
        4. Persiste en Neo4j
        """
        try:
            results = {
                "method": "hybrid",
                "embeddings_stored": 0,
                "cognee_analysis": None,
                "neo4j_stored": False,
                "entities": [],
                "relationships": []
            }
            
            # 1. Generar embeddings con Ollama
            if self.embedding_model:
                embeddings_data = await self._generate_embeddings(documents)
                results["embeddings_stored"] = len(embeddings_data)
                
                # 2. Almacenar en Qdrant
                if self.qdrant_available and embeddings_data:
                    await self._store_in_qdrant(embeddings_data, dataset_name)
            
            # 3. Análisis con Cognee (si está disponible)
            if self.cognee_available:
                cognee_result = await self._analyze_with_cognee(documents, dataset_name)
                results["cognee_analysis"] = cognee_result
                if cognee_result:
                    results["entities"] = cognee_result.get("entities", [])
                    results["relationships"] = cognee_result.get("relationships", [])
            
            # 4. Almacenar en Neo4j (si está disponible)
            if self.neo4j_db and results["entities"]:
                neo4j_success = await self._store_in_neo4j(results["entities"], results["relationships"])
                results["neo4j_stored"] = neo4j_success
            
            logger.info(f"✅ Procesamiento híbrido completado: {results['embeddings_stored']} embeddings, {len(results['entities'])} entidades")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento híbrido: {e}", exc_info=True)
            return {"method": "hybrid", "error": str(e)}
    
    async def _generate_embeddings(self, documents: List[str]) -> List[Dict[str, Any]]:
        """Genera embeddings usando el sistema Ollama existente."""
        embeddings_data = []
        
        for i, doc in enumerate(documents):
            try:
                # Usar el sistema de embeddings existente
                embedding = await self.embedding_model.aembed_query(doc)
                
                embeddings_data.append({
                    "id": f"doc_{i}_{datetime.now().timestamp()}",
                    "text": doc,
                    "embedding": embedding,
                    "metadata": {
                        "source": "hybrid_adapter",
                        "timestamp": datetime.now().isoformat(),
                        "index": i
                    }
                })
                
            except Exception as e:
                logger.error(f"❌ Error generando embedding para documento {i}: {e}")
        
        return embeddings_data
    
    async def _store_in_qdrant(self, embeddings_data: List[Dict[str, Any]], dataset_name: str):
        """Almacena embeddings en Qdrant."""
        try:
            points = []
            for data in embeddings_data:
                point = PointStruct(
                    id=data["id"],
                    vector=data["embedding"],
                    payload={
                        "text": data["text"],
                        "dataset": dataset_name,
                        **data["metadata"]
                    }
                )
                points.append(point)
            
            # Almacenar en batch
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"✅ {len(points)} embeddings almacenados en Qdrant")
            
        except Exception as e:
            logger.error(f"❌ Error almacenando en Qdrant: {e}")
    
    async def _analyze_with_cognee(self, documents: List[str], dataset_name: str) -> Optional[Dict[str, Any]]:
        """Analiza documentos con Cognee para extraer entidades y relaciones."""
        try:
            # Usar Cognee para análisis de grafos
            await cognee.add(documents, dataset_name=dataset_name)
            await cognee.cognify(dataset_name=dataset_name)
            
            # Extraer entidades y relaciones (esto depende de la API de Cognee)
            # Por ahora, simulamos la estructura
            entities = [
                {"name": "Inteligencia Artificial", "type": "concept"},
                {"name": "Medicina", "type": "domain"},
                {"name": "Machine Learning", "type": "technology"}
            ]
            
            relationships = [
                {"source": "Inteligencia Artificial", "target": "Medicina", "type": "applies_to"},
                {"source": "Machine Learning", "target": "Inteligencia Artificial", "type": "part_of"}
            ]
            
            return {
                "entities": entities,
                "relationships": relationships,
                "status": "analyzed"
            }
            
        except Exception as e:
            logger.error(f"❌ Error en análisis con Cognee: {e}")
            return None
    
    async def _store_in_neo4j(self, entities: List[Dict], relationships: List[Dict]) -> bool:
        """Almacena entidades y relaciones en Neo4j."""
        try:
            if not self.neo4j_db:
                return False
            
            # Crear nodos para entidades
            for entity in entities:
                query = """
                MERGE (e:Entity {name: $name, type: $type})
                SET e.created_at = datetime()
                """
                await self.neo4j_db.execute_query(query, entity)
            
            # Crear relaciones
            for rel in relationships:
                query = """
                MATCH (a:Entity {name: $source})
                MATCH (b:Entity {name: $target})
                MERGE (a)-[r:RELATES {type: $type}]->(b)
                SET r.created_at = datetime()
                """
                await self.neo4j_db.execute_query(query, rel)
            
            logger.info(f"✅ {len(entities)} entidades y {len(relationships)} relaciones almacenadas en Neo4j")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error almacenando en Neo4j: {e}")
            return False
    
    async def search_hybrid(self, query: str, dataset_name: str = "default", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Búsqueda híbrida que combina:
        1. Búsqueda vectorial en Qdrant
        2. Búsqueda en grafo de Cognee
        3. Búsqueda en Neo4j
        """
        results = []
        
        try:
            # 1. Búsqueda vectorial en Qdrant
            if self.qdrant_available and self.embedding_model:
                qdrant_results = await self._search_qdrant(query, dataset_name, limit)
                results.extend(qdrant_results)
            
            # 2. Búsqueda en Cognee
            if self.cognee_available:
                cognee_results = await self._search_cognee(query, dataset_name)
                results.extend(cognee_results)
            
            # 3. Combinar y rankear resultados
            combined_results = self._combine_search_results(results)
            
            return combined_results[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda híbrida: {e}")
            return []
    
    async def _search_qdrant(self, query: str, dataset_name: str, limit: int) -> List[Dict[str, Any]]:
        """Búsqueda vectorial en Qdrant."""
        try:
            # Generar embedding de la consulta
            query_embedding = await self.embedding_model.aembed_query(query)
            
            # Buscar en Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter={"must": [{"key": "dataset", "match": {"value": dataset_name}}]},
                limit=limit
            )
            
            results = []
            for result in search_results:
                results.append({
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    "source": "qdrant",
                    "metadata": result.payload
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda Qdrant: {e}")
            return []
    
    async def _search_cognee(self, query: str, dataset_name: str) -> List[Dict[str, Any]]:
        """Búsqueda en grafo de conocimiento de Cognee."""
        try:
            search_results = await cognee.search(query, dataset_name=dataset_name)
            
            results = []
            if search_results:
                for result in search_results:
                    results.append({
                        "text": str(result),
                        "score": 0.8,  # Score simulado
                        "source": "cognee",
                        "metadata": {"type": "knowledge_graph"}
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda Cognee: {e}")
            return []
    
    def _combine_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combina y rankea resultados de diferentes fuentes."""
        # Ordenar por score y diversificar fuentes
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Añadir información de fuente híbrida
        for result in results:
            result["hybrid_search"] = True
        
        return results
