# core/citation_models.py

"""
Modelos de datos para el sistema de citas y fuentes de KognitoAI.

Este módulo define las estructuras de datos necesarias para implementar
un sistema de citas similar al de OpenWebUI, donde las herramientas
pueden devolver tanto contexto para el LLM como fuentes estructuradas
para mostrar al usuario.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class SourceType(str, Enum):
    """Tipos de fuentes disponibles en el sistema."""
    WEB = "web"
    DOCUMENT = "document"
    MEMORY = "memory"
    CODE = "code"
    DATABASE = "database"
    GRAPH = "graph"
    NOTE = "note"


class Source(BaseModel):
    """
    Representa una fuente individual que puede ser citada en una respuesta.
    Attributes:
        id: Identificador único de la fuente (usado para citas [1], [2], etc.)
        title: Título descriptivo de la fuente
        url: URL o identificador de la fuente (puede ser URL web, path de archivo, etc.)
        snippet: Fragmento de texto relevante de la fuente
        type: Tipo de fuente (web, document, memory, etc.)
        metadata: Metadatos adicionales específicos del tipo de fuente
    """
    id: Union[int, str] = Field(..., description="Identificador único para la cita")
    title: str = Field(..., description="Título descriptivo de la fuente")
    url: str = Field(..., description="URL o identificador de la fuente")
    snippet: str = Field(..., description="Fragmento relevante de la fuente")
    type: SourceType = Field(default=SourceType.WEB, description="Tipo de fuente")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos adicionales")


class ToolOutputWithSources(BaseModel):
    """
    Estructura de salida estándar para herramientas que pueden proporcionar fuentes.
    Esta clase define el formato que deben devolver las herramientas cuando
    quieren proporcionar tanto contexto para el LLM como fuentes para citar.
    Attributes:
        context_for_llm: Texto formateado para incluir en el prompt del LLM
        sources: Lista de fuentes que pueden ser citadas
        summary: Resumen opcional de la información encontrada
    """
    context_for_llm: str = Field(..., description="Contexto formateado para el LLM con referencias [1], [2], etc.")
    sources: List[Source] = Field(default_factory=list, description="Lista de fuentes citables")
    summary: Optional[str] = Field(default=None, description="Resumen opcional de la información")


class CitationResponse(BaseModel):
    """
    Respuesta completa del agente que incluye tanto el texto generado como las fuentes.
    Esta es la estructura final que se envía al frontend, combinando la respuesta
    del LLM con las fuentes estructuradas para mostrar al usuario.
    Attributes:
        response_text: Texto de respuesta generado por el LLM (puede incluir citas [1], [2])
        sources: Lista de fuentes citadas en la respuesta
        has_citations: Indica si la respuesta contiene citas
    """
    response_text: str = Field(..., description="Respuesta del LLM")
    sources: List[Source] = Field(default_factory=list, description="Fuentes citadas")
    has_citations: bool = Field(default=False, description="Indica si hay citas en la respuesta")
    @property
    def source_count(self) -> int:
        """Retorna el número de fuentes disponibles."""
        return len(self.sources)


def format_context_with_sources(sources: List[Source]) -> str:
    """
    Formatea una lista de fuentes en un contexto legible para el LLM.
    Args:
        sources: Lista de fuentes a formatear
    Returns:
        Texto formateado con las fuentes numeradas para incluir en el prompt
    """
    if not sources:
        return ""
    context_parts = []
    for source in sources:
        # No incluir la URL en el snippet que se pasa al LLM para evitar que la repita
        context_parts.append(
            f"Contexto [{source.id}] - {source.title}:\n{source.snippet}\n"
        )
    return "\n".join(context_parts)


def create_web_source(source_id: int, title: str, url: str, snippet: str,
                       metadata: Optional[Dict[str, Any]] = None) -> Source:
    """
    Función helper para crear una fuente web.
    Args:
        source_id: ID único de la fuente
        title: Título de la página web
        url: URL de la página
        snippet: Fragmento relevante del contenido
        metadata: Metadatos adicionales (ej: fecha, autor, etc.)
    Returns:
        Objeto Source configurado para fuente web
    """
    return Source(
        id=source_id,
        title=title,
        url=url,
        snippet=snippet,
        type=SourceType.WEB,
        metadata=metadata or {}
    )


def create_document_source(source_id: int, title: str, file_path: str, snippet: str,
                            metadata: Optional[Dict[str, Any]] = None) -> Source:
    """
    Función helper para crear una fuente de documento.
    Args:
        source_id: ID único de la fuente
        title: Nombre del documento
        file_path: Ruta o identificador del archivo
        snippet: Fragmento relevante del documento
        metadata: Metadatos adicionales (ej: página, sección, etc.)
    Returns:
        Objeto Source configurado para documento
    """
    return Source(
        id=source_id,
        title=title,
        url=file_path,
        snippet=snippet,
        type=SourceType.DOCUMENT,
        metadata=metadata or {}
    )


def create_memory_source(source_id: int, title: str, memory_id: str, snippet: str,
                          metadata: Optional[Dict[str, Any]] = None) -> Source:
    """
    Función helper para crear una fuente de memoria/conocimiento.
    Args:
        source_id: ID único de la fuente
        title: Título descriptivo de la memoria
        memory_id: Identificador de la memoria en la base de datos
        snippet: Fragmento relevante de la memoria
        metadata: Metadatos adicionales (ej: fecha, workspace, etc.)
    Returns:
        Objeto Source configurado para memoria
    """
    return Source(
        id=source_id,
        title=title,
        url=f"memory://{memory_id}",
        snippet=snippet,
        type=SourceType.MEMORY,
        metadata=metadata or {}
    )


def create_note_source(source_id: int, title: str, note_id: str, snippet: str,
                       metadata: Optional[Dict[str, Any]] = None) -> Source:
    """
    Función helper para crear una fuente de nota.
    Args:
        source_id: ID único de la fuente
        title: Título de la nota
        note_id: Identificador de la nota en la base de datos
        snippet: Fragmento relevante de la nota
        metadata: Metadatos adicionales (ej: categoría, etc.)
    Returns:
        Objeto Source configurado para nota
    """
    return Source(
        id=source_id,
        title=title,
        url=f"note://{note_id}",
        snippet=snippet,
        type=SourceType.NOTE,
        metadata=metadata or {}
    )


# Constantes para el sistema de prompts
CITATION_SYSTEM_PROMPT = """
Cuando uses información de las fuentes proporcionadas, SIEMPRE cita la fuente usando el formato [número] al final de la oración o párrafo que use esa información.

Ejemplo:
- "La inteligencia artificial está transformando la industria [1]."
- "Según estudios recientes, el 85% de las empresas planean adoptar IA en los próximos dos años [2] [3]."

MUY IMPORTANTE: El formato de la cita debe ser EXCLUSIVAMENTE el número de la fuente entre corchetes. NUNCA incluyas palabras como "Fuente", "Ref", "Cita" o cualquier otro texto dentro de los corchetes.

INCORRECTO: [Fuente 1], [Ref. 2], [Cita 3]
CORRECTO: [1], [2], [3]

Reglas para las citas:
1. Usa SOLO los números de fuente proporcionados en el contexto, y sin ninguna palabra adicional dentro de los corchetes.
2. Coloca las citas al final de las oraciones que usen esa información
3. Si usas información de múltiples fuentes en una oración, incluye todas las citas por separado. Por ejemplo, en lugar de `[1, 2, 3]`, debes usar `[1] [2] [3]`.
4. NO inventes números de citas que no correspondan a las fuentes proporcionadas
5. Sé preciso: solo cita las fuentes que realmente usaste para esa información específica
"""

CONTEXT_TEMPLATE = """
Contexto de fuentes disponibles:
{context}

{citation_instructions}
"""