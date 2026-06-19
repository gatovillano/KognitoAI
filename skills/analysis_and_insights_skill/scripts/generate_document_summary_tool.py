# tools/generate_document_summary_tool.py

import logging
import asyncio
from typing import Any, Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from core.llm_manager import get_fast_llm
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser

logger = logging.getLogger(__name__)

# --- Modelo de Salida Pydantic (resumen simple) ---

class DocumentSummary(BaseModel):
    """Resumen estructurado simple de un documento."""
    summary: str = Field(description="Resumen ejecutivo del documento en 1-2 párrafos (máximo 150 palabras). Debe capturar la esencia y las conclusiones principales.")
    key_points: list[str] = Field(description="Lista de 3-5 puntos clave del documento, cada uno como una frase concisa.")
    topics: list[str] = Field(description="Lista de 3-5 temas o etiquetas principales que representan el contenido del documento.")
    document_type: str = Field(description="Tipo de documento (ej: 'informe', 'artículo', 'técnico', 'legal', 'correspondencia', 'contrato', 'acta', 'memorando', 'otro').")
    confidence: float = Field(description="Nivel de confianza del resumen generado (0.0 a 1.0). Usa 0.9 para documentos claros, 0.7 para ambiguos.")

# --- Esquema de Entrada ---

class GenerateDocumentSummaryInput(BaseModel):
    """Define el esquema de entrada para la herramienta de resumen de documentos."""
    text: str = Field(
        ...,
        description="El contenido completo del texto del documento a resumir."
    )
    document_title: Optional[str] = Field(
        None,
        description="Título del documento (opcional, para contexto)."
    )

# --- Herramienta LangChain ---

class GenerateDocumentSummaryTool(BaseTool):
    """
    Herramienta de LangChain que genera un resumen estructurado simple de un documento.
    Más rápido y conciso que un análisis completo. Ideal para vistas previas y tarjetas.
    """
    name: str = "generate_document_summary"
    description: str = (
        "Útil para generar un resumen rápido y estructurado de un documento. "
        "Devuelve: resumen ejecutivo (1-2 párrafos), puntos clave (lista), temas principales (lista), "
        "tipo de documento y nivel de confianza. Es más rápido que un análisis completo."
    )
    args_schema: Type[BaseModel] = GenerateDocumentSummaryInput
    return_direct: bool = False
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="El ID de Telegram del usuario, inyectado automáticamente.")

    async def _arun(self, text: str, document_title: Optional[str] = None, **kwargs: Any) -> str:
        """Ejecuta la lógica de generación de resumen de forma asíncrona."""
        logger.info(f"Generando resumen estructurado para documento: {document_title or 'sin título'}")
        try:
            result = await self._generate_summary(text, document_title)
            logger.info("Resumen generado exitosamente.")
            return self._format_result(result)
        except Exception as e:
            logger.error(f"Error durante la generación de resumen: {e}", exc_info=True)
            return f"Ocurrió un error al intentar resumir el documento: {str(e)}"

    def _run(self, text: str, document_title: Optional[str] = None, **kwargs: Any) -> str:
        """Ejecución síncrona (delega a _arun)."""
        logger.info("Ejecutando generación de resumen en modo síncrono...")
        try:
            result = asyncio.run(self._arun(text=text, document_title=document_title, **kwargs))
            return result
        except RuntimeError as e:
            logger.warning(f"RuntimeError en _run, podría indicar un loop de eventos activo: {e}.")
            return "Error: No se pudo ejecutar el resumen en modo síncrono debido a un conflicto de loop de eventos."
        except Exception as e:
            logger.error(f"Error durante la ejecución síncrona del resumen: {e}", exc_info=True)
            return f"Ocurrió un error durante la generación de resumen: {str(e)}"

    async def _generate_summary(self, text: str, document_title: Optional[str]) -> DocumentSummary:
        """Genera el resumen usando el LLM rápido y parsea con Pydantic."""
        # Validación mínima
        if not text or len(text.strip()) < 50:
            return DocumentSummary(
                summary="El documento tiene muy poco contenido para generar un resumen significativo.",
                key_points=["Contenido insuficiente"],
                topics=["vacío"],
                document_type="desconocido",
                confidence=0.5
            )

        # Obtener LLM rápido
        llm = get_fast_llm()

        # Parser para forzar estructura JSON
        parser = PydanticOutputParser(pydantic_object=DocumentSummary)

        # Prompt conciso
        prompt = f"""
Eres KAI (Kognito AI), un asistente experto en análisis de documentos. Tu tarea es generar un resumen ESTRUCTURADO y CONCISO del siguiente documento.

INSTRUCCIONES:
1. **Resumen Ejecutivo**: Escribe un resumen en 1-2 párrafos (máximo 150 palabras) que capture la esencia, propósito y conclusiones principales del documento.
2. **Puntos Clave**: Identifica 3-5 puntos clave, cada uno como una frase corta y clara.
3. **Temas Principales**: Lista 3-5 temas o etiquetas que mejor representen el contenido (ej: 'contratos', 'legal', 'finanzas').
4. **Tipo de Documento**: Clasifica el documento en una de estas categorías: 'informe', 'artículo', 'técnico', 'legal', 'correspondencia', 'contrato', 'acta', 'memorando', 'otro'.
5. **Confianza**: Asigna un valor de 0.0 a 1.0 que refleje qué tan seguro estás de tu resumen (0.9 para textos claros, 0.7 para ambiguos).

DOCUMENTO:
Título: {document_title or 'No especificado'}
Contenido:
{text[:8000]}  # Limitar a 8000 caracteres para velocidad

{parser.get_format_instructions()}
"""

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            response_content = response.content
            if isinstance(response_content, list):
                response_content = " ".join(str(item) for item in response_content)
            elif not isinstance(response_content, str):
                response_content = str(response_content)

            # Parsear con Pydantic
            parsed = await parser.aparse(response_content)
            return parsed
        except Exception as e:
            logger.error(f"Error parsing summary: {e}")
            # Fallback: resumen muy simple
            first_lines = " ".join(text.split()[:50])
            return DocumentSummary(
                summary=f"Documento sobre: {first_lines}...",
                key_points=["Contenido no analizable completamente"],
                topics=["general"],
                document_type="otro",
                confidence=0.5
            )

    def _format_result(self, result: DocumentSummary) -> str:
        """Formatea el resultado como string (para logging)."""
        # En realidad, el resultado se guardará como JSON en la BD, pero para logging
        formatted = (
            f"Resumen generado (confianza: {result.confidence}):\n"
            f"- Resumen: {result.summary}\n"
            f"- Puntos clave: {', '.join(result.key_points)}\n"
            f"- Temas: {', '.join(result.topics)}\n"
            f"- Tipo: {result.document_type}"
        )
        return formatted
