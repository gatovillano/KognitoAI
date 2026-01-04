# knowledge_graph/hybrid_graph_processor.py

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Set, TYPE_CHECKING
from datetime import datetime
import json
import re

from knowledge_graph.prompts_graph import RELATIONSHIP_EXTRACTION_PROMPT

if TYPE_CHECKING:
    from knowledge_graph.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

class HybridGraphProcessor:
    """
    Procesador híbrido que combina modelos especializados locales con LLMs.
    
    Pipeline:
    1. spaCy: Extracción de entidades básicas (NER)
    2. SentenceTransformers: Embeddings semánticos y relaciones
    3. Co-ocurrencia: Relaciones por proximidad textual
    4. LLM (Gemini Flash): Enriquecimiento de relaciones (opcional)
    """
    
    def __init__(self, llm=None, fast_llm=None, progress_tracker: Optional["ProgressTracker"] = None):
        self.llm = llm
        self.fast_llm = fast_llm
        self.spacy_model = None
        self.gliner_model = None  # NUEVO: Modelo GLiNER
        self.sentence_transformer = None
        self.initialized = False
        self._save_callback = None
        self.progress_tracker = progress_tracker  # Tracker de progreso
        logger.info("🔧 HybridGraphProcessor inicializado")
    
    async def initialize(self):
        """Inicializa todos los modelos necesarios."""
        if self.initialized:
            return
            
        logger.info("🚀 Inicializando modelos especializados...")
        
        try:
            from core.config import settings
            
            # Decidir qué modelos inicializar según configuración
            if settings.use_hybrid_ner:
                # Modo híbrido: ambos modelos
                logger.info("⚙️ Modo híbrido NER activado: spaCy + GLiNER")
                await self._initialize_spacy()
                if settings.use_gliner:
                    await self._initialize_gliner()
            elif settings.use_gliner:
                # Solo GLiNER
                logger.info("⚙️ Modo GLiNER exclusivo activado")
                await self._initialize_gliner()
            else:
                # Solo spaCy (fallback)
                logger.info("⚙️ Modo spaCy exclusivo activado") 
                await self._initialize_spacy()
            
            # Inicializar SentenceTransformers (siempre necesario)
            await self._initialize_sentence_transformers()
            
            self.initialized = True
            logger.info("✅ Todos los modelos especializados inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando modelos: {e}")
            raise
    
    async def _initialize_spacy(self):
        """Inicializa el modelo de spaCy para español."""
        try:
            import spacy
            from spacy.cli import download

            # Priorizar modelo en español
            model_name = "es_core_news_sm"  # Modelo pequeño para español (~15MB)
            try:
                # Solo deshabilitar lemmatizer, mantener parser para noun_chunks
                self.spacy_model = spacy.load(model_name, disable=["lemmatizer"])
                logger.info(f"✅ spaCy modelo español cargado: {model_name}")
            except OSError:
                logger.info(f"📥 Descargando modelo spaCy español: {model_name}")
                download(model_name)
                self.spacy_model = spacy.load(model_name, disable=["lemmatizer"])
                logger.info(f"✅ spaCy modelo español descargado y cargado: {model_name}")

        except Exception as e:
            logger.warning(f"⚠️ Error con spaCy español, intentando inglés como fallback: {e}")
            try:
                import spacy
                model_name = "en_core_web_sm"
                try:
                    self.spacy_model = spacy.load(model_name, disable=["lemmatizer"])
                    logger.info(f"✅ spaCy modelo inglés cargado (fallback): {model_name}")
                except OSError:
                    logger.info(f"📥 Descargando modelo spaCy inglés (fallback): {model_name}")
                    spacy.cli.download(model_name)
                    self.spacy_model = spacy.load(model_name, disable=["lemmatizer"])
                    logger.info(f"✅ spaCy modelo inglés descargado y cargado (fallback): {model_name}")
            except Exception as e2:
                logger.error(f"❌ Error inicializando spaCy: {e2}")
                logger.warning("⚠️ spaCy no estará disponible para extracción de entidades")
                self.spacy_model = None  # Asegurar que esté en None
    
    async def _initialize_gliner(self):
        """Inicializa el modelo GLiNER para NER mejorado con zero-shot."""
        try:
            from gliner import GLiNER
            from core.config import settings
            
            # Mapeo de tamaños de modelo
            model_map = {
                "small": "urchade/gliner_small-v2.1",      # ~250MB, buena precisión
                "base": "urchade/gliner_base",             # ~500MB, mejor precisión  
                "large": "urchade/gliner_large-v2.1"       # ~1GB, máxima precisión
            }
            
            model_size = settings.gliner_model_size.lower()
            model_name = model_map.get(model_size, model_map["small"])
            
            logger.info(f"📥 Descargando modelo GLiNER: {model_name} (tamaño: {model_size})")
            logger.info(f"⏳ Esto puede tomar un momento en la primera ejecución...")
            
            # Cargar modelo (se descarga automáticamente si no existe)
            self.gliner_model = GLiNER.from_pretrained(model_name)
            
            logger.info(f"✅ GLiNER modelo cargado exitosamente: {model_name}")
            logger.info(f"🎯 Características:")
            logger.info(f"   - Zero-shot NER (sin reentrenamiento)")
            logger.info(f"   - Tipos de entidades personalizables")
            logger.info(f"   - Umbral de confianza: {settings.gliner_threshold}")
            
        except ImportError:
            logger.error("❌ GLiNER no está instalado. Ejecuta: pip install gliner")
            logger.warning("⚠️ Continuando sin GLiNER...")
            self.gliner_model = None
        except Exception as e:
            logger.error(f"❌ Error inicializando GLiNER: {e}")
            logger.warning("⚠️ Continuando sin GLiNER...")
            self.gliner_model = None

    
    async def _initialize_sentence_transformers(self):
        """Inicializa el modelo de embeddings usando Ollama."""
        try:
            from utils.embeddings import get_embedding_model, initialize_embeddings
            
            logger.info("📥 Inicializando modelo de embeddings con Ollama...")
            
            # Inicializar el modelo de embeddings si no está ya inicializado
            await initialize_embeddings()
            
            # Obtener la instancia del modelo
            self.sentence_transformer = get_embedding_model()
            
            if self.sentence_transformer is None:
                raise ValueError("No se pudo obtener el modelo de embeddings de Ollama")
            
            logger.info(f"✅ Modelo de embeddings Ollama inicializado: {self.sentence_transformer.model}")

        except Exception as e:
            logger.error(f"❌ Error inicializando embeddings de Ollama: {e}")
            raise

    def set_save_callback(self, callback):
        """Configura un callback para guardar datos inmediatamente después de Fase 2."""
        self._save_callback = callback
        logger.info("💾 Callback de guardado configurado")
    
    def _add_tenant_ids(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agrega account_id, workspace_id y dataset_name a un diccionario de datos (entidad o relación).
        
        Args:
            data: Diccionario de entidad o relación
            
        Returns:
            El mismo diccionario con los IDs y dataset_name agregados
        """
        if hasattr(self, 'account_id') and self.account_id:
            data["account_id"] = self.account_id
        if hasattr(self, 'workspace_id') and self.workspace_id:
            data["workspace_id"] = self.workspace_id
        if hasattr(self, 'dataset_name') and self.dataset_name:
            data["dataset_name"] = self.dataset_name
        return data
    
    async def _get_embeddings(self, texts: List[str]):
        """
        Genera embeddings para una lista de textos usando Ollama.
        
        Args:
            texts: Lista de textos para generar embeddings
            
        Returns:
            Array numpy con los embeddings
        """
        import numpy as np
        
        if not texts:
            return np.array([])
        
        # Generar embeddings de manera async por lotes
        # La API aembed_documents espera una lista de documentos (str), y devuelve una lista de listas de floats
        embeddings = await self.sentence_transformer.aembed_documents(texts)
        
        return np.array(embeddings)
    
    async def process_documents(
        self, 
        documents: List[Dict[str, Any]], 
        dataset_name: str,
        account_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        progress_tracker: Optional["ProgressTracker"] = None
    ) -> Dict[str, Any]:
        """
        Procesa documentos usando el pipeline híbrido.
        
        Args:
            documents: Lista de documentos con contenido
            dataset_name: Nombre del dataset
            account_id: ID de la cuenta del usuario (para multi-tenancy)
            workspace_id: ID del workspace (para organización)
            progress_tracker: Tracker opcional para reportar progreso
            
        Returns:
            Dict con entidades, relaciones y metadatos del grafo
        """
        # Usar tracker proporcionado o el de la instancia
        tracker = progress_tracker or self.progress_tracker
        
        # Importar aquí para evitar circular imports
        if tracker:
            from knowledge_graph.progress_tracker import ProcessingPhase
        
        if not self.initialized:
            await self.initialize()
        
        # Almacenar IDs y dataset_name para usarlos en la creación de entidades/relaciones
        self.account_id = account_id
        self.workspace_id = workspace_id
        self.dataset_name = dataset_name
        
        logger.info(f"🧠 Iniciando procesamiento híbrido de {len(documents)} documentos")
        logger.info(f"   📋 Account ID: {account_id}")
        logger.info(f"   📁 Workspace ID: {workspace_id}")
        logger.info(f"   📦 Dataset: {dataset_name}")
        
        try:
            # ═══════════════════════════════════════════════════════════════
            # FASE 1: Extracción de entidades (spaCy, GLiNER o híbrido)
            # ═══════════════════════════════════════════════════════════════
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.HYBRID_EXTRACTING_ENTITIES,
                    f"📝 Extrayendo entidades de {len(documents)} documentos...",
                    10,
                    {"documents_processed": len(documents)}
                )
            
            entities = await self._extract_entities(documents)
            logger.info(f"✅ Fase 1 completada: {len(entities)} entidades extraídas")
            
            if tracker:
                tracker.update_sub_progress(f"📝 Extraídas {len(entities)} entidades, deduplicando...", 50)
            
            # Deduplicación inteligente basada en embeddings
            entities = await self._deduplicate_entities(entities)
            logger.info(f"✅ Deduplicación completada: {len(entities)} entidades únicas")
            
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.HYBRID_DEDUPLICATING,
                    f"✅ {len(entities)} entidades únicas después de deduplicación",
                    25,
                    {"entities_count": len(entities)}
                )
            
            # ═══════════════════════════════════════════════════════════════
            # FASE 2: Análisis semántico con SentenceTransformers
            # ═══════════════════════════════════════════════════════════════
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.HYBRID_SEMANTIC_RELATIONSHIPS,
                    f"🔗 Analizando relaciones semánticas entre {len(entities)} entidades...",
                    35
                )
            
            relationships = await self._extract_relationships_semantic(documents, entities)
            logger.info(f"✅ Fase 2 completada: {len(relationships)} relaciones semánticas")
            
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.HYBRID_SEMANTIC_RELATIONSHIPS,
                    f"✅ {len(relationships)} relaciones semánticas creadas",
                    50,
                    {"relationships_count": len(relationships)}
                )

            # 🚨 GUARDAR INMEDIATAMENTE después de Fase 2 (antes de que se cuelgue)
            logger.info("💾 GUARDANDO DATOS INMEDIATAMENTE después de Fase 2...")
            try:
                # Crear resultado parcial con Fase 1 + Fase 2
                partial_result = {
                    "entities": entities,
                    "relationships": relationships,
                    "metadata": {
                        "dataset_name": dataset_name,
                        "processed_with": "hybrid_pipeline_phase2",
                        "processing_time": datetime.now().isoformat(),
                        "documents_count": len(documents),
                        "entities_count": len(entities),
                        "relationships_count": len(relationships),
                        "phases_completed": ["spacy_entities", "semantic_relationships"],
                        "status": "phase2_complete"
                    }
                }

                # Llamar callback de guardado si existe
                if hasattr(self, '_save_callback') and self._save_callback:
                    logger.info("📞 Ejecutando callback de guardado...")
                    await self._save_callback(entities, relationships)
                    logger.info("✅ Callback de guardado ejecutado exitosamente")

            except Exception as save_error:
                logger.error(f"❌ Error guardando después de Fase 2: {save_error}")
                # Continuar procesamiento aunque falle el guardado

            # ═══════════════════════════════════════════════════════════════
            # FASE 3: Co-ocurrencia optimizada para candidatos
            # ═══════════════════════════════════════════════════════════════
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.HYBRID_COOCCURRENCE,
                    "🔍 Generando candidatos de relación por co-ocurrencia...",
                    60
                )
            
            logger.info("⏭️ Fase 3: Generando candidatos de relación por co-ocurrencia optimizada")
            cooccurrence_rels = await self._extract_cooccurrence_relationships_optimized(documents, entities)
            
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.HYBRID_COOCCURRENCE,
                    f"✅ {len(cooccurrence_rels)} candidatos de co-ocurrencia generados",
                    70,
                    {"cooccurrence_candidates": len(cooccurrence_rels)}
                )
            
            # ═══════════════════════════════════════════════════════════════
            # FASE 4: Enriquecimiento con LLM (Si está disponible)
            # ═══════════════════════════════════════════════════════════════
            if (self.fast_llm or self.llm) and cooccurrence_rels:
                if tracker:
                    tracker.update_phase(
                        ProcessingPhase.HYBRID_LLM_ENRICHMENT,
                        f"🤖 Enriqueciendo {len(cooccurrence_rels)} relaciones con LLM...",
                        75
                    )
                
                logger.info(f"🤖 Fase 4: Enriqueciendo {len(cooccurrence_rels)} relaciones con LLM...")
                enriched_rels = await self._enrich_relationships_with_llm(documents, cooccurrence_rels, entities)
                # Combinar relaciones semánticas con las enriquecidas por LLM
                all_relationships = relationships + enriched_rels
                logger.info(f"✅ Fase 4 completada: {len(enriched_rels)} relaciones enriquecidas")
                
                if tracker:
                    tracker.update_phase(
                        ProcessingPhase.HYBRID_LLM_ENRICHMENT,
                        f"✅ {len(enriched_rels)} relaciones enriquecidas con LLM",
                        90,
                        {"relationships_count": len(all_relationships)}
                    )
            else:
                # Si no hay LLM, usar solo las semánticas (o añadir co-ocurrencias básicas si se prefiere)
                all_relationships = relationships
                logger.info("⚠️ Fase 4 saltada: LLM no disponible o no hay candidatos")
                
                if tracker:
                    tracker.update_sub_progress("⏭️ Fase LLM saltada (no disponible o sin candidatos)", 90)
            
            logger.info(f"✅ Procesamiento completado con {len(all_relationships)} relaciones totales")
            
            # ═══════════════════════════════════════════════════════════════
            # FINALIZACIÓN
            # ═══════════════════════════════════════════════════════════════
            # Crear resultado final
            result = {
                "entities": entities,
                "relationships": all_relationships,
                "metadata": {
                    "dataset_name": dataset_name,
                    "processed_with": "hybrid_pipeline",
                    "processing_time": datetime.now().isoformat(),
                    "documents_count": len(documents),
                    "entities_count": len(entities),
                    "relationships_count": len(all_relationships),
                    "phases": {
                        "spacy_entities": len(entities),
                        "semantic_relationships": len(relationships),
                        "cooccurrence_relationships": len(cooccurrence_rels)
                    }
                }
            }
            
            logger.info(f"🎉 Procesamiento híbrido completado:")
            logger.info(f"   📊 Entidades: {len(entities)}")
            logger.info(f"   🔗 Relaciones: {len(all_relationships)}")
            logger.info(f"   ⚡ Método: Pipeline híbrido local")
            
            # Marcar progreso como casi completo (el guardado a Neo4j se hace después)
            if tracker:
                tracker.update_phase(
                    ProcessingPhase.SAVING_TO_NEO4J,
                    f"💾 Guardando {len(entities)} entidades y {len(all_relationships)} relaciones en Neo4j...",
                    95,
                    {"entities_count": len(entities), "relationships_count": len(all_relationships)}
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento híbrido: {e}")
            if tracker:
                tracker.set_error(str(e))
            raise
    
    async def _extract_entities_spacy(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extrae entidades usando spaCy con validaciones de calidad mejoradas."""
        # ✅ NUEVA VERIFICACIÓN: Verificar que spaCy está disponible
        if self.spacy_model is None:
            logger.warning("⚠️ spaCy no está disponible. Saltando extracción de spaCy.")
            return []
        
        entities = []
        entity_set = set()  # Para evitar duplicados
        
        # Lista de palabras genéricas a excluir
        generic_words = {
            'cosa', 'cosas', 'parte', 'partes', 'tipo', 'tipos', 'forma', 'formas',
            'manera', 'maneras', 'ejemplo', 'ejemplos', 'caso', 'casos', 'vez', 'veces',
            'tiempo', 'tiempos', 'momento', 'momentos', 'lugar', 'lugares', 'punto', 'puntos',
            'área', 'áreas', 'aspecto', 'aspectos', 'elemento', 'elementos', 'factor', 'factores',
            'thing', 'things', 'part', 'parts', 'type', 'types', 'way', 'ways', 'example', 'examples'
        }
        
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            if not content:
                continue
                
            logger.debug(f"🔍 Procesando documento {i+1} con spaCy...")
            
            # Procesar con spaCy en un hilo separado para no bloquear
            spacy_doc = await asyncio.to_thread(self.spacy_model, content[:10000])  # Limitar a 10k caracteres
            
            # Extraer entidades nombradas con validación mejorada
            for ent in spacy_doc.ents:
                entity_text = ent.text.strip()
                entity_lower = entity_text.lower()
                
                # Validaciones de calidad RELAJADAS para más cobertura
                if (len(entity_text) < 2 or  # Reducido de 3 a 2 para mayor cobertura
                    entity_lower in generic_words or  # No palabras genéricas
                    not any(c.isalpha() for c in entity_text) or  # Debe contener letras
                    entity_text.count(' ') > 8):  # Aumentado de 5 a 8 (máximo 9 palabras)
                    continue
                
                # Filtrar entidades que son solo números o puntuación
                if entity_text.replace(' ', '').replace('.', '').replace(',', '').isdigit():
                    continue
                
                entity_key = f"{entity_lower}_{ent.label_}"
                if entity_key not in entity_set:
                    entity_set.add(entity_key)
                    
                    # Calcular confianza basada en características de la entidad
                    confidence = self._calculate_entity_confidence(ent)
                    
                    entity_data = self._add_tenant_ids({
                        "id": f"entity_{len(entities)}",
                        "name": entity_text,
                        "type": ent.label_,
                        "description": f"{ent.label_}: {entity_text}",
                        "source_document": doc.get('title', f'doc_{i}'),
                        "source_document_id": doc.get('id'),
                        "confidence": confidence,
                        "extraction_method": "spacy_ner"
                    })
                    entities.append(entity_data)
            
            # Extraer conceptos semánticos más ricos
            await self._extract_semantic_concepts(spacy_doc, doc, i, entities, entity_set)
        
        return entities
    
    def _calculate_entity_confidence(self, entity) -> float:
        """Calcula la confianza de una entidad basada en sus características."""
        base_confidence = 0.9
        
        # Penalizar entidades muy cortas
        if len(entity.text) < 4:
            base_confidence -= 0.1
        
        # Bonificar entidades en mayúsculas (nombres propios)
        if entity.text[0].isupper():
            base_confidence += 0.05
        
        # Penalizar si contiene muchos números
        num_digits = sum(c.isdigit() for c in entity.text)
        if num_digits > len(entity.text) * 0.3:
            base_confidence -= 0.1
        
        # Bonificar tipos importantes
        important_types = ['PERSON', 'ORG', 'GPE', 'PRODUCT', 'EVENT', 'PER', 'LOC']
        if entity.label_ in important_types:
            base_confidence += 0.05
        
        return round(max(0.5, min(1.0, base_confidence)), 2)
    
    async def _extract_entities(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Dispatcher para extracción de entidades que decide qué modelo usar.
        
        Modos:
        - spaCy solo: Rápido, bueno para entidades estándar
        - GLiNER solo: Más preciso, tipos personalizados
        - Híbrido: Combina ambos para mejor cobertura
        """
        from core.config import settings
        
        # ✅ NUEVA VERIFICACIÓN: Verificar qué modelos están realmente disponibles
        spacy_available = self.spacy_model is not None
        gliner_available = self.gliner_model is not None
        
        logger.info(f"🔍 Modelos disponibles: spaCy={spacy_available}, GLiNER={gliner_available}")
        
        if settings.use_hybrid_ner and gliner_available and spacy_available:
            # Modo híbrido: combinar spaCy (rápido) + GLiNER (preciso)
            logger.info("🔄 Modo híbrido: spaCy + GLiNER activado")
            
            spacy_entities = await self._extract_entities_spacy(documents)
            logger.info(f"   📊 spaCy extrajo: {len(spacy_entities)} entidades")
            
            gliner_entities = await self._extract_entities_gliner(documents)
            logger.info(f"   📊 GLiNER extrajo: {len(gliner_entities)} entidades")
            
            # Combinar y marcar fuente
            for ent in spacy_entities:
                ent["extraction_method"] = f"{ent.get('extraction_method', 'spacy')}_hybrid"
            for ent in gliner_entities:
                ent["extraction_method"] = f"{ent.get('extraction_method', 'gliner')}_hybrid"
            
            combined = spacy_entities + gliner_entities
            logger.info(f"   ✅ Total combinado: {len(combined)} entidades (antes de deduplicar)")
            return combined
            
        elif gliner_available:
            # Solo GLiNER (si spaCy no está disponible o no se requiere híbrido)
            logger.info("🎯 Modo GLiNER exclusivo activado")
            return await self._extract_entities_gliner(documents)
            
        elif spacy_available:
            # Solo spaCy (fallback si GLiNER no está disponible)
            logger.info("⚡ Modo spaCy exclusivo activado")
            return await self._extract_entities_spacy(documents)
            
        else:
            # 🚨 NINGÚN MODELO DISPONIBLE
            logger.error("❌ ERROR: No hay modelos NER disponibles (ni spaCy ni GLiNER)")
            logger.error("❌ No se pueden extraer entidades. Verificar instalación de dependencias.")
            return []
    
    async def _extract_entities_gliner(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extrae entidades usando GLiNER con tipos personalizados."""
        from core.config import settings
        
        entities = []
        entity_set = set()
        
        # Definir tipos de entidades (personalizables según tu dominio)
        entity_labels = [
            # Entidades básicas (compatibles con spaCy)
            "person", "organization", "location", "product", "event", "date", "money",
            
            # Conceptos académicos/técnicos y de negocio (AMPLIADO)
            "theory", "methodology", "concept", "technology", "research_area",
            "institution", "publication", "dataset", "algorithm", "framework",
            "scientific_term", "model", "technique", "approach", "system",
            "skill", "tool", "problem", "solution", "metric", "goal", "strategy",
            "software", "hardware", "language", "protocol"
        ]
        
        logger.info(f"🎯 GLiNER extraerá {len(entity_labels)} tipos de entidades")
        
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            if not content:
                continue
            
            logger.debug(f"🔍 Procesando documento {i+1} con GLiNER...")
            
            # ✅ SOLUCIÓN AJUSTADA: Dividir contenido considerando límite real de GLiNER (384 chars)
            chunks = self._split_content_intelligently(content, max_chars=350)  # Margen de seguridad antes de 384
            
            # Procesar máximo 25 chunks por documento (aumentado de 10 para textos densos)
            for chunk_idx, chunk in enumerate(chunks[:25]):
                try:
                    # Predecir entidades con GLiNER en un hilo separado
                    predicted_entities = await asyncio.to_thread(
                        self.gliner_model.predict_entities,
                        chunk,
                        entity_labels,
                        threshold=settings.gliner_threshold
                    )
                    
                    for ent in predicted_entities:
                        entity_text = ent['text'].strip()
                        entity_lower = entity_text.lower()
                        entity_label = ent['label']
                        entity_score = ent['score']
                        
                        # Validaciones de calidad RELAJADAS para más cobertura
                        if (len(entity_text) < 2 or  # Reducido de 3 a 2
                            not any(c.isalpha() for c in entity_text) or
                            entity_text.count(' ') > 8):  # Aumentado de 6 a 8 (máximo 9 palabras)
                            continue
                        
                        entity_key = f"{entity_lower}_{entity_label}"
                        if entity_key not in entity_set:
                            entity_set.add(entity_key)
                            
                            # Mapear labels de GLiNER a tipos compatibles
                            entity_type = self._map_gliner_label_to_type(entity_label)
                            
                            entity_data = self._add_tenant_ids({
                                "id": f"entity_gliner_{len(entities)}",
                                "name": entity_text,
                                "type": entity_type,
                                "description": f"{entity_label}: {entity_text}",
                                "source_document": doc.get('title', f'doc_{i}'),
                                "source_document_id": doc.get('id'),
                                "confidence": round(entity_score, 2),
                                "extraction_method": "gliner_zero_shot",
                                "gliner_label": entity_label,  # Guardar label original
                                "chunk_index": chunk_idx,  # NUEVO: Indicar de qué chunk viene
                                "was_split": len(chunks) > 1  # NUEVO: Indicar si el texto fue dividido
                            })
                            entities.append(entity_data)
                            
                except Exception as e:
                    logger.warning(f"⚠️ Error procesando chunk {chunk_idx} del doc {i}: {e}")
                    continue
        
        logger.info(f"✅ GLiNER extrajo {len(entities)} entidades")
        logger.info(f"📊 Procesamiento: {len(chunks)} chunks por documento (límite: 350 chars para evitar truncamiento de GLiNER)")
        return entities
    
    def _split_content_intelligently(self, content: str, max_chars: int = 350) -> List[str]:
        """División inteligente del contenido para evitar truncamiento de GLiNER.
        
        Args:
            content: Texto a dividir
            max_chars: Límite máximo por chunk (350 para evitar truncamiento de GLiNER a 384)
        
        Returns:
            Lista de chunks con texto dividido inteligentemente
        """
        if len(content) <= max_chars:
            return [content]
        
        chunks = []
        current_chunk = ""
        
        # Patrones de división (en orden de prioridad)
        split_patterns = [
            r'\.\s+',           # Fin de oración (punto + espacio)
            r';\s+',            # Punto y coma + espacio
            r',\s+',            # Coma + espacio (menos preferible)
            r'\n\s*\n',         # Párrafos vacíos
            r'\n',              # Líneas nuevas
            r'\s+'              # Espacios en blanco (último recurso)
        ]
        
        sentences = content.split('. ')
        
        for sentence in sentences:
            # Agregar el punto de vuelta si no es la última oración
            if sentence != sentences[-1]:
                sentence += '. '
            
            # Si agregar esta oración excede el límite
            if len(current_chunk + sentence) > max_chars:
                # Guardar el chunk actual si no está vacío
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # Si la oración individual es muy larga, dividirla
                if len(sentence) > max_chars:
                    # Dividir por comas si es muy larga
                    parts = sentence.split(', ')
                    temp_chunk = ""
                    for part in parts:
                        if len(temp_chunk + part) > max_chars:
                            if temp_chunk.strip():
                                chunks.append(temp_chunk.strip())
                            temp_chunk = part
                        else:
                            temp_chunk += ", " + part if temp_chunk else part
                    
                    if temp_chunk.strip():
                        current_chunk = temp_chunk
                    else:
                        current_chunk = ""
                else:
                    current_chunk = sentence
            else:
                # Agregar al chunk actual
                current_chunk += sentence
        
        # Agregar el último chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _map_gliner_label_to_type(self, gliner_label: str) -> str:
        """Mapea labels de GLiNER a tipos compatibles con el sistema."""
        label_map = {
            # Básicas
            "person": "PERSON",
            "organization": "ORG",
            "location": "LOC",
            "product": "PRODUCT",
            "event": "EVENT",
            "date": "DATE",
            "money": "MONEY",
            
            # Conceptos (convertir a nuestro sistema de tipos)
            "theory": "CONCEPT_TECHNICAL",
            "methodology": "CONCEPT_TECHNICAL",
            "concept": "CONCEPT_PHRASE",
            "technology": "CONCEPT_TECHNICAL",
            "research_area": "CONCEPT_PHRASE",
            "institution": "ORG",
            "publication": "PRODUCT",
            "dataset": "PRODUCT",
            "algorithm": "CONCEPT_TECHNICAL",
            "framework": "CONCEPT_TECHNICAL",
            "scientific_term": "CONCEPT_TECHNICAL",
            "model": "CONCEPT_TECHNICAL",
            "technique": "CONCEPT_TECHNICAL",
            "approach": "CONCEPT_PHRASE",
            "system": "CONCEPT_TECHNICAL"
        }
        
        return label_map.get(gliner_label.lower(), gliner_label.upper())

    
    async def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detecta y fusiona entidades duplicadas o muy similares usando embeddings.
        
        Args:
            entities: Lista de entidades extraídas
            
        Returns:
            Lista de entidades deduplicadas
        """
        if len(entities) < 2:
            return entities
        
        logger.info(f"🔄 Iniciando deduplicación de {len(entities)} entidades...")
        
        # Crear textos para embeddings (nombre + descripción)
        entity_texts = [
            f"{e.get('name', '')} {e.get('description', '')}"
            for e in entities
        ]
        
        # Generar embeddings
        embeddings = await self._get_embeddings(entity_texts)
        
        # Calcular matriz de similitud en un hilo separado
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = await asyncio.to_thread(cosine_similarity, embeddings)
        
        # Encontrar y fusionar duplicados
        threshold = 0.92  # Muy similar (>92%)
        processed = set()
        deduplicated_entities = []
        duplicates_found = 0
        
        for i, entity in enumerate(entities):
            if i in processed:
                continue
            
            # Encontrar todas las entidades muy similares a esta
            similar_indices = []
            for j in range(i + 1, len(entities)):
                if j not in processed and similarities[i][j] > threshold:
                    # Verificar también que sean del mismo tipo o tipos compatibles
                    type_i = entity.get("type", "")
                    type_j = entities[j].get("type", "")
                    
                    if self._are_compatible_types(type_i, type_j):
                        similar_indices.append(j)
                        processed.add(j)
            
            if similar_indices:
                # Fusionar esta entidad con sus duplicados
                to_merge = [entity] + [entities[idx] for idx in similar_indices]
                merged = self._merge_entities(to_merge)
                deduplicated_entities.append(merged)
                duplicates_found += len(similar_indices)
            else:
                # Entidad única, mantener tal cual
                deduplicated_entities.append(entity)
            
            processed.add(i)
        
        logger.info(f"✅ Deduplicación completada:")
        logger.info(f"   📊 Entidades originales: {len(entities)}")
        logger.info(f"   📊 Duplicados fusionados: {duplicates_found}")
        logger.info(f"   📊 Entidades únicas: {len(deduplicated_entities)}")
        
        return deduplicated_entities
    
    def _are_compatible_types(self, type1: str, type2: str) -> bool:
        """Verifica si dos tipos de entidades son compatibles para fusión."""
        # Tipos exactamente iguales
        if type1 == type2:
            return True
        
        # Grupos de tipos compatibles
        compatible_groups = [
            {"PERSON", "PER"},  # Personas
            {"ORG", "ORGANIZATION"},  # Organizaciones
            {"LOC", "GPE", "LOCATION"},  # Lugares
            {"CONCEPT_PHRASE", "CONCEPT_COMPOUND", "CONCEPT_TECHNICAL"},  # Conceptos
        ]
        
        for group in compatible_groups:
            if type1 in group and type2 in group:
                return True
        
        return False
    
    def _merge_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fusiona múltiples entidades duplicadas en una sola enriquecida.
        
        Args:
            entities: Lista de entidades a fusionar
            
        Returns:
            Entidad fusionada con metadatos consolidados
        """
        if not entities:
            return {}
        
        # Tomar el nombre más largo/descriptivo
        best_name = max([e.get("name", "") for e in entities], key=len)
        
        # Tomar la descripción más informativa
        descriptions = [e.get("description", "") for e in entities if e.get("description")]
        best_description = max(descriptions, key=len) if descriptions else ""
        
        # Tomar el tipo más específico (priorizar tipos no-CONCEPT)
        types = [e.get("type", "") for e in entities]
        non_concept_types = [t for t in types if "CONCEPT" not in t]
        primary_type = non_concept_types[0] if non_concept_types else types[0]
        
        # Calcular confianza promedio ponderada
        confidences = [e.get("confidence", 0.5) for e in entities]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Consolidar documentos fuente
        source_docs = list(set(e.get("source_document", "") for e in entities if e.get("source_document")))
        
        # Consolidar métodos de extracción
        methods = list(set(e.get("extraction_method", "") for e in entities if e.get("extraction_method")))
        
        # Crear entidad fusionada
        merged_entity = {
            "id": entities[0]["id"],  # Mantener el primer ID
            "name": best_name,
            "description": best_description,
            "type": primary_type,
            "confidence": round(min(0.99, avg_confidence + 0.05), 2),  # Bonus por fusión
            "source_document": source_docs[0] if source_docs else "",
            "extraction_method": "+".join(methods[:2]),  # Máximo 2 métodos
            "merged_from": len(entities),
            "merged_variants": [e.get("name", "") for e in entities if e.get("name") != best_name][:3]  # Hasta 3 variantes
        }

        # Preservar IDs de tenant y dataset_name (usando el primero que tenga valor)
        for key in ["account_id", "workspace_id", "dataset_name"]:
            for e in entities:
                if e.get(key):
                    merged_entity[key] = e[key]
                    break
        
        # Preservar metadatos adicionales del mejor candidato
        for key in ["frequency", "dependency", "centrality_score"]:
            values = [e.get(key) for e in entities if key in e]
            if values:
                if key == "frequency":
                    merged_entity[key] = sum(values)  # Sumar frecuencias
                else:
                    merged_entity[key] = max(values)  # Tomar el mejor valor
        
        return merged_entity

    
    async def _extract_relationships_semantic(self, documents: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extrae relaciones semánticas más inteligentes entre conceptos."""
        relationships = []

        if len(entities) < 2:
            return relationships

        logger.info(f"🔗 Calculando relaciones semánticas conceptuales entre {len(entities)} entidades...")

        # Separar entidades por tipo para relaciones más inteligentes
        entities_by_type = {}
        for ent in entities:
            ent_type = ent.get("type", "UNKNOWN")
            if ent_type not in entities_by_type:
                entities_by_type[ent_type] = []
            entities_by_type[ent_type].append(ent)

        logger.info(f"📊 Tipos de entidades encontrados: {list(entities_by_type.keys())}")

        # 1. Relaciones entre conceptos y entidades nombradas
        await self._create_concept_entity_relationships(entities_by_type, relationships)

        # 2. Relaciones entre conceptos similares
        await self._create_concept_similarity_relationships(entities_by_type, relationships)

        # 3. Relaciones jerárquicas (conceptos generales vs específicos)
        await self._create_hierarchical_relationships(entities_by_type, relationships)

        logger.info(f"✅ Relaciones semánticas creadas: {len(relationships)}")
        return relationships

    async def _create_concept_entity_relationships(self, entities_by_type, relationships):
        """Crea relaciones entre conceptos y entidades nombradas."""

        # Obtener conceptos y entidades nombradas
        concepts = []
        named_entities = []

        for ent_type, entities in entities_by_type.items():
            if "CONCEPT" in ent_type:
                concepts.extend(entities)
            elif ent_type in ["PER", "ORG", "LOC", "MISC"]:
                named_entities.extend(entities)

        if not concepts or not named_entities:
            return

        logger.info(f"🔗 Relacionando {len(concepts)} conceptos con {len(named_entities)} entidades nombradas")

        # Crear embeddings
        concept_texts = [f"{c['name']} {c['description']}" for c in concepts]
        entity_texts = [f"{e['name']} {e['description']}" for e in named_entities]

        if concept_texts and entity_texts:
            concept_embeddings = await self._get_embeddings(concept_texts)
            entity_embeddings = await self._get_embeddings(entity_texts)

            # Calcular similitudes cruzadas en un hilo separado
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            cross_similarities = await asyncio.to_thread(cosine_similarity, concept_embeddings, entity_embeddings)

            # OPTIMIZACIÓN: En lugar de iterar sobre TODAS las combinaciones,
            # solo tomamos las top-k más similares para cada concepto
            threshold = 0.65  # REDUCIDO de 0.75 para mayor densidad
            max_relations_per_concept = 8  # AUMENTADO de 3 para mayor conectividad
            
            logger.info(f"⚡ Optimizando: buscando top-{max_relations_per_concept} relaciones por concepto (umbral: {threshold})")
            
            for i, concept in enumerate(concepts):
                # Obtener los índices de las entidades más similares para este concepto
                similarities_for_concept = cross_similarities[i]
                top_indices = np.argsort(similarities_for_concept)[-max_relations_per_concept:][::-1]
                
                for j in top_indices:
                    similarity = similarities_for_concept[j]

                    if similarity > threshold:
                        entity = named_entities[j]
                        # Determinar tipo de relación más específico
                        rel_type = self._determine_relationship_type(concept, entity, similarity)

                        relationships.append(self._add_tenant_ids({
                            "id": f"concept_rel_{len(relationships)}",
                            "source_entity_id": concept["id"],
                            "target_entity_id": entity["id"],
                            "type": rel_type,  # Usar 'type' en lugar de 'relationship_type'
                            "relationship_type": rel_type,  # Mantener ambos por compatibilidad
                            "description": f"{concept['name']} está relacionado con {entity['name']}",
                            "confidence": float(similarity),
                            "extraction_method": "semantic_concept_entity"
                        }))
            
            logger.info(f"✅ Creadas {len([r for r in relationships if r.get('extraction_method') == 'semantic_concept_entity'])} relaciones concepto-entidad")

    async def _create_concept_similarity_relationships(self, entities_by_type, relationships):
        """Crea relaciones entre conceptos similares."""

        all_concepts = []
        for ent_type, entities in entities_by_type.items():
            if "CONCEPT" in ent_type:
                all_concepts.extend(entities)

        if len(all_concepts) < 2:
            return

        logger.info(f"🔗 Relacionando conceptos similares: {len(all_concepts)} conceptos")

        # Crear embeddings para conceptos
        concept_texts = [f"{c['name']} {c['description']}" for c in all_concepts]
        embeddings = await self._get_embeddings(concept_texts)

        # Calcular similitudes en un hilo separado
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        similarities = await asyncio.to_thread(cosine_similarity, embeddings)

        # OPTIMIZACIÓN: Limitar el número de relaciones por concepto
        threshold = 0.70  # REDUCIDO de 0.80 para mayor densidad
        max_relations_per_concept = 5  # AUMENTADO de 2 para mayor conectividad
        
        logger.info(f"⚡ Optimizando: buscando top-{max_relations_per_concept} conceptos similares por concepto (umbral: {threshold})")
        
        for i in range(len(all_concepts)):
            # Obtener los índices de los conceptos más similares (excluyendo el mismo)
            similarities_for_concept = similarities[i]
            # Excluir el propio concepto (i) y obtener los top-k
            top_indices = np.argsort(similarities_for_concept)[-(max_relations_per_concept+1):-1][::-1]
            
            for j in top_indices:
                if j > i:  # Evitar duplicados (solo crear A->B, no B->A)
                    similarity = similarities[i][j]

                    if similarity > threshold:
                        relationships.append(self._add_tenant_ids({
                        "id": f"concept_sim_{len(relationships)}",
                        "source_entity_id": all_concepts[i]["id"],
                        "target_entity_id": all_concepts[j]["id"],
                        "type": "CONCEPTUAL_SIMILARITY",
                        "relationship_type": "CONCEPTUAL_SIMILARITY",
                        "description": f"Conceptos relacionados: {all_concepts[i]['name']} ↔ {all_concepts[j]['name']}",
                        "confidence": float(similarity),
                        "extraction_method": "semantic_concept_similarity"
                    }))

    async def _create_hierarchical_relationships(self, entities_by_type, relationships):
        """Crea relaciones jerárquicas entre conceptos generales y específicos."""

        # Obtener diferentes tipos de conceptos
        phrases = entities_by_type.get("CONCEPT_PHRASE", [])
        compounds = entities_by_type.get("CONCEPT_COMPOUND", [])
        technical = entities_by_type.get("CONCEPT_TECHNICAL", [])

        # Crear relaciones jerárquicas: técnico -> compuesto -> frase
        hierarchies = [
            (technical, compounds, "SPECIALIZES"),
            (compounds, phrases, "PART_OF"),
            (technical, phrases, "INSTANCE_OF")
        ]

        for source_concepts, target_concepts, rel_type in hierarchies:
            if not source_concepts or not target_concepts:
                continue

            # Crear embeddings
            source_texts = [f"{c['name']}" for c in source_concepts]
            target_texts = [f"{c['name']}" for c in target_concepts]

            if source_texts and target_texts:
                source_embeddings = await self._get_embeddings(source_texts)
                target_embeddings = await self._get_embeddings(target_texts)

                from sklearn.metrics.pairwise import cosine_similarity
                similarities = await asyncio.to_thread(cosine_similarity, source_embeddings, target_embeddings)

                # Umbral más alto para relaciones jerárquicas de calidad
                threshold = 0.60  # REDUCIDO de 0.70 para mayor densidad
                for i, source_concept in enumerate(source_concepts):
                    for j, target_concept in enumerate(target_concepts):
                        similarity = similarities[i][j]

                        if similarity > threshold:
                            relationships.append(self._add_tenant_ids({
                                "id": f"hierarchy_{len(relationships)}",
                                "source_entity_id": source_concept["id"],
                                "target_entity_id": target_concept["id"],
                                "type": rel_type,
                                "relationship_type": rel_type,
                                "description": f"{source_concept['name']} {rel_type.lower().replace('_', ' ')} {target_concept['name']}",
                                "confidence": float(similarity),
                                "extraction_method": "semantic_hierarchy"
                            }))

    def _determine_relationship_type(self, concept, entity, similarity):
        """Determina el tipo de relación más específico basado en los tipos de entidades y palabras clave."""

        concept_type = concept.get("type", "").upper()
        entity_type = entity.get("type", "").upper()
        concept_name = concept.get("name", "").lower()
        entity_name = entity.get("name", "").lower()
        
        # Priorizar etiquetas específicas de GLiNER si están disponibles
        gliner_label = entity.get("gliner_label", "").lower()
        concept_gliner_label = concept.get("gliner_label", "").lower()
        
        # Combinación de nombres para búsqueda de palabras clave
        combined_text = f"{concept_name} {entity_name}"

        # 0. Lógica específica para etiquetas de GLiNER (Muy precisa)
        if gliner_label == "tool" or gliner_label == "software":
            return "USES_TOOL"
        if gliner_label == "problem":
            return "ADDRESSES_PROBLEM"
        if gliner_label == "solution":
            return "PROVIDES_SOLUTION"
        if gliner_label == "skill":
            return "REQUIRES_SKILL"
        if gliner_label == "metric":
            return "MEASURED_BY"

        # 1. Relaciones de PERSONA
        if entity_type in ["PER", "PERSON"]:
            if "CONCEPT_TECHNICAL" in concept_type or any(w in concept_name for w in ["experto", "especialista", "conocimiento", "habilidad"]):
                return "EXPERT_IN"
            elif any(w in concept_name for w in ["trabaja", "empleado", "puesto", "cargo", "director", "gerente"]):
                return "WORKS_AS"
            elif any(w in concept_name for w in ["creó", "desarrolló", "autor", "inventor", "fundador"]):
                return "CREATED_BY"
            elif any(w in concept_name for w in ["vive", "reside", "nació", "ubicado"]):
                return "LIVES_IN"
            elif "CONCEPT_PHRASE" in concept_type:
                return "ASSOCIATED_WITH_PERSON"
            return "RELATED_TO_PERSON"

        # 2. Relaciones de ORGANIZACIÓN
        elif entity_type in ["ORG", "ORGANIZATION"]:
            if any(w in concept_name for w in ["sede", "oficina", "ubicación"]):
                return "HEADQUARTERED_IN"
            elif any(w in concept_name for w in ["producto", "servicio", "ofrece", "vende"]):
                return "PROVIDES"
            elif any(w in concept_name for w in ["miembro", "socio", "afiliado", "pertenece"]):
                return "MEMBER_OF"
            elif "CONCEPT_TECHNICAL" in concept_type:
                return "USES_TECHNOLOGY"
            return "ASSOCIATED_WITH_ORG"

        # 3. Relaciones de UBICACIÓN / GEOPOLÍTICA
        elif entity_type in ["LOC", "LOCATION", "GPE"]:
            if any(w in concept_name for w in ["capital", "ciudad", "región"]):
                return "IS_CITY_OF"
            elif any(w in concept_name for w in ["clima", "geografía", "terreno"]):
                return "GEOGRAPHY_OF"
            return "LOCATED_IN"

        # 4. Relaciones TÉCNICAS / CONCEPTUALES (NUEVO)
        elif "CONCEPT" in concept_type and "CONCEPT" in entity_type:
            if any(w in combined_text for w in ["causa", "genera", "produce", "provoca"]):
                return "CAUSES"
            elif any(w in combined_text for w in ["influye", "afecta", "impacta"]):
                return "INFLUENCES"
            elif any(w in combined_text for w in ["requiere", "necesita", "depende"]):
                return "DEPENDS_ON"
            elif any(w in combined_text for w in ["ejemplo", "instancia", "como"]):
                return "INSTANCE_OF"
            elif any(w in combined_text for w in ["parte", "componente", "segmento"]):
                return "PART_OF"
            elif any(w in combined_text for w in ["mejora", "optimiza", "potencia"]):
                return "ENHANCES"
            return "CONCEPTUAL_LINK"

        # 5. Relaciones de PRODUCTO / EVENTO
        elif entity_type in ["PRODUCT", "EVENT"]:
            if entity_type == "EVENT":
                return "OCCURS_DURING"
            return "RELATED_TO_PRODUCT"

        # 6. Fallback genérico con detección de dirección
        if any(w in concept_name for w in ["parte de", "pertenece a", "contenido en"]):
            return "PART_OF"
        if any(w in concept_name for w in ["contiene", "incluye", "abarca"]):
            return "CONTAINS"
            
        return "SEMANTIC_ASSOCIATION"
    
    async def _extract_cooccurrence_relationships(self, documents: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extrae relaciones por co-ocurrencia en el texto."""
        relationships = []
        
        logger.info(f"📍 Analizando co-ocurrencia de entidades...")
        
        # Crear mapa de entidades por nombre
        entity_map = {ent['name'].lower(): ent for ent in entities}
        
        for doc in documents:
            content = doc.get('content', '').lower()
            if not content:
                continue
            
            # Encontrar entidades que aparecen en el mismo documento
            found_entities = []
            for entity_name, entity in entity_map.items():
                if entity_name in content:
                    found_entities.append(entity)
            
            # Crear relaciones de co-ocurrencia
            for i in range(len(found_entities)):
                for j in range(i + 1, len(found_entities)):
                    # Verificar si aparecen cerca en el texto (ventana de 200 caracteres)
                    entity1_pos = content.find(found_entities[i]['name'].lower())
                    entity2_pos = content.find(found_entities[j]['name'].lower())
                    
                    if abs(entity1_pos - entity2_pos) < 200:  # Aparecen cerca
                        relationships.append(self._add_tenant_ids({
                            "id": f"cooc_{len(relationships)}",
                            "source_entity_id": found_entities[i]["id"],
                            "target_entity_id": found_entities[j]["id"],
                            "type": "CO_OCCURRENCE",
                            "relationship_type": "CO_OCCURRENCE",
                            "description": f"Co-ocurrencia en documento: {doc.get('title', 'documento')}",
                            "confidence": 0.8,
                            "extraction_method": "cooccurrence_analysis",
                            "source_document": doc.get('title', 'documento')
                        }))
        
        return relationships

    async def _extract_cooccurrence_relationships_light(self, documents: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Versión ligera del análisis de co-ocurrencia.
        Solo analiza las entidades más importantes en pocos documentos.
        """
        relationships = []

        logger.info(f"🔗 Análisis ligero de co-ocurrencia: {len(documents)} docs, {len(entities)} entidades")

        # Crear mapa de entidades por nombre (solo las primeras)
        entity_map = {ent['name'].lower(): ent for ent in entities[:100]}  # Solo primeras 100

        # Procesar solo algunos documentos
        for i, doc in enumerate(documents[:10]):  # Solo primeros 10 documentos
            content = doc.get('content', '').lower()
            if not content:
                continue

            # Encontrar entidades que aparecen en el documento
            found_entities = []
            for entity_name, entity in entity_map.items():
                if entity_name in content:
                    found_entities.append(entity)

            # Crear relaciones simples (sin verificar proximidad)
            for j in range(len(found_entities)):
                for k in range(j + 1, len(found_entities)):
                    if len(relationships) >= 100:  # Límite de relaciones
                        break

                    relationships.append(self._add_tenant_ids({
                        "id": f"light_cooc_{len(relationships)}",
                        "source_entity_id": found_entities[j]["id"],
                        "target_entity_id": found_entities[k]["id"],
                        "type": "CO_OCCURRENCE_LIGHT",
                        "relationship_type": "CO_OCCURRENCE_LIGHT",
                        "description": f"Co-ocurrencia ligera en {doc.get('title', 'documento')}",
                        "confidence": 0.6,
                        "extraction_method": "cooccurrence_light",
                        "source_document": doc.get('title', 'documento')
                    }))

                if len(relationships) >= 100:
                    break

            if len(relationships) >= 100:
                break

        logger.info(f"✅ Co-ocurrencia ligera: {len(relationships)} relaciones creadas")
        return relationships

    async def _extract_cooccurrence_relationships_optimized(self, documents: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Análisis optimizado de co-ocurrencia que es más liviano pero completo.

        Optimizaciones:
        1. Filtrar entidades por relevancia (confianza > 0.8)
        2. Usar ventanas deslizantes en lugar de documentos completos
        3. Procesar en lotes con pausas
        4. Límites inteligentes por tipo de entidad
        """
        relationships = []

        logger.info(f"🔗 Iniciando co-ocurrencia optimizada: {len(documents)} docs, {len(entities)} entidades")

        # 1. Filtrar entidades por relevancia
        high_confidence_entities = [
            ent for ent in entities
            if ent.get("confidence", 0) > 0.8 and len(ent.get("name", "")) > 2
        ]

        # 2. Priorizar tipos importantes
        priority_types = ["PERSON", "ORG", "LOC", "CONCEPT"]
        priority_entities = [
            ent for ent in high_confidence_entities
            if ent.get("type") in priority_types
        ]

        # 3. Combinar entidades prioritarias + algunas otras
        selected_entities = priority_entities[:800]  # Máximo 800 entidades prioritarias
        if len(selected_entities) < 500:
            # Agregar más entidades si hay pocas prioritarias
            other_entities = [
                ent for ent in high_confidence_entities
                if ent not in selected_entities
            ]
            selected_entities.extend(other_entities[:500 - len(selected_entities)])

        logger.info(f"📊 Entidades seleccionadas para co-ocurrencia: {len(selected_entities)}")
        logger.info(f"   - Prioritarias: {len(priority_entities)}")
        logger.info(f"   - Total procesadas: {len(selected_entities)}")

        # 4. Crear mapeo eficiente de entidades
        entity_map = {}
        entity_names_lower = []
        for entity in selected_entities:
            name_lower = entity["name"].lower()
            entity_map[name_lower] = entity
            entity_names_lower.append(name_lower)

        # 5. Procesar documentos con ventanas deslizantes
        total_docs = min(len(documents), 50)  # Máximo 50 documentos

        for doc_idx, doc in enumerate(documents[:total_docs]):
            if doc_idx % 10 == 0:
                logger.info(f"📄 Procesando documento {doc_idx + 1}/{total_docs}")

            content = doc.get("content", "").lower()
            if not content or len(content) < 100:
                continue

            # 6. Usar ventanas deslizantes en lugar de documento completo
            window_size = 1000  # Ventana de 1000 caracteres
            overlap = 200       # Solapamiento de 200 caracteres

            for start in range(0, len(content), window_size - overlap):
                await asyncio.sleep(0) # Ceder control en cada ventana
                window = content[start:start + window_size]

                # Encontrar entidades en esta ventana
                window_entities = []
                for name_lower in entity_names_lower:
                    if name_lower in window:
                        window_entities.append(entity_map[name_lower])

                # Crear relaciones solo dentro de esta ventana
                for i, entity1 in enumerate(window_entities):
                    for entity2 in window_entities[i + 1:]:
                        # Verificar proximidad real en la ventana
                        pos1 = window.find(entity1["name"].lower())
                        pos2 = window.find(entity2["name"].lower())

                        if pos1 != -1 and pos2 != -1 and abs(pos1 - pos2) < 300:
                            # Calcular confianza basada en proximidad
                            distance = abs(pos1 - pos2)
                            confidence = max(0.5, 1.0 - (distance / 300))

                            relationships.append(self._add_tenant_ids({
                                "id": f"opt_cooc_{len(relationships)}",
                                "source_entity_id": entity1["id"],
                                "target_entity_id": entity2["id"],
                                "type": "CO_OCCURRENCE_OPT",
                                "relationship_type": "CO_OCCURRENCE_OPT",
                                "description": f"Co-ocurrencia optimizada (distancia: {distance} chars)",
                                "confidence": round(confidence, 2),
                                "extraction_method": "cooccurrence_optimized",
                                "source_document": doc.get("title", f"doc_{doc_idx}"),
                                "window_position": start
                            }))

                # Límite de relaciones por documento
                if len(relationships) >= 2000:
                    logger.info(f"⚠️ Límite de relaciones alcanzado: {len(relationships)}")
                    break

            # Pausa pequeña cada 10 documentos para no sobrecargar
            if doc_idx % 10 == 9:
                await asyncio.sleep(0.1)

            # Límite global de relaciones
            if len(relationships) >= 2000:
                break

        logger.info(f"✅ Co-ocurrencia optimizada completada: {len(relationships)} relaciones")
        return relationships

    async def _enrich_relationships_with_llm(self, documents: List[Dict[str, Any]], candidate_rels: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enriquece las relaciones candidatas usando un LLM para determinar el tipo y descripción exactos.
        
        Args:
            documents: Lista de documentos originales para extraer contexto
            candidate_rels: Relaciones potenciales (ej. por co-ocurrencia)
            entities: Lista de todas las entidades para obtener metadatos
            
        Returns:
            Lista de relaciones enriquecidas y validadas por el LLM
        """
        if not candidate_rels:
            return []
            
        llm_to_use = self.fast_llm or self.llm
        enriched_relationships = []
        
        # Crear mapa de entidades para acceso rápido
        entity_map = {ent["id"]: ent for ent in entities}
        
        # Agrupar candidatos por documento para optimizar contexto
        rels_by_doc = {}
        for rel in candidate_rels:
            doc_title = rel.get("source_document")
            if doc_title not in rels_by_doc:
                rels_by_doc[doc_title] = []
            rels_by_doc[doc_title].append(rel)
            
        # Mapa de contenido de documentos
        doc_content_map = {doc.get("title"): doc.get("content", "") for doc in documents}
        
        # Procesar por lotes de documentos
        for doc_title, rels in rels_by_doc.items():
            content = doc_content_map.get(doc_title, "")
            if not content:
                continue
                
            # Limitar a las top 15 relaciones por documento para no saturar el prompt
            # Priorizar por confianza si está disponible
            sorted_rels = sorted(rels, key=lambda x: x.get("confidence", 0), reverse=True)[:15]
            
            # Procesar en sub-lotes de 5 pares de entidades para máxima precisión
            batch_size = 5
            for i in range(0, len(sorted_rels), batch_size):
                batch = sorted_rels[i:i + batch_size]
                
                # Preparar el prompt para el lote
                pairs_info = []
                for rel in batch:
                    ent_a = entity_map.get(rel["source_entity_id"])
                    ent_b = entity_map.get(rel["target_entity_id"])
                    if ent_a and ent_b:
                        pairs_info.append({
                            "id": rel["id"],
                            "a": ent_a["name"],
                            "a_type": ent_a["type"],
                            "b": ent_b["name"],
                            "b_type": ent_b["type"]
                        })
                
                if not pairs_info:
                    continue
                
                # Intentar extraer un fragmento de texto relevante (ventana alrededor de las entidades)
                # Para simplificar, tomamos los primeros 3000 caracteres del documento si es largo
                context_snippet = content[:3000] 
                
                from knowledge_graph.prompts_graph import RELATIONSHIP_EXTRACTION_PROMPT

                prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
                    context=context_snippet,
                    pairs_info=json.dumps(pairs_info, indent=2, ensure_ascii=False)
                )

                try:
                    logger.info(f"🧠 Consultando LLM para {len(pairs_info)} relaciones en '{doc_title}'")
                    response = await llm_to_use.ainvoke(prompt)
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    
                    # Limpiar respuesta si es necesario (quitar markdown blocks)
                    if "```json" in response_text:
                        response_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in response_text:
                        response_text = response_text.split("```")[1].split("```")[0].strip()
                    
                    data = json.loads(response_text)
                    llm_rels = data.get("relationships", [])
                    
                    for llm_rel in llm_rels:
                        # Buscar la relación original en el batch usando el 'id'
                        orig_rel = next((r for r in batch if r["id"] == llm_rel["id"]), None)
                        
                        if orig_rel:
                            ent_a = entity_map.get(orig_rel["source_entity_id"])
                            ent_b = entity_map.get(orig_rel["target_entity_id"])
                            
                            # Asegurarse de que el tipo no sea "NO_RELATION"
                            if llm_rel.get("type") == "NO_RELATION":
                                logger.debug(f"ℹ️ LLM no encontró relación para {ent_a['name']} y {ent_b['name']}")
                                continue

                            direction = llm_rel.get("direction", "a->b")
                            source_id = orig_rel["source_entity_id"] if direction == "a->b" else orig_rel["target_entity_id"]
                            target_id = orig_rel["target_entity_id"] if direction == "a->b" else orig_rel["source_entity_id"]
                            
                            enriched_rel = self._add_tenant_ids({
                                "id": f"llm_rel_{len(enriched_relationships)}",
                                "source_entity_id": source_id,
                                "target_entity_id": target_id,
                                "type": llm_rel.get("type", "RELATED_TO"),
                                "relationship_type": llm_rel.get("type", "RELATED_TO"),
                                "description": llm_rel.get("description", ""),
                                "confidence": float(llm_rel.get("confidence", 0.7)),
                                "extraction_method": "llm_enriched_cooccurrence",
                                "source_document": doc_title
                            })
                            enriched_relationships.append(enriched_rel)
                        else:
                            logger.warning(f"⚠️ Relación del LLM con ID {llm_rel.get('id')} no encontrada en el batch original. Ignorando.")
                            
                except Exception as e:
                    logger.error(f"❌ Error enriqueciendo relaciones con LLM: {e}")
                    continue
                    
        return enriched_relationships

    async def _extract_semantic_concepts(self, spacy_doc, doc, doc_index, entities, entity_set):
        """
        Extrae conceptos semánticos más ricos que simples palabras.

        Incluye:
        1. Frases nominales (noun phrases) - MEJORADO
        2. Conceptos compuestos - MEJORADO
        3. Términos técnicos - MEJORADO
        4. Expresiones clave - MEJORADO
        """
        
        # Palabras vacías adicionales para conceptos
        stop_words_extended = {
            'cosa', 'cosas', 'parte', 'manera', 'forma', 'tipo', 'ejemplo', 'caso',
            'thing', 'things', 'part', 'way', 'type', 'example', 'case',
            'este', 'esta', 'esto', 'ese', 'esa', 'eso', 'aquel', 'aquella', 'aquello'
        }

        # 1. Extraer frases nominales (noun phrases) - CON VALIDACIÓN MEJORADA
        for chunk in spacy_doc.noun_chunks:
            chunk_text = chunk.text.strip()
            chunk_lower = chunk_text.lower()
            
            # Validaciones RELAJADAS para mayor cobertura
            if (len(chunk_text) < 5 or  # Reducido de 8 a 5 caracteres para frases nominales
                len(chunk_text) > 100 or  # Máximo 100
                chunk.root.is_stop or  # Raíz no debe ser stop word
                chunk.root.pos_ not in ["NOUN", "PROPN"] or  # Solo sustantivos
                chunk_lower in stop_words_extended or  # No palabras vacías
                chunk_text.count(' ') > 5):  # Máximo 6 palabras (aumentado de 5)
                continue
            
            # Validar que tenga contenido semántico real
            words = chunk_text.split()
            content_words = [w for w in words if len(w) > 2 and w.lower() not in stop_words_extended]
            if len(content_words) < 2:  # Debe tener al menos 2 palabras con contenido
                continue

            concept_key = f"{chunk_lower}_noun_phrase"
            if concept_key not in entity_set:
                entity_set.add(concept_key)
                
                # Calcular confianza basada en complejidad
                confidence = 0.75 + (min(len(content_words), 3) * 0.05)
                
                entities.append(self._add_tenant_ids({
                    "id": f"concept_np_{len(entities)}",
                    "name": chunk_text,
                    "type": "CONCEPT_PHRASE",
                    "description": f"Frase nominal: {chunk_text}",
                    "source_document": doc.get('title', f'doc_{doc_index}'),
                    "confidence": round(confidence, 2),
                    "extraction_method": "spacy_noun_phrases"
                }))

        # 2. Extraer conceptos compuestos (adjetivo + sustantivo) - MEJORADO
        for i, token in enumerate(spacy_doc[:-1]):
            next_token = spacy_doc[i + 1]

            # Buscar patrones: adjetivo + sustantivo
            if (token.pos_ == "ADJ" and
                next_token.pos_ in ["NOUN", "PROPN"] and
                not token.is_stop and not next_token.is_stop and
                len(token.text) > 3 and len(next_token.text) > 3):  # Palabras más largas

                compound_concept = f"{token.text} {next_token.text}"
                compound_lower = compound_concept.lower()
                
                # Validar que no sea genérico
                if compound_lower in stop_words_extended:
                    continue
                
                concept_key = f"{compound_lower}_compound"

                if (concept_key not in entity_set and
                    len(compound_concept) > 5 and  # Reducido de 8 a 5 caracteres
                    len(compound_concept) < 50):

                    entity_set.add(concept_key)
                    entities.append(self._add_tenant_ids({
                        "id": f"concept_comp_{len(entities)}",
                        "name": compound_concept.strip(),
                        "type": "CONCEPT_COMPOUND",
                        "description": f"Concepto compuesto: {compound_concept}",
                        "source_document": doc.get('title', f'doc_{doc_index}'),
                        "confidence": 0.8,  # Mayor confianza para compuestos validados
                        "extraction_method": "spacy_compounds"
                    }))

        # 3. Extraer términos técnicos (sustantivos con alta frecuencia) - UMBRAL MÁS ALTO
        noun_freq = {}
        for token in spacy_doc:
            if (token.pos_ in ["NOUN", "PROPN"] and
                len(token.lemma_) > 4 and  # Mínimo 5 caracteres
                not token.is_stop and
                token.is_alpha and
                token.lemma_.lower() not in stop_words_extended):

                lemma = token.lemma_.lower()
                noun_freq[lemma] = noun_freq.get(lemma, 0) + 1

        # Agregar solo sustantivos con frecuencia significativa
        for lemma, freq in noun_freq.items():
            if freq >= 3:  # Aumentar umbral a 3 apariciones
                concept_key = f"{lemma}_technical"
                if concept_key not in entity_set:
                    entity_set.add(concept_key)
                    
                    # Confianza más alta para términos muy frecuentes
                    confidence = min(0.95, 0.7 + (freq * 0.08))
                    
                    entities.append(self._add_tenant_ids({
                        "id": f"concept_tech_{len(entities)}",
                        "name": lemma.title(),
                        "type": "CONCEPT_TECHNICAL",
                        "description": f"Término técnico (freq: {freq}): {lemma}",
                        "source_document": doc.get('title', f'doc_{doc_index}'),
                        "confidence": round(confidence, 2),
                        "extraction_method": "spacy_technical_terms",
                        "frequency": freq  # Agregar metadato de frecuencia
                    }))

        # 4. Extraer expresiones clave usando dependencias sintácticas - MEJORADO
        for token in spacy_doc:
            # Buscar patrones de dependencia interesantes
            if (token.dep_ in ["nsubj", "dobj", "pobj"] and 
                token.head.pos_ == "VERB" and
                len(token.text) > 4 and  # Palabras más largas
                len(token.head.text) > 3 and  # Verbo significativo
                not token.is_stop and
                not token.head.is_stop and
                token.pos_ in ["NOUN", "PROPN"]):

                expression = f"{token.text} {token.head.text}"
                expression_lower = expression.lower()
                
                # Validar que no sea construcción genérica
                if any(sw in expression_lower for sw in stop_words_extended):
                    continue
                
                concept_key = f"{expression_lower}_expression"

                if (concept_key not in entity_set and
                    len(expression) > 6 and  # Reducido de 10 a 6 caracteres
                    len(expression) < 60):

                    entity_set.add(concept_key)
                    
                    # Confianza basada en el tipo de dependencia
                    confidence = 0.75 if token.dep_ == "nsubj" else 0.7
                    
                    entities.append(self._add_tenant_ids({
                        "id": f"concept_expr_{len(entities)}",
                        "name": expression.strip(),
                        "type": "CONCEPT_EXPRESSION",
                        "description": f"Expresión clave: {expression} (relación: {token.dep_})",
                        "source_document": doc.get('title', f'doc_{doc_index}'),
                        "confidence": confidence,
                        "extraction_method": "spacy_expressions",
                        "dependency": token.dep_  # Agregar metadato de dependencia
                    }))

        logger.debug(f"✅ Conceptos semánticos extraídos del documento {doc_index + 1}")
