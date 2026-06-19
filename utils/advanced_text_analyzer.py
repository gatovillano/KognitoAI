# utils/advanced_text_analyzer.py

import logging
import asyncio
import re
from typing import List, Dict, Optional, TypeVar, cast, Type

# LangChain y Pydantic para robustez y estructura
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from core.config import settings
from core.llm_manager import (
    get_llm_for_user,
    get_fast_llm,
    get_main_llm,
    get_configured_fallback_llm,
)
from core.utils.llm_utils import safe_json_loads
from pydantic import BaseModel, Field # Usamos pydantic v2
from typing import List, Dict, Optional, TypeVar, cast, Type, Any

logger = logging.getLogger(__name__)

_PydanticType = TypeVar('_PydanticType', bound=BaseModel)

# Límites conservadores para evitar timeouts por prompts excesivos en análisis de colección.
MAX_COLLECTION_CONTEXT_CHARS = 18000
MAX_COLLECTION_DOC_SNIPPET_CHARS = 700

# --- Modelos de Salida Pydantic para garantizar la estructura del LLM ---


class CollectionConnection(BaseModel):
    """Define una conexión específica encontrada entre documentos de una colección."""
    document_titles: List[str] = Field(description="Los títulos de los documentos entre los que se encontró la conexión.")
    insight: str = Field(description="Descripción de la sinergia, evolución o contradicción encontrada entre estos documentos.")

class ThemeQuote(BaseModel):
    """Define una cita o referencia relacionada con un tema transversal en un documento."""
    document_title: str = Field(description="El título del documento de donde se extrajo la cita.")
    quote: str = Field(description="La cita o fragmento relevante del documento relacionado con el tema. Cuida que las citas sean parrafos y oraciones completas y no fragmentos cortados arbitrariamente")


class ThemeReference(BaseModel):
    """Define un tema transversal con citas relacionadas de los documentos."""
    theme: str = Field(description="El nombre del tema transversal.")
    related_quotes: List[ThemeQuote] = Field(description="Lista de citas o fragmentos de los documentos relacionados con este tema.Cuida que las citas sean parrafos y oraciones completas y no fragmentos cortados arbitrariamente")


class KnowledgeGap(BaseModel):
    """Define una brecha de conocimiento identificada en el texto con explicación detallada."""
    gap_title: str = Field(description="El título o nombre de la brecha de conocimiento identificada.")
    explanation: str = Field(description="Explicación detallada de la brecha, por qué existe, qué implicaciones tiene y por qué es importante abordarla. Debe ser más explicativo que una simple pregunta.")
    related_context: str = Field(description="Contexto del texto donde se identifica esta brecha y por qué surge de la lectura.")


class SingleTextAnalysis(BaseModel):
    """Define la estructura de salida para el análisis de un único texto."""
    executive_summary: str = Field(description="Un resumen conciso que captura la esencia y las conclusiones principales del texto.")
    general_analysis: str = Field(description="Un análisis general extenso del documento que profundiza en el contexto, metodología, argumentos principales, implicaciones y relevancia (500-1000 palabras). Utiliza separación de parrafos pra facilitar la lectura")
    key_themes: List[ThemeReference] = Field(default_factory=list, description="Una lista de hasta 12 conceptos o temas centrales del texto, cada uno con citas del texto y explicación detallada.")
    central_concepts: List[str] = Field(default_factory=list, description="Una lista de hasta 8 conceptos centrales del texto en el formato 'CONCEPTO: DEFINICIÓN DETALLADA CON CONTEXTO Y EJEMPLOS'.")
    discipline: List[str] = Field(default_factory=list, description="El area, disciplina o campo al que refiere el documento. Por ejemplo si es un documémico y de qué área, o si es un documento técnico, etc.').")
    authorial_tone: str = Field(default="", description="El tono o la voz del autor (ej. 'Formal y Académico', 'Informal y Conversacional', 'Urgente y Directo', 'Escéptico y Crítico').")
    knowledge_gaps: List[KnowledgeGap] = Field(default_factory=list, description="Una lista de 5 a 8 brechas de conocimiento identificadas en el texto, cada una con explicación detallada de por qué existe esta brecha y qué implicaciones tiene.")
    exploration_questions: List[str] = Field(default_factory=list, description="Una lista de 5 a 8 preguntas adicionales para explorar a partir del texto, que el texto inspira pero no responde directamente.")
    problematic_areas: List[str] = Field(default_factory=list, description="Una lista de 3 a 5 áreas problemáticas, desafíos o puntos de controversia identificados en el texto.")
    final_reflections: List[str] = Field(default_factory=list, description="Una lista de 3 a 5 reflexiones finales sobre la importancia del contenido en el área que aborda, su aporte al conocimiento y apertura de temas de reflexión. Si se trata de documentos más técnicos o laborales puedes hablar de las posibilidades que abre, proyectos posibles o recomendaciones de gestión")
    kai_synthesis: str = Field(default="", description="Una síntesis única y profunda desde la perspectiva de KAI (Kognito AI) como exocerebro del usuario. Debe ser una reflexión de alto nivel (100-150 palabras) que conecte el contenido del documento con el contexto más amplio del conocimiento del usuario, identificando oportunidades, conexiones no obvias y valor estratégico.")

class DocumentSummary(BaseModel):
    """Estructura de salida simplificada para el resumen de un documento."""
    executive_summary: str = Field(
        description="Un resumen ejecutivo muy extenso y detallado (500-800 palabras) en español, estructurado en varios párrafos bien desarrollados que capture de manera condensada pero completa el contenido completo del documento, incluyendo todos sus puntos principales, objetivos, desarrollo de ideas, hallazgos, metodologías (si aplica), conclusiones y relevancia. Debe permitir al usuario comprender a fondo y con total claridad todo el documento sin necesidad de leer la versión completa."
    )
    document_structure: List[str] = Field(
        default_factory=list,
        description="Lista ordenada de las secciones o partes principales del documento. Cada elemento debe seguir el formato: 'Nombre de la Sección: descripción breve de qué trata y qué aporta (1-2 oraciones)'. Si el documento no tiene secciones explícitas, sintetiza su estructura lógica."
    )
    main_ideas: List[str] = Field(
        default_factory=list,
        description="Lista de 4 a 7 ideas, argumentos o afirmaciones principales del documento. Cada idea debe ser una oración completa y autoexplicativa."
    )
    kai_synthesis: str = Field(
        default="",
        description="Síntesis única desde la perspectiva de KAI (Kognito AI) como exocerebro del usuario (60-100 palabras). Reflexión estratégica que conecte el documento con el conocimiento más amplio del usuario, destacando su valor práctico o conexiones clave."
    )


class CollectionAnalysis(BaseModel):
    """Define la estructura de salida para el análisis de una colección de textos."""
    collection_summary: str = Field(description="Un resumen analítico que sintetiza la información de TODOS los documentos como un todo. Debe ser comprehensivo y detallado (200-300 palabras)")
    general_analysis: str = Field(description="Un análisis general extenso de la colección que profundiza en el contexto, metodología, argumentos principales, implicaciones y relevancia de los documentos en conjunto (500-1000 palabras). Utiliza separación de parrafos para facilitar la lectura.")
    authorial_tone: str = Field(default="", description="El tono o la voz predominante en la colección de documentos (ej. 'Formal y Académico', 'Informal y Conversacional', 'Urgente y Directo', 'Escéptico y Crítico').")
    cross_cutting_themes: List[ThemeReference] = Field(default_factory=list, description="Lista de hasta 10 temas recurrentes de los documentos que puedes identificar, cada uno con citas relacionadas de los documentos. Puedes agruparlos en algún concepto que los englobe cuando hay similitud semántica")
    central_concepts: List[str] = Field(default_factory=list, description="Una lista de hasta 8 conceptos, ideas o tesis centrales de la colección en el formato 'CONCEPTO: DEFINICIÓN DETALLADA'. Destaca con negrita el nombre de los conceptos")
    concept_relationships: List[str] = Field(default_factory=list, description="Una lista de hasta 8 descripciones detalladas de cómo los conceptos centrales se relacionan entre sí en la colección.")
    identified_connections: List[CollectionConnection] = Field(default_factory=list, description="Lista de insights específicos que conectan dos o más documentos. Incluye sinergias, evoluciones, contradicciones o complementariedades.")
    emergent_knowledge_gaps: List[KnowledgeGap] = Field(default_factory=list, description="Lista de 5-8 brechas de conocimiento emergentes de la colección en su conjunto, cada una con explicación detallada de por qué existe esta brecha y qué implicaciones tiene.")
    exploration_questions: List[str] = Field(default_factory=list, description="Lista de 5-8 preguntas adicionales para explorar a partir de la colección, que el texto inspira pero no responde directamente.")
    problematic_areas: List[str] = Field(default_factory=list, description="Una lista de 3 a 5 áreas problemáticas o desafíos comunes/emergentes identificados a través de la colección de documentos.")
    final_reflections: List[str] = Field(default_factory=list, description="3-5 reflexiones finales sobre la importancia del contenido en el área que aborda, su aporte al conocimiento y apertura de temas de reflexión. Si se trata de documentos más técnicos o laborales, puedes hablar de las posibilidades que abre, proyectos posibles o recomendaciones de gestión")
    collection_insights: List[str] = Field(default_factory=list, description="3-5 insights únicos que emergen del análisis conjunto de todos los documentos, que no serían evidentes analizando documentos individuales")
    methodological_notes: List[str] = Field(default_factory=list, description="2-3 observaciones sobre la metodología, enfoque o perspectiva común en los documentos analizados")
    kai_synthesis: str = Field(default="", description="Una síntesis de alto nivel desde la perspectiva de KAI (Kognito AI) como exocerebro del usuario. Debe ser una reflexión estratégica (150-200 palabras) que conecte el contenido de la colección con el contexto más amplio del conocimiento del usuario, identificando patrones emergentes, oportunidades de acción y valor estratégico único que surge del análisis conjunto.")


# --- Helpers para resiliencia ante errores de proveedor LLM ---

def _clone_without_streaming(llm: Any) -> Any:
    """Clona un LLM desactivando streaming para evitar MidStreamFallbackError."""
    llm_copy = llm
    if hasattr(llm, "model_copy"):
        try:
            llm_copy = llm.model_copy(deep=True)
        except TypeError:
            llm_copy = llm.model_copy()
    elif hasattr(llm, "copy"):
        try:
            llm_copy = llm.copy(deep=True)
        except TypeError:
            llm_copy = llm.copy()
    if hasattr(llm_copy, "streaming"):
        llm_copy.streaming = False
    extra_body = getattr(llm_copy, "extra_body", None)
    if isinstance(extra_body, dict):
        extra_body.setdefault("include_reasoning", False)
    return llm_copy


def _is_retryable_llm_provider_error(exc: Exception) -> bool:
    """Detecta errores transitorios de proveedor que ameritan reintento con fallback."""
    error_text = str(exc).lower()
    if any(marker in error_text for marker in [
        "authenticationerror",
        "api key not valid",
        "invalid api key",
        "incorrect api key",
        "unauthorized",
        "forbidden",
        "401",
    ]):
        return False
    return any(marker in error_text for marker in [
        "timeout",
        "timed out",
        "litellm.timeout",
        "midstreamfallbackerror",
        "openrouterexception",
        "provider returned error",
        "error_type': 'unmapped'",
        'error_type": "unmapped"',
        "serviceunavailableerror",
    ])


def _hydrate_with_model_defaults(model_cls: Type[_PydanticType], payload: Any) -> Any:
    """Completa campos omitidos por el LLM usando defaults declarados en el modelo."""
    if not isinstance(payload, dict):
        return payload

    hydrated_payload = dict(payload)
    for field_name, field_info in model_cls.model_fields.items():
        if field_name in hydrated_payload or field_info.is_required():
            continue
        if field_info.default_factory is not None:
            hydrated_payload[field_name] = field_info.default_factory()
        else:
            hydrated_payload[field_name] = field_info.default
    return hydrated_payload


def _get_effective_llm_identity(llm: Any) -> tuple[str, str]:
    """Devuelve proveedor y modelo efectivos para logging, no los aliases internos de LiteLLM."""
    raw_model = getattr(llm, "model_name", None) or getattr(llm, "model", None) or "desconocido"
    raw_provider = getattr(llm, "provider", None) or getattr(llm, "custom_llm_provider", None) or "desconocido"
    api_base = str(getattr(llm, "api_base", None) or "")

    effective_provider = str(raw_provider)
    effective_model = str(raw_model)

    if "openrouter.ai" in api_base or effective_model.startswith("openrouter/"):
        effective_provider = "openrouter"
        if effective_model.startswith("openrouter/"):
            effective_model = effective_model[len("openrouter/"):]
        elif effective_model.startswith("openai/"):
            effective_model = effective_model[len("openai/"):]
    elif effective_provider == "openai" and effective_model.startswith("openai/"):
        effective_model = effective_model[len("openai/"):]

    return effective_provider, effective_model


# --- Clase Principal del Analizador ---

class AdvancedTextAnalyzer:
    """
    Una clase encapsulada para realizar análisis de texto avanzados usando modelos de lenguaje.
    Gestiona la inicialización de modelos y proporciona métodos de análisis robustos.
    """
    async def _get_model(self, account_id: Optional[str] = None) -> Any:
        """Obtiene el modelo de análisis (personalizado por usuario o global)."""
        if account_id:
            logger.info(f"Obteniendo modelo personalizado para análisis (usuario: {account_id})...")
            return await get_llm_for_user(account_id, purpose="fast")
        
        logger.info("Usando modelo rápido global para análisis de texto avanzado...")
        return get_fast_llm()

    async def _run_analysis_with_parser(self, prompt: str, output_parser: PydanticOutputParser, pydantic_object: Type[_PydanticType], account_id: Optional[str] = None, timeout_seconds: Optional[float] = None) -> _PydanticType:
        """
        Función centralizada y robusta para ejecutar una llamada al LLM y parsear la salida.
        """
        import json

        full_prompt = f"{prompt}\n\n{output_parser.get_format_instructions()}"

        def _format_error(exc: Optional[Exception]) -> str:
            if exc is None:
                return "Error desconocido (sin excepción capturada)."
            text = str(exc).strip()
            if text:
                return f"{type(exc).__name__}: {text}"
            return f"{type(exc).__name__}: {repr(exc)}"

        async def _try_invoke_and_parse(candidate_llm: Any, timeout_seconds: float) -> _PydanticType:
            provider_name, model_name = _get_effective_llm_identity(candidate_llm)
            logger.info("Invocando LLM (%s/%s) con timeout de %s segundos...", provider_name, model_name, timeout_seconds)
            response = await asyncio.wait_for(
                _clone_without_streaming(candidate_llm).ainvoke([HumanMessage(content=full_prompt)]),
                timeout=timeout_seconds,
            )
            response_content = response.content
            if isinstance(response_content, list):
                response_content = " ".join(str(item) for item in response_content)
            elif not isinstance(response_content, str):
                response_content = str(response_content)

            logger.info("Respuesta del LLM recibida (longitud: %d caracteres). Iniciando parseo a JSON...", len(response_content))

            try:
                obj = safe_json_loads(response_content)
                obj = _hydrate_with_model_defaults(pydantic_object, obj)
                json_string = json.dumps(obj)
            except Exception as parse_err:
                logger.error(f"Error en safe_json_loads: {parse_err}")
                json_string = response_content

            parsed_output = await output_parser.aparse(json_string)
            logger.info("Parseo de JSON estructurado exitoso para el objeto %s.", pydantic_object.__name__)
            return cast(pydantic_object, parsed_output)

        def _llm_signature(candidate_llm: Any) -> str:
            provider, model = _get_effective_llm_identity(candidate_llm)
            return f"{provider}|{model}"

        candidates: List[Any] = []
        seen_signatures: set[str] = set()

        def _append_candidate(candidate_llm: Any):
            if not candidate_llm:
                return
            sig = _llm_signature(candidate_llm)
            if sig in seen_signatures:
                return
            seen_signatures.add(sig)
            candidates.append(candidate_llm)

        # Orden de intentos:
        # 1) rápido de usuario/global, 2) principal del usuario, 3) fallback configurado.
        primary_llm = await self._get_model(account_id)
        _append_candidate(primary_llm)

        if account_id:
            try:
                user_main_llm = await get_llm_for_user(account_id, purpose="main")
                _append_candidate(user_main_llm)
            except Exception as e:
                logger.warning("No se pudo obtener LLM principal del usuario para fallback: %s", e)

        fallback_llm = await get_configured_fallback_llm(
            account_id=account_id,
            failed_purpose="fast",
        )
        _append_candidate(fallback_llm)

        last_error: Optional[Exception] = None
        attempt_errors: List[str] = []

        # Último recurso: intentar también modelos globales distintos a los ya evaluados.
        _append_candidate(get_main_llm())
        _append_candidate(get_fast_llm())

        if not candidates:
            raise ValueError("No hay modelos LLM disponibles para ejecutar el análisis.")

        candidate_signatures = [f"{_get_effective_llm_identity(c)[0]}|{_get_effective_llm_identity(c)[1]}" for c in candidates]
        logger.info(
            "Iniciando ejecución de análisis con parser (%s). Candidatos de LLM a evaluar en orden: %s | Longitud de prompt: %d chars.",
            pydantic_object.__name__,
            candidate_signatures,
            len(full_prompt)
        )

        for idx, candidate in enumerate(candidates, start=1):
            provider_name, model_name = _get_effective_llm_identity(candidate)
            try:
                logger.info(
                    "Analizador de texto: intento LLM %s/%s | provider=%s | model=%s",
                    idx,
                    len(candidates),
                    provider_name,
                    model_name,
                )
                effective_timeout = timeout_seconds if timeout_seconds is not None else float(settings.llm_request_timeout)
                return await _try_invoke_and_parse(candidate, timeout_seconds=effective_timeout)
            except Exception as exc:
                last_error = exc
                retryable = _is_retryable_llm_provider_error(exc) or isinstance(exc, asyncio.TimeoutError)
                formatted_error = _format_error(exc)
                attempt_errors.append(
                    f"attempt={idx}/{len(candidates)} provider={provider_name} model={model_name} error={formatted_error}"
                )
                logger.warning(
                    "Analizador de texto: fallo intento %s/%s | retryable=%s | provider=%s | model=%s | error=%s",
                    idx,
                    len(candidates),
                    retryable,
                    provider_name,
                    model_name,
                    formatted_error,
                )
                if not retryable:
                    break

        logger.error(
            "Fallo en el pipeline de análisis tras agotar candidatos LLM. intentos=%s",
            " | ".join(attempt_errors) if attempt_errors else "sin_detalle",
            exc_info=last_error if last_error else False,
        )
        raise ValueError(
            "No se pudo obtener una respuesta JSON válida del LLM. "
            f"Último error: {_format_error(last_error)}"
        )

    async def analyze_single_text(self, text: str, document_title: str = "Documento analizado", account_id: Optional[str] = None) -> SingleTextAnalysis:
        """
        Ejecuta un análisis completo y estructurado sobre un único fragmento de texto.
        """
        logger.info(
            "Iniciando análisis de texto único. Título: '%s' | Usuario (account_id): %s | Longitud texto: %d caracteres.",
            document_title,
            account_id,
            len(text) if text else 0
        )
        if not text or len(text.split()) < 30:
            logger.warning(
                "Texto demasiado corto para análisis detallado (título: '%s'). Longitud: %d palabras. Retornando estructura vacía.",
                document_title,
                len(text.split()) if text else 0
            )
            return SingleTextAnalysis(
                executive_summary=text, general_analysis="Texto insuficiente para análisis detallado",
                key_themes=[], central_concepts=[], discipline=[], authorial_tone="N/A",
                knowledge_gaps=[], exploration_questions=[], problematic_areas=[],
                final_reflections=[], kai_synthesis="Texto insuficiente para generar una síntesis."
            )

        prompt = f"""
        Eres KAI (Kognito AI), un analista experto en análisis textual de conocimientos que actúa como exocerebro proactivo del usuario. Realiza un análisis exhaustivo y detallado del siguiente texto. Asegúrate de que todo el contenido generado esté en español.
 
        INSTRUCCIONES ESPECÍFICAS:
        1. **Resumen ejecutivo**: Conciso pero completo (50-80 palabras) en español.

        2. **Análisis general**: EXTENSO y profundo (500-1000 palabras) redactado en varios párrafos separados para facilitar la lectura, que incluya:
           - Contexto histórico, teórico o práctico del documento
           - Metodología o enfoque utilizado por el autor
           - Argumentos principales y su estructura lógica
           - Implicaciones teóricas y prácticas
           - Relevancia en el campo de conocimiento
           - Conexiones con otros temas o disciplinas
           - Evaluación crítica del contenido
           - Fortalezas y debilidades del texto
           - Audiencia objetivo y propósito del documento
           - Contribuciones originales o innovadoras
           - Limitaciones o sesgos identificados

        3. **Temas clave**: Hasta 12 temas importantes del texto. ESTRUCTURA REQUERIDA para cada tema:
           {{
             "theme": "Nombre del tema específico",
             "related_quotes": [
               {{
                 "document_title": "{document_title}",
                 "quote": "Cita textual completa del documento (párrafo u oración completa)"
               }}
             ]
           }}
           - Cada tema debe tener al menos 1-2 citas relevantes del texto
           - Las citas deben ser párrafos u oraciones completas, no fragmentos cortados
           - Usa nombres de temas específicos y descriptivos

        4. **Conceptos centrales**: Hasta 8 conceptos en formato 'CONCEPTO: DEFINICIÓN DETALLADA CON CONTEXTO Y EJEMPLOS. Destaca los conceptos en negrita'

        5. **Disciplina**: Área(s) de conocimiento específica(s)

        6. **Tono del autor**: Descripción precisa del estilo y enfoque

        7. **Brechas de conocimiento**: 5-8 brechas de conocimiento identificadas. ESTRUCTURA REQUERIDA para cada brecha:
           {{
             "gap_title": "Nombre descriptivo de la brecha",
             "explanation": "Explicación detallada de por qué existe esta brecha, qué implicaciones tiene y por qué es importante abordarla",
             "related_context": "Contexto específico del texto donde se identifica esta brecha"
           }}
           - Cada brecha debe tener explicación detallada, no solo preguntas

        8. **Preguntas para explorar**: 5-8 preguntas adicionales para explorar a partir del texto, que el texto inspira pero no responde directamente.

        9. **Problemáticas**: 3-5 áreas problemáticas, desafíos o puntos de controversia identificados en el texto.

        10. **Reflexiones finales**: 3-5 reflexiones sobre importancia, aportes y proyecciones

        11. **Síntesis de KAI**: Como exocerebro del usuario, genera una reflexión estratégica de alto nivel (100-150 palabras) que:
            - Conecte este documento con el contexto más amplio del conocimiento del usuario
            - Identifique oportunidades de acción o aplicación práctica
            - Señale conexiones no obvias con otros dominios o áreas de interés
            - Destaque el valor estratégico único de este contenido
            - Proponga formas de aprovechar este conocimiento de manera proactiva
            - Adopta un tono reflexivo, estratégico y orientado a la acción

        Para los temas clave y conceptos centrales, utiliza nombres precisos y relevantes al contexto del texto, priorizando términos específicos del dominio o categorías reconocibles por el usuario.

        IMPORTANTE: Los temas clave deben seguir EXACTAMENTE la estructura JSON mostrada arriba, con "theme" y "related_quotes" como campos obligatorios.
        
        IMPORTANTE: Las brechas de conocimiento deben seguir EXACTAMENTE la estructura JSON mostrada arriba, con "gap_title", "explanation" y "related_context" como campos obligatorios.

        IMPORTANTE: Tu salida JSON debe incluir TODOS los campos del esquema, incluso si alguno queda vacío. Para listas usa [] y para strings usa "".

        Texto a analizar:
        ---
        {text}
        ---
        """
        parser = PydanticOutputParser(pydantic_object=SingleTextAnalysis)
        result = await self._run_analysis_with_parser(prompt, parser, SingleTextAnalysis, account_id=account_id)
        logger.info(
            "Análisis de texto único completado con éxito para '%s'. Temas encontrados: %d | Conceptos centrales: %d | Brechas identificadas: %d.",
            document_title,
            len(result.key_themes),
            len(result.central_concepts),
            len(result.knowledge_gaps)
        )
        return cast(SingleTextAnalysis, result)

    async def summarize_document(self, text: str, document_title: str = "Documento", account_id: Optional[str] = None) -> 'DocumentSummary':
        """
        Genera un resumen estructurado y conciso de un documento.
        Diferente al análisis completo: más ligero, orientado a comprensión rápida.
        """
        logger.info(
            "Iniciando resumen de documento. Título: '%s' | Usuario (account_id): %s | Longitud texto: %d caracteres.",
            document_title,
            account_id,
            len(text) if text else 0
        )
        if not text or len(text.split()) < 30:
            logger.warning(
                "Texto demasiado corto para generar un resumen estructurado (título: '%s'). Longitud: %d palabras. Retornando estructura vacía.",
                document_title,
                len(text.split()) if text else 0
            )
            return DocumentSummary(
                executive_summary=text,
                document_structure=[],
                main_ideas=[],
                kai_synthesis="Texto insuficiente para generar un resumen."
            )

        prompt = f"""
        Eres KAI (Kognito AI), el exocerebro del usuario. Tu tarea es generar un resumen estructurado y claro del siguiente documento.
        Todo el contenido debe estar en español.

        INSTRUCCIONES:

        1. **Resumen Ejecutivo** (500-800 palabras): Redacta un resumen ejecutivo muy extenso y detallado, estructurado en varios párrafos bien diferenciados en español. Debe capturar de manera condensada pero completa el contenido completo del documento, incluyendo todos sus puntos principales, objetivos, desarrollo de ideas, hallazgos, metodologías (si aplica), conclusiones y relevancia. Debe permitir al usuario comprender a fondo y con total claridad todo el documento sin necesidad de leerlo en su totalidad.

        2. **Estructura del Documento**: Lista ordenada de las secciones o partes del documento. Para cada una indica:
           - Su nombre o título (si lo tiene)
           - Una breve descripción de qué trata y qué aporta (1-2 oraciones)
           Si el documento no tiene secciones explícitas, sintetiza su estructura lógica (introducción, desarrollo, conclusión, etc.).

        3. **Ideas Principales** (4-7 ideas): Las ideas, argumentos o afirmaciones más importantes del documento. Cada una debe ser una oración completa y autoexplicativa, no una simple palabra clave.

        4. **Síntesis de KAI** (60-100 palabras): Como exocerebro del usuario, reflexiona brevemente sobre el valor práctico o estratégico de este documento. ¿Qué conexiones abre? ¿Qué utilidad concreta tiene para el usuario? Usa un tono reflexivo y orientado a la acción.

        Documento a resumir ("{document_title}"):
        ---
        {text}
        ---
        """
        parser = PydanticOutputParser(pydantic_object=DocumentSummary)
        result = await self._run_analysis_with_parser(prompt, parser, DocumentSummary, account_id=account_id)
        logger.info(
            "Resumen de documento completado con éxito para '%s'. Estructura (secciones): %d | Ideas principales: %d.",
            document_title,
            len(result.document_structure),
            len(result.main_ideas)
        )
        return cast(DocumentSummary, result)

    async def analyze_collection(self, documents: List[Dict[str, str]], account_id: Optional[str] = None) -> CollectionAnalysis:
        """
        Analiza una colección de documentos para encontrar temas transversales, conexiones y brechas de conocimiento emergentes.
        """
        logger.info(
            "Iniciando análisis de colección de documentos. Total documentos: %d | Usuario (account_id): %s",
            len(documents) if documents else 0,
            account_id
        )
        if not documents:
            logger.warning("Colección de documentos vacía proporcionada para análisis. Retornando estructura vacía.")
            return CollectionAnalysis(
                collection_summary="No se proporcionaron textos para analizar.",
                general_analysis="No se proporcionaron textos para analizar.",
                authorial_tone="",
                cross_cutting_themes=[],
                central_concepts=[],
                concept_relationships=[],
                identified_connections=[],
                emergent_knowledge_gaps=[],
                exploration_questions=[],
                problematic_areas=[],
                final_reflections=[],
                collection_insights=[],
                methodological_notes=[],
                kai_synthesis="",
            )
            
        full_context_text = ""
        truncated_docs = 0
        total_context_chars = 0
        for i, doc in enumerate(documents):
            title = doc.get('title', f"Documento {i+1}")
            raw_content = doc.get('content', '')
            if len(raw_content) > MAX_COLLECTION_DOC_SNIPPET_CHARS:
                content_snippet = raw_content[:MAX_COLLECTION_DOC_SNIPPET_CHARS] + '...'
            else:
                content_snippet = raw_content

            next_block = f"--- INICIO DOCUMENTO: '{title}' ---\n{content_snippet}\n--- FIN DOCUMENTO: '{title}' ---\n\n"
            if total_context_chars + len(next_block) > MAX_COLLECTION_CONTEXT_CHARS:
                truncated_docs += 1
                continue

            full_context_text += next_block
            total_context_chars += len(next_block)

        if truncated_docs > 0:
            logger.warning(
                "Colección truncada para evitar timeout del proveedor LLM: %s documentos omitidos (chars=%s/%s)",
                truncated_docs,
                total_context_chars,
                MAX_COLLECTION_CONTEXT_CHARS,
            )
        else:
            logger.info(
                "Contexto de colección construido exitosamente. Documentos incluidos: %d (caracteres totales: %d).",
                len(documents) - truncated_docs,
                total_context_chars
            )

        output_parser = PydanticOutputParser(pydantic_object=CollectionAnalysis)
        prompt = f"""
        Eres KAI (Kognito AI), un analista de investigación experto en síntesis de conocimiento que actúa como exocerebro proactivo del usuario. Analiza esta colección de documentos. Asegúrate de que todo el contenido generado esté en español.
 
        INSTRUCCIONES ESPECÍFICAS PARA EL ANÁLISIS DE COLECCIÓN:
        Tu tarea es generar un análisis exhaustivo de la colección de documentos, asegurándote de incluir TODOS los siguientes campos en tu respuesta JSON, siguiendo las descripciones y formatos indicados. Todo el contenido generado debe estar en español:

        1.  **collection_summary**: Un resumen analítico que sintetiza la información de TODOS los documentos como un todo. Debe ser comprehensivo y detallado (200-300 palabras).
        2.  **general_analysis**: EXTENSO y profundo (500-1000 palabras) redactado en varios párrafos separados para facilitar la lectura, que incluya:
           - Contexto histórico, teórico o práctico de la colección
           - Metodología o enfoque común en los documentos
           - Argumentos principales y su estructura lógica en conjunto
           - Implicaciones teóricas y prácticas de la colección
           - Relevancia en el campo de conocimiento
           - Conexiones con otros temas o disciplinas
           - Evaluación crítica del contenido de la colección
           - Fortalezas y debilidades de la colección
           - Audiencia objetivo y propósito de la colección
           - Contribuciones originales o innovadoras de la colección
           - Limitaciones o sesgos identificados en la colección
        3.  **authorial_tone**: El tono o la voz predominante en la colección de documentos (ej. 'Formal y Académico', 'Informal y Conversacional', 'Urgente y Directo', 'Escéptico y Crítico').
        4.  **cross_cutting_themes**: Una lista de hasta 10 temas recurrentes que identificas entre los documentos. Cada tema debe incluir citas relevantes de los documentos que lo ilustren. Puedes agruparlos en algún concepto que los englobe cuando hay similitud semántica.
        3.  **central_concepts**: Una lista de hasta 8 conceptos, ideas o tesis centrales de la colección. Cada uno debe estar en el formato 'CONCEPTO: DEFINICIÓN DETALLADA'. Destaca el nombre del concepto en negrita.
        4.  **concept_relationships**: Una lista de hasta 8 descripciones detalladas de cómo los conceptos centrales se relacionan entre sí dentro de la colección.
        5.  **identified_connections**: Una lista de insights específicos que conectan dos o más documentos. Incluye sinergias, evoluciones, contradicciones o complementariedades. Cada conexión debe especificar los títulos de los documentos involucrados y una descripción del insight.
        6.  **emergent_knowledge_gaps**: Una lista de 5-8 brechas de conocimiento emergentes. ESTRUCTURA REQUERIDA para cada brecha:
           {{
             "gap_title": "Nombre descriptivo de la brecha emergente",
             "explanation": "Explicación detallada de por qué esta brecha emerge de la colección y qué implicaciones tiene",
             "related_context": "Contexto de la colección donde se identifica esta brecha"
           }}
           - Cada brecha emergente debe tener explicación detallada, no solo preguntas
        7.  **exploration_questions**: Una lista de 5-8 preguntas adicionales para explorar a partir de la colección, que el texto inspira pero no responde directamente.
        8.  **problematic_areas**: Una lista de 3 a 5 áreas problemáticas o desafíos comunes/emergentes identificados a través de la colección de documentos.
        9.  **final_reflections**: 3-5 reflexiones finales sobre la importancia del contenido en el área que aborda, su aporte al conocimiento y apertura de temas de reflexión. Si se trata de documentos más técnicos o laborales, puedes hablar de las posibilidades que abre, proyectos posibles o recomendaciones de gestión.
        10. **collection_insights**: 3-5 insights únicos que emergen del análisis conjunto de todos los documentos, que no serían evidentes analizando documentos individuales.
        11. **methodological_notes**: 2-3 observaciones sobre la metodología, enfoque o perspectiva común en los documentos analizados.
        12. **kai_synthesis**: Como exocerebro del usuario, genera una síntesis estratégica de alto nivel (150-200 palabras) que:
            - Conecte el contenido de esta colección con el contexto más amplio del conocimiento del usuario
            - Identifique patrones emergentes y oportunidades estratégicas únicas que surgen del análisis conjunto
            - Señale conexiones no obvias entre los documentos y con otros dominios
            - Destaque el valor estratégico único de esta colección como un todo
            - Proponga acciones concretas o áreas de exploración prioritarias
            - Adopta un tono reflexivo, estratégico y orientado a la acción

        Asegúrate de que cada campo esté presente en la salida JSON, incluso si está vacío (en cuyo caso, usa un array vacío `[]` para las listas o un string vacío `""` para los strings).

        Colección de documentos:
        {full_context_text}
        """
        result = await self._run_analysis_with_parser(
            prompt,
            output_parser,
            CollectionAnalysis,
            account_id=account_id,
            timeout_seconds=max(float(settings.llm_request_timeout), 180.0),
        )
        logger.info(
            "Análisis de colección de documentos completado con éxito. Temas transversales: %d | Conexiones identificadas: %d | Insights de la colección: %d.",
            len(result.cross_cutting_themes),
            len(result.identified_connections),
            len(result.collection_insights)
        )
        return cast(CollectionAnalysis, result)

# --- INSTANCIA ÚNICA ---
# Se crea una única instancia del analizador para ser importada y reutilizada en toda la aplicación.
# Esto asegura que el modelo de Gemini solo se cargue una vez.
text_analyzer = AdvancedTextAnalyzer()
