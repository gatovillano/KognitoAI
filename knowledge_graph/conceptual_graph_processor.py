"""
Procesador de Grafo Conceptual que extrae citas de ideas completas y las relaciona temáticamente.
Crea un grafo donde cada nodo es una idea/concepto expresado como cita textual.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re
import hashlib
from core.config import settings
from core.utils.llm_utils import (
    invoke_structured_output,
    is_token_limit_exceeded,
    prune_messages_to_fit_token_limit,
    is_openrouter_model,
    safe_bind_tools,
)
from core.llm_manager import get_llm_for_user, get_fallback_llm
from langchain_core.messages import HumanMessage, SystemMessage
from knowledge_graph.conceptual_graph_schemas import (
    QuotesExtractionOutput,
    ThematicRelationshipOutput,
    CentralConceptOutput,
    ProfileDescriptionOutput,
)

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
    
    def __init__(self, llm=None, sentence_transformer=None, **kwargs):
        """
        Inicializa el procesador conceptual.
        
        Args:
            llm: Modelo de lenguaje para análisis semántico
            sentence_transformer: Modelo para embeddings semánticos
            **kwargs: Parámetros opcionales para compatibilidad (fast_llm, neo4j_adapter,
                progress_tracker, etc.).
        """
        self.llm = llm
        self.embedding_model = sentence_transformer # Renamed to generic embedding_model
        self.initialized = False
        self.llm_cache = {}  # Cache para resultados de LLM
        # Compatibilidad hacia atrás/adelante con integraciones que inyectan argumentos extra.
        self.fast_llm = kwargs.get("fast_llm")
        self.neo4j_adapter = kwargs.get("neo4j_adapter")
        self.progress_tracker = kwargs.get("progress_tracker")
        self.workspace_name = kwargs.get("workspace_name")
        logger.info(f"🧠 ConceptualGraphProcessor inicializado (workspace: {self.workspace_name})")
    
    async def initialize(self):
        """Inicializa los modelos necesarios."""
        if self.initialized:
            return
        
        logger.info("🚀 Inicializando modelos para procesamiento conceptual...")
        
        try:
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
    
    async def process_documents_conceptually(self, documents: List[Dict[str, Any]], dataset_name: str, **kwargs) -> Dict[str, Any]:
        """
        Procesa documentos extrayendo citas conceptuales y sus relaciones temáticas.
        
        Args:
            documents: Lista de documentos con contenido
            dataset_name: Nombre del dataset
            **kwargs: Parámetros opcionales de contexto para compatibilidad (account_id,
                progress_tracker, etc.).
            
        Returns:
            Dict con nodos conceptuales, relaciones temáticas y perfiles de ideas
        """
        if not self.initialized:
            await self.initialize()

        # Contexto opcional para compatibilidad con utilidades asíncronas (embeddings/LLM).
        self.current_account_id = kwargs.get("account_id")
        await self._ensure_user_llms()
        
        logger.info(f"🧠 Iniciando procesamiento conceptual de {len(documents)} documentos")
        
        try:
            # Fase 1: Extraer citas conceptuales
            conceptual_quotes = await self._extract_conceptual_quotes(documents)
            logger.info(f"✅ Fase 1: {len(conceptual_quotes)} citas conceptuales extraídas")
            
            # Fase 2: Analizar relaciones temáticas
            thematic_relationships = await self._analyze_thematic_relationships(conceptual_quotes)
            logger.info(f"✅ Fase 2: {len(thematic_relationships)} relaciones temáticas")
            
            # Fase 3: Identificar perfiles de ideas centrales
            idea_profiles = await self._identify_central_idea_profiles(conceptual_quotes, thematic_relationships)
            logger.info(f"✅ Fase 3: {len(idea_profiles)} perfiles de ideas identificados")
            
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
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento conceptual: {e}")
            raise

    async def _ensure_user_llms(self):
        """Asegura que el procesador use el modelo configurado por el usuario cuando hay account_id."""
        account_id = getattr(self, "current_account_id", None)
        if not account_id:
            return

        try:
            from core.llm_manager import get_llm_for_user

            user_main_llm = await get_llm_for_user(account_id, purpose="main")
            user_fast_llm = await get_llm_for_user(account_id, purpose="fast")

            if user_main_llm:
                self.llm = user_main_llm
                # Mantener consistencia: fast_llm del usuario si existe; sino, mismo llm principal.
                self.fast_llm = user_fast_llm or user_main_llm

                model_name = (
                    getattr(self.llm, "model_name", None)
                    or getattr(self.llm, "model", None)
                    or "desconocido"
                )
                logger.info(
                    "🤖 ConceptualGraphProcessor usando modelo configurado por usuario "
                    "(account_id=%s, model=%s)",
                    account_id,
                    model_name,
                )
            else:
                logger.warning(
                    "⚠️ No se encontró LLM personalizado para account_id=%s; se mantiene LLM actual.",
                    account_id,
                )
        except Exception as e:
            logger.warning(
                "⚠️ No se pudo resolver LLM de usuario para account_id=%s: %s. Se mantiene LLM actual.",
                account_id,
                e,
            )

    async def _create_document_nodes(self, documents: List[Dict[str, Any]], workspace_id=None, account_id=None, dataset_name=None):
        """
        Método de compatibilidad para integraciones que esperan crear nodos DOCUMENT
        desde este procesador. En esta versión no persiste nodos y actúa como no-op.
        """
        logger.debug(
            "🧩 _create_document_nodes no-op (compatibilidad): docs=%s workspace_id=%s account_id=%s dataset=%s",
            len(documents) if documents else 0,
            workspace_id,
            account_id,
            dataset_name,
        )
        return []
    
    async def _extract_conceptual_quotes(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Método privado: Extrae citas conceptuales usando múltiples estrategias.
        
        Estrategias utilizadas:
        1. LLM para contenido largo (>500 chars)
        2. Análisis de oraciones conceptualmente ricas
        3. Extracción de párrafos con alta densidad conceptual
        
        Elimina duplicados y filtra por calidad (confidence >= 0.6).
        """

        conceptual_quotes = []

        for doc_idx, doc in enumerate(documents):
            content = doc.get('content', '')
            if not content:
                continue

            logger.debug(f"🔍 Extrayendo conceptos del documento {doc_idx + 1}")

            # Estrategia 1: Usar LLM para extraer ideas clave (solo si el contenido es significativo)
            if self.llm and len(content) > 500:
                llm_quotes = await self._extract_quotes_with_llm(content, doc)
                conceptual_quotes.extend(llm_quotes)
            elif self.llm:
                logger.debug("⚠️ Contenido demasiado corto para extracción con LLM, usando métodos alternativos")

            # Estrategia 2: Extraer oraciones conceptualmente ricas
            sentence_quotes = await self._extract_rich_sentences(content, doc, doc_idx)
            conceptual_quotes.extend(sentence_quotes)

            # Estrategia 3: Extraer párrafos con alta densidad conceptual
            paragraph_quotes = await self._extract_conceptual_paragraphs(content, doc, doc_idx)
            conceptual_quotes.extend(paragraph_quotes)

        # Eliminar duplicados y filtrar por calidad
        unique_quotes = await self._deduplicate_and_filter_quotes(conceptual_quotes)

        return unique_quotes
    
    async def _extract_quotes_with_llm(self, content: str, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Usa el LLM para extraer citas conceptuales de alta calidad con salida estructurada."""

        # Validar que el contenido no esté vacío
        if not content or len(content.strip()) < 50:
            logger.warning("⚠️ Contenido demasiado corto para extracción de citas con LLM")
            return []

        # Generar una clave única para el cache
        cache_key = f"extract_quotes_{hashlib.md5(content.encode()).hexdigest()}"

        # Verificar si el resultado está en caché
        if cache_key in self.llm_cache:
            logger.debug(f"📥 Usando resultado en caché para extracción de citas")
            return self.llm_cache[cache_key]

        # System prompt for quote extraction
        system_prompt = """Eres un experto en análisis conceptual. Tu tarea es extraer citas clave que expresen ideas completas y coherentes con valor teórico/conceptual.

Criterios de extracción:
1. Ideas completas y coherentes (no frases sueltas)
2. Valor conceptual/teórico (no puramente descriptivo)
3. Representativas del contenido principal
4. 5-10 citas máximo

Categorías válidas: teoría, metodología, conclusión, definición, definición_conceptual, enfoque_metodológico, marco_teórico, hallazgo_empírico, ejemplo_práctico, análisis_crítico, desarrollo_teórico
Importancia: alta o media"""

        if getattr(self, "workspace_name", None):
            system_prompt += f"\n\n**CONTEXTO CRÍTICO DE PROYECTO / WORKSPACE**: Las citas extraídas deben pertenecer y enmarcarse estrictamente dentro de la temática e información del proyecto/workspace '{self.workspace_name}'. Evita extraer elementos o ideas ajenas a este proyecto."

        prompt = f"""Analiza el siguiente texto y extrae 5-10 citas clave que expresen ideas conceptuales completas:

Texto:
{content[:3000]}"""

        try:
            # Usar salida estructurada con fallback chain
            result = await self._call_structured_llm(
                prompt=prompt,
                schema=QuotesExtractionOutput,
                cache_key=cache_key,
                system_prompt=system_prompt,
                max_retries=3,
            )

            if not result or not result.quotes:
                logger.warning("⚠️ Respuesta vacía o inválida del LLM para extracción de citas")
                return []

            quotes = []
            for quote_data in result.quotes:
                quote = {
                    "id": self._generate_quote_id(quote_data.text),
                    "text": quote_data.text,
                    "concept": quote_data.concept,
                    "importance": quote_data.importance,
                    "category": quote_data.category,
                    "source_document": doc.get('title', 'documento'),
                    "extraction_method": "llm_conceptual",
                    "confidence": 0.9 if quote_data.importance == "alta" else 0.7,
                    "type": "CONCEPTUAL_QUOTE"
                }
                quotes.append(quote)

            # Almacenar en caché
            self.llm_cache[cache_key] = quotes
            return quotes

        except Exception as e:
            logger.error(f"❌ Error extrayendo citas con LLM: {e}")
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
        Método privado: Analiza relaciones temáticas usando embeddings y LLM por lotes.
        
        Proceso:
        1. Calcula embeddings para todas las citas
        2. Identifica pares candidatos (similitud > 0.7)
        3. Procesa en lotes con LLM (10 pares por llamada)
        4. Genera relaciones basadas en categorías y estructura
        5. Crea relaciones estructurales (mismo documento/categoría)
        
        Cachea resultados para optimizar llamadas al LLM.
        """

        if len(quotes) < 2:
            return []

        logger.info(f"🔗 Analizando relaciones temáticas entre {len(quotes)} citas con enfoque por lotes.")
        relationships = []

        # Fase 1: Calcular todos los embeddings y similitudes
        quote_texts = [f"{quote['concept']}: {quote['text']}" for quote in quotes]
        if self.embedding_model is None:
            logger.error("❌ Modelo de embeddings no está inicializado.")
            raise RuntimeError("Modelo de embeddings no está inicializado.")
        
        try:
            # En contexto async, priorizar API asíncrona del modelo de embeddings.
            aembed_fn = getattr(self.embedding_model, "aembed_documents", None)
            if callable(aembed_fn):
                maybe_embeddings = aembed_fn(quote_texts)
                embeddings = await maybe_embeddings if asyncio.iscoroutine(maybe_embeddings) else maybe_embeddings
            else:
                embeddings = await asyncio.to_thread(self.embedding_model.embed_documents, quote_texts)
        except NotImplementedError as e:
            # Algunos wrappers sync lanzan esta excepción dentro de loops async.
            if "aembed_documents" in str(e):
                from utils.embeddings import aembed_documents
                embeddings = await aembed_documents(quote_texts, account_id=getattr(self, "current_account_id", None))
            else:
                logger.error(f"Error generando embeddings: {e}")
                raise
        except Exception as e:
            logger.error(f"Error generando embeddings: {e}")
            raise

        if not embeddings:
            raise RuntimeError("No se pudieron generar embeddings para el análisis temático")

        try:
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            logger.warning("⚠️ sklearn no está instalado. Usando cálculo manual de similitud coseno.")
            # Fallback: calcular similitud coseno manualmente
            import numpy as np
            embeddings_array = np.array(embeddings)
            norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            normalized = embeddings_array / norms
            similarities = np.dot(normalized, normalized.T)
        else:
            similarities = cosine_similarity(embeddings)

        # Identificar pares candidatos para análisis
        candidate_pairs = []
        for i in range(len(quotes)):
            for j in range(i + 1, len(quotes)):
                similarity = float(similarities[i][j])
                if similarity > 0.7: # Umbral para considerar un par
                    candidate_pairs.append({
                        "quote1_idx": i,
                        "quote2_idx": j,
                        "similarity": similarity
                    })
        
        if self.llm:
            logger.info(f"🔎 {len(candidate_pairs)} pares de citas candidatas para análisis de relación por LLM.")

            # Procesar candidatos en lotes con LLM
            BATCH_SIZE = 10 # Agrupar de a 10 pares por llamada al LLM
            for i in range(0, len(candidate_pairs), BATCH_SIZE):
                batch = candidate_pairs[i:i + BATCH_SIZE]
                
                try:
                    # Llamar al LLM con el lote
                    batch_results = await self._create_batch_llm_relationships(batch, quotes)

                    # Procesar los resultados del lote
                    for res in batch_results:
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
                                "type": res.get("type", "RELACION_TEMATICA_LLM"), # Usar tipo del LLM
                                "similarity_score": float(similarity),
                                "description": res.get("description", "Las ideas están temáticamente relacionadas (LLM)."), # Usar descripción del LLM
                                "confidence": self._calculate_relationship_confidence(
                                    quote1, quote2, similarity
                                ),
                                "extraction_method": "llm_thematic_batch"
                            }
                            relationships.append(relationship)
                        except (KeyError, IndexError) as e:
                            logger.error(f"❌ Error procesando resultado de relación del lote: {e} - Data: {res}")
                except Exception as e:
                    logger.error(f"❌ Error en el procesamiento por lotes con LLM, recurriendo a reglas: {e}")
                    # Fallback a reglas para este lote si el LLM falla
                    for pair in batch:
                        quote1 = quotes[pair["quote1_idx"]]
                        quote2 = quotes[pair["quote2_idx"]]
                        similarity = pair["similarity"]
                        
                        relationship_type = self._determine_thematic_relationship_type(quote1, quote2, similarity)
                        description = self._generate_relationship_description(quote1, quote2, relationship_type)
                        confidence = self._calculate_relationship_confidence(quote1, quote2, similarity)

                        relationships.append({
                            "id": f"thematic_rel_{len(relationships)}",
                            "source_id": quote1["id"],
                            "target_id": quote2["id"],
                            "type": relationship_type,
                            "similarity_score": similarity,
                            "description": description,
                            "confidence": confidence,
                            "extraction_method": "thematic_similarity_fallback"
                        })
        else:
            logger.warning("⚠️ LLM no disponible para análisis de relaciones temáticas. Recurriendo a reglas predefinidas.")
            # Crear relaciones basadas en similitud temática usando reglas si el LLM no está disponible
            for pair in candidate_pairs:
                quote1 = quotes[pair["quote1_idx"]]
                quote2 = quotes[pair["quote2_idx"]]
                similarity = pair["similarity"]

                relationship_type = self._determine_thematic_relationship_type(quote1, quote2, similarity)
                description = self._generate_relationship_description(quote1, quote2, relationship_type)
                confidence = self._calculate_relationship_confidence(quote1, quote2, similarity)

                relationships.append({
                    "id": f"thematic_rel_{len(relationships)}",
                    "source_id": quote1["id"],
                    "target_id": quote2["id"],
                    "type": relationship_type,
                    "similarity_score": similarity,
                    "description": description,
                    "confidence": confidence,
                    "extraction_method": "thematic_similarity_rules"
                })

        # Agregar relaciones estructurales (no dependen del LLM)
        category_relationships = await self._create_category_relationships(quotes)
        relationships.extend(category_relationships)
        document_relationships = await self._create_document_relationships(quotes)
        relationships.extend(document_relationships)

        logger.info(f"✅ {len(relationships)} relaciones temáticas creadas en total.")
        return relationships

    def _determine_thematic_relationship_type(self, quote1: Dict, quote2: Dict, similarity: float) -> str:
        """Determina el tipo de relación temática entre dos citas."""
        
        cat1 = quote1.get("category", "")
        cat2 = quote2.get("category", "")
        
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
        """Crea relaciones entre citas de la misma categoría conceptual."""

        relationships = []

        # Agrupar por categoría
        categories = {}
        for quote in quotes:
            category = quote.get("category", "general")
            if category not in categories:
                categories[category] = []
            categories[category].append(quote)

        # Crear relaciones dentro de cada categoría
        for category, category_quotes in categories.items():
            if len(category_quotes) < 2:
                continue

            # Conectar citas importantes de la misma categoría
            important_quotes = [q for q in category_quotes if q.get("importance") == "alta"]

            for i, quote1 in enumerate(important_quotes):
                for quote2 in important_quotes[i+1:]:
                    relationship = {
                        "id": f"category_rel_{len(relationships)}",
                        "source_id": quote1["id"],
                        "target_id": quote2["id"],
                        "type": f"MISMA_CATEGORIA_{category.upper()}",
                        "description": f"Ambas citas pertenecen a la categoría '{category}'",
                        "confidence": 0.8,
                        "extraction_method": "category_grouping"
                    }
                    relationships.append(relationship)

        return relationships

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
        """Identifica el concepto central de un grupo de citas usando salida estructurada."""

        # Extraer conceptos para el LLM
        concepts = [quote.get("concept", "") for quote in cluster_quotes if quote.get("concept")]

        if not concepts:
            raise ValueError("No se proporcionaron conceptos para identificar un concepto central.")

        combined_concepts = ", ".join(list(set(concepts)))

        # Generar una clave única para el cache
        cache_key = f"central_concept_{hashlib.md5(combined_concepts.encode()).hexdigest()}"

        # Verificar si el resultado está en caché
        if cache_key in self.llm_cache:
            logger.debug(f"📥 Usando resultado en caché para concepto central")
            return self.llm_cache[cache_key]

        system_prompt = """Eres un experto en síntesis conceptual. Tu tarea es identificar el concepto central altamente granular y específico que agrupe un conjunto de conceptos relacionados.

Criterios para el concepto central:
1. **Altamente Descriptivo y Específico**: Captura la esencia única del grupo con el mayor detalle posible. Evita generalizaciones.
2. **Granular**: Profundiza en los detalles específicos que unifican los conceptos.
3. **Informativo**: Refleja la naturaleza de la idea, incorporando palabras clave relevantes.
4. **Único y Distintivo**: Suficientemente específico para no confundirse con otros perfiles.
5. **Evitar genéricos**: NO uses "Desarrollo conceptual", "Idea principal", "Concepto central", "Tema General", "Análisis", "Relación Conceptual", "Perspectivas sobre", "Conceptos diversos no clasificados".
6. **Formato**: Título de tema o frase que resuma la idea principal.

Ejemplos:
- "equidad de género, empoderamiento femenino, brecha salarial" -> "Análisis de la Brecha Salarial y Estrategias de Empoderamiento Femenino en el Mercado Laboral"
- "cambio climático, energías renovables, impacto ambiental" -> "Innovaciones en Energías Renovables para Mitigar el Impacto del Cambio Climático Urbano"
- "neurociencia, plasticidad cerebral, aprendizaje" -> "Mecanismos Neuronales Subyacentes a la Plasticidad Cerebral y la Adquisición de Nuevas Habilidades"
- "algoritmos de machine learning, redes neuronales, deep learning" -> "Aplicaciones Avanzadas de Redes Neuronales Profundas en el Procesamiento de Lenguaje Natural" """

        if getattr(self, "workspace_name", None):
            system_prompt += f"\n\n**CONTEXTO CRÍTICO DE PROYECTO / WORKSPACE**: El concepto central formulado debe alinearse y pertenecer al proyecto/workspace '{self.workspace_name}'."

        prompt = f"""Dado el siguiente conjunto de conceptos relacionados: "{combined_concepts}".

Identifica la idea principal o concepto central **altamente granular y específico** que agrupe estos conceptos. Genera una frase o título descriptivo para este "Perfil de Idea"."""

        try:
            result = await self._call_structured_llm(
                prompt=prompt,
                schema=CentralConceptOutput,
                cache_key=cache_key,
                system_prompt=system_prompt,
                max_retries=3,
            )

            if result and result.concept:
                central_concept_llm = result.concept.strip()
                logger.debug(f"🧠 LLM identificó concepto central granular: {central_concept_llm}")
                self.llm_cache[cache_key] = central_concept_llm
                return central_concept_llm
            else:
                logger.warning("⚠️ LLM devolvió un concepto central vacío, usando fallback")
                return self._generate_fallback_central_concept(concepts)

        except Exception as e:
            logger.error(f"❌ Falló la identificación de concepto central: {e}")
            return self._generate_fallback_central_concept(concepts)

    async def _generate_profile_description(self, central_concept: str, categories: List[str], quotes_count: int, cluster_quotes: List[Dict[str, Any]]) -> str:
        """Genera descripción de un perfil de ideas usando salida estructurada."""

        categories_str = ", ".join(categories) if categories else "conceptos generales"
        quotes_texts = [q['text'] for q in cluster_quotes[:5]]

        # Generar una clave única para el cache
        cache_key = f"profile_desc_{hashlib.md5((central_concept + categories_str).encode()).hexdigest()}"

        # Verificar si el resultado está en caché
        if cache_key in self.llm_cache:
            logger.debug(f"📥 Usando resultado en caché para descripción de perfil")
            return self.llm_cache[cache_key]

        system_prompt = """Eres un experto en síntesis de conocimiento. Genera descripciones detalladas y completas de perfiles de ideas conceptuales.

La descripción debe:
1. Resaltar la importancia del concepto central
2. Explicar qué unifica las citas del cluster
3. Mencionar las principales categorías involucradas
4. Proporcionar un resumen coherente del conocimiento que representa el perfil
5. Ser exhaustiva y detallada, sin límite de palabras"""

        if getattr(self, "workspace_name", None):
            system_prompt += f"\n\n**CONTEXTO CRÍTICO DE PROYECTO / WORKSPACE**: La descripción redactada debe enmarcarse y pertenecer estrictamente al proyecto/workspace '{self.workspace_name}'."

        prompt = f"""El siguiente conjunto de {quotes_count} citas conceptuales se agrupa bajo el concepto central: "{central_concept}"

Categorías involucradas: {categories_str}

Citas clave:
{chr(10).join(f'- {text}' for text in quotes_texts)}

Genera una descripción detallada y completa para este perfil de ideas."""

        try:
            result = await self._call_structured_llm(
                prompt=prompt,
                schema=ProfileDescriptionOutput,
                cache_key=cache_key,
                system_prompt=system_prompt,
                max_retries=3,
            )

            if result and result.description:
                description = result.description.strip()
                logger.debug(f"🧠 LLM generó descripción de perfil: {description[:100]}...")
                self.llm_cache[cache_key] = description
                return description
            else:
                logger.error("❌ El LLM devolvió una descripción de perfil vacía.")
                # Fallback básico
                return f"Perfil de ideas centrado en '{central_concept}', que agrupa {quotes_count} citas conceptuales de las categorías: {categories_str}. Este perfil representa la convergencia temática de estos conceptos en el corpus analizado."

        except Exception as e:
            logger.error(f"❌ Falló la generación de descripción de perfil: {e}")
            return f"Perfil de ideas centrado en '{central_concept}', que agrupa {quotes_count} citas conceptuales de las categorías: {categories_str}. Este perfil representa la convergencia temática de estos conceptos en el corpus analizado."

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
        if not self.llm:
            logger.error("❌ LLM no disponible para crear relaciones por lotes")
            return []
        
        # Semáforo para limitar la concurrencia máxima (evitar saturar la API)
        semaphore = asyncio.Semaphore(4)
        
        async def _process_pair(pair: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            quote1_idx = pair["quote1_idx"]
            quote2_idx = pair["quote2_idx"]
            try:
                quote1 = quotes[quote1_idx]
                quote2 = quotes[quote2_idx]
                similarity = pair["similarity"]
                cache_key = f"relationship_{quote1_idx}_{quote2_idx}_{similarity}"
                
                if cache_key in self.llm_cache:
                    logger.debug(f"📥 Usando resultado en caché para relación entre citas {quote1_idx} y {quote2_idx}")
                    return self.llm_cache[cache_key]
                
                async with semaphore:
                    return await self._call_llm_with_retry_and_validation(
                        quote1, quote2, similarity, cache_key, quote1_idx, quote2_idx
                    )
            except Exception as e:
                logger.error(f"❌ Error procesando par de citas {quote1_idx}-{quote2_idx} en el lote: {e}")
                return None
        
        # Ejecutar todos los pares concurrentemente (con límite de semáforo)
        results = await asyncio.gather(*[_process_pair(pair) for pair in batch], return_exceptions=False)
        batch_results = [r for r in results if r is not None]
        return batch_results
    
    async def _call_llm_with_retry_and_validation(self, quote1: Dict, quote2: Dict, similarity: float, 
                                                cache_key: str, quote1_idx: int, quote2_idx: int) -> Optional[Dict[str, Any]]:
        """
        Llamada al LLM con salida estructurada para análisis de relaciones temáticas.
        Usa fallback chain (fast -> main -> fallback) y reintentos automáticos.

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
        # Verificar caché primero
        if cache_key in self.llm_cache:
            logger.debug(f"📥 Usando resultado en caché para relación {quote1_idx}-{quote2_idx}")
            return self.llm_cache[cache_key]

        # System prompt for relationship analysis
        system_prompt = """Eres un experto en análisis temático. Tu tarea es identificar la relación temática entre dos citas conceptuales.

Tipos de relación válidos:
- CONCEPTOS_RELACIONADOS: Conceptos similares o afines
- MARCOS_TEORICOS_AFINES: Marcos teóricos que comparten fundamentos
- ENFOQUES_METODOLOGICOS: Enfoques metodológicos complementarios
- HALLAZGOS_CONVERGENTES: Hallazgos que apuntan a la misma conclusión
- FUNDAMENTACION_TEORICA: Una cita fundamenta teóricamente a la otra
- APLICACION_METODOLOGICA: Una cita aplica la metodología de la otra
- VALIDACION_EMPIRICA: Una cita valida empíricamente a la otra
- CONFIRMACION_CONCEPTUAL: Una cita confirma conceptualmente a la otra
- ALTA_CONVERGENCIA_TEMATICA: Similitud muy alta (>0.85)
- CONVERGENCIA_TEMATICA: Similitud alta (>0.75)
- RELACION_TEMATICA: Relación temática general

Niveles de confianza: alta, media, baja"""

        if getattr(self, "workspace_name", None):
            system_prompt += f"\n\n**CONTEXTO CRÍTICO DE PROYECTO / WORKSPACE**: Los conceptos y citas que estás analizando pertenecen al proyecto/workspace '{self.workspace_name}'. Determina su relación semántica bajo este contexto."

        prompt = self._build_relationship_prompt(quote1, quote2, similarity)

        try:
            # Usar salida estructurada con fallback chain
            result = await self._call_structured_llm(
                prompt=prompt,
                schema=ThematicRelationshipOutput,
                cache_key=cache_key,
                system_prompt=system_prompt,
                max_retries=3,
            )

            if not result:
                logger.warning(f"⚠️ Respuesta vacía del LLM para par {quote1_idx}-{quote2_idx}, usando fallback")
                return self._create_default_relationship(quote1_idx, quote2_idx, similarity)

            # Convertir confianza string a numérico
            confidence_map = {"alta": 0.9, "media": 0.7, "baja": 0.5}
            confidence = confidence_map.get(result.confidence.lower(), 0.7)

            output = {
                "original_pair": {
                    "quote1_idx": quote1_idx,
                    "quote2_idx": quote2_idx,
                    "similarity": similarity
                },
                "type": result.type,
                "description": result.description,
                "confidence": confidence
            }

            # Almacenar en caché
            self.llm_cache[cache_key] = output
            logger.debug(f"✅ LLM respondió correctamente para par {quote1_idx}-{quote2_idx}: {result.type}")
            return output

        except Exception as e:
            logger.error(f"❌ Error en llamada estructurada para par {quote1_idx}-{quote2_idx}: {e}")
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
        Maneja bloques markdown (```json ... ```), caracteres de control y JSON anidado con arrays.
        
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
        
        # Extraer contenido de bloques markdown (```json ... ``` o ``` ... ```)
        md_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
        if md_match:
            cleaned = md_match.group(1).strip()
        
        # Intentar parsear directamente tras limpiar markdown
        try:
            import json
            json.loads(cleaned)
            return cleaned
        except Exception:
            pass
        
        # Buscar el bloque JSON más externo usando un balance de llaves
        start = cleaned.find('{')
        if start == -1:
            return None
        
        depth = 0
        for i, ch in enumerate(cleaned[start:], start=start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start:i + 1]
                    try:
                        import json
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        pass
                    break
        
        # Si no se encuentra JSON válido, devolver None
        return None
    
    async def _call_structured_llm(
        self,
        prompt: str,
        schema: Any,
        cache_key: str,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
    ) -> Optional[Any]:
        """
        Llamada estructurada al LLM usando invoke_structured_output con fallback chain.

        Args:
            prompt: Prompt para el LLM
            schema: Esquema Pydantic para la salida estructurada
            cache_key: Clave para el caché
            system_prompt: Prompt de sistema opcional
            max_retries: Número máximo de reintentos

        Returns:
            Instancia del schema parseada o None si falla
        """
        # Verificar caché primero
        if cache_key in self.llm_cache:
            logger.debug(f"📥 Usando resultado en caché para {cache_key}")
            return self.llm_cache[cache_key]

        # Obtener LLMs con fallback chain (fast -> main -> fallback)
        account_id = getattr(self, "current_account_id", None)

        if account_id:
            fast_llm = await get_llm_for_user(account_id, purpose="fast")
            main_llm = await get_llm_for_user(account_id, purpose="main")
        else:
            fast_llm = get_fast_llm()
            main_llm = get_main_llm()

        fallback_llm = get_fallback_llm()

        # Construir lista de LLMs a intentar en orden
        llms_to_try = []
        if fast_llm:
            llms_to_try.append(("fast", fast_llm))
        if main_llm and (not fast_llm or main_llm != fast_llm):
            llms_to_try.append(("main", main_llm))
        if fallback_llm and fallback_llm not in [llm for _, llm in llms_to_try]:
            llms_to_try.append(("fallback", fallback_llm))

        if not llms_to_try:
            logger.error("❌ No hay LLMs disponibles para llamada estructurada")
            return None

        # Construir mensajes
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        retry_config = {"stop_after_attempt": max_retries}

        for llm_name, llm in llms_to_try:
            logger.debug(f"🤖 Intentando LLM '{llm_name}' para {cache_key}")

            try:
                # Prune messages to fit token limit
                pruned_messages = await prune_messages_to_fit_token_limit(
                    messages, llm, settings.deep_research_max_tokens
                )

                if not pruned_messages:
                    logger.warning(f"⚠️ Mensajes podados vacíos para {llm_name}")
                    continue

                # Usar invoke_structured_output con reintentos automáticos
                result = await invoke_structured_output(
                    llm, schema, prompt, retry_config
                )

                if result is not None:
                    logger.debug(f"✅ LLM '{llm_name}' respondió correctamente para {cache_key}")
                    self.llm_cache[cache_key] = result
                    return result

            except Exception as e:
                error_str = str(e)

                # Manejar límite de tokens específicamente
                if is_token_limit_exceeded(e):
                    logger.warning(f"⚠️ Límite de tokens excedido con {llm_name}: {e}")
                    # Intentar con más poda agresiva
                    try:
                        aggressive_messages = await prune_messages_to_fit_token_limit(
                            messages, llm, settings.deep_research_max_tokens, keep_ratio=0.1
                        )
                        if aggressive_messages:
                            # Reconstruir prompt simple para el intento agresivo
                            simple_prompt = prompt
                            if system_prompt:
                                simple_prompt = f"{system_prompt}\n\n{simple_prompt}"
                            result = await invoke_structured_output(
                                llm, schema, simple_prompt, retry_config
                            )
                            if result is not None:
                                logger.debug(f"✅ LLM '{llm_name}' respondió con poda agresiva")
                                self.llm_cache[cache_key] = result
                                return result
                    except Exception as e2:
                        logger.warning(f"⚠️ Poda agresiva también falló: {e2}")

                # Manejar errores de OpenRouter tool_choice
                elif "tool_choice" in error_str and "Openrouter" in error_str:
                    logger.warning(f"⚠️ Error tool_choice OpenRouter con {llm_name}, intentando json_mode...")
                    try:
                        # Forzar json_mode
                        if is_openrouter_model(llm):
                            model_json = llm.with_structured_output(schema, method="json_mode")
                            if hasattr(model_json, 'streaming'):
                                model_json.streaming = False
                            model_json = model_json.with_retry(**retry_config)
                            result = await model_json.ainvoke(pruned_messages)
                            if result is not None:
                                logger.debug(f"✅ LLM '{llm_name}' respondió con json_mode")
                                self.llm_cache[cache_key] = result
                                return result
                    except Exception as e2:
                        logger.warning(f"⚠️ json_mode también falló: {e2}")

                else:
                    logger.warning(f"⚠️ LLM '{llm_name}' falló: {e}")

                # Continuar al siguiente LLM en la cadena de fallback
                continue

        logger.error(f"❌ Todos los LLMs fallaron para {cache_key}")
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
