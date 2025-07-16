# knowledge_graph/hybrid_graph_processor.py

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)

class HybridGraphProcessor:
    """
    Procesador híbrido que combina modelos especializados locales con LLMs.
    
    Pipeline:
    1. spaCy: Extracción de entidades básicas (NER)
    2. SentenceTransformers: Embeddings semánticos y relaciones
    3. Co-ocurrencia: Relaciones por proximidad textual
    4. Gemini Flash: Solo para análisis contextual complejo (opcional)
    """
    
    def __init__(self):
        self.spacy_model = None
        self.sentence_transformer = None
        self.initialized = False
        self._save_callback = None
        logger.info("🔧 HybridGraphProcessor inicializado")
    
    async def initialize(self):
        """Inicializa todos los modelos necesarios."""
        if self.initialized:
            return
            
        logger.info("🚀 Inicializando modelos especializados...")
        
        try:
            # Inicializar spaCy
            await self._initialize_spacy()
            
            # Inicializar SentenceTransformers
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
                self.spacy_model = spacy.load(model_name)
                logger.info(f"✅ spaCy modelo español cargado: {model_name}")
            except OSError:
                logger.info(f"📥 Descargando modelo spaCy español: {model_name}")
                download(model_name)
                self.spacy_model = spacy.load(model_name)
                logger.info(f"✅ spaCy modelo español descargado y cargado: {model_name}")

        except Exception as e:
            logger.warning(f"⚠️ Error con spaCy español, intentando inglés como fallback: {e}")
            try:
                import spacy
                model_name = "en_core_web_sm"
                try:
                    self.spacy_model = spacy.load(model_name)
                    logger.info(f"✅ spaCy modelo inglés cargado (fallback): {model_name}")
                except OSError:
                    logger.info(f"📥 Descargando modelo spaCy inglés (fallback): {model_name}")
                    spacy.cli.download(model_name)
                    self.spacy_model = spacy.load(model_name)
                    logger.info(f"✅ spaCy modelo inglés descargado y cargado (fallback): {model_name}")
            except Exception as e2:
                logger.error(f"❌ Error inicializando spaCy: {e2}")
                raise
    
    async def _initialize_sentence_transformers(self):
        """Inicializa SentenceTransformers con modelo pequeño."""
        try:
            from sentence_transformers import SentenceTransformer

            # Usar modelo multilingüe que funciona bien con español
            model_name = "paraphrase-multilingual-MiniLM-L12-v2"  # Soporta español
            logger.info(f"📥 Cargando SentenceTransformer multilingüe: {model_name}")

            # Configurar cache local para evitar re-descargas
            import os
            cache_dir = "/app/.cache/sentence_transformers"
            os.makedirs(cache_dir, exist_ok=True)

            self.sentence_transformer = SentenceTransformer(
                model_name,
                cache_folder=cache_dir,
                device='cpu'  # Forzar CPU para menor uso de memoria
            )
            logger.info(f"✅ SentenceTransformer multilingüe cargado: {model_name}")

        except Exception as e:
            logger.error(f"❌ Error inicializando SentenceTransformers: {e}")
            raise

    def set_save_callback(self, callback):
        """Configura un callback para guardar datos inmediatamente después de Fase 2."""
        self._save_callback = callback
        logger.info("💾 Callback de guardado configurado")
    
    async def process_documents(self, documents: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
        """
        Procesa documentos usando el pipeline híbrido.
        
        Args:
            documents: Lista de documentos con contenido
            dataset_name: Nombre del dataset
            
        Returns:
            Dict con entidades, relaciones y metadatos del grafo
        """
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"🧠 Iniciando procesamiento híbrido de {len(documents)} documentos")
        
        try:
            # Fase 1: Extracción de entidades con spaCy
            entities = await self._extract_entities_spacy(documents)
            logger.info(f"✅ Fase 1 completada: {len(entities)} entidades extraídas")
            
            # Fase 2: Análisis semántico con SentenceTransformers
            relationships = await self._extract_relationships_semantic(documents, entities)
            logger.info(f"✅ Fase 2 completada: {len(relationships)} relaciones semánticas")

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

            # Fase 3: Relaciones por co-ocurrencia (OPTIMIZADA)
            logger.info("⏭️ Fase 3: Saltando co-ocurrencia pesada, usando solo relaciones semánticas")

            # Solo usar relaciones semánticas (ya son muy ricas)
            all_relationships = relationships
            cooccurrence_rels = []  # Inicializar para metadatos

            # Co-ocurrencia optimizada pero más completa
            logger.info("🔗 Ejecutando análisis optimizado de co-ocurrencia...")
            try:
                cooccurrence_rels = await self._extract_cooccurrence_relationships_optimized(
                    documents, entities
                )
                all_relationships.extend(cooccurrence_rels)
                logger.info(f"✅ Fase 3 optimizada completada: {len(cooccurrence_rels)} relaciones adicionales")
            except Exception as e:
                logger.warning(f"⚠️ Error en co-ocurrencia optimizada: {e}")
                logger.info("✅ Continuando solo con relaciones semánticas")
                cooccurrence_rels = []
            
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
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento híbrido: {e}")
            raise
    
    async def _extract_entities_spacy(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extrae entidades usando spaCy."""
        entities = []
        entity_set = set()  # Para evitar duplicados
        
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            if not content:
                continue
                
            logger.debug(f"🔍 Procesando documento {i+1} con spaCy...")
            
            # Procesar con spaCy
            spacy_doc = self.spacy_model(content[:10000])  # Limitar a 10k caracteres
            
            # Extraer entidades nombradas
            for ent in spacy_doc.ents:
                entity_key = f"{ent.text.lower()}_{ent.label_}"
                if entity_key not in entity_set and len(ent.text.strip()) > 2:
                    entity_set.add(entity_key)
                    entities.append({
                        "id": f"entity_{len(entities)}",
                        "name": ent.text.strip(),
                        "type": ent.label_,
                        "description": f"{ent.label_}: {ent.text}",
                        "source_document": doc.get('title', f'doc_{i}'),
                        "confidence": 0.9,  # spaCy es bastante confiable
                        "extraction_method": "spacy_ner"
                    })
            
            # Extraer conceptos semánticos más ricos
            await self._extract_semantic_concepts(spacy_doc, doc, i, entities, entity_set)
        
        return entities
    
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
            concept_embeddings = self.sentence_transformer.encode(concept_texts)
            entity_embeddings = self.sentence_transformer.encode(entity_texts)

            # Calcular similitudes cruzadas
            from sklearn.metrics.pairwise import cosine_similarity
            cross_similarities = cosine_similarity(concept_embeddings, entity_embeddings)

            # Crear relaciones con umbral más alto para mayor calidad
            threshold = 0.7
            for i, concept in enumerate(concepts):
                for j, entity in enumerate(named_entities):
                    similarity = cross_similarities[i][j]

                    if similarity > threshold:
                        # Determinar tipo de relación más específico
                        rel_type = self._determine_relationship_type(concept, entity, similarity)

                        relationships.append({
                            "id": f"concept_rel_{len(relationships)}",
                            "source_entity_id": concept["id"],
                            "target_entity_id": entity["id"],
                            "type": rel_type,  # Usar 'type' en lugar de 'relationship_type'
                            "relationship_type": rel_type,  # Mantener ambos por compatibilidad
                            "description": f"{concept['name']} está relacionado con {entity['name']}",
                            "confidence": float(similarity),
                            "extraction_method": "semantic_concept_entity"
                        })

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
        embeddings = self.sentence_transformer.encode(concept_texts)

        # Calcular similitudes
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(embeddings)

        # Crear relaciones con umbral alto para conceptos de calidad
        threshold = 0.75
        for i in range(len(all_concepts)):
            for j in range(i + 1, len(all_concepts)):
                similarity = similarities[i][j]

                if similarity > threshold:
                    relationships.append({
                        "id": f"concept_sim_{len(relationships)}",
                        "source_entity_id": all_concepts[i]["id"],
                        "target_entity_id": all_concepts[j]["id"],
                        "type": "CONCEPTUAL_SIMILARITY",
                        "relationship_type": "CONCEPTUAL_SIMILARITY",
                        "description": f"Conceptos relacionados: {all_concepts[i]['name']} ↔ {all_concepts[j]['name']}",
                        "confidence": float(similarity),
                        "extraction_method": "semantic_concept_similarity"
                    })

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
                source_embeddings = self.sentence_transformer.encode(source_texts)
                target_embeddings = self.sentence_transformer.encode(target_texts)

                from sklearn.metrics.pairwise import cosine_similarity
                similarities = cosine_similarity(source_embeddings, target_embeddings)

                # Umbral más bajo para relaciones jerárquicas
                threshold = 0.6
                for i, source_concept in enumerate(source_concepts):
                    for j, target_concept in enumerate(target_concepts):
                        similarity = similarities[i][j]

                        if similarity > threshold:
                            relationships.append({
                                "id": f"hierarchy_{len(relationships)}",
                                "source_entity_id": source_concept["id"],
                                "target_entity_id": target_concept["id"],
                                "type": rel_type,
                                "relationship_type": rel_type,
                                "description": f"{source_concept['name']} {rel_type.lower().replace('_', ' ')} {target_concept['name']}",
                                "confidence": float(similarity),
                                "extraction_method": "semantic_hierarchy"
                            })

    def _determine_relationship_type(self, concept, entity, similarity):
        """Determina el tipo de relación más específico basado en los tipos de entidades."""

        concept_type = concept.get("type", "")
        entity_type = entity.get("type", "")

        # Reglas específicas para tipos de relación
        if entity_type == "PER":
            if "CONCEPT_TECHNICAL" in concept_type:
                return "PERSON_EXPERTISE"
            elif "CONCEPT_PHRASE" in concept_type:
                return "PERSON_ASSOCIATED_WITH"
            else:
                return "PERSON_RELATED_TO"

        elif entity_type == "ORG":
            if "CONCEPT_TECHNICAL" in concept_type:
                return "ORG_SPECIALIZES_IN"
            elif "CONCEPT_COMPOUND" in concept_type:
                return "ORG_INVOLVED_IN"
            else:
                return "ORG_RELATED_TO"

        elif entity_type == "LOC":
            return "LOCATION_CONTEXT"

        else:
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
                        relationships.append({
                            "id": f"cooc_{len(relationships)}",
                            "source_entity_id": found_entities[i]["id"],
                            "target_entity_id": found_entities[j]["id"],
                            "type": "CO_OCCURRENCE",
                            "relationship_type": "CO_OCCURRENCE",
                            "description": f"Co-ocurrencia en documento: {doc.get('title', 'documento')}",
                            "confidence": 0.8,
                            "extraction_method": "cooccurrence_analysis",
                            "source_document": doc.get('title', 'documento')
                        })
        
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

                    relationships.append({
                        "id": f"light_cooc_{len(relationships)}",
                        "source_entity_id": found_entities[j]["id"],
                        "target_entity_id": found_entities[k]["id"],
                        "type": "CO_OCCURRENCE_LIGHT",
                        "relationship_type": "CO_OCCURRENCE_LIGHT",
                        "description": f"Co-ocurrencia ligera en {doc.get('title', 'documento')}",
                        "confidence": 0.6,
                        "extraction_method": "cooccurrence_light",
                        "source_document": doc.get('title', 'documento')
                    })

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

                            relationships.append({
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
                            })

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

    async def _extract_semantic_concepts(self, spacy_doc, doc, doc_index, entities, entity_set):
        """
        Extrae conceptos semánticos más ricos que simples palabras.

        Incluye:
        1. Frases nominales (noun phrases)
        2. Conceptos compuestos
        3. Términos técnicos
        4. Expresiones clave
        """

        # 1. Extraer frases nominales (noun phrases)
        for chunk in spacy_doc.noun_chunks:
            # Filtrar frases nominales relevantes
            if (len(chunk.text) > 5 and
                len(chunk.text) < 100 and
                not chunk.root.is_stop and
                chunk.root.pos_ in ["NOUN", "PROPN"]):

                concept_key = f"{chunk.text.lower()}_noun_phrase"
                if concept_key not in entity_set:
                    entity_set.add(concept_key)
                    entities.append({
                        "id": f"concept_np_{len(entities)}",
                        "name": chunk.text.strip(),
                        "type": "CONCEPT_PHRASE",
                        "description": f"Frase nominal: {chunk.text}",
                        "source_document": doc.get('title', f'doc_{doc_index}'),
                        "confidence": 0.8,
                        "extraction_method": "spacy_noun_phrases"
                    })

        # 2. Extraer conceptos compuestos (adjetivo + sustantivo)
        for i, token in enumerate(spacy_doc[:-1]):
            next_token = spacy_doc[i + 1]

            # Buscar patrones: adjetivo + sustantivo
            if (token.pos_ == "ADJ" and
                next_token.pos_ in ["NOUN", "PROPN"] and
                not token.is_stop and not next_token.is_stop):

                compound_concept = f"{token.text} {next_token.text}"
                concept_key = f"{compound_concept.lower()}_compound"

                if (concept_key not in entity_set and
                    len(compound_concept) > 5 and
                    len(compound_concept) < 50):

                    entity_set.add(concept_key)
                    entities.append({
                        "id": f"concept_comp_{len(entities)}",
                        "name": compound_concept.strip(),
                        "type": "CONCEPT_COMPOUND",
                        "description": f"Concepto compuesto: {compound_concept}",
                        "source_document": doc.get('title', f'doc_{doc_index}'),
                        "confidence": 0.75,
                        "extraction_method": "spacy_compounds"
                    })

        # 3. Extraer términos técnicos (sustantivos con alta frecuencia)
        noun_freq = {}
        for token in spacy_doc:
            if (token.pos_ in ["NOUN", "PROPN"] and
                len(token.lemma_) > 3 and
                not token.is_stop and
                token.is_alpha):

                lemma = token.lemma_.lower()
                noun_freq[lemma] = noun_freq.get(lemma, 0) + 1

        # Agregar sustantivos frecuentes como conceptos técnicos
        for lemma, freq in noun_freq.items():
            if freq >= 2:  # Aparece al menos 2 veces
                concept_key = f"{lemma}_technical"
                if concept_key not in entity_set:
                    entity_set.add(concept_key)
                    entities.append({
                        "id": f"concept_tech_{len(entities)}",
                        "name": lemma.title(),
                        "type": "CONCEPT_TECHNICAL",
                        "description": f"Término técnico (freq: {freq}): {lemma}",
                        "source_document": doc.get('title', f'doc_{doc_index}'),
                        "confidence": min(0.9, 0.6 + (freq * 0.1)),  # Confianza basada en frecuencia
                        "extraction_method": "spacy_technical_terms"
                    })

        # 4. Extraer expresiones clave usando dependencias sintácticas
        for token in spacy_doc:
            # Buscar patrones de dependencia interesantes
            if token.dep_ in ["nsubj", "dobj", "pobj"] and token.head.pos_ == "VERB":
                # Sujeto/objeto de verbo importante
                if (len(token.text) > 3 and
                    not token.is_stop and
                    token.pos_ in ["NOUN", "PROPN"]):

                    expression = f"{token.text} {token.head.text}"
                    concept_key = f"{expression.lower()}_expression"

                    if (concept_key not in entity_set and
                        len(expression) > 5 and
                        len(expression) < 60):

                        entity_set.add(concept_key)
                        entities.append({
                            "id": f"concept_expr_{len(entities)}",
                            "name": expression.strip(),
                            "type": "CONCEPT_EXPRESSION",
                            "description": f"Expresión clave: {expression} (relación: {token.dep_})",
                            "source_document": doc.get('title', f'doc_{doc_index}'),
                            "confidence": 0.7,
                            "extraction_method": "spacy_expressions"
                        })

        logger.debug(f"✅ Conceptos semánticos extraídos del documento {doc_index + 1}")
