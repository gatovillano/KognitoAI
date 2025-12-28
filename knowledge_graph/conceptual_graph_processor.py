"""
Procesador de Grafo Conceptual que extrae citas de ideas completas y las relaciona temáticamente.
Crea un grafo donde cada nodo es una idea/concepto expresado como cita textual.
"""

import logging
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
import re
import hashlib

if TYPE_CHECKING:
    from knowledge_graph.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

class ConceptualGraphProcessor:
    """
    Procesador especializado en extracción y análisis conceptual usando LLM.
    
    Responsabilidades:
    - Extracción de citas conceptuales de alta calidad usando LLM
    - Análisis de relaciones temáticas entre ideas conceptuales
    - Identificación de perfiles de ideas centrales interrelacionadas
    - Procesamiento específico del dominio conceptual (no híbrido)
    
    Filosofía:
    - Cada nodo = Una cita que expresa una idea completa
    - Las relaciones = Conexiones temáticas entre ideas
    - Perfiles = Clusters de ideas centrales interrelacionadas
    
    Nota: Todos los métodos son privados excepto process_documents_conceptually e initialize.
    """
    
    def __init__(self, llm=None, fast_llm=None, sentence_transformer=None, neo4j_adapter=None,
                 enable_parallel_processing=True,
                 max_parallel_batches=4,
                 max_parallel_documents=10,
                 cache_size_limit=1000,
                 progress_tracker: Optional["ProgressTracker"] = None):
        """
        Inicializa el procesador conceptual con optimizaciones configurables.

        Args:
            llm: Modelo de lenguaje principal para análisis complejo
            fast_llm: Modelo de lenguaje rápido para tareas simples
            sentence_transformer: Modelo para embeddings semánticos
            neo4j_adapter: Adaptador para interactuar con la base de datos Neo4j
            enable_parallel_processing: Habilitar procesamiento paralelo de lotes
            max_parallel_batches: Máximo número de lotes de relaciones a procesar en paralelo
            max_parallel_documents: Máximo número de documentos a procesar en paralelo
            cache_size_limit: Límite de tamaño del caché (0 = sin límite)
            progress_tracker: Tracker opcional para reportar progreso
        """
        self.llm = llm
        self.fast_llm = fast_llm  # OPTIMIZACIÓN: LLM rápido para tareas simples
        self.embedding_model = sentence_transformer # Renamed to generic embedding_model
        self.neo4j_adapter = neo4j_adapter  # Asignar el adaptador Neo4j
        self.initialized = False
        self.progress_tracker = progress_tracker  # Tracker de progreso

        # Configuración de optimización
        self.enable_parallel_processing = enable_parallel_processing
        self.max_parallel_batches = max_parallel_batches
        self.max_parallel_documents = max_parallel_documents
        self.cache_size_limit = cache_size_limit

        # Cache para resultados de LLM con límite de tamaño
        self.llm_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info("🧠 ConceptualGraphProcessor inicializado con optimizaciones:")
        logger.info(f"   🚀 Procesamiento paralelo: {'✅' if enable_parallel_processing else '❌'}")
        logger.info(f"   📊 Lotes paralelos máximos: {max_parallel_batches}")
        logger.info(f"   📄 Documentos paralelos máximos: {max_parallel_documents}")
        logger.info(f"   💾 Límite de caché: {cache_size_limit if cache_size_limit > 0 else 'Sin límite'}")
        logger.info(f"   ⚡ Fast LLM disponible: {'✅' if fast_llm else '❌'}")
    
    def clear_cache(self):
        """Limpia el caché de LLM y muestra estadísticas."""
        cache_size = len(self.llm_cache)
        hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) * 100 if (self.cache_hits + self.cache_misses) > 0 else 0
        
        logger.info(f"🧹 Limpiando caché:")
        logger.info(f"   📊 Tamaño anterior: {cache_size} entradas")
        logger.info(f"   🎯 Tasa de aciertos: {hit_rate:.1f}%")
        logger.info(f"   💾 Hits: {self.cache_hits}, Misses: {self.cache_misses}")
        
        self.llm_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("✅ Caché limpiado")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests * 100 if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.llm_cache),
            "cache_limit": self.cache_size_limit,
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    def _manage_cache_size(self):
        """Gestiona el tamaño del caché según el límite configurado."""
        if self.cache_size_limit > 0 and len(self.llm_cache) >= self.cache_size_limit:
            # Remover las entradas más antiguas (primera mitad)
            keys_to_remove = list(self.llm_cache.keys())[:self.cache_size_limit // 2]
            for key in keys_to_remove:
                del self.llm_cache[key]
            logger.debug(f"🗑️ Caché reducido: eliminadas {len(keys_to_remove)} entradas antiguas")
    
    def _check_cache(self, cache_key: str) -> Optional[Any]:
        """Verifica el caché con manejo de límites de tamaño."""
        if cache_key in self.llm_cache:
            self.cache_hits += 1
            return self.llm_cache[cache_key]
        else:
            self.cache_misses += 1
            return None
    
    def _store_in_cache(self, cache_key: str, value: Any):
        """Almacena un valor en el caché con gestión de tamaño."""
        self.llm_cache[cache_key] = value
        self._manage_cache_size()
    
    async def initialize(self):
        """Inicializa los modelos necesarios."""
        if self.initialized:
            return
        
        logger.info("🚀 Inicializando modelos para procesamiento conceptual...")
        
        try:
            # Añadir logs para LLM y fast_LLM
            logger.info(f"💡 ConceptualGraphProcessor: LLM principal recibido: {self.llm is not None}")
            logger.info(f"💡 ConceptualGraphProcessor: Fast LLM recibido: {self.fast_llm is not None}")

            # Inicializar Embedding Model si no se proporciona
            if not self.embedding_model:
                await self._initialize_embedding_model()
            
            self.initialized = True
            logger.info("✅ Procesador conceptual inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando procesador conceptual: {e}")
            raise
    
    async def _initialize_embedding_model(self):
        """Inicializa el modelo de embeddings (Ollama/OpenAI/etc)."""
        try:
            from utils.embeddings import get_embedding_model
            
            logger.info("📥 Cargando modelo de embeddings compartido...")
            self.embedding_model = get_embedding_model()
            
            if not self.embedding_model:
                raise ValueError("No se pudo obtener el modelo de embeddings compartido.")

            logger.info(f"✅ Modelo de embeddings cargado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando modelo de embeddings: {e}")
            raise
    
    async def process_documents_conceptually(
        self, 
        documents: List[Dict[str, Any]], 
        dataset_name: str,
        progress_tracker: Optional["ProgressTracker"] = None
    ) -> Dict[str, Any]:
        """
        Procesa documentos extrayendo citas conceptuales y sus relaciones temáticas.
        
        Args:
            documents: Lista de documentos con contenido
            dataset_name: Nombre del dataset
            progress_tracker: Tracker opcional para reportar progreso
            
        Returns:
            Dict con nodos conceptuales, relaciones temáticas y perfiles de ideas
        """
        # Usar tracker proporcionado o el de la instancia
        tracker = progress_tracker or self.progress_tracker
        
        # Importar aquí para evitar circular imports
        if tracker:
            from knowledge_graph.progress_tracker import ProcessingPhase
        
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"🧠 Iniciando procesamiento conceptual de {len(documents)} documentos")
        
        try:
            # ═══════════════════════════════════════════════════════════════
            # FASE 1: Crear y preparar nodos DOCUMENT
            # ═══════════════════════════════════════════════════════════════
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.CONCEPTUAL_CREATING_DOCUMENTS,
                    f"📄 Preparando {len(documents)} documentos para procesamiento...",
                    5,
                    {"documents_processed": len(documents)}
                )
            
            workspace_id = documents[0].get('metadata', {}).get('workspace_id')
            account_id = documents[0].get('metadata', {}).get('account_id')
            processed_documents = await self._create_document_nodes(documents, workspace_id, account_id, dataset_name)
            logger.info(f"✅ NUEVA FASE 1: {len(processed_documents)} nodos DOCUMENT creados y preparados.")
            
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.CONCEPTUAL_CREATING_DOCUMENTS,
                    f"✅ {len(processed_documents)} documentos preparados",
                    15,
                    {"documents_processed": len(processed_documents)}
                )

            # ═══════════════════════════════════════════════════════════════
            # FASE 2: Extraer citas conceptuales
            # ═══════════════════════════════════════════════════════════════
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.CONCEPTUAL_EXTRACTING_QUOTES,
                    f"💭 Extrayendo citas conceptuales de {len(processed_documents)} documentos...",
                    20
                )
            
            conceptual_quotes = await self._extract_conceptual_quotes(processed_documents)
            logger.info(f"✅ Fase 2: {len(conceptual_quotes)} citas conceptuales extraídas")
            
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.CONCEPTUAL_EXTRACTING_QUOTES,
                    f"✅ {len(conceptual_quotes)} citas conceptuales extraídas",
                    40,
                    {"quotes_extracted": len(conceptual_quotes)}
                )
            
            # ═══════════════════════════════════════════════════════════════
            # FASE 3: Analizar relaciones temáticas (la más lenta)
            # ═══════════════════════════════════════════════════════════════
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.CONCEPTUAL_THEMATIC_RELATIONSHIPS,
                    f"🔗 Analizando relaciones temáticas entre {len(conceptual_quotes)} citas...",
                    45
                )
            
            thematic_relationships = await self._analyze_thematic_relationships(conceptual_quotes)
            logger.info(f"✅ Fase 3: {len(thematic_relationships)} relaciones temáticas")
            
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.CONCEPTUAL_THEMATIC_RELATIONSHIPS,
                    f"✅ {len(thematic_relationships)} relaciones temáticas creadas",
                    75,
                    {"relationships_count": len(thematic_relationships)}
                )
            
            # ═══════════════════════════════════════════════════════════════
            # FASE 4: Identificar perfiles de ideas centrales
            # ═══════════════════════════════════════════════════════════════
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.CONCEPTUAL_IDEA_PROFILES,
                    f"📊 Identificando perfiles de ideas centrales...",
                    80
                )
            
            idea_profiles = await self._identify_central_idea_profiles(conceptual_quotes, thematic_relationships)
            logger.info(f"✅ Fase 4: {len(idea_profiles)} perfiles de ideas identificados")
            
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.CONCEPTUAL_IDEA_PROFILES,
                    f"✅ {len(idea_profiles)} perfiles de ideas identificados",
                    90,
                    {"profiles_count": len(idea_profiles)}
                )
            
            # ═══════════════════════════════════════════════════════════════
            # FINALIZACIÓN
            # ═══════════════════════════════════════════════════════════════
            # Crear resultado final
            result = {
                "conceptual_nodes": conceptual_quotes,
                "thematic_relationships": thematic_relationships,
                "idea_profiles": idea_profiles,
                "metadata": {
                    "dataset_name": dataset_name,
                    "processed_with": "conceptual_graph_processor",
                    "processing_time": datetime.now().isoformat(),
                    "documents_count": len(documents),
                    "quotes_count": len(conceptual_quotes),
                    "relationships_count": len(thematic_relationships),
                    "profiles_count": len(idea_profiles)
                }
            }
            
            logger.info(f"🎉 Procesamiento conceptual completado:")
            logger.info(f"   💭 Citas conceptuales: {len(conceptual_quotes)}")
            logger.info(f"   🔗 Relaciones temáticas: {len(thematic_relationships)}")
            logger.info(f"   📊 Perfiles de ideas: {len(idea_profiles)}")
            
            # Marcar progreso como casi completo (el guardado a Neo4j se hace después)
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.SAVING_TO_NEO4J,
                    f"💾 Guardando {len(conceptual_quotes)} citas y {len(thematic_relationships)} relaciones en Neo4j...",
                    95,
                    {
                        "quotes_extracted": len(conceptual_quotes),
                        "relationships_count": len(thematic_relationships),
                        "entities_count": len(conceptual_quotes)  # Para compatibilidad
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento conceptual: {e}")
            if tracker:
                tracker.set_error(str(e))
            raise
    
    async def _extract_conceptual_quotes(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Método privado: Extrae citas conceptuales usando múltiples estrategias en paralelo.

        Estrategias utilizadas:
        1. LLM para contenido largo (>500 chars)
        2. Análisis de oraciones conceptualmente ricas
        3. Extracción de párrafos con alta densidad conceptual

        OPTIMIZACIÓN: Procesamiento paralelo de documentos para mayor velocidad.

        Elimina duplicados y filtra por calidad (confidence >= 0.6).
        """

        logger.info(f"🚀 Iniciando extracción conceptual paralela de {len(documents)} documentos")

        # OPTIMIZACIÓN: Procesar documentos en paralelo por lotes
        batch_size = min(self.max_parallel_documents, len(documents))
        all_quotes = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"📦 Procesando lote {i//batch_size + 1} de {len(batch)} documentos")

            # Crear tareas para procesar cada documento del lote en paralelo
            tasks = []
            for doc_idx, doc in enumerate(batch):
                global_idx = i + doc_idx
                task = asyncio.create_task(self._process_single_document(doc, global_idx))
                tasks.append(task)

            # Ejecutar todas las tareas del lote en paralelo
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Procesar resultados
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"❌ Error procesando documento: {result}")
                        continue
                    if result:
                        all_quotes.extend(result)

            except Exception as e:
                logger.error(f"❌ Error en procesamiento de lote: {e}")
                # Continuar con el siguiente lote

        logger.info(f"✅ Extracción paralela completada: {len(all_quotes)} citas extraídas")

        # Eliminar duplicados y filtrar por calidad
        unique_quotes = await self._deduplicate_and_filter_quotes(all_quotes)

        return unique_quotes

    async def _process_single_document(self, doc: Dict[str, Any], doc_idx: int) -> List[Dict[str, Any]]:
        """
        Procesa un documento individual extrayendo citas conceptuales usando múltiples estrategias.

        Args:
            doc: Documento a procesar
            doc_idx: Índice global del documento

        Returns:
            Lista de citas conceptuales extraídas del documento
        """
        content = doc.get('content', '')
        logger.debug(f"🔍 _process_single_document: Documento {doc_idx + 1} - Título: {doc.get('title', 'N/A')}, Longitud contenido: {len(content)}")

        if not content:
            logger.warning(f"⚠️ _process_single_document: Documento {doc_idx + 1} tiene contenido vacío. Saltando.")
            return []

        logger.debug(f"🔍 Procesando documento {doc_idx + 1} en paralelo")

        quotes = []

        try:
            # Estrategia 1: Usar LLM para extraer ideas clave (solo si el contenido es significativo)
            if self.llm and len(content) > 500:
                logger.debug(f"🚀 _process_single_document: Llamando a _extract_quotes_with_llm para documento {doc_idx + 1}")
                llm_quotes = await self._extract_quotes_with_llm(content, doc)
                quotes.extend(llm_quotes)
            elif self.llm:
                logger.debug(f"⚠️ Documento {doc_idx + 1}: Contenido demasiado corto ({len(content)} chars) para extracción con LLM (>500 chars requerido)")

            # Estrategia 2: Extraer oraciones conceptualmente ricas
            logger.debug(f"🚀 _process_single_document: Llamando a _extract_rich_sentences para documento {doc_idx + 1}")
            sentence_quotes = await self._extract_rich_sentences(content, doc, doc_idx)
            quotes.extend(sentence_quotes)

            # Estrategia 3: Extraer párrafos con alta densidad conceptual
            logger.debug(f"🚀 _process_single_document: Llamando a _extract_conceptual_paragraphs para documento {doc_idx + 1}")
            paragraph_quotes = await self._extract_conceptual_paragraphs(content, doc, doc_idx)
            quotes.extend(paragraph_quotes)

            doc_id = doc.get("id")
            for quote in quotes:
                quote["source_document_id"] = doc_id

            logger.debug(f"✅ Documento {doc_idx + 1}: {len(quotes)} citas extraídas en total.")
            return quotes


        except Exception as e:
            logger.error(f"❌ Error procesando documento {doc_idx + 1}: {e}", exc_info=True)
            return []

    async def _extract_quotes_with_llm_batch(self, documents_batch: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Extrae citas conceptuales usando LLM con procesamiento por lotes optimizado.
        OPTIMIZACIÓN: Usa fast_llm para tareas de extracción simples.

        Args:
            documents_batch: Lista de tuplas (content, doc_metadata)

        Returns:
            Lista de citas conceptuales extraídas
        """
        # OPTIMIZACIÓN: Usar fast_llm si está disponible, sino main llm
        llm_to_use = self.fast_llm or self.llm
        if not llm_to_use:
            return []

        # Filtrar documentos válidos
        valid_docs = [(content, doc) for content, doc in documents_batch
                     if content and len(content.strip()) >= 50]

        if not valid_docs:
            logger.warning("⚠️ No hay documentos válidos para extracción por lotes")
            return []

        # Generar clave de caché basada en todos los contenidos
        combined_content = "|".join(content[:1000] for content, _ in valid_docs)  # Primeros 1000 chars de cada uno
        cache_key = f"batch_quotes_{hashlib.md5(combined_content.encode()).hexdigest()[:16]}"

        # Verificar caché
        cached_result = self._check_cache(cache_key)
        if cached_result is not None:
            logger.debug(f"📥 Usando resultado en caché para lote de {len(valid_docs)} documentos")
            return cached_result

        try:
            # Crear prompt optimizado para múltiples documentos
            prompt_parts = []
            for i, (content, doc) in enumerate(valid_docs):
                doc_title = doc.get('title', f'doc_{i+1}')
                truncated_content = content[:1500]  # Reducir tokens por documento
                prompt_parts.append(f"Documento {i+1} ({doc_title}):\n{truncated_content}\n---")

            combined_prompt = "\n".join(prompt_parts)

            prompt = f"""
Analiza los siguientes documentos y extrae citas conceptuales clave de cada uno.

Para cada documento, identifica 3-5 citas que expresen ideas conceptuales completas.

Criterios para cada cita:
1. Ideas completas y coherentes
2. Valor conceptual/teórico significativo
3. Representativas del contenido del documento
4. Evita lo puramente descriptivo

Documentos:
{combined_prompt}

Responde en formato JSON:
{{
    "documents": [
        {{
            "doc_index": 0,
            "quotes": [
                {{
                    "text": "cita exacta del documento",
                    "concept": "concepto principal expresado",
                    "importance": "alta/media",
                    "category": "teoría/metodología/conclusión/definición"
                }}
            ]
        }}
    ]
}}

IMPORTANTE:
- Solo el JSON solicitado
- Mantén las citas fieles al texto original
- doc_index corresponde al número del documento (0, 1, 2, etc.)
"""

            logger.info(f"⚡ Usando {'fast_llm' if self.fast_llm and llm_to_use == self.fast_llm else 'main_llm'} para extracción por lotes")
            response = await llm_to_use.ainvoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Parsear respuesta JSON
            import json
            try:
                parsed = json.loads(response_text)
                documents_data = parsed.get("documents", [])

                all_quotes = []
                for doc_data in documents_data:
                    doc_index = doc_data.get("doc_index", 0)
                    if doc_index < len(valid_docs):
                        content, doc = valid_docs[doc_index]
                        quotes_data = doc_data.get("quotes", [])

                        for quote_data in quotes_data:
                            quote = {
                                "id": self._generate_quote_id(quote_data.get("text", "")),
                                "text": quote_data.get("text", ""),
                                "concept": quote_data.get("concept", ""),
                                "importance": quote_data.get("importance", "media"),
                                "category": quote_data.get("category", "general"),
                                "source_document": doc.get('title', f'doc_{doc_index}'),
                                "source_document_id": doc.get('id'),
                                "extraction_method": f"llm_conceptual_batch_{'fast' if self.fast_llm and llm_to_use == self.fast_llm else 'main'}",
                                "confidence": 0.9 if quote_data.get("importance") == "alta" else 0.7,
                                "type": "CONCEPTUAL_QUOTE"
                            }
                            all_quotes.append(quote)

                # Almacenar en caché
                self._store_in_cache(cache_key, all_quotes)
                logger.info(f"✅ Extraídas {len(all_quotes)} citas de {len(valid_docs)} documentos en lote")
                return all_quotes

            except json.JSONDecodeError:
                logger.warning("⚠️ Error parseando respuesta JSON del lote. Usando método individual como fallback...")
                # Fallback: procesar individualmente
                return await self._extract_quotes_with_llm_fallback(valid_docs)

        except Exception as e:
            logger.error(f"❌ Error en extracción por lotes: {e}")
            # Fallback: procesar individualmente
            return await self._extract_quotes_with_llm_fallback(valid_docs)

    async def _extract_quotes_with_llm_fallback(self, valid_docs: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Fallback: extrae citas individualmente cuando el procesamiento por lotes falla."""
        all_quotes = []
        for content, doc in valid_docs:
            quotes = await self._extract_quotes_with_llm(content, doc)
            all_quotes.extend(quotes)
        return all_quotes

    async def _extract_quotes_with_llm(self, content: str, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Usa el LLM para extraer citas conceptuales de alta calidad (método individual)."""

        llm_to_use = self.fast_llm or self.llm
        if not llm_to_use:
            logger.error("❌ _extract_quotes_with_llm: LLM no disponible.")
            return []

        # Validar que el contenido no esté vacío
        if not content or len(content.strip()) < 50:
            logger.warning(f"⚠️ _extract_quotes_with_llm: Contenido demasiado corto ({len(content)} chars) para extracción de citas con LLM.")
            return []
        
        logger.debug(f"📝 _extract_quotes_with_llm: Procesando documento '{doc.get('title', 'N/A')}' con {len(content)} caracteres.")

        # Generar una clave única para el cache
        cache_key = f"extract_quotes_{hashlib.md5(content.encode()).hexdigest()[:16]}"

        # Verificar si el resultado está en caché
        cached_result = self._check_cache(cache_key)
        if cached_result is not None:
            logger.debug(f"📥 _extract_quotes_with_llm: Usando resultado en caché para extracción de citas.")
            return cached_result

        try:
            # Optimizar el prompt para reducir tokens
            prompt = f"""
Analiza el texto y extrae 3-5 citas clave que expresen ideas conceptuales completas.

Criterios:
1. Ideas completas y coherentes
2. Valor conceptual/teórico
3. Representativas del contenido
4. Evita lo puramente descriptivo

Texto:
{content[:2000]}

Responde en formato JSON:
{{
    "quotes": [
        {{
            "text": "cita exacta",
            "concept": "concepto principal",
            "importance": "alta/media",
            "category": "teoría/metodología/conclusión/definición"
        }}
    ]
}}
IMPORTANTE: Solo el JSON solicitado.
"""
            logger.debug(f"💬 _extract_quotes_with_llm: Enviando prompt al LLM (primeros 500 chars): {prompt[:500]}...")

            response = await llm_to_use.ainvoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            logger.debug(f"✅ _extract_quotes_with_llm: Respuesta cruda del LLM (primeros 500 chars): {response_text[:500]}...")

            # Parsear respuesta JSON
            import json
            try:
                parsed = json.loads(response_text)
                quotes_data = parsed.get("quotes", [])

                quotes = []
                for quote_data in quotes_data:
                    quote = {
                        "id": self._generate_quote_id(quote_data.get("text", "")),
                        "text": quote_data.get("text", ""),
                        "concept": quote_data.get("concept", ""),
                        "importance": quote_data.get("importance", "media"),
                        "category": quote_data.get("category", "general"),
                        "source_document": doc.get('title', 'documento'),
                        "extraction_method": "llm_conceptual",
                        "confidence": 0.9 if quote_data.get("importance") == "alta" else 0.7,
                        "type": "CONCEPTUAL_QUOTE"
                    }
                    quotes.append(quote)

                # Almacenar en caché
                self._store_in_cache(cache_key, quotes)
                logger.debug(f"✨ _extract_quotes_with_llm: Extraídas {len(quotes)} citas con LLM.")
                return quotes
            except json.JSONDecodeError as json_e:
                logger.warning(f"⚠️ _extract_quotes_with_llm: Error parseando respuesta JSON del LLM: {json_e}. Intentando extraer JSON válido de la respuesta...")

                # Usar método mejorado de validación y limpieza
                cleaned_response = self._validate_and_clean_llm_response(response_text)
                logger.debug(f"🧹 _extract_quotes_with_llm: Respuesta limpiada (primeros 500 chars): {cleaned_response[:500]}...")

                if not cleaned_response:
                    logger.warning(f"⚠️ _extract_quotes_with_llm: Respuesta vacía o inválida del LLM para extracción de citas después de limpieza.")
                    return []

                try:
                    parsed = json.loads(cleaned_response)
                    quotes_data = parsed.get("quotes", [])
                    quotes = []
                    for quote_data in quotes_data:
                        quote = {
                            "id": self._generate_quote_id(quote_data.get("text", "")),
                            "text": quote_data.get("text", ""),
                            "concept": quote_data.get("concept", ""),
                            "importance": quote_data.get("importance", "media"),
                            "category": quote_data.get("category", "general"),
                            "source_document": doc.get('title', 'documento'),
                            "extraction_method": "llm_conceptual",
                            "confidence": 0.9 if quote_data.get("importance") == "alta" else 0.7,
                            "type": "CONCEPTUAL_QUOTE"
                        }
                        quotes.append(quote)

                    # Almacenar en caché
                    self._store_in_cache(cache_key, quotes)
                    logger.debug(f"✨ _extract_quotes_with_llm: Extraídas {len(quotes)} citas con LLM después de limpieza.")
                    return quotes
                except Exception as e2:
                    logger.error(f"❌ _extract_quotes_with_llm: Error parseando JSON limpiado: {e2}", exc_info=True)
                    return []
        except Exception as e:
            logger.error(f"❌ _extract_quotes_with_llm: Error extrayendo citas con LLM: {e}", exc_info=True)
            return []
    
    async def _extract_rich_sentences(self, content: str, doc: Dict[str, Any], doc_idx: int) -> List[Dict[str, Any]]:
        """Extrae oraciones conceptualmente ricas usando análisis textual."""

        quotes = []

        # Validar que el contenido no esté vacío
        if not content or len(content.strip()) < 100:
            logger.warning("⚠️ Contenido demasiado corto para extracción de oraciones ricas")
            return []

        # Dividir en oraciones
        sentences = re.split(r'[.!?]+', content)

        for sent_idx, sentence in enumerate(sentences):
            sentence = sentence.strip()

            # Filtros de calidad
            if (len(sentence) < 50 or len(sentence) > 300 or
                not self._is_conceptually_rich(sentence)):
                continue

            # Determinar categoría conceptual
            category = self._categorize_sentence(sentence)

            quote = {
                "id": self._generate_quote_id(sentence),
                "text": sentence,
                "concept": self._extract_main_concept(sentence),
                "importance": self._assess_importance(sentence),
                "category": category,
                "source_document": doc.get('title', f'doc_{doc_idx}'),
                "extraction_method": "sentence_analysis",
                "confidence": self._calculate_sentence_confidence(sentence),
                "type": "CONCEPTUAL_QUOTE",
                "position": sent_idx
            }
            quotes.append(quote)

        return quotes
    
    async def _extract_conceptual_paragraphs(self, content: str, doc: Dict[str, Any], doc_idx: int) -> List[Dict[str, Any]]:
        """Extrae párrafos con alta densidad conceptual y asigna categorías descriptivas."""

        quotes = []

        # Validar que el contenido no esté vacío
        if not content or len(content.strip()) < 200:
            logger.warning("⚠️ Contenido demasiado corto para extracción de párrafos conceptuales")
            return []

        # Dividir en párrafos
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        for para_idx, paragraph in enumerate(paragraphs):
            # Filtros de calidad para párrafos
            if (len(paragraph) < 100 or len(paragraph) > 800 or
                not self._is_conceptually_dense_paragraph(paragraph)):
                continue

            # Determinar categoría basada en el contenido del párrafo
            category = self._categorize_paragraph(paragraph)

            quote = {
                "id": self._generate_quote_id(paragraph),
                "text": paragraph,
                "concept": self._extract_paragraph_concept(paragraph),
                "importance": "alta",  # Los párrafos suelen ser más importantes
                "category": category,
                "source_document": doc.get('title', f'doc_{doc_idx}'),
                "extraction_method": "paragraph_analysis",
                "confidence": 0.8,
                "type": "CONCEPTUAL_QUOTE",
                "position": para_idx
            }
            quotes.append(quote)

        return quotes
    
    def _is_conceptually_rich(self, sentence: str) -> bool:
        """Determina si una oración es conceptualmente rica."""
        
        # Palabras que indican riqueza conceptual
        conceptual_indicators = [
            'concepto', 'teoría', 'modelo', 'framework', 'enfoque', 'metodología',
            'principio', 'fundamento', 'base', 'esencia', 'naturaleza',
            'implica', 'sugiere', 'demuestra', 'evidencia', 'indica',
            'relación', 'conexión', 'vínculo', 'asociación',
            'importante', 'fundamental', 'esencial', 'clave', 'crucial',
            'permite', 'facilita', 'posibilita', 'genera', 'produce'
        ]
        
        sentence_lower = sentence.lower()
        
        # Contar indicadores conceptuales
        conceptual_score = sum(1 for indicator in conceptual_indicators 
                              if indicator in sentence_lower)
        
        # Verificar estructura conceptual (verbos de pensamiento, conectores)
        thinking_verbs = ['considera', 'analiza', 'examina', 'evalúa', 'propone', 'argumenta']
        has_thinking_verbs = any(verb in sentence_lower for verb in thinking_verbs)
        
        return conceptual_score >= 2 or has_thinking_verbs
    
    def _categorize_sentence(self, sentence: str) -> str:
        """Categoriza una oración según su tipo conceptual con categorías más descriptivas."""
        
        sentence_lower = sentence.lower()
        
        if any(word in sentence_lower for word in ['define', 'definición', 'concepto de', 'se entiende por']):
            return 'definición_conceptual'
        elif any(word in sentence_lower for word in ['metodología', 'método', 'procedimiento', 'proceso']):
            return 'enfoque_metodológico'
        elif any(word in sentence_lower for word in ['teoría', 'modelo', 'framework', 'enfoque teórico']):
            return 'marco_teórico'
        elif any(word in sentence_lower for word in ['concluye', 'resultado', 'evidencia', 'demuestra']):
            return 'hallazgo_empírico'
        elif any(word in sentence_lower for word in ['relación', 'conexión', 'vínculo', 'asociación']):
            return 'relación_temática'
        elif any(word in sentence_lower for word in ['ejemplo', 'caso de estudio', 'ilustración']):
            return 'ejemplo_práctico'
        elif any(word in sentence_lower for word in ['crítica', 'limitación', 'desafío']):
            return 'análisis_crítico'
        else:
            return 'desarrollo_teórico'
    
    def _extract_main_concept(self, text: str) -> str:
        """Extrae el concepto principal de un texto."""
        
        # Buscar sustantivos clave y frases nominales importantes
        # Implementación simplificada - se puede mejorar con NLP
        
        words = text.split()
        
        # Buscar patrones conceptuales
        concept_patterns = [
            r'el concepto de (\w+(?:\s+\w+)*)',
            r'la teoría de (\w+(?:\s+\w+)*)',
            r'el modelo de (\w+(?:\s+\w+)*)',
            r'la metodología de (\w+(?:\s+\w+)*)'
        ]
        
        for pattern in concept_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).title()
        
        # Fallback: usar las primeras palabras significativas
        significant_words = [word for word in words[:10] 
                           if len(word) > 3 and word.lower() not in ['este', 'esta', 'estos', 'estas']]
        
        return ' '.join(significant_words[:3]) if significant_words else "Concepto general"
    
    def _assess_importance(self, sentence: str) -> str:
        """Evalúa la importancia de una oración."""
        
        high_importance_indicators = [
            'fundamental', 'esencial', 'crucial', 'importante', 'clave',
            'principal', 'central', 'básico', 'primordial'
        ]
        
        sentence_lower = sentence.lower()
        importance_score = sum(1 for indicator in high_importance_indicators 
                              if indicator in sentence_lower)
        
        if importance_score >= 2:
            return 'alta'
        elif importance_score >= 1:
            return 'media'
        else:
            return 'media'  # Default
    
    def _calculate_sentence_confidence(self, sentence: str) -> float:
        """Calcula la confianza de una oración conceptual."""
        
        # Factores que aumentan la confianza
        factors = {
            'length': min(1.0, len(sentence) / 150),  # Oraciones de longitud media
            'conceptual_words': min(1.0, len([w for w in sentence.split() 
                                            if len(w) > 6]) / 10),
            'structure': 0.8 if any(conn in sentence.lower() 
                                  for conn in ['porque', 'debido', 'por tanto', 'así']) else 0.5
        }
        
        confidence = sum(factors.values()) / len(factors)
        return round(confidence, 2)
    
    def _categorize_paragraph(self, paragraph: str) -> str:
        """Categoriza un párrafo según su contenido conceptual."""
        
        paragraph_lower = paragraph.lower()
        
        if any(word in paragraph_lower for word in ['teoría', 'modelo', 'framework', 'enfoque teórico']):
            return 'marco_teórico'
        elif any(word in paragraph_lower for word in ['metodología', 'método', 'procedimiento', 'proceso']):
            return 'enfoque_metodológico'
        elif any(word in paragraph_lower for word in ['resultado', 'evidencia', 'hallazgo']):
            return 'hallazgo_empírico'
        elif any(word in paragraph_lower for word in ['ejemplo', 'caso de estudio', 'ilustración']):
            return 'ejemplo_práctico'
        elif any(word in paragraph_lower for word in ['crítica', 'limitación', 'desafío']):
            return 'análisis_crítico'
        else:
            return 'desarrollo_teórico'

    def _is_conceptually_dense_paragraph(self, paragraph: str) -> bool:
        """Determina si un párrafo tiene alta densidad conceptual."""
        
        sentences = re.split(r'[.!?]+', paragraph)
        conceptual_sentences = sum(1 for sent in sentences
                                  if self._is_conceptually_rich(sent.strip()))
        
        density = conceptual_sentences / max(len(sentences), 1)
        return density >= 0.5  # Al menos 50% de oraciones conceptuales
    
    def _extract_paragraph_concept(self, paragraph: str) -> str:
        """Extrae el concepto principal de un párrafo."""
        
        # Usar la primera oración como base conceptual
        first_sentence = paragraph.split('.')[0]
        return self._extract_main_concept(first_sentence)
    
    def _generate_quote_id(self, text: str) -> str:
        """Genera un ID único para una cita."""
        
        # Usar hash del texto para generar ID único
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
        return f"quote_{text_hash}"
    
    async def _deduplicate_and_filter_quotes(self, quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Elimina duplicados y filtra citas por calidad."""
        
        # Eliminar duplicados exactos
        seen_texts = set()
        unique_quotes = []
        
        for quote in quotes:
            text = quote.get('text', '').strip()
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_quotes.append(quote)
        
        # Filtrar por calidad mínima
        quality_quotes = [quote for quote in unique_quotes 
                         if quote.get('confidence', 0) >= 0.6]
        
        # Ordenar por importancia y confianza
        quality_quotes.sort(key=lambda x: (
            x.get('importance') == 'alta',
            x.get('confidence', 0)
        ), reverse=True)
        
        return quality_quotes

    async def _analyze_thematic_relationships(self, quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Método privado optimizado: Analiza relaciones temáticas usando embeddings y LLM por lotes en paralelo.
        
        Optimizaciones implementadas:
        1. Procesamiento paralelo de lotes usando asyncio.gather()
        2. Agrupación inteligente por similitud y categoría
        3. Lotes dinámicos basados en confianza
        4. Caché agresivo para reducir llamadas LLM
        5. Early exit para relaciones regla-basadas de alta confianza
        
        Proceso optimizado:
        1. Calcula embeddings para todas las citas
        2. Identifica pares candidatos (similitud > 0.7)
        3. Agrupa por similitud y categorías
        4. Procesa en lotes paralelos (25-50 pares por llamada)
        5. Procesa lotes de alta confianza con reglas
        6. Genera relaciones basadas en categorías y estructura
        7. Crea relaciones estructurales (mismo documento/categoría)
        """

        if len(quotes) < 2:
            return []

        logger.info(f"🔗 Analizando relaciones temáticas entre {len(quotes)} citas con optimización paralela.")
        relationships = []

        # FASE 1: Crear relaciones por categoría PRIMERO (sin importar similitud)
        logger.info("🏷️ Creando relaciones por categoría - TODAS las citas de la misma categoría")
        category_relationships = await self._create_category_relationships(quotes)
        relationships.extend(category_relationships)
        logger.info(f"✅ {len(category_relationships)} relaciones por categoría creadas")

        # FASE 2: Análisis de similitud para relaciones temáticas adicionales
        quote_texts = [f"{quote['concept']}: {quote['text']}" for quote in quotes]
        if self.embedding_model is None:
            logger.error("❌ Modelo de embeddings no está inicializado.")
            raise RuntimeError("Modelo de embeddings no está inicializado.")
        
        try:
            # Usar aembed_documents para no bloquear el loop de eventos
            embeddings = await self.embedding_model.aembed_documents(quote_texts)
        except Exception as e:
            logger.error(f"Error generando embeddings: {e}")
            raise

        try:
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            logger.warning("⚠️ sklearn no está instalado. Usando cálculo manual de similitud coseno.")
            # Fallback: calcular similitud coseno manualmente
            import numpy as np
            embeddings_array = np.array(embeddings)
            norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            normalized = embeddings_array / norms
            # Ejecutar el cálculo de numpy en un hilo para no bloquear
            similarities = await asyncio.to_thread(np.dot, normalized, normalized.T)
        else:
            # Ejecutar cosine_similarity en un hilo para no bloquear
            similarities = await asyncio.to_thread(cosine_similarity, embeddings)

        # Identificar y agrupar pares candidatos para análisis adicional
        candidate_pairs = self._group_candidate_pairs_by_similarity(quotes, similarities)
        
        if self.llm:
            logger.info(f"🔎 {len(candidate_pairs['high'] + candidate_pairs['medium'] + candidate_pairs['low'])} pares de citas candidatas para análisis optimizado.")

            # Procesamiento paralelo de lotes por grupos de similitud
            all_batch_tasks = []
            
            # Procesar grupos de alta y media similitud en paralelo
            for similarity_group, pairs in [('high', candidate_pairs['high']), ('medium', candidate_pairs['medium'])]:
                if pairs:
                    # Determinar tamaño de lote dinámicamente basado en calidad
                    if similarity_group == 'high':
                        batch_size = min(75, max(25, len(pairs) // 2))  # Lotes más grandes para alta calidad
                    else:
                        batch_size = min(50, max(20, len(pairs) // 3))  # Lotes medianos para media calidad

                    logger.info(f"📦 {similarity_group} similitud: {len(pairs)} pares → lotes de {batch_size}")

                    # Crear tareas de lotes para procesamiento paralelo
                    batch_tasks = self._create_parallel_batch_tasks(pairs, quotes, batch_size)
                    all_batch_tasks.extend(batch_tasks)
            
            # Ejecutar todos los lotes en paralelo
            if all_batch_tasks:
                logger.info(f"🚀 Procesando {len(all_batch_tasks)} lotes en paralelo...")
                batch_results = await asyncio.gather(*all_batch_tasks, return_exceptions=True)
                
                # Procesar resultados
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ Error en lote {i}: {result}")
                        continue
                    
                    if result:
                        for res in result:
                            try:
                                original_pair_info = res["original_pair"]
                                quote1_idx = original_pair_info["quote1_idx"]
                                quote2_idx = original_pair_info["quote2_idx"]
                                quote1 = quotes[quote1_idx]
                                quote2 = quotes[quote2_idx]
                                similarity = original_pair_info["similarity"]

                                relationship = {
                                    "id": f"thematic_rel_{len(relationships)}",
                                    "source_id": quote1["id"],
                                    "target_id": quote2["id"],
                                    "type": res.get("type", "RELACION_TEMATICA_LLM"),
                                    "similarity_score": float(similarity),
                                    "description": res.get("description", "Las ideas están temáticamente relacionadas (LLM)."),
                                    "confidence": self._calculate_relationship_confidence(
                                        quote1, quote2, similarity
                                    ),
                                    "extraction_method": f"llm_thematic_parallel_{original_pair_info.get('batch_group', 'default')}"
                                }
                                relationships.append(relationship)
                            except (KeyError, IndexError) as e:
                                logger.error(f"❌ Error procesando resultado de lote: {e} - Data: {res}")
            
            # Procesar pares de baja similitud con reglas optimizadas
            if candidate_pairs['low']:
                logger.info(f"📏 Procesando {len(candidate_pairs['low'])} pares de baja similitud con reglas optimizadas...")
                rule_relationships = await self._create_rule_based_relationships_batch(candidate_pairs['low'], quotes)
                relationships.extend(rule_relationships)
        
        else:
            logger.warning("⚠️ LLM no disponible para análisis de relaciones temáticas. Recurriendo a reglas optimizadas.")
            # Crear todas las relaciones con reglas optimizadas
            all_pairs = candidate_pairs['high'] + candidate_pairs['medium'] + candidate_pairs['low']
            rule_relationships = await self._create_rule_based_relationships_batch(all_pairs, quotes)
            relationships.extend(rule_relationships)

        # Agregar relaciones estructurales adicionales (no dependen del LLM)
        document_relationships = await self._create_document_relationships(quotes)
        relationships.extend(document_relationships)

        logger.info(f"✅ {len(relationships)} relaciones temáticas creadas en total con optimización paralela.")
        return relationships
    
    def _group_candidate_pairs_by_similarity(self, quotes: List[Dict[str, Any]], similarities) -> Dict[str, List[Dict[str, Any]]]:
        """
        Agrupa pares candidatos por rangos de similitud para procesamiento optimizado.
        
        Args:
            quotes: Lista de citas
            similarities: Matriz de similitudes
            
        Returns:
            Diccionario con pares agrupados por similitud
        """
        grouped_pairs = {
            'high': [],     # Similitud > 0.85 - muy alta
            'medium': [],   # Similitud 0.75-0.85 - alta
            'low': []       # Similitud 0.7-0.75 - media
        }
        
        for i in range(len(quotes)):
            for j in range(i + 1, len(quotes)):
                similarity = float(similarities[i][j])
                if similarity > 0.7:  # Umbral mínimo
                    pair = {
                        "quote1_idx": i,
                        "quote2_idx": j,
                        "similarity": similarity,
                        "quotes": [quotes[i], quotes[j]]  # Incluir quotes para análisis
                    }
                    
                    if similarity > 0.85:
                        grouped_pairs['high'].append(pair)
                    elif similarity > 0.75:
                        grouped_pairs['medium'].append(pair)
                    else:
                        grouped_pairs['low'].append(pair)
        
        logger.info(f"📊 Pares agrupados: {len(grouped_pairs['high'])} alta, {len(grouped_pairs['medium'])} media, {len(grouped_pairs['low'])} baja similitud")
        return grouped_pairs
    
    def _create_parallel_batch_tasks(self, pairs: List[Dict[str, Any]], quotes: List[Dict[str, Any]], batch_size: int) -> List[asyncio.Task]:
        """
        Crea tareas para procesamiento paralelo de lotes respetando el límite de paralelismo.
        
        Args:
            pairs: Lista de pares a procesar
            quotes: Lista completa de citas
            batch_size: Tamaño del lote
            
        Returns:
            Lista de tareas asyncio (limitadas por max_parallel_batches)
        """
        tasks = []
        
        # Calcular número total de lotes
        total_batches = (len(pairs) + batch_size - 1) // batch_size
        batches_to_process = min(total_batches, self.max_parallel_batches)
        
        logger.info(f"📦 Creando {batches_to_process} tareas paralelas (de {total_batches} lotes totales)")
        
        for i in range(0, len(pairs), batch_size):
            batch_num = i // batch_size
            if batch_num >= batches_to_process:
                break  # No crear más tareas del límite
                
            batch = pairs[i:i + batch_size]
            
            # Crear tarea para el lote
            task = asyncio.create_task(
                self._create_batch_llm_relationships_optimized(batch, quotes, f"batch_{batch_num}")
            )
            tasks.append(task)
        
        return tasks
    
    async def _create_rule_based_relationships_batch(self, pairs: List[Dict[str, Any]], quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Crea relaciones basadas en reglas para pares de baja confianza de forma optimizada.
        
        Args:
            pairs: Lista de pares a procesar
            quotes: Lista completa de citas
            
        Returns:
            Lista de relaciones generadas
        """
        relationships = []
        
        for pair in pairs:
            quote1_idx = pair["quote1_idx"]
            quote2_idx = pair["quote2_idx"]
            quote1 = quotes[quote1_idx]
            quote2 = quotes[quote2_idx]
            similarity = pair["similarity"]
            
            # Determinar si la relación puede ser determinada por reglas
            relationship_type = self._determine_thematic_relationship_type(quote1, quote2, similarity)
            
            # Solo usar reglas para casos claros
            if self._is_rule_determinable_relationship(quote1, quote2, relationship_type):
                description = self._generate_relationship_description(quote1, quote2, relationship_type)
                confidence = self._calculate_relationship_confidence(quote1, quote2, similarity)
                
                relationships.append({
                    "id": f"thematic_rel_rule_{len(relationships)}",
                    "source_id": quote1["id"],
                    "target_id": quote2["id"],
                    "type": relationship_type,
                    "similarity_score": similarity,
                    "description": description,
                    "confidence": confidence,
                    "extraction_method": "rule_based_optimized"
                })
            else:
                # OPTIMIZACIÓN: Para pares de baja similitud sin reglas claras, NO usar LLM individual.
                # Usar relación por defecto directamente para evitar latencia excesiva.
                default_rel = self._create_default_relationship(quote1_idx, quote2_idx, similarity)
                relationships.append({
                    "id": f"thematic_rel_default_{len(relationships)}",
                    "source_id": quote1["id"],
                    "target_id": quote2["id"],
                    "type": default_rel["type"],
                    "similarity_score": similarity,
                    "description": default_rel["description"],
                    "confidence": default_rel["confidence"],
                    "extraction_method": "default_optimized_fast"
                })
        
        return relationships
    
    def _is_rule_determinable_relationship(self, quote1: Dict, quote2: Dict, relationship_type: str) -> bool:
        """
        Determina si una relación puede ser identificada confiablemente por reglas.
        
        Args:
            quote1: Primera cita
            quote2: Segunda cita
            relationship_type: Tipo de relación propuesto
            
        Returns:
            True si la relación puede ser determinada por reglas
        """
        # Relaciones claramente determinables por reglas
        rule_determinable_types = [
            "CONCEPTOS_RELACIONADOS",
            "MARCOS_TEORICOS_AFINES", 
            "ENFOQUES_METODOLOGICOS",
            "HALLAZGOS_CONVERGENTES",
            "FUNDAMENTACION_TEORICA",
            "APLICACION_METODOLOGICA",
            "VALIDACION_EMPIRICA",
            "CONFIRMACION_CONCEPTUAL"
            "EJEMPLO_PRÁCTICO"
        ]
        
        # Si es una relación de categoría clara, usar reglas
        if relationship_type in rule_determinable_types:
            return True
        
        # Si ambas citas tienen la misma categoría, probablemente sea determinable
        cat1 = quote1.get("category", "")
        cat2 = quote2.get("category", "")
        if cat1 and cat2 and cat1 == cat2:
            return True
        
        # Si tienen conceptos muy similares, probablemente sea determinable
        concept1 = quote1.get("concept", "").lower()
        concept2 = quote2.get("concept", "").lower()
        if concept1 and concept2:
            # Verificar si comparten palabras clave significativas
            words1 = set(concept1.split())
            words2 = set(concept2.split())
            common_words = words1.intersection(words2)
            if len(common_words) >= 2:  # Al menos 2 palabras en común
                return True
        
        return False
    
    async def _create_batch_llm_relationships_optimized(self, batch: List[Dict[str, Any]], quotes: List[Dict[str, Any]], batch_id: str) -> List[Dict[str, Any]]:
        """
        Versión optimizada para crear relaciones de un lote usando LLM.
        
        Args:
            batch: Lista de pares de citas para analizar
            quotes: Lista completa de citas
            batch_id: Identificador del lote
            
        Returns:
            Lista de relaciones temáticas generadas por el LLM
        """
        llm_to_use = self.fast_llm or self.llm
        if not llm_to_use:
            logger.error("❌ LLM no disponible para crear relaciones por lotes optimizadas")
            return []
        
        batch_results = []
        
        # Crear un prompt optimizado para múltiples pares
        prompt = self._build_optimized_batch_prompt(batch, quotes)
        
        try:
            # Cache key para el lote completo
            batch_content_hash = hashlib.md5(str(batch).encode()).hexdigest()[:12]
            cache_key = f"batch_relationships_{batch_id}_{batch_content_hash}"
            
            # Verificar caché
            cached_result = self._check_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"📥 Usando resultado en caché para lote {batch_id}")
                return cached_result
            
            # Llamar al LLM con el lote completo
            response = await asyncio.wait_for(
                llm_to_use.ainvoke(prompt), 
                timeout=60.0  # Timeout más largo para lotes grandes
            )
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Procesar respuesta
            batch_relationships = self._parse_optimized_batch_response(response_text, batch, quotes, batch_id)
            
            if batch_relationships:
                # Almacenar en caché
                self._store_in_cache(cache_key, batch_relationships)
                logger.debug(f"✅ LLM procesó lote {batch_id} con {len(batch_relationships)} relaciones")
                return batch_relationships
            else:
                # Fallback: procesar pares individualmente
                logger.warning(f"⚠️ Falló procesamiento de lote {batch_id}, usando fallback individual")
                return await self._fallback_individual_processing(batch, quotes, batch_id)
                
        except Exception as e:
            logger.error(f"❌ Error en procesamiento de lote {batch_id}: {e}")
            # Fallback a procesamiento individual
            return await self._fallback_individual_processing(batch, quotes, batch_id)
    
    def _build_optimized_batch_prompt(self, batch: List[Dict[str, Any]], quotes: List[Dict[str, Any]]) -> str:
        """
        Construye un prompt optimizado para analizar múltiples pares de citas.
        
        Args:
            batch: Lista de pares
            quotes: Lista completa de citas
            
        Returns:
            Prompt formateado para el LLM
        """
        pairs_info = []
        for i, pair in enumerate(batch):
            quote1_idx = pair["quote1_idx"]
            quote2_idx = pair["quote2_idx"]
            similarity = pair["similarity"]
            
            quote1 = quotes[quote1_idx]
            quote2 = quotes[quote2_idx]
            
            pair_info = f"""Par {i+1}:
Cita 1: {quote1['text'][:200]}...
Concepto: {quote1['concept']}
Categoría: {quote1['category']}

Cita 2: {quote2['text'][:200]}...
Concepto: {quote2['concept']}
Categoría: {quote2['category']}

Similitud: {similarity:.3f}"""
            pairs_info.append(pair_info)
        
        return f"""Analiza las siguientes {len(batch)} pares de citas conceptuales y determina las relaciones temáticas entre ellas.

{pairs_info}

Para cada par, responde con un objeto JSON válido en el siguiente formato:
[
    {{
        "pair_index": {0},
        "type": "tipo_de_relacion",
        "description": "descripción detallada de la relación",
        "confidence": "alta"
    }},
    ...
]

Tipos de relación disponibles (Usa los más específicos posibles):
- ES_PARTE_DE (Una idea es componente de otra)
- CONTIENE_A (Una idea engloba a otra)
- VIVE_EN (Relación de ubicación o residencia)
- PERTENECE_A (Relación de propiedad o membresía)
- TRABAJA_EN (Relación laboral)
- CONCEPTOS_RELACIONADOS
- MARCOS_TEORICOS_AFINES
- ENFOQUES_METODOLOGICOS
- HALLAZGOS_CONVERGENTES
- FUNDAMENTACION_TEORICA
- APLICACION_METODOLOGICA
- VALIDACION_EMPIRICA
- CONFIRMACION_CONCEPTUAL
- ALTA_CONVERGENCIA_TEMATICA
- CONVERGENCIA_TEMATICA
- RELACION_TEMATICA
- EJEMPLO_PRÁCTICO

Responde ÚNICAMENTE con el array JSON solicitado."""
    
    def _parse_optimized_batch_response(self, response_text: str, batch: List[Dict[str, Any]], quotes: List[Dict[str, Any]], batch_id: str) -> List[Dict[str, Any]]:
        """
        Parsea la respuesta optimizada del LLM para un lote.
        
        Args:
            response_text: Texto de respuesta del LLM
            batch: Lista de pares procesados
            quotes: Lista completa de citas
            batch_id: Identificador del lote
            
        Returns:
            Lista de relaciones parseadas
        """
        import json
        
        try:
            # Limpiar respuesta
            cleaned_response = self._validate_and_clean_response(response_text)
            if not cleaned_response:
                return []
            
            # Parsear JSON
            parsed_relationships = json.loads(cleaned_response)
            
            if not isinstance(parsed_relationships, list):
                return []
            
            # Convertir a formato estándar
            results = []
            for rel_data in parsed_relationships:
                if not isinstance(rel_data, dict) or "pair_index" not in rel_data:
                    continue
                
                pair_index = rel_data["pair_index"]
                if 0 <= pair_index < len(batch):
                    pair = batch[pair_index]
                    quote1_idx = pair["quote1_idx"]
                    quote2_idx = pair["quote2_idx"]
                    similarity = pair["similarity"]
                    
                    # Convertir confianza
                    confidence_str = rel_data.get("confidence", "media").lower()
                    confidence_map = {"alta": 0.9, "media": 0.7, "baja": 0.5}
                    confidence = confidence_map.get(confidence_str, 0.7)
                    
                    result = {
                        "original_pair": {
                            "quote1_idx": quote1_idx,
                            "quote2_idx": quote2_idx,
                            "similarity": similarity,
                            "batch_group": batch_id
                        },
                        "type": rel_data.get("type", "RELACION_TEMATICA"),
                        "description": rel_data.get("description", "Relación temática"),
                        "confidence": confidence
                    }
                    results.append(result)
            
            logger.debug(f"✅ Parseados {len(results)} relaciones del lote {batch_id}")
            return results
            
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"⚠️ Error parseando respuesta optimizada del lote {batch_id}: {e}")
            return []
    
    async def _fallback_individual_processing(self, batch: List[Dict[str, Any]], quotes: List[Dict[str, Any]], batch_id: str) -> List[Dict[str, Any]]:
        """
        Fallback para procesar pares individualmente cuando falla el procesamiento por lotes.
        
        Args:
            batch: Lista de pares
            quotes: Lista completa de citas
            batch_id: Identificador del lote
            
        Returns:
            Lista de relaciones procesadas individualmente
        """
        results = []
        
        for i, pair in enumerate(batch):
            try:
                quote1_idx = pair["quote1_idx"]
                quote2_idx = pair["quote2_idx"]
                quote1 = quotes[quote1_idx]
                quote2 = quotes[quote2_idx]
                similarity = pair["similarity"]
                
                cache_key = f"fallback_individual_{quote1_idx}_{quote2_idx}"
                
                result = await self._call_llm_with_retry_and_validation(
                    quote1, quote2, similarity, cache_key, quote1_idx, quote2_idx
                )
                
                if result:
                    result["original_pair"]["batch_group"] = f"{batch_id}_fallback"
                    results.append(result)
                    
            except Exception as e:
                logger.warning(f"⚠️ Falló procesamiento individual del par {i} en lote {batch_id}: {e}")
                # Usar relación por defecto
                default_rel = self._create_default_relationship(
                    pair["quote1_idx"], pair["quote2_idx"], pair["similarity"]
                )
                default_rel["original_pair"] = {
                    "quote1_idx": pair["quote1_idx"],
                    "quote2_idx": pair["quote2_idx"],
                    "similarity": pair["similarity"],
                    "batch_group": f"{batch_id}_default"
                }
                results.append(default_rel)
        
        logger.info(f"📥 Fallback completado para lote {batch_id}: {len(results)} relaciones")
        return results

    def _determine_thematic_relationship_type(self, quote1: Dict, quote2: Dict, similarity: float) -> str:
        """Determina el tipo de relación temática entre dos citas."""
        
        cat1 = quote1.get("category", "")
        cat2 = quote2.get("category", "")
        concept1 = quote1.get("concept", "").lower()
        concept2 = quote2.get("concept", "").lower()
        text1 = quote1.get("text", "").lower()
        
        # Relaciones jerárquicas y de pertenencia (Basado en texto)
        if any(p in text1 for p in ["es parte de", "pertenece a", "miembro de"]):
            return "ES_PARTE_DE"
        if any(p in text1 for p in ["incluye", "contiene", "conformado por"]):
            return "CONTIENE_A"
        if any(p in text1 for p in ["vive en", "reside en", "ubicado en"]):
            return "VIVE_EN"
            
        # Relaciones por categoría
        if cat1 == cat2:
            if cat1 == "definición_conceptual":
                return "CONCEPTOS_RELACIONADOS"
            elif cat1 == "marco_teórico":
                return "MARCOS_TEORICOS_AFINES"
            elif cat1 == "enfoque_metodológico":
                return "ENFOQUES_METODOLOGICOS"
            elif cat1 == "hallazgo_empírico":
                return "HALLAZGOS_CONVERGENTES"
            elif cat1 == "ejemplo_práctico":
                return "EJEMPLOS_COMPLEMENTARIOS"
            elif cat1 == "análisis_crítico":
                return "ANALISIS_CRITICO_RELACIONADO"
            else:
                return "DESARROLLO_TEMATICO"
        
        # Relaciones entre categorías diferentes
        if (cat1 == "definición_conceptual" and cat2 == "marco_teórico") or (cat1 == "marco_teórico" and cat2 == "definición_conceptual"):
            return "FUNDAMENTACION_TEORICA"
        elif (cat1 == "marco_teórico" and cat2 == "enfoque_metodológico") or (cat1 == "enfoque_metodológico" and cat2 == "marco_teórico"):
            return "APLICACION_METODOLOGICA"
        elif (cat1 == "enfoque_metodológico" and cat2 == "hallazgo_empírico") or (cat1 == "hallazgo_empírico" and cat2 == "enfoque_metodológico"):
            return "VALIDACION_EMPIRICA"
        elif (cat1 == "definición_conceptual" and cat2 == "hallazgo_empírico") or (cat1 == "hallazgo_empírico" and cat2 == "definición_conceptual"):
            return "CONFIRMACION_CONCEPTUAL"
        
        # Relación temática general basada en similitud
        if similarity > 0.85:
            return "ALTA_CONVERGENCIA_TEMATICA"
        elif similarity > 0.75:
            return "CONVERGENCIA_TEMATICA"
        else:
            return "RELACION_TEMATICA"

    def _generate_relationship_description(self, quote1: Dict, quote2: Dict, rel_type: str) -> str:
        """Genera descripción de la relación entre dos citas."""

        concept1 = quote1.get("concept", "Concepto A")
        concept2 = quote2.get("concept", "Concepto B")

        descriptions = {
            "ES_PARTE_DE": f"'{concept1}' es parte integral o pertenece a '{concept2}'",
            "CONTIENE_A": f"'{concept1}' incluye o contiene conceptualmente a '{concept2}'",
            "VIVE_EN": f"'{concept1}' reside, vive o se ubica en '{concept2}'",
            "CONCEPTOS_RELACIONADOS": f"Los conceptos '{concept1}' y '{concept2}' están conceptualmente relacionados",
            "MARCOS_TEORICOS_AFINES": f"Los marcos teóricos de '{concept1}' y '{concept2}' son afines",
            "ENFOQUES_METODOLOGICOS": f"Los enfoques metodológicos de '{concept1}' y '{concept2}' son complementarios",
            "HALLAZGOS_CONVERGENTES": f"Los hallazgos sobre '{concept1}' y '{concept2}' convergen",
            "FUNDAMENTACION_TEORICA": f"'{concept1}' fundamenta teóricamente a '{concept2}'",
            "APLICACION_METODOLOGICA": f"'{concept1}' se aplica metodológicamente en '{concept2}'",
            "VALIDACION_EMPIRICA": f"'{concept1}' valida empíricamente '{concept2}'",
            "CONFIRMACION_CONCEPTUAL": f"'{concept1}' confirma conceptualmente '{concept2}'",
            "ALTA_CONVERGENCIA_TEMATICA": f"'{concept1}' y '{concept2}' muestran alta convergencia temática",
            "CONVERGENCIA_TEMATICA": f"'{concept1}' y '{concept2}' convergen temáticamente",
            "RELACION_TEMATICA": f"'{concept1}' y '{concept2}' están temáticamente relacionados"
        }

        return descriptions.get(rel_type, f"Relación temática entre '{concept1}' y '{concept2}'")

    def _calculate_relationship_confidence(self, quote1: Dict, quote2: Dict, similarity: float) -> float:
        """Calcula la confianza de una relación temática."""

        # Factores que afectan la confianza
        conf1 = quote1.get("confidence", 0.5)
        conf2 = quote2.get("confidence", 0.5)

        # Confianza base de las citas
        base_confidence = (conf1 + conf2) / 2

        # Ajuste por similitud semántica
        similarity_boost = min(0.3, (similarity - 0.7) * 1.5) if similarity > 0.7 else 0

        # Ajuste por categorías compatibles
        cat1 = quote1.get("category", "")
        cat2 = quote2.get("category", "")
        category_boost = 0.1 if cat1 == cat2 else 0.05

        final_confidence = base_confidence + similarity_boost + category_boost
        # CAMBIO: Asegurar que el resultado final sea un float nativo
        return float(round(min(1.0, final_confidence), 2))

    async def _create_category_relationships(self, quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Crea relaciones entre TODAS las citas de la misma categoría conceptual."""

        relationships = []

        # Agrupar por categoría
        categories = {}
        for quote in quotes:
            category = quote.get("category", "general")
            if category not in categories:
                categories[category] = []
            categories[category].append(quote)

        # Crear relaciones dentro de cada categoría - TODAS las citas de la misma categoría
        for category, category_quotes in categories.items():
            if len(category_quotes) < 2:
                continue

            logger.info(f"🔗 Creando relaciones para categoría '{category}': {len(category_quotes)} citas")
            
            # Conectar TODAS las citas de la misma categoría, no solo las importantes
            for i, quote1 in enumerate(category_quotes):
                for j, quote2 in enumerate(category_quotes[i+1:], i+1):
                    # Determinar confianza basada en importancia
                    confidence = 0.9 if (quote1.get("importance") == "alta" and quote2.get("importance") == "alta") else 0.7
                    
                    # Determinar tipo de relación específico por categoría
                    category_specific_type = self._get_category_relationship_type(category)
                    
                    relationship = {
                        "id": f"category_rel_{len(relationships)}",
                        "source_id": quote1["id"],
                        "target_id": quote2["id"],
                        "type": category_specific_type,
                        "description": f"Ambas citas pertenecen a la categoría '{category}': {quote1.get('concept', 'N/A')} ↔ {quote2.get('concept', 'N/A')}",
                        "confidence": confidence,
                        "extraction_method": "category_comprehensive",
                        "category": category
                    }
                    relationships.append(relationship)

        logger.info(f"✅ Creadas {len(relationships)} relaciones por categoría")
        return relationships
    
    def _get_category_relationship_type(self, category: str) -> str:
        """Determina el tipo de relación específico para cada categoría."""
        category_type_mapping = {
            "definición_conceptual": "MISMA_DEFINICION_CONCEPTUAL",
            "marco_teórico": "MISMO_MARCO_TEORICO", 
            "enfoque_metodológico": "MISMO_ENFOQUE_METODOLOGICO",
            "hallazgo_empírico": "MISMO_HALLAZGO_EMPIRICO",
            "relación_temática": "MISMA_RELACION_TEMATICA",
            "ejemplo_práctico": "MISMO_EJEMPLO_PRACTICO",
            "análisis_crítico": "MISMO_ANALISIS_CRITICO",
            "desarrollo_teórico": "MISMO_DESARROLLO_TEORICO"
        }
        
        return category_type_mapping.get(category, f"MISMA_CATEGORIA_{category.upper()}")

    async def _create_document_relationships(self, quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Crea relaciones entre citas del mismo documento."""

        relationships = []

        # Agrupar por documento fuente
        documents = {}
        for quote in quotes:
            doc = quote.get("source_document", "unknown")
            if doc not in documents:
                documents[doc] = []
            documents[doc].append(quote)

        # Crear relaciones secuenciales dentro de cada documento
        for doc, doc_quotes in documents.items():
            if len(doc_quotes) < 2:
                continue

            # Ordenar por posición si está disponible
            doc_quotes.sort(key=lambda x: x.get("position", 0))

            # Conectar citas consecutivas importantes
            for i in range(len(doc_quotes) - 1):
                quote1 = doc_quotes[i]
                quote2 = doc_quotes[i + 1]

                # Solo conectar si ambas son importantes
                if (quote1.get("importance") == "alta" and
                    quote2.get("importance") == "alta"):

                    relationship = {
                        "id": f"doc_seq_{len(relationships)}",
                        "source_id": quote1["id"],
                        "target_id": quote2["id"],
                        "type": "SECUENCIA_CONCEPTUAL",
                        "description": f"Desarrollo secuencial de ideas en '{doc}'",
                        "confidence": 0.7,
                        "extraction_method": "document_sequence"
                    }
                    relationships.append(relationship)

        return relationships

    async def _identify_central_idea_profiles(self, quotes: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifica perfiles de ideas centrales interrelacionadas."""

        logger.info("📊 Identificando perfiles de ideas centrales...")

        # Crear grafo de conectividad
        connectivity = {}
        for quote in quotes:
            connectivity[quote["id"]] = {"quote": quote, "connections": set()}

        # Agregar conexiones
        for rel in relationships:
            source_id = rel.get("source_id")
            target_id = rel.get("target_id")

            if source_id in connectivity and target_id in connectivity:
                connectivity[source_id]["connections"].add(target_id)
                connectivity[target_id]["connections"].add(source_id)

        # Identificar clusters de ideas altamente conectadas
        profiles = []
        processed = set()

        for quote_id, data in connectivity.items():
            if quote_id in processed:
                continue

            # Encontrar cluster conectado
            cluster = self._find_connected_cluster(quote_id, connectivity, processed)

            if len(cluster) >= 3:  # Mínimo 3 citas para formar un perfil
                profile = await self._create_idea_profile(cluster, connectivity)
                profiles.append(profile)

        # Ordenar perfiles por importancia
        profiles.sort(key=lambda x: x.get("importance_score", 0), reverse=True)

        logger.info(f"✅ {len(profiles)} perfiles de ideas identificados")
        return profiles

    def _find_connected_cluster(self, start_id: str, connectivity: Dict, processed: set) -> List[str]:
        """Encuentra un cluster de citas conectadas usando BFS."""

        cluster = []
        queue = [start_id]
        visited = set()

        while queue:
            current_id = queue.pop(0)

            if current_id in visited:
                continue

            visited.add(current_id)
            processed.add(current_id)
            cluster.append(current_id)

            # Agregar conexiones no visitadas
            connections = connectivity[current_id]["connections"]
            for conn_id in connections:
                if conn_id not in visited and len(cluster) < 10:  # Limitar tamaño del cluster
                    queue.append(conn_id)

        return cluster

    async def _create_idea_profile(self, cluster_ids: List[str], connectivity: Dict) -> Dict[str, Any]:
        """Crea un perfil de ideas a partir de un cluster de citas."""

        cluster_quotes = [connectivity[quote_id]["quote"] for quote_id in cluster_ids]

        # Analizar conceptos centrales
        concepts = [quote.get("concept", "") for quote in cluster_quotes]
        central_concept = await self._identify_central_concept(cluster_quotes)

        # Calcular puntuación de importancia
        importance_scores = [
            1.0 if quote.get("importance") == "alta" else 0.5
            for quote in cluster_quotes
        ]
        importance_score = sum(importance_scores) / len(importance_scores)

        # Identificar categorías representadas
        categories = list(set(quote.get("category", "") for quote in cluster_quotes))
        categories_str = ", ".join(categories) if categories else ""

        # Crear descripción del perfil
        profile_description = await self._generate_profile_description(central_concept, categories, len(cluster_quotes), cluster_quotes)

        # Generar un ID más robusto, usando un hash del concepto central y las categorías
        profile_id_hash = hashlib.md5(f"{central_concept}_{categories_str}".encode('utf-8')).hexdigest()[:12]
        
        profile = {
            "id": f"profile_{profile_id_hash}",
            "central_concept": central_concept,
            "description": profile_description,
            "quote_ids": cluster_ids,
            "quotes_count": len(cluster_quotes),
            "categories": categories,
            "importance_score": round(importance_score, 2),
            "coherence_score": self._calculate_coherence_score(cluster_quotes),
            "documents_span": list(set(quote.get("source_document", "") for quote in cluster_quotes)),
            "type": "IDEA_PROFILE"
        }

        return profile

    async def _identify_central_concept(self, cluster_quotes: List[Dict[str, Any]]) -> str:
        """Identifica el concepto central de un grupo de citas, usando LLM si está disponible."""

        # Extraer conceptos para el LLM
        concepts = [quote.get("concept", "") for quote in cluster_quotes if quote.get("concept")]
        
        llm_to_use = self.fast_llm or self.llm
        if llm_to_use and concepts:
            try:
                combined_concepts = ", ".join(list(set(concepts)))
                
                # Generar una clave única para el cache
                cache_key = f"central_concept_{hashlib.md5(combined_concepts.encode()).hexdigest()}"
                
                # Verificar si el resultado está en caché
                if cache_key in self.llm_cache:
                    logger.debug(f"📥 Usando resultado en caché para concepto central")
                    return self.llm_cache[cache_key]
                
                prompt = f"""Dado el siguiente conjunto de conceptos relacionados: "{combined_concepts}".
                Tu tarea es identificar la idea principal o un concepto central **altamente granular y específico** que agrupe estos conceptos. Genera una frase o un título para este "Perfil de Idea" que sea lo más descriptivo posible.

                Criterios para la frase/título del Perfil de Idea:
                1.  **Altamente Descriptivo y Específico**: Debe capturar la esencia única del grupo de conceptos, indicando claramente qué está agrupando con el mayor detalle posible. Evita generalizaciones. Por ejemplo, en lugar de "Teoría", usa "Teoría de la Relatividad de Einstein" o "Mecanismos de Plasticidad Neuronal en el Aprendizaje".
                2.  **Granular**: Profundiza en los detalles específicos que unifican los conceptos. Si los conceptos son "gestión de proyectos ágiles", "Scrum", "Kanban", un título granular sería "Metodologías Ágiles para la Gestión de Proyectos de Software" en lugar de solo "Gestión de Proyectos".
                3.  **Informativo**: Debe reflejar la naturaleza o esencia de la idea, incorporando palabras clave relevantes.
                4.  **Único y Distintivo**: Debe ser lo suficientemente específico para no confundirse con otros perfiles.
                5.  **Evitar genéricos**: NO uses frases vagas como "Desarrollo conceptual", "Idea principal", "Concepto central", "Tema General", "Análisis", "Relación Conceptual", "Perspectivas sobre", "Conceptos diversos no clasificados". Enfócate en la esencia temática única y detallada que agrupa estos conceptos.
                6.  **Formato**: Debe sonar como un título de tema o categoría principal, o una frase que resuma la idea principal.

                Ejemplos de granularidad deseada:
                - Input: "equidad de género, empoderamiento femenino, brecha salarial" -> Output: "Análisis de la Brecha Salarial y Estrategias de Empoderamiento Femenino en el Mercado Laboral"
                - Input: "cambio climático, energías renovables, impacto ambiental" -> Output: "Innovaciones en Energías Renovables para Mitigar el Impacto del Cambio Climático Urbano"
                - Input: "neurociencia, plasticidad cerebral, aprendizaje" -> Output: "Mecanismos Neuronales Subyacentes a la Plasticidad Cerebral y la Adquisición de Nuevas Habilidades"
                - Input: "algoritmos de machine learning, redes neuronales, deep learning" -> Output: "Aplicaciones Avanzadas de Redes Neuronales Profundas en el Procesamiento de Lenguaje Natural"

                Responde ÚNICAMENTE con la frase o título del concepto central altamente granular."""
                
                # Usar método de llamada robusta al LLM
                response_text = await self._call_llm_safely(prompt, cache_key)
                
                if response_text and response_text.strip():
                    central_concept_llm = response_text.strip()
                    logger.debug(f"🧠 LLM identificó concepto central granular: {central_concept_llm}")
                    # Almacenar en caché
                    self.llm_cache[cache_key] = central_concept_llm
                    return central_concept_llm
                else:
                    logger.warning("⚠️ LLM devolvió un concepto central vacío o inválido.")
                    # Usar fallback inteligente basado en conceptos disponibles
                    return self._generate_fallback_central_concept(concepts)
            except Exception as e:
                logger.error(f"❌ Falló la identificación de concepto central por LLM: {e}")
                raise

        raise ValueError("El LLM no está disponible o no se proporcionaron conceptos para identificar un concepto central.")

    async def _generate_profile_description(self, central_concept: str, categories: List[str], quotes_count: int, cluster_quotes: List[Dict[str, Any]]) -> str:
        """Genera descripción de un perfil de ideas, usando fast_llm para tareas simples."""

        categories_str = ", ".join(categories) if categories else "conceptos generales"

        # OPTIMIZACIÓN: Usar fast_llm para descripciones de perfil (tarea más simple)
        llm_to_use = self.fast_llm or self.llm
        if not llm_to_use:
            raise ValueError("El LLM no está disponible para generar la descripción del perfil.")

        try:
            # Generar una clave única para el cache
            quotes_texts = [q['text'] for q in cluster_quotes]
            cache_key = f"profile_desc_{hashlib.md5((central_concept + categories_str).encode()).hexdigest()[:16]}"

            # Verificar si el resultado está en caché
            cached_result = self._check_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"📥 Usando resultado en caché para descripción de perfil")
                return cached_result

            # Usar LLM para una descripción más elaborada
            prompt = f"""El siguiente conjunto de {quotes_count} citas conceptuales se agrupa bajo el concepto central de '{central_concept}'.
            Categorías principales: {categories_str}

            Aquí están algunas de las citas clave:
            {chr(10).join(f"- {text[:100]}..." for text in quotes_texts[:5])}

            Genera una descripción detallada y completa para este perfil de ideas. La descripción debe:
            1. Resaltar la importancia del concepto central.
            2. Explicar qué unifica estas citas.
            3. Mencionar brevemente las principales categorías involucradas.
            4. Proporcionar un resumen coherente del conocimiento que este perfil representa.

            Responde ÚNICAMENTE con la descripción."""

            logger.info(f"⚡ Usando {'fast_llm' if self.fast_llm and llm_to_use == self.fast_llm else 'main_llm'} para descripción de perfil")
            response = await llm_to_use.ainvoke(prompt)
            profile_description_llm = response.content.strip() if hasattr(response, 'content') else str(response).strip()

            if profile_description_llm:
                logger.debug(f"🧠 LLM generó descripción de perfil: {profile_description_llm[:100]}...")
                # Almacenar en caché
                self._store_in_cache(cache_key, profile_description_llm)
                return profile_description_llm
            else:
                logger.error("❌ El LLM devolvió una descripción de perfil vacía.")
                raise ValueError("El LLM no pudo generar una descripción de perfil válida.")
        except Exception as e:
            logger.error(f"❌ Falló la generación de descripción de perfil por LLM: {e}")
            raise

    def _calculate_coherence_score(self, quotes: List[Dict[str, Any]]) -> float:
        """Calcula la puntuación de coherencia de un grupo de citas."""

        # Factores de coherencia
        confidence_scores = [quote.get("confidence", 0.5) for quote in quotes]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)

        # Diversidad de categorías (menos diversidad = más coherencia)
        categories = set(quote.get("category", "") for quote in quotes)
        category_coherence = max(0.3, 1.0 - (len(categories) - 1) * 0.2)

        # Coherencia final
        coherence = (avg_confidence + category_coherence) / 2
        return round(coherence, 2)

    async def _create_batch_llm_relationships(self, batch: List[Dict[str, Any]], quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Crea relaciones temáticas para un lote de pares de citas usando el LLM.
        
        Args:
            batch: Lista de pares de citas para analizar
            quotes: Lista completa de citas
            
        Returns:
            Lista de relaciones temáticas generadas por el LLM
        """
        llm_to_use = self.fast_llm or self.llm
        if not llm_to_use:
            logger.error("❌ LLM no disponible para crear relaciones por lotes")
            return []
        
        batch_results = []
        
        for pair in batch:
            try:
                quote1_idx = pair["quote1_idx"]
                quote2_idx = pair["quote2_idx"]
                quote1 = quotes[quote1_idx]
                quote2 = quotes[quote2_idx]
                similarity = pair["similarity"]
                
                # Generar una clave única para el cache
                cache_key = f"relationship_{quote1_idx}_{quote2_idx}_{similarity}"
                
                # Verificar si el resultado está en caché
                cached_result = self._check_cache(cache_key)
                if cached_result is not None:
                    logger.debug(f"📥 Usando resultado en caché para relación entre citas {quote1_idx} y {quote2_idx}")
                    batch_results.append(cached_result)
                    continue
                
                # Usar el método mejorado de llamada al LLM con validación y reintentos
                result = await self._call_llm_with_retry_and_validation(
                    quote1, quote2, similarity, cache_key, quote1_idx, quote2_idx, llm_to_use=llm_to_use
                )
                
                if result:
                    batch_results.append(result)
                    
            except Exception as e:
                logger.error(f"❌ Error procesando par de citas {quote1_idx}-{quote2_idx} en el lote: {e}")
                continue
        
        return batch_results
    
    async def _call_llm_with_retry_and_validation(self, quote1: Dict, quote2: Dict, similarity: float, 
                                                cache_key: str, quote1_idx: int, quote2_idx: int) -> Optional[Dict[str, Any]]:
        """
        Llamada al LLM con validación mejorada, reintentos y manejo robusto de errores.
        
        Args:
            quote1: Primera cita
            quote2: Segunda cita
            similarity: Puntuación de similitud
            cache_key: Clave para el caché
            quote1_idx: Índice de la primera cita
            quote2_idx: Índice de la segunda cita
            
        Returns:
            Resultado procesado o None si falla completamente
        """
        import json
        import re
        import time
        
        llm_to_use = self.fast_llm or self.llm
        if not llm_to_use:
            logger.error("❌ LLM no disponible para _call_llm_with_retry_and_validation")
            return None

        # Configuración de reintentos
        max_retries = 3  # Número máximo de reintentos
        retry_delay = 1.0  # Delay base para backoff exponencial

        for attempt in range(max_retries):
            try:
                # Crear prompt para el LLM
                prompt = self._build_relationship_prompt(quote1, quote2, similarity)
                
                logger.debug(f"🤖 Llamando LLM para par {quote1_idx}-{quote2_idx} (intento {attempt + 1}/{max_retries})")
                
                response = await asyncio.wait_for(
                    llm_to_use.ainvoke(prompt), 
                    timeout=30.0  # Timeout de 30 segundos
                )
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Log de la respuesta para debugging
                logger.debug(f"📝 Respuesta LLM para par {quote1_idx}-{quote2_idx}: '{response_text[:200]}{'...' if len(response_text) > 200 else ''}'")
                
                # Validar y limpiar la respuesta
                cleaned_response = self._validate_and_clean_response(response_text)
                
                if not cleaned_response:
                    logger.warning(f"⚠️ Respuesta vacía o inválida del LLM para par {quote1_idx}-{quote2_idx} (intento {attempt + 1})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2 ** attempt))  # Backoff exponencial
                        continue
                    else:
                        # Usar valores por defecto después de todos los intentos
                        return self._create_default_relationship(quote1_idx, quote2_idx, similarity)
                
                # Parsear respuesta JSON
                try:
                    parsed = json.loads(cleaned_response)
                    
                    # Validar estructura de la respuesta
                    if not isinstance(parsed, dict) or "type" not in parsed:
                        raise ValueError("Respuesta JSON no tiene la estructura esperada")
                    
                    relationship_type = parsed.get("type", "RELACION_TEMATICA")
                    description = parsed.get("description", "Las ideas están temáticamente relacionadas (LLM)")
                    confidence_str = parsed.get("confidence", "media")
                    
                    # Convertir confianza a valor numérico
                    confidence_map = {"alta": 0.9, "media": 0.7, "baja": 0.5}
                    confidence = confidence_map.get(confidence_str.lower(), 0.7)
                    
                    result = {
                        "original_pair": {
                            "quote1_idx": quote1_idx,
                            "quote2_idx": quote2_idx,
                            "similarity": similarity
                        },
                        "type": relationship_type,
                        "description": description,
                        "confidence": confidence
                    }
                    
                    # Almacenar en caché
                    self._store_in_cache(cache_key, result)
                    logger.debug(f"✅ LLM respondió correctamente para par {quote1_idx}-{quote2_idx}")
                    return result
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"⚠️ Error parseando JSON del LLM para par {quote1_idx}-{quote2_idx}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        # Intentar extraer JSON manualmente de la respuesta
                        extracted_result = self._extract_json_from_text(response_text, quote1_idx, quote2_idx, similarity)
                        if extracted_result:
                            self._store_in_cache(cache_key, extracted_result)
                            return extracted_result
                        else:
                            return self._create_default_relationship(quote1_idx, quote2_idx, similarity)
                
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout en llamada LLM para par {quote1_idx}-{quote2_idx} (intento {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    return self._create_default_relationship(quote1_idx, quote2_idx, similarity)
                    
            except Exception as e:
                logger.error(f"❌ Error inesperado en llamada LLM para par {quote1_idx}-{quote2_idx}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    return self._create_default_relationship(quote1_idx, quote2_idx, similarity)
        
        # Si llegamos aquí, todos los intentos fallaron
        logger.error(f"❌ Todos los intentos fallaron para par {quote1_idx}-{quote2_idx}, usando valores por defecto")
        return self._create_default_relationship(quote1_idx, quote2_idx, similarity)
    
    def _build_relationship_prompt(self, quote1: Dict, quote2: Dict, similarity: float) -> str:
        """
        Construye el prompt para el análisis de relaciones temáticas.
        
        Args:
            quote1: Primera cita
            quote2: Segunda cita
            similarity: Puntuación de similitud
            
        Returns:
            Prompt formateado para el LLM
        """
        return f"""
Analiza las siguientes dos citas conceptuales y determina la relación temática entre ellas:

Cita 1: {quote1['text']}
Concepto: {quote1['concept']}
Categoría: {quote1['category']}

Cita 2: {quote2['text']}
Concepto: {quote2['concept']}
Categoría: {quote2['category']}

Similitud semántica: {similarity}

Instrucciones:
1. Identifica el tipo de relación temática entre estas citas
2. Proporciona una descripción clara de la relación
3. Usa los siguientes tipos de relación si son aplicables:
   - CONCEPTOS_RELACIONADOS
   - MARCOS_TEORICOS_AFINES
   - ENFOQUES_METODOLOGICOS
   - HALLAZGOS_CONVERGENTES
   - FUNDAMENTACION_TEORICA
   - APLICACION_METODOLOGICA
   - VALIDACION_EMPIRICA
   - CONFIRMACION_CONCEPTUAL
   - ALTA_CONVERGENCIA_TEMATICA
   - CONVERGENCIA_TEMATICA
   - RELACION_TEMATICA
   - EJEMPLO_PRÁCTICO

   
Responde ÚNICAMENTE con un objeto JSON válido:
{{
    "type": "tipo_de_relacion",
    "description": "descripción detallada de la relación",
    "confidence": "alta"
}}

NO incluyas texto adicional, solo el JSON."""
    
    def _validate_and_clean_response(self, response_text: str) -> Optional[str]:
        """
        Valida y limpia la respuesta del LLM antes de parsear JSON.
        
        Args:
            response_text: Texto de respuesta del LLM
            
        Returns:
            Texto limpio o None si la respuesta es inválida
        """
        if not response_text or not response_text.strip():
            return None
        
        # Limpiar la respuesta
        cleaned = response_text.strip()
        
        # Remover caracteres de control y normalizar
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', cleaned)
        
        # Buscar JSON en la respuesta
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned)
        if json_match:
            return json_match.group(0)
        
        # Si no se encuentra JSON válido, devolver None
        return None
    
    def _extract_json_from_text(self, text: str, quote1_idx: int, quote2_idx: int, similarity: float) -> Optional[Dict[str, Any]]:
        """
        Intenta extraer información JSON manualmente del texto de respuesta.
        
        Args:
            text: Texto de respuesta
            quote1_idx: Índice de la primera cita
            quote2_idx: Índice de la segunda cita
            similarity: Puntuación de similitud
            
        Returns:
            Resultado extraído o None si falla
        """
        import re
        
        try:
            # Buscar patrones de tipo de relación
            type_patterns = {
                "CONCEPTOS_RELACIONADOS": r"conceptos?\s+relacionados?",
                "MARCOS_TEORICOS_AFINES": r"marcos?\s+te[oó]ricos?\s+afines?",
                "ENFOQUES_METODOLOGICOS": r"enfoques?\s+metodol[oó]gicos?",
                "HALLAZGOS_CONVERGENTES": r"hallazgos?\s+convergentes?",
                "FUNDAMENTACION_TEORICA": r"fundamentaci[oó]n\s+te[oó]rica",
                "APLICACION_METODOLOGICA": r"aplicaci[oó]n\s+metodol[oó]gica",
                "VALIDACION_EMPIRICA": r"validaci[oó]n\s+emp[ií]rica",
                "CONFIRMACION_CONCEPTUAL": r"confirmaci[oó]n\s+conceptual",
                "ALTA_CONVERGENCIA_TEMATICA": r"alta\s+convergencia\s+tem[aá]tica",
                "CONVERGENCIA_TEMATICA": r"convergencia\s+tem[aá]tica",
                "RELACION_TEMATICA": r"relaci[oó]n\s+tem[aá]tica"
            }
            
            text_lower = text.lower()
            detected_type = "RELACION_TEMATICA"
            
            for rel_type, pattern in type_patterns.items():
                if re.search(pattern, text_lower):
                    detected_type = rel_type
                    break
            
            # Extraer descripción
            description_match = re.search(r"descripci[oó]n\s*:?\s*([^{}\"]+)", text_lower)
            description = description_match.group(1).strip() if description_match else "Las ideas están temáticamente relacionadas"
            
            # Detectar confianza
            confidence = 0.7  # default
            if any(word in text_lower for word in ["alta", "high", "strong"]):
                confidence = 0.9
            elif any(word in text_lower for word in ["baja", "low", "weak"]):
                confidence = 0.5
            
            return {
                "original_pair": {
                    "quote1_idx": quote1_idx,
                    "quote2_idx": quote2_idx,
                    "similarity": similarity
                },
                "type": detected_type,
                "description": description,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error extrayendo JSON manualmente: {e}")
            return None
    
    def _create_default_relationship(self, quote1_idx: int, quote2_idx: int, similarity: float) -> Dict[str, Any]:
        """
        Crea una relación por defecto cuando el LLM falla completamente.
        
        Args:
            quote1_idx: Índice de la primera cita
            quote2_idx: Índice de la segunda cita
            similarity: Puntuación de similitud
            
        Returns:
            Relación por defecto
        """
        # Determinar tipo de relación basado en similitud
        if similarity > 0.85:
            rel_type = "ALTA_CONVERGENCIA_TEMATICA"
        elif similarity > 0.75:
            rel_type = "CONVERGENCIA_TEMATICA"
        else:
            rel_type = "RELACION_TEMATICA"
        
        return {
            "original_pair": {
                "quote1_idx": quote1_idx,
                "quote2_idx": quote2_idx,
                "similarity": similarity
            },
            "type": rel_type,
            "description": f"Relación temática basada en similitud ({similarity:.2f})",
            "confidence": 0.6  # Confianza reducida para relaciones por defecto
        }
    
    def _validate_and_clean_llm_response(self, response_text: str) -> Optional[str]:
        """
        Valida y limpia la respuesta del LLM para extracción de citas.
        
        Args:
            response_text: Texto de respuesta del LLM
            
        Returns:
            Texto limpio o None si la respuesta es inválida
        """
        if not response_text or not response_text.strip():
            return None
        
        # Limpiar la respuesta
        cleaned = response_text.strip()
        
        # Remover caracteres de control y normalizar
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', cleaned)
        
        # Buscar JSON en la respuesta
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned)
        if json_match:
            return json_match.group(0)
        
        # Si no se encuentra JSON válido, devolver None
        return None
    
    async def _call_llm_safely(self, prompt: str, cache_key: str) -> Optional[str]:
        """
        Llamada segura al LLM con reintentos y manejo de errores.
        
        Args:
            prompt: Prompt para el LLM
            cache_key: Clave para el caché
            
        Returns:
            Respuesta del LLM o None si falla
        """
        max_retries = 2
        retry_delay = 1.0
        
        llm_to_use = self.fast_llm or self.llm
        if not llm_to_use:
            logger.error("❌ LLM no disponible para _call_llm_safely")
            return None

        for attempt in range(max_retries):
            try:
                logger.debug(f"🤖 Llamada segura LLM (intento {attempt + 1}/{max_retries})")
                
                response = await asyncio.wait_for(
                    llm_to_use.ainvoke(prompt), 
                    timeout=20.0
                )
                
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                if response_text and response_text.strip():
                    logger.debug(f"✅ LLM respondió correctamente")
                    return response_text
                else:
                    logger.warning(f"⚠️ LLM respondió con contenido vacío (intento {attempt + 1})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout en llamada LLM (intento {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Error en llamada LLM: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
        
        logger.error(f"❌ Todos los intentos fallaron para llamada LLM")
        return None
    
    def _generate_fallback_central_concept(self, concepts: List[str]) -> str:
        """
        Genera un concepto central de fallback cuando el LLM falla.
        
        Args:
            concepts: Lista de conceptos disponibles
            
        Returns:
            Concepto central generado
        """
        if not concepts:
            return "Concepto Central No Identificado"
        
        # Eliminar duplicados y limpiar
        unique_concepts = list(set(concept.strip() for concept in concepts if concept.strip()))
        
        if len(unique_concepts) == 1:
            return unique_concepts[0]
        elif len(unique_concepts) == 2:
            return f"{unique_concepts[0]} y {unique_concepts[1]}"
        elif len(unique_concepts) <= 5:
            return ", ".join(unique_concepts[:-1]) + f" y {unique_concepts[-1]}"
        else:
            return ", ".join(unique_concepts[:3]) + f" y {len(unique_concepts)-3} conceptos relacionados"

    async def _create_document_nodes(self, documents: List[Dict[str, Any]], workspace_id: str, account_id: str, dataset_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Crea nodos DOCUMENT de primer nivel en el grafo, generando ID, resumen, keywords y embedding para cada documento.
        Persiste los nodos en Neo4j usando neo4j_adapter.
        """
        logger.info(f"📄 Creando nodos DOCUMENT para {len(documents)} documentos...")
        document_nodes = []
        
        tasks = []
        for doc_data in documents:
            tasks.append(self._process_single_document_for_node(doc_data, workspace_id, account_id, dataset_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"❌ Error procesando documento para nodo: {result}")
                continue
            if result:
                document_nodes.append(result)

        if self.neo4j_adapter:
            logger.info(f"💾 Persistiendo {len(document_nodes)} nodos DOCUMENT en Neo4j...")
            await self.neo4j_adapter.create_document_nodes(document_nodes)
            logger.info(f"✅ {len(document_nodes)} nodos DOCUMENT persistidos en Neo4j.")

        logger.info(f"✅ {len(document_nodes)} nodos DOCUMENT creados.")
        return document_nodes

    async def _process_single_document_for_node(self, doc_data: Dict[str, Any], workspace_id: str, account_id: str, dataset_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Procesa un solo documento para crear su nodo DOCUMENT con metadatos y embedding.
        """
        try:
            doc_id = doc_data.get('document_id') or doc_data.get('metadata', {}).get('document_id') or str(uuid.uuid4())

            content = doc_data.get('content', '')
            title = doc_data.get('title', 'Documento sin título')
            url = doc_data.get('url', '')
            source_type = doc_data.get('source_type', 'unknown')
            publication_date = doc_data.get('publication_date')
            author = doc_data.get('author')
            topic = doc_data.get('topic', 'general')
            
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest() if content else ''

            summary = await self._generate_document_summary(content)
            keywords = await self._generate_document_keywords(content)

            embedding = None
            if self.embedding_model and content:
                try:
                    embedding = await self.embedding_model.aembed_documents([content])
                    if embedding:
                        embedding = embedding[0]
                except Exception as e:
                    logger.warning(f"⚠️ Falló la generación de embedding para documento '{title}': {e}")
            
            document_node = {
                "id": doc_id,
                "title": title,
                "url": url,
                "content": summary or (content[:500] + "..." if content else ""),
                "content_hash": content_hash,
                "summary": summary,
                "keywords": keywords,
                "embedding": embedding,
                "publication_date": publication_date,
                "author": author,
                "source_type": source_type,
                "topic": topic,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "workspace_id": workspace_id,
                "account_id": account_id,
                "dataset_name": dataset_name,
                "type": "DOCUMENT"
            }
            return document_node
        except Exception as e:
            logger.error(f"❌ Error al crear nodo DOCUMENT para '{doc_data.get('title', 'documento sin título')}': {e}")
            return None

    async def _generate_document_summary(self, content: str) -> str:
        """Genera un resumen conciso de un documento usando LLM."""
        if not content or len(content.strip()) < 100:
            return content[:200] + "..." if content else "Contenido demasiado corto para resumir."

        llm_to_use = self.fast_llm or self.llm
        if not llm_to_use:
            return content[:200] + "..."

        cache_key = f"doc_summary_{hashlib.md5(content.encode()).hexdigest()[:16]}"
        cached_result = self._check_cache(cache_key)
        if cached_result is not None:
            return cached_result

        prompt = f"""
        Genera un resumen conciso y objetivo del siguiente documento. El resumen debe capturar las ideas principales y los puntos clave en 3-5 oraciones.

        Documento:
        {content[:4000]}

        Resumen:
        """
        try:
            response = await llm_to_use.ainvoke(prompt)
            summary = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            self._store_in_cache(cache_key, summary)
            return summary
        except Exception as e:
            logger.warning(f"⚠️ Falló la generación de resumen con LLM: {e}")
            return content[:200] + "..."

    async def _generate_document_keywords(self, content: str) -> List[str]:
        """Extrae palabras clave representativas de un documento usando LLM."""
        if not content or len(content.strip()) < 100:
            return []

        llm_to_use = self.fast_llm or self.llm
        if not llm_to_use:
            return []

        cache_key = f"doc_keywords_{hashlib.md5(content.encode()).hexdigest()[:16]}"
        cached_result = self._check_cache(cache_key)
        if cached_result is not None:
            return cached_result

        prompt = f"""
        Extrae una lista de 5-10 palabras clave o frases cortas que representen los temas principales del siguiente documento. Responde únicamente con las palabras clave separadas por comas.

        Documento:
        {content[:4000]}

        Palabras clave:
        """
        try:
            response = await llm_to_use.ainvoke(prompt)
            keywords_str = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
            self._store_in_cache(cache_key, keywords)
            return keywords
        except Exception as e:
            logger.warning(f"⚠️ Falló la generación de palabras clave con LLM: {e}")
            return []
