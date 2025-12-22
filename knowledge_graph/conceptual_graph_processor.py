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
    
    def __init__(self, llm=None, sentence_transformer=None):
        """
        Inicializa el procesador conceptual.
        
        Args:
            llm: Modelo de lenguaje para análisis semántico
            sentence_transformer: Modelo para embeddings semánticos
        """
        self.llm = llm
        self.embedding_model = sentence_transformer # Renamed to generic embedding_model
        self.initialized = False
        self.llm_cache = {}  # Cache para resultados de LLM
        logger.info("🧠 ConceptualGraphProcessor inicializado")
    
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
    
    async def process_documents_conceptually(self, documents: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
        """
        Procesa documentos extrayendo citas conceptuales y sus relaciones temáticas.
        
        Args:
            documents: Lista de documentos con contenido
            dataset_name: Nombre del dataset
            
        Returns:
            Dict con nodos conceptuales, relaciones temáticas y perfiles de ideas
        """
        if not self.initialized:
            await self.initialize()
        
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
        """Usa el LLM para extraer citas conceptuales de alta calidad."""
        
        if not self.llm:
            return []
        
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
        
        try:
            # Optimizar el prompt para reducir tokens
            prompt = f"""
Analiza el texto y extrae 5-10 citas clave que expresen ideas conceptuales completas.

Criterios:
1. Ideas completas y coherentes
2. Valor conceptual/teórico
3. Representativas del contenido
4. Evita lo puramente descriptivo

Texto:
{content[:3000]}

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
            
            response = await self.llm.ainvoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
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
                self.llm_cache[cache_key] = quotes
                return quotes
            except json.JSONDecodeError:
                logger.warning("⚠️ Error parseando respuesta JSON del LLM. Intentando extraer JSON válido de la respuesta...")
                
                # Usar método mejorado de validación y limpieza
                cleaned_response = self._validate_and_clean_llm_response(response_text)
                
                if not cleaned_response:
                    logger.warning(f"⚠️ Respuesta vacía o inválida del LLM para extracción de citas")
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
                    self.llm_cache[cache_key] = quotes
                    return quotes
                except Exception as e2:
                    logger.error(f"❌ Error parseando JSON limpiado: {e2}")
                    return []
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
            embeddings = self.embedding_model.embed_documents(quote_texts)
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
        """Identifica el concepto central de un grupo de citas, usando LLM si está disponible."""

        # Extraer conceptos para el LLM
        concepts = [quote.get("concept", "") for quote in cluster_quotes if quote.get("concept")]
        
        if self.llm and concepts:
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
        """Genera descripción de un perfil de ideas, usando LLM si está disponible."""

        categories_str = ", ".join(categories) if categories else "conceptos generales"
        
        if not self.llm:
            raise ValueError("El LLM no está disponible para generar la descripción del perfil.")
        
        try:
            # Generar una clave única para el cache
            quotes_texts = [q['text'] for q in cluster_quotes]
            cache_key = f"profile_desc_{hashlib.md5((central_concept + categories_str).encode()).hexdigest()}"
            
            # Verificar si el resultado está en caché
            if cache_key in self.llm_cache:
                logger.debug(f"📥 Usando resultado en caché para descripción de perfil")
                return self.llm_cache[cache_key]
            
            # Usar LLM para una descripción más elaborada
            prompt = f"""El siguiente conjunto de {quotes_count} citas conceptuales se agrupa bajo el concepto central de
            Aquí están algunas de las citas clave:
            {quotes_texts[:5]}

            Genera una descripción detallada y completa (sin límite de palabras) para este perfil de ideas. La descripción debe:
            1. Resaltar la importancia del concepto central.
            2. Explicar qué unifica estas citas.
            3. Mencionar brevemente las principales categorías involucradas.
            4. Proporcionar un resumen coherente del conocimiento que este perfil representa.
            Responde ÚNICAMENTE con la descripción."""
            
            response = await self.llm.ainvoke(prompt)
            profile_description_llm = response.content.strip()
            if profile_description_llm:
                logger.debug(f"🧠 LLM generó descripción de perfil: {profile_description_llm}")
                # Almacenar en caché
                self.llm_cache[cache_key] = profile_description_llm
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
        if not self.llm:
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
                if cache_key in self.llm_cache:
                    logger.debug(f"📥 Usando resultado en caché para relación entre citas {quote1_idx} y {quote2_idx}")
                    batch_results.append(self.llm_cache[cache_key])
                    continue
                
                # Usar el método mejorado de llamada al LLM con validación y reintentos
                result = await self._call_llm_with_retry_and_validation(
                    quote1, quote2, similarity, cache_key, quote1_idx, quote2_idx
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
        
        max_retries = 3
        retry_delay = 1.0  # segundos
        
        for attempt in range(max_retries):
            try:
                # Crear prompt para el LLM
                prompt = self._build_relationship_prompt(quote1, quote2, similarity)
                
                logger.debug(f"🤖 Llamando LLM para par {quote1_idx}-{quote2_idx} (intento {attempt + 1}/{max_retries})")
                
                response = await asyncio.wait_for(
                    self.llm.ainvoke(prompt), 
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
                    self.llm_cache[cache_key] = result
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
                            self.llm_cache[cache_key] = extracted_result
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
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"🤖 Llamada segura LLM (intento {attempt + 1}/{max_retries})")
                
                response = await asyncio.wait_for(
                    self.llm.ainvoke(prompt), 
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
