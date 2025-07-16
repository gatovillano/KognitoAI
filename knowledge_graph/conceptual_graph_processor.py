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
    Procesador que crea grafos basados en ideas conceptuales extraídas como citas.
    
    Filosofía:
    - Cada nodo = Una cita que expresa una idea completa
    - Las relaciones = Conexiones temáticas entre ideas
    - Perfiles = Clusters de ideas centrales interrelacionadas
    """
    
    def __init__(self, llm=None, sentence_transformer=None):
        """
        Inicializa el procesador conceptual.
        
        Args:
            llm: Modelo de lenguaje para análisis semántico
            sentence_transformer: Modelo para embeddings semánticos
        """
        self.llm = llm
        self.sentence_transformer = sentence_transformer
        self.initialized = False
        logger.info("🧠 ConceptualGraphProcessor inicializado")
    
    async def initialize(self):
        """Inicializa los modelos necesarios."""
        if self.initialized:
            return
        
        logger.info("🚀 Inicializando modelos para procesamiento conceptual...")
        
        try:
            # Inicializar SentenceTransformers si no se proporciona
            if not self.sentence_transformer:
                await self._initialize_sentence_transformers()
            
            self.initialized = True
            logger.info("✅ Procesador conceptual inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando procesador conceptual: {e}")
            raise
    
    async def _initialize_sentence_transformers(self):
        """Inicializa SentenceTransformers."""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Usar modelo multilingüe optimizado para ideas conceptuales
            model_name = "paraphrase-multilingual-mpnet-base-v2"  # Mejor para conceptos
            logger.info(f"📥 Cargando modelo conceptual: {model_name}")
            
            import os
            cache_dir = "/app/.cache/sentence_transformers"
            os.makedirs(cache_dir, exist_ok=True)
            
            self.sentence_transformer = SentenceTransformer(
                model_name,
                cache_folder=cache_dir,
                device='cpu'
            )
            logger.info(f"✅ Modelo conceptual cargado: {model_name}")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando SentenceTransformers: {e}")
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
        """Extrae citas que expresan ideas conceptuales completas."""
        
        conceptual_quotes = []
        
        for doc_idx, doc in enumerate(documents):
            content = doc.get('content', '')
            if not content:
                continue
            
            logger.debug(f"🔍 Extrayendo conceptos del documento {doc_idx + 1}")
            
            # Estrategia 1: Usar LLM para extraer ideas clave
            if self.llm:
                llm_quotes = await self._extract_quotes_with_llm(content, doc)
                conceptual_quotes.extend(llm_quotes)
            
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
        
        try:
            prompt = f"""
Analiza el siguiente texto y extrae las 5-10 citas más importantes que expresen ideas conceptuales completas y significativas.

Criterios para las citas:
1. Deben expresar una idea completa y coherente
2. Deben tener valor conceptual o teórico
3. Deben ser representativas del contenido
4. Pueden ser oraciones o párrafos cortos
5. Evita citas puramente descriptivas o factuales

Texto:
{content[:3000]}

Responde en formato JSON:
{{
    "quotes": [
        {{
            "text": "cita textual exacta",
            "concept": "concepto principal que expresa",
            "importance": "alta/media",
            "category": "teoría/metodología/conclusión/definición"
        }}
    ]
}}
IMPORTANTE: Responde ÚNICAMENTE con el objeto JSON solicitado, sin ningún texto adicional antes o después.
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
                
                return quotes
            except json.JSONDecodeError:
                logger.warning("⚠️ Error parseando respuesta JSON del LLM. Intentando extraer JSON válido de la respuesta...")
                
                # Intentar limpiar la respuesta para aislar el JSON
                cleaned_response_text = response_text.strip()
                
                # Encontrar el índice del primer '{' y el último '}'
                first_brace = cleaned_response_text.find('{')
                last_brace = cleaned_response_text.rfind('}')
                
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    # Extraer lo que está entre el primer '{' y el último '}'
                    potential_json = cleaned_response_text[first_brace : last_brace + 1]
                    try:
                        parsed = json.loads(potential_json)
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
                        return quotes
                    except Exception as e2:
                        logger.error(f"❌ Error parseando JSON limpiado: {e2}")
                        return []
                else:
                    logger.warning("⚠️ No se encontró un bloque JSON válido después de limpiar la respuesta del LLM.")
                    return []
        except Exception as e:
            logger.error(f"❌ Error extrayendo citas con LLM: {e}")
            return []
    
    async def _extract_rich_sentences(self, content: str, doc: Dict[str, Any], doc_idx: int) -> List[Dict[str, Any]]:
        """Extrae oraciones conceptualmente ricas usando análisis textual."""
        
        quotes = []
        
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
        """Extrae párrafos con alta densidad conceptual."""
        
        quotes = []
        
        # Dividir en párrafos
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        for para_idx, paragraph in enumerate(paragraphs):
            # Filtros de calidad para párrafos
            if (len(paragraph) < 100 or len(paragraph) > 800 or
                not self._is_conceptually_dense_paragraph(paragraph)):
                continue
            
            quote = {
                "id": self._generate_quote_id(paragraph),
                "text": paragraph,
                "concept": self._extract_paragraph_concept(paragraph),
                "importance": "alta",  # Los párrafos suelen ser más importantes
                "category": "desarrollo_conceptual",
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
        """Categoriza una oración según su tipo conceptual."""
        
        sentence_lower = sentence.lower()
        
        if any(word in sentence_lower for word in ['define', 'definición', 'concepto de', 'se entiende por']):
            return 'definición'
        elif any(word in sentence_lower for word in ['metodología', 'método', 'procedimiento', 'proceso']):
            return 'metodología'
        elif any(word in sentence_lower for word in ['teoría', 'modelo', 'framework', 'enfoque teórico']):
            return 'teoría'
        elif any(word in sentence_lower for word in ['concluye', 'resultado', 'evidencia', 'demuestra']):
            return 'conclusión'
        elif any(word in sentence_lower for word in ['relación', 'conexión', 'vínculo', 'asociación']):
            return 'relación_conceptual'
        else:
            return 'desarrollo_conceptual'
    
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
        
        # Limitar cantidad para evitar sobrecarga
        return quality_quotes[:200]  # Máximo 200 citas conceptuales

    async def _analyze_thematic_relationships(self, quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analiza relaciones temáticas entre citas conceptuales."""

        if len(quotes) < 2:
            return []

        logger.info(f"🔗 Analizando relaciones temáticas entre {len(quotes)} citas")

        relationships = []

        # Crear embeddings para todas las citas
        quote_texts = [f"{quote['concept']}: {quote['text']}" for quote in quotes]
        if self.sentence_transformer is None:
            logger.error("❌ SentenceTransformer no está inicializado. No se pueden generar embeddings.")
            raise RuntimeError("SentenceTransformer no está inicializado. Asegúrese de que la inicialización sea exitosa.")
        embeddings = self.sentence_transformer.encode(quote_texts)

        # Analizar similitudes semánticas
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(embeddings)

        # Crear relaciones basadas en similitud temática
        for i in range(len(quotes)):
            for j in range(i + 1, len(quotes)):
                # CAMBIO: Convertir a float nativo de Python
                similarity = float(similarities[i][j])

                # Umbral más alto para relaciones conceptuales de calidad
                if similarity > 0.7:
                    relationship_type = self._determine_thematic_relationship_type(
                        quotes[i], quotes[j], similarity
                    )

                    relationship = {
                        "id": f"thematic_rel_{len(relationships)}",
                        "source_id": quotes[i]["id"],
                        "target_id": quotes[j]["id"],
                        "type": relationship_type,
                        # CAMBIO: Asegurarse de que el score también sea float
                        "similarity_score": float(similarity),
                        "description": self._generate_relationship_description(
                            quotes[i], quotes[j], relationship_type
                        ),
                        "confidence": self._calculate_relationship_confidence(
                            quotes[i], quotes[j], similarity
                        ),
                        "extraction_method": "thematic_similarity"
                    }
                    relationships.append(relationship)

        # Agregar relaciones por categoría conceptual
        category_relationships = await self._create_category_relationships(quotes)
        relationships.extend(category_relationships)

        # Agregar relaciones por documento fuente
        document_relationships = await self._create_document_relationships(quotes)
        relationships.extend(document_relationships)

        logger.info(f"✅ {len(relationships)} relaciones temáticas creadas")
        return relationships

    def _determine_thematic_relationship_type(self, quote1: Dict, quote2: Dict, similarity: float) -> str:
        """Determina el tipo de relación temática entre dos citas."""

        cat1 = quote1.get("category", "")
        cat2 = quote2.get("category", "")

        # Relaciones por categoría
        if cat1 == cat2:
            if cat1 == "definición":
                return "CONCEPTOS_RELACIONADOS"
            elif cat1 == "teoría":
                return "MARCOS_TEORICOS_AFINES"
            elif cat1 == "metodología":
                return "ENFOQUES_METODOLOGICOS"
            elif cat1 == "conclusión":
                return "HALLAZGOS_CONVERGENTES"
            else:
                return "DESARROLLO_TEMATICO"

        # Relaciones entre categorías diferentes
        if (cat1 == "definición" and cat2 == "teoría") or (cat1 == "teoría" and cat2 == "definición"):
            return "FUNDAMENTACION_TEORICA"
        elif (cat1 == "teoría" and cat2 == "metodología") or (cat1 == "metodología" and cat2 == "teoría"):
            return "APLICACION_METODOLOGICA"
        elif (cat1 == "metodología" and cat2 == "conclusión") or (cat1 == "conclusión" and cat2 == "metodología"):
            return "VALIDACION_EMPIRICA"
        elif (cat1 == "definición" and cat2 == "conclusión") or (cat1 == "conclusión" and cat2 == "definición"):
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
        central_concept = self._identify_central_concept(concepts)

        # Calcular puntuación de importancia
        importance_scores = [
            1.0 if quote.get("importance") == "alta" else 0.5
            for quote in cluster_quotes
        ]
        importance_score = sum(importance_scores) / len(importance_scores)

        # Identificar categorías representadas
        categories = list(set(quote.get("category", "") for quote in cluster_quotes))

        # Crear descripción del perfil
        profile_description = self._generate_profile_description(central_concept, categories, len(cluster_quotes))

        profile = {
            "id": f"profile_{len(cluster_ids)}_{central_concept.replace(' ', '_').lower()}",
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

    def _identify_central_concept(self, concepts: List[str]) -> str:
        """Identifica el concepto central de un grupo de conceptos."""

        # Contar frecuencia de palabras en los conceptos
        word_freq = {}
        for concept in concepts:
            words = concept.lower().split()
            for word in words:
                if len(word) > 3:  # Solo palabras significativas
                    word_freq[word] = word_freq.get(word, 0) + 1

        # Encontrar palabras más frecuentes
        if word_freq:
            most_common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            central_words = [word for word, freq in most_common_words]
            return " ".join(central_words).title()

        return "Concepto Central"

    def _generate_profile_description(self, central_concept: str, categories: List[str], quotes_count: int) -> str:
        """Genera descripción de un perfil de ideas."""

        categories_str = ", ".join(categories) if categories else "conceptos generales"

        return (f"Perfil de ideas centrado en '{central_concept}' que agrupa {quotes_count} "
                f"citas conceptuales relacionadas con {categories_str}. "
                f"Representa un núcleo temático coherente de conocimiento.")

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
