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

            # Construir relaciones (Código -> Citas [1:N] y Código -> Categoría)
            relationships = []

            # 1. Relaciones Cita -> Código (donde 1 Código agrupa N citas)
            for quote in quotes:
                relationships.append({
                    "id": f"rel_quote_code_{quote['id']}",
                    "source_id": quote["id"],
                    "target_id": quote["code_id"],
                    "type": "EXPRESSES_CODE",
                    "description": f"La cita es agrupada bajo el código atómico '{quote['code']}'",
                    "explanation": quote.get("code_explanation", ""),
                })

            # 2. Relaciones Código -> Categoría
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
        """Asigna el LLM del usuario si se pasa account_id."""
        account_id = getattr(self, "current_account_id", None)
        if not account_id:
            return

        try:
            user_main_llm = await get_llm_for_user(account_id, purpose="main")
            if user_main_llm:
                self.llm = user_main_llm
                self.fast_llm = (await get_llm_for_user(account_id, purpose="fast")) or user_main_llm
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar LLM personalizado para account_id={account_id}: {e}")

    async def _extract_and_code_exhaustively(
        self,
        documents: List[Dict[str, Any]],
        theoretical_framework: str,
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Segmenta el corpus de forma exhaustiva y clasifica las citas en Códigos atómicos contenedores (1:N).
        """
        all_quotes = []
        code_nodes: Dict[str, Dict[str, Any]] = {}

        system_prompt = self._build_coding_system_prompt(theoretical_framework, research_question, hypothesis)

        for doc_idx, doc in enumerate(documents):
            content = doc.get("content", "")
            title = doc.get("title", f"Documento_{doc_idx + 1}")
            if not content.strip():
                continue

            chunks = self._chunk_text_exhaustively(content, chunk_size=2000)
            logger.info(f"📄 Procesando '{title}' ({len(chunks)} bloques exhaustivos)...")

            for chunk_idx, chunk in enumerate(chunks):
                prompt = f"""{system_prompt}

Analiza exhaustivamente el siguiente fragmento del documento '{title}' (Bloque {chunk_idx + 1}/{len(chunks)}):

---
{chunk}
---

Instrucciones:
1. Extrae casi la totalidad de pasajes y oraciones significativas como citas.
2. Asigna cada cita al Código atómico y conciso que mejor la represente.
3. Recuerda que los Códigos actúan como contenedores (relación 1:N): reutiliza un mismo Código existente si la cita comparte el mismo aspecto analítico relevante, o crea un nuevo Código atómico si trata un aspecto distinto.
4. Proporciona una breve justificación de la asignación del código a la luz del marco teórico."""

                try:
                    target_llm = self.llm or self.fast_llm
                    if not target_llm:
                        raise RuntimeError("LLM no está disponible en AnthropologicalGraphProcessor")

                    result: AnthropologicalExhaustiveExtractionOutput = await invoke_structured_output(
                        target_llm,
                        AnthropologicalExhaustiveExtractionOutput,
                        prompt,
                    )

                    if result and result.quotes:
                        for item in result.quotes:
                            quote_id = self._generate_id("quote", item.text)
                            code_name = item.code.strip().upper()
                            code_id = self._generate_id("code", code_name)

                            # Registrar o actualizar el nodo de Código contenedor (1:N)
                            if code_id not in code_nodes:
                                code_nodes[code_id] = {
                                    "id": code_id,
                                    "code_name": code_name,
                                    "description": item.code_explanation,
                                    "type": "ANTHROPOLOGICAL_CODE",
                                    "quotes_count": 0,
                                }
                            code_nodes[code_id]["quotes_count"] += 1

                            doc_id = f"doc_{hashlib.md5(title.encode('utf-8')).hexdigest()[:12]}"
                            quote_dict = {
                                "id": quote_id,
                                "text": item.text,
                                "code": code_name,
                                "code_id": code_id,
                                "code_explanation": item.code_explanation,
                                "analytical_level": item.analytical_level,
                                "relevance": item.relevance,
                                "source_document": title,
                                "source_document_id": doc_id,
                                "chunk_index": chunk_idx,
                                "type": "ANTHROPOLOGICAL_QUOTE",
                            }
                            all_quotes.append(quote_dict)

                except Exception as e:
                    logger.error(f"❌ Error codificando bloque {chunk_idx + 1} de '{title}': {e}")

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

        system_prompt = f"""Eres un metodólogo cualitativo experto en Antropología.
Tu tarea es agrupar un conjunto de códigos atómicos (que contienen múltiples citas) en Categorías analíticas superiores.

Marco Teórico de Referencia:
{theoretical_framework[:3000]}
"""
        if research_question:
            system_prompt += f"\nPregunta de Investigación: {research_question}"
        if hypothesis:
            system_prompt += f"\nHipótesis: {hypothesis}"

        prompt = f"""{system_prompt}

Revisa los siguientes Códigos Atómicos extraídos del trabajo de campo:

{codes_summary}

Instrucciones:
1. Agrupa los códigos atómicos en Categorías analíticas superiores coherentes.
2. Explica la conexión de cada categoría con el marco teórico y los objetivos de investigación."""

        categories = []
        category_relationships = []

        try:
            target_llm = self.llm or self.fast_llm
            result: AnthropologicalGroupingOutput = await invoke_structured_output(
                target_llm,
                AnthropologicalGroupingOutput,
                prompt,
            )

            if result and result.categories:
                for cat_item in result.categories:
                    cat_id = self._generate_id("category", cat_item.category_name)
                    cat_dict = {
                        "id": cat_id,
                        "category_name": cat_item.category_name,
                        "description": cat_item.category_description,
                        "theoretical_connection": cat_item.theoretical_connection,
                        "codes": cat_item.codes,
                        "type": "ANTHROPOLOGICAL_CATEGORY",
                    }
                    categories.append(cat_dict)

                    for code_str in cat_item.codes:
                        code_str_clean = code_str.strip().upper()
                        matching_code_id = self._generate_id("code", code_str_clean)

                        if matching_code_id in code_nodes:
                            category_relationships.append({
                                "id": f"rel_code_cat_{matching_code_id}_{cat_id}",
                                "source_id": matching_code_id,
                                "target_id": cat_id,
                                "type": "BELONGS_TO_CATEGORY",
                                "description": f"El código '{code_str_clean}' pertenece a la categoría '{cat_item.category_name}'",
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
2. Relación 1:N (Código a Citas): Cada cita se asigna a un Código atómico. Un mismo Código atómico puede agrupar MÚLTIPLES citas de diferentes pasajes del texto que expresen el mismo aspecto analítico relevante.
3. Lente Teórico: La asignación del código y la justificación deben estar guiadas hermenéuticamente por el Marco Teórico.

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
