"""
Procesador de Grafo Antropológico (AnthropologicalGraphProcessor)

Especializado en codificación cualitativa etnográfica y antropológica.
Realiza extracción exhaustiva de citas (abarcando casi la totalidad del texto),
asigna cada cita a un Código que la representa (relación 1:N: 1 Código agrupa Múltiples Citas),
y agrupa posteriormente los códigos en Categorías analíticas superiores bajo el marco teórico,
pregunta de investigación e hipótesis.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import hashlib

from core.config import settings
from core.utils.llm_utils import (
    invoke_structured_output,
    prune_messages_to_fit_token_limit,
)
from core.llm_manager import get_llm_for_user
from langchain_core.messages import HumanMessage, SystemMessage
from knowledge_graph.anthropological_schemas import (
    AnthropologicalQuoteItem,
    AnthropologicalExhaustiveExtractionOutput,
    CategoryGroupingItem,
    AnthropologicalGroupingOutput,
    AnthropologicalCodeConsolidationOutput,
)

logger = logging.getLogger(__name__)


class AnthropologicalGraphProcessor:
    """
    Procesador de Grafo de Conocimiento enfocado en Investigación Antropológica y Cualitativa.

    Principios Etnográficos:
    1. Cobertura Exhaustiva: Procesa progresivamente la totalidad de las transcripciones/documentos.
    2. Codificación 1:N: Cada cita pertenece a un único Código, pero un Código atómico actúa como contenedor de MÚLTIPLES citas (1:N).
    3. Agrupación Jerárquica: Los códigos se estructuran en Categorías analíticas superiores.
    4. Guía Hermenéutica: El Marco Teórico, la Pregunta de Investigación y la Hipótesis guían la interpretación.
    """

    def __init__(self, llm=None, sentence_transformer=None, **kwargs):
        self.llm = llm
        self.embedding_model = sentence_transformer
        self.initialized = False
        self.llm_cache = {}
        self.fast_llm = kwargs.get("fast_llm")
        self.neo4j_adapter = kwargs.get("neo4j_adapter")
        self.progress_tracker = kwargs.get("progress_tracker")
        self.workspace_name = kwargs.get("workspace_name")
        logger.info(f"📜 AnthropologicalGraphProcessor inicializado (workspace: {self.workspace_name})")

    async def initialize(self):
        """Inicializa los modelos necesarios."""
        if self.initialized:
            return

        logger.info("🚀 Inicializando procesador de grafo antropológico...")
        try:
            if not self.embedding_model:
                try:
                    from utils.embeddings import get_embedding_model
                    self.embedding_model = get_embedding_model()
                except Exception as e:
                    logger.warning(f"⚠️ Modelo de embeddings opcional no inicializado: {e}")
            
            self.initialized = True
            logger.info("✅ AnthropologicalGraphProcessor listo")
        except Exception as e:
            logger.error(f"❌ Error inicializando procesador antropológico: {e}")
            raise

    async def process_documents_anthropologically(
        self,
        documents: List[Dict[str, Any]],
        theoretical_framework: str,
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
        dataset_name: str = "anthropological_study",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Procesa exhaustivamente un corpus de documentos/transcripciones según la metodología antropológica.

        Args:
            documents: Lista de documentos con {'content': str, 'title': str}
            theoretical_framework: Texto o extractos del marco teórico que guiarán la codificación
            research_question: (Opcional) Pregunta de investigación
            hypothesis: (Opcional) Hipótesis de investigación
            dataset_name: Nombre del conjunto de datos

        Returns:
            Dict con citas, códigos atómicos (1:N), categorías y relaciones jerárquicas del grafo.
        """
        if not self.initialized:
            await self.initialize()

        self.current_account_id = kwargs.get("account_id")
        await self._ensure_user_llms()

        logger.info(f"📜 Iniciando procesamiento antropológico de {len(documents)} documentos")
        logger.info(f"   Marco teórico provisto: {len(theoretical_framework)} caracteres")

        try:
            # Fase 1: Extracción Exhaustiva y Codificación Atómica (1:N)
            quotes, code_nodes = await self._extract_and_code_exhaustively(
                documents=documents,
                theoretical_framework=theoretical_framework,
                research_question=research_question,
                hypothesis=hypothesis,
            )
            logger.info(f"✅ Fase 1 completada: {len(quotes)} citas extraídas agrupadas en {len(code_nodes)} códigos únicos (relación 1:N).")

            # Fase 2: Agrupación de Códigos en Categorías Analíticas
            categories, category_relationships = await self._group_codes_into_categories(
                code_nodes=code_nodes,
                theoretical_framework=theoretical_framework,
                research_question=research_question,
                hypothesis=hypothesis,
            )
            logger.info(f"✅ Fase 2 completada: {len(categories)} categorías superiores generadas.")

            # Construir relaciones jerárquicas estrictas: Cita -> Código (1:N) y Código -> Categoría (1:N)
            relationships = []

            # 1. Relaciones Cita -> Código (Cada cita pertenece a 1 Código)
            for quote in quotes:
                relationships.append({
                    "id": f"rel_quote_code_{quote['id']}",
                    "source_id": quote["id"],
                    "target_id": quote["code_id"],
                    "type": "BELONGS_TO_CODE",
                    "description": f"La cita pertenece al código atómico '{quote['code']}'",
                    "explanation": quote.get("code_explanation", ""),
                })

            # 2. Relaciones Código -> Categoría (Cada código pertenece a 1 Categoría)
            relationships.extend(category_relationships)

            result = {
                "quotes": quotes,
                "codes": list(code_nodes.values()),
                "categories": categories,
                "relationships": relationships,
                "metadata": {
                    "dataset_name": dataset_name,
                    "processed_with": "anthropological_graph_processor",
                    "processing_time": datetime.now().isoformat(),
                    "documents_count": len(documents),
                    "quotes_count": len(quotes),
                    "codes_count": len(code_nodes),
                    "categories_count": len(categories),
                    "cardinality": "1:N (Código contenedor de múltiples Citas)",
                    "has_research_question": bool(research_question),
                    "has_hypothesis": bool(hypothesis),
                }
            }

            logger.info("🎉 Procesamiento antropológico exhaustivo completado exitosamente.")
            return result

        except Exception as e:
            logger.error(f"❌ Error durante el procesamiento antropológico: {e}", exc_info=True)
            raise

    async def _ensure_user_llms(self):
        """Asigna el LLM principal (main LLM) del usuario o sistema para el análisis cualitativo."""
        account_id = getattr(self, "current_account_id", None)
        if account_id:
            try:
                user_main_llm = await get_llm_for_user(account_id, purpose="main")
                if user_main_llm:
                    self.llm = user_main_llm
            except Exception as e:
                logger.warning(f"⚠️ No se pudo cargar LLM personalizado para account_id={account_id}: {e}")

        if not self.llm:
            from core.llm_manager import get_main_llm
            self.llm = get_main_llm()

    async def _extract_and_code_exhaustively(
        self,
        documents: List[Dict[str, Any]],
        theoretical_framework: str,
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Segmenta el corpus de forma exhaustiva y clasifica las citas en Códigos atómicos contenedores (1:N) en PARALELO.
        """
        all_quotes = []
        code_nodes: Dict[str, Dict[str, Any]] = {}

        system_prompt = self._build_coding_system_prompt(theoretical_framework, research_question, hypothesis)

        # Preparar todos los bloques (chunks) de todos los documentos para procesamiento SECUENCIAL
        # (secuencial para permitir reutilización de códigos ya creados en chunks anteriores)
        chunk_items = []
        for doc_idx, doc in enumerate(documents):
            content = doc.get("content", "")
            title = doc.get("title", f"Documento_{doc_idx + 1}")
            if not content.strip():
                continue
            chunks = self._chunk_text_exhaustively(content, chunk_size=2000)
            doc_id = f"doc_{hashlib.md5(title.encode('utf-8')).hexdigest()[:12]}"
            for chunk_idx, chunk in enumerate(chunks):
                chunk_items.append({
                    "title": title,
                    "doc_id": doc_id,
                    "chunk_idx": chunk_idx,
                    "total_chunks": len(chunks),
                    "chunk": chunk,
                })

        logger.info(f"⚡ Procesando {len(chunk_items)} bloques SECUENCIALMENTE con catálogo de códigos compartido...")

        semaphore = asyncio.Semaphore(4)

        async def _process_chunk(item: Dict[str, Any], existing_code_catalog: List[str]):
            async with semaphore:
                # Incluir catálogo de códigos ya existentes para forzar reutilización
                catalog_section = ""
                if existing_code_catalog:
                    catalog_str = "\n".join(f"  - {c}" for c in existing_code_catalog[:80])
                    catalog_section = f"""

CATÁLOGO DE CÓDIGOS YA EXISTENTES (reutiliza estos nombres EXACTOS cuando corresponda):
{catalog_str}

IMPORTANTE: Si la cita que vas a extraer encaja en alguno de los códigos de este catálogo, 
USA ESE NOMBRE EXACTO. Solo crea un código nuevo si el fenómeno que describes no está cubierto por ningún código existente.
"""

                prompt = f"""{system_prompt}{catalog_section}

Analiza exhaustivamente el siguiente fragmento del documento '{item['title']}' (Bloque {item['chunk_idx'] + 1}/{item['total_chunks']}):

---
{item['chunk']}
---

INSTRUCCIONES DE CODIFICACIÓN (1:N — UN CÓDIGO AGRUPA MÚLTIPLES CITAS):
1. Extrae los pasajes significativos como citas textuales.
2. Asigna cada cita al Código más adecuado. PRIORIZA reutilizar un código del catálogo existente antes de crear uno nuevo.
3. Un mismo código debe agrupar múltiples citas que expresen el mismo fenómeno. Evita crear un código exclusivo por cada cita.
4. Los códigos nuevos deben ser concisos, en MAYÚSCULAS, y expresar un concepto analítico claro (no una descripción literal de la cita).
5. Proporciona una justificación de la asignación del código a la luz del marco teórico."""

                try:
                    target_llm = self.llm
                    if not target_llm:
                        from core.llm_manager import get_main_llm
                        target_llm = get_main_llm()
                        self.llm = target_llm

                    result: AnthropologicalExhaustiveExtractionOutput = await invoke_structured_output(
                        target_llm,
                        AnthropologicalExhaustiveExtractionOutput,
                        prompt,
                    )
                    return result, item
                except Exception as e:
                    logger.error(f"❌ Error codificando bloque {item['chunk_idx'] + 1} de '{item['title']}': {e}")
                    return None, item

        # Procesar en lotes pequeños secuencialmente para compartir catálogo de códigos
        BATCH_SIZE = 4
        all_results = []
        for batch_start in range(0, len(chunk_items), BATCH_SIZE):
            batch = chunk_items[batch_start:batch_start + BATCH_SIZE]
            current_catalog = [n["code_name"] for n in code_nodes.values()]
            tasks = [_process_chunk(item, current_catalog) for item in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(batch_results)

            # Acumular códigos del batch para el siguiente lote
            for res in batch_results:
                if isinstance(res, tuple) and res[0] is not None:
                    output, item = res
                    if output and output.quotes:
                        for quote_item in output.quotes:
                            code_name = quote_item.code.strip().upper()
                            code_id = self._generate_id("code", code_name)
                            if code_id not in code_nodes:
                                code_nodes[code_id] = {
                                    "id": code_id,
                                    "code_name": code_name,
                                    "description": quote_item.code_explanation,
                                    "type": "ANTHROPOLOGICAL_CODE",
                                    "quotes_count": 0,
                                }

        results = all_results
        # Resetear code_nodes para reconstruir con conteos correctos
        code_nodes = {}

        for res in results:
            if isinstance(res, tuple) and res[0] is not None:
                output, item = res
                if output and output.quotes:
                    for quote_item in output.quotes:
                        quote_id = self._generate_id("quote", quote_item.text)
                        code_name = quote_item.code.strip().upper()
                        code_id = self._generate_id("code", code_name)

                        if code_id not in code_nodes:
                            code_nodes[code_id] = {
                                "id": code_id,
                                "code_name": code_name,
                                "description": quote_item.code_explanation,
                                "type": "ANTHROPOLOGICAL_CODE",
                                "quotes_count": 0,
                            }
                        code_nodes[code_id]["quotes_count"] += 1

                        quote_dict = {
                            "id": quote_id,
                            "text": quote_item.text,
                            "code": code_name,
                            "code_id": code_id,
                            "code_explanation": quote_item.code_explanation,
                            "analytical_level": quote_item.analytical_level,
                            "relevance": quote_item.relevance,
                            "source_document": item["title"],
                            "source_document_id": item["doc_id"],
                            "chunk_index": item["chunk_idx"],
                            "type": "ANTHROPOLOGICAL_QUOTE",
                        }
                        all_quotes.append(quote_dict)

        # Fase de Consolidación: Depuración de códigos léxicos similares MANTENIENDO GRANULARIDAD FINA (1:N)
        all_quotes, code_nodes = await self._consolidate_codes(
            all_quotes,
            code_nodes,
            theoretical_framework,
            research_question,
            hypothesis,
        )

        return all_quotes, code_nodes

    async def _consolidate_codes(
        self,
        all_quotes: List[Dict[str, Any]],
        code_nodes: Dict[str, Dict[str, Any]],
        theoretical_framework: str,
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Depura códigos preliminares manteniendo la alta granularidad y riqueza cualitativa del análisis etnográfico (1:N).
        Unifica únicamente sinónimos o variantes léxicas directas para no perder matices específicos.
        """
        if len(code_nodes) <= 2:
            return all_quotes, code_nodes

        logger.info(f"🔄 Depurando {len(code_nodes)} códigos preliminares (preservando granularidad fina 1:N)...")

        preliminary_codes_summary = "\n".join([
            f"- CÓDIGO PRELIMINAR: '{c['code_name']}' (Citas actuales: {c['quotes_count']}) - Explicación: {c['description']}"
            for c in code_nodes.values()
        ])

        system_prompt = f"""Eres un metodólogo cualitativo y antropólogo experto en desarrollo de teoría fundamentada.
Tu tarea es depurar los códigos atómicos preliminares MANTENIENDO UNA ALTA GRANULARIDAD Y RIQUEZA CUALITATIVA.

REGLAS DE GRANULARIDAD Y DEPURACIÓN DE CÓDIGOS (1:N):
1. PRESERVAR LA GRANULARIDAD CUALITATIVA: NO sobre-simplifiques ni fusiones códigos que representen matices etnográficos, emic o empíricos distintos. Conserva la especificidad de los conceptos (ej. diferencia "SABERES_BOTÁNICOS_LOCALES" de "TRANSMISIÓN_INTERGENERACIONAL_DE_SABERES").
2. UNIFICAR SOLO DUPLICADOS LÉXICOS / SINÓNIMOS EXACTOS: Solo combina aquellos códigos preliminares que sean prácticamente idénticos en significado o variantes directas de redacción.
3. AGRUPACIÓN 1:N REUTILIZABLE: Mantén un catálogo rico y detallado de códigos específicos que agrupen las citas correspondientes sin perder la finura analítica.
4. MAPEO COMPLETO: Todos los códigos preliminares deben ser asignados a un código canónico (si un código preliminar es único y relevante, permanece tal cual como código canónico individual en `merged_codes`).

Marco Teórico de Referencia:
{theoretical_framework[:2500]}
"""
        if research_question:
            system_prompt += f"\nPregunta de Investigación: {research_question}"

        prompt = f"""{system_prompt}

Códigos preliminares generados durante la lectura del corpus:
{preliminary_codes_summary}

Instrucciones:
1. Revisa la lista de códigos preliminares y unifica ÚNICAMENTE aquellos que sean sinónimos directos o variantes léxicas del mismo concepto específico.
2. Mantén la mayor granularidad posible conservando los matices etnográficos particulares.
3. Devuelve la lista de Códigos Canónicos resultantes (donde `merged_codes` contiene los códigos preliminares que unifica). Si un código preliminar es específico y relevante, mantenlo tal cual como código canónico individual."""

        try:
            target_llm = self.llm
            if not target_llm:
                from core.llm_manager import get_main_llm
                target_llm = get_main_llm()

            result: AnthropologicalCodeConsolidationOutput = await invoke_structured_output(
                target_llm,
                AnthropologicalCodeConsolidationOutput,
                prompt,
            )

            if result and result.consolidated_codes:
                # Mapa de código preliminar -> código canónico
                code_mapping: Dict[str, str] = {}
                canonical_nodes: Dict[str, Dict[str, Any]] = {}

                for item in result.consolidated_codes:
                    canon_name = item.canonical_code.strip().upper()
                    canon_id = self._generate_id("code", canon_name)

                    canonical_nodes[canon_id] = {
                        "id": canon_id,
                        "code_name": canon_name,
                        "description": item.description,
                        "type": "ANTHROPOLOGICAL_CODE",
                        "quotes_count": 0,
                    }

                    for old_code in item.merged_codes:
                        old_clean = old_code.strip().upper()
                        code_mapping[old_clean] = canon_name

                # Reasignar todas las citas al código canónico unificado
                for quote in all_quotes:
                    old_code = quote["code"]
                    canon_code = code_mapping.get(old_code, old_code)
                    canon_id = self._generate_id("code", canon_code)

                    quote["code"] = canon_code
                    quote["code_id"] = canon_id

                    if canon_id not in canonical_nodes:
                        canonical_nodes[canon_id] = {
                            "id": canon_id,
                            "code_name": canon_code,
                            "description": quote.get("code_explanation", ""),
                            "type": "ANTHROPOLOGICAL_CODE",
                            "quotes_count": 0,
                        }
                    canonical_nodes[canon_id]["quotes_count"] += 1

                logger.info(f"✅ Consolidación completada: {len(code_nodes)} códigos preliminares unificados en {len(canonical_nodes)} códigos canónicos.")
                return all_quotes, canonical_nodes

        except Exception as e:
            logger.error(f"⚠️ Error en consolidación de códigos: {e}. Manteniendo códigos preliminares.")

        return all_quotes, code_nodes

    async def _group_codes_into_categories(
        self,
        code_nodes: Dict[str, Dict[str, Any]],
        theoretical_framework: str,
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Agrupa los Códigos atómicos (contenedores de citas) en Categorías analíticas superiores.
        """
        if not code_nodes:
            return [], []

        codes_summary = "\n".join([
            f"- CÓDIGO: '{c['code_name']}' (Citas agrupadas: {c['quotes_count']}) - Explicación: {c['description']}"
            for c in code_nodes.values()
        ])

        system_prompt = f"""Eres un metodólogo cualitativo y antropólogo experto en desarrollo de teoría fundamentada, antropología teórica e investigación etnográfica.
Tu tarea es agrupar un conjunto de códigos atómicos (que contienen múltiples citas) en Categorías analíticas superiores y DESARROLLAR EXHAUSTIVAMENTE LA IDEA CENTRAL DE CADA CATEGORÍA con una alta densidad teórico-analítica.

REGLAS DE DESARROLLO CATEGORIAL Y TEÓRICO-ANALÍTICO DENSO:
1. DESARROLLO TEÓRICO-ANALÍTICO DE LA CATEGORÍA (`category_description`):
   - NO te limites a resumir o listar los códigos. Redacta un desarrollo teórico extenso, riguroso y profundo (estilo perfil de ideas centrales).
   - Articula las dimensiones epistemológicas, estructurales y cualitativas que unifican los códigos de la categoría.
   - Explícita los mecanismos socio-culturales, mediaciones simbólicas, dispositivos de poder o lógicas institucionales observadas en el campo.
   - Analiza las tensiones, ambivalencias o contradicciones entre la perspectiva emic (los sujetos) y la interpretación etic (analítica).

2. ARTICULACIÓN Y DISCUSIÓN TEÓRICA (`theoretical_connection`):
   - Elabora una discusión teórica fundamentada conectando la categoría con los paradigmas, conceptos clave y autores del marco teórico de referencia.
   - Detalla explícitamente de qué manera esta categoría responde o problematiza la Pregunta de Investigación y cómo operacionaliza, matiza o evalúa la Hipótesis de trabajo.

3. PERTENENCIA JERÁRQUICA ESTRICTA (1:N):
   - Cada Código atómico debe pertenecer a EXACTAMENTE UNA Categoría analítica superior. No dupliques un mismo código en múltiples categorías. Todos los códigos deben ser clasificados.

Marco Teórico de Referencia:
{theoretical_framework[:3000]}
"""
        if research_question:
            system_prompt += f"\nPregunta de Investigación: {research_question}"
        if hypothesis:
            system_prompt += f"\nHipótesis de Trabajo: {hypothesis}"

        prompt = f"""{system_prompt}

Revisa los siguientes Códigos Atómicos extraídos del trabajo de campo:

{codes_summary}

Instrucciones:
1. Agrupa cada código atómico en una Categoría analítica superior única (relación 1:N: 1 Categoría agrupa múltiples Códigos).
2. Redacta en `category_description` un desarrollo TEÓRICO-ANALÍTICO RICO, DENSO Y EXTENSO que analice a fondo el fenómeno conceptual, los mecanismos socio-culturales y la significación antropológica.
3. Desarrolla ampliamente en `theoretical_connection` la articulación conceptual con el marco teórico, respondiendo a la pregunta de investigación y evaluando la hipótesis de trabajo."""

        categories = []
        category_relationships = []
        assigned_code_ids = set()

        # Índice de búsqueda por nombre normalizado como fallback al MD5
        # Normalización: upper + strip de espacios y puntuación no significativa
        def _normalize(s: str) -> str:
            return s.strip().upper().replace("-", "_").replace(" ", "_")

        code_by_name: Dict[str, str] = {
            _normalize(v["code_name"]): k
            for k, v in code_nodes.items()
        }

        try:
            target_llm = self.llm
            if not target_llm:
                from core.llm_manager import get_main_llm
                target_llm = get_main_llm()

            result: AnthropologicalGroupingOutput = await invoke_structured_output(
                target_llm,
                AnthropologicalGroupingOutput,
                prompt,
            )

            if result and result.categories:
                for cat_item in result.categories:
                    cat_id = self._generate_id("category", cat_item.category_name)
                    assigned_codes_for_cat = []

                    for code_str in cat_item.codes:
                        code_str_clean = code_str.strip().upper()
                        # 1er intento: match exacto por MD5
                        matching_code_id = self._generate_id("code", code_str_clean)

                        # 2do intento: match por nombre normalizado (fallback)
                        if matching_code_id not in code_nodes:
                            normalized = _normalize(code_str_clean)
                            matching_code_id = code_by_name.get(normalized, "")
                            if matching_code_id:
                                logger.debug(f"🔄 Match fuzzy: '{code_str_clean}' → '{code_nodes[matching_code_id]['code_name']}'")
                            else:
                                logger.warning(f"⚠️  Código no encontrado al agrupar en categoría: '{code_str_clean}'")
                                continue

                        # Enforzar pertenencia única: 1 Código pertenece a 1 Categoría
                        if matching_code_id not in assigned_code_ids:
                            assigned_code_ids.add(matching_code_id)
                            assigned_codes_for_cat.append(code_str_clean)

                            code_nodes[matching_code_id]["category_id"] = cat_id
                            code_nodes[matching_code_id]["category_name"] = cat_item.category_name

                            category_relationships.append({
                                "id": f"rel_code_cat_{matching_code_id}_{cat_id}",
                                "source_id": matching_code_id,
                                "target_id": cat_id,
                                "type": "BELONGS_TO_CATEGORY",
                                "description": f"El código '{code_nodes[matching_code_id]['code_name']}' pertenece a la categoría '{cat_item.category_name}'",
                            })

                    if assigned_codes_for_cat:
                        cat_dict = {
                            "id": cat_id,
                            "category_name": cat_item.category_name,
                            "description": cat_item.category_description,
                            "theoretical_connection": cat_item.theoretical_connection,
                            "codes": assigned_codes_for_cat,
                            "type": "ANTHROPOLOGICAL_CATEGORY",
                        }
                        categories.append(cat_dict)
                        logger.info(f"✅ Categoría '{cat_item.category_name}': {len(assigned_codes_for_cat)} códigos asignados")

            # Garantizar que ningún código quede huérfano de categoría
            unassigned_code_ids = set(code_nodes.keys()) - assigned_code_ids
            if unassigned_code_ids:
                general_cat_id = self._generate_id("category", "CATEGORÍA GENERAL")
                unassigned_names = []
                for u_id in unassigned_code_ids:
                    code_name = code_nodes[u_id]["code_name"]
                    unassigned_names.append(code_name)
                    code_nodes[u_id]["category_id"] = general_cat_id
                    code_nodes[u_id]["category_name"] = "CATEGORÍA GENERAL"
                    category_relationships.append({
                        "id": f"rel_code_cat_{u_id}_{general_cat_id}",
                        "source_id": u_id,
                        "target_id": general_cat_id,
                        "type": "BELONGS_TO_CATEGORY",
                        "description": f"El código '{code_name}' pertenece a la categoría 'CATEGORÍA GENERAL'",
                    })
                categories.append({
                    "id": general_cat_id,
                    "category_name": "CATEGORÍA GENERAL",
                    "description": "Categoría analítica aglutinadora de códigos etnográficos transversales y dimensiones situacionales emergentes que articulan aspectos transversales del trabajo de campo.",
                    "theoretical_connection": "Articulación conceptual emergente del corpus etnográfico en diálogo prospectivo con el marco teórico de referencia.",
                    "codes": unassigned_names,
                    "type": "ANTHROPOLOGICAL_CATEGORY",
                })

        except Exception as e:
            logger.error(f"❌ Error agrupando códigos en categorías: {e}")

        return categories, category_relationships

    def _build_coding_system_prompt(
        self,
        theoretical_framework: str,
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None
    ) -> str:
        prompt = f"""Eres un etnógrafo y analista cualitativo experto. Tu objetivo es realizar una codificación exhaustiva de un corpus textual.

REGLAS DE CODIFICACIÓN ANTROPOLÓGICA:
1. Cobertura Exhaustiva: Debes capturar casi todas las citas relevantes que expresen sentidos emic o analíticos.
2. Relación 1:N ESTRICTA (Código a Citas): Un mismo Código atómico DEBE agrupar MÚLTIPLES citas. Está PROHIBIDO crear un código exclusivo para una sola cita. Si un concepto ya tiene código, REUTILIZA ese código.
3. Economía de Códigos: El número total de códigos debe ser SIGNIFICATIVAMENTE MENOR que el número de citas. Aspira a que cada código tenga al menos 3-5 citas.
4. Lente Teórico: La asignación del código y la justificación deben estar guiadas hermenéuticamente por el Marco Teórico.
5. Nombres de código: Concisos, en MAYÚSCULAS, expresan un concepto analítico (no una descripción literal de la cita).

MARCO TEÓRICO:
{theoretical_framework[:2500]}
"""
        if research_question:
            prompt += f"\nPREGUNTA DE INVESTIGACIÓN: {research_question}"
        if hypothesis:
            prompt += f"\nHIPÓTESIS: {hypothesis}"

        return prompt

    def _chunk_text_exhaustively(self, text: str, chunk_size: int = 2000) -> List[str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = []
        current_len = 0

        for p in paragraphs:
            if current_len + len(p) > chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [p]
                current_len = len(p)
            else:
                current_chunk.append(p)
                current_len += len(p)

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks if chunks else [text]

    def _generate_id(self, prefix: str, text: str) -> str:
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{text_hash}"
