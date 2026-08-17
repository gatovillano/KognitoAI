"""
Esquemas Pydantic para salidas estructuradas del LLM en AnthropologicalGraphProcessor.
Permiten extracción exhaustiva con codificación 1:N (un Código atómico agrupa Múltiples Citas)
y posterior estructuración de Códigos en Categorías superiores.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class AnthropologicalQuoteItem(BaseModel):
    """Esquema para una cita textual asignada a un único código atómico."""
    text: str = Field(..., description="Cita textual exacta del corpus o transcripción etnográfica")
    code: str = Field(..., description="Nombre del código atómico y conciso al que pertenece esta cita")
    code_explanation: str = Field(..., description="Justificación de la asignación del código a la luz del marco teórico, pregunta de investigación o hipótesis")
    analytical_level: Literal["emic", "etic", "teorico", "empirico"] = Field(
        default="emic", 
        description="Nivel analítico de la cita (emic: perspectiva local/actor, etic: analítico, teórico, empírico)"
    )
    relevance: Literal["alta", "media", "baja", "fundamental"] = Field(default="alta", description="Relevancia cualitativa de la cita")


class AnthropologicalExhaustiveExtractionOutput(BaseModel):
    """Esquema para la extracción exhaustiva de citas y su clasificación en códigos atómicos (1:N)."""
    quotes: List[AnthropologicalQuoteItem] = Field(
        default_factory=list, 
        description="Lista exhaustiva de citas extraídas clasificadas en códigos atómicos"
    )


class CategoryGroupingItem(BaseModel):
    """Esquema para agrupar códigos atómicos en una categoría analítica superior con un desarrollo denso, riguroso y teóricamente articulado."""
    category_name: str = Field(..., description="Nombre de la categoría analítica superior (en formato conceptual conciso y relevante)")
    codes: List[str] = Field(..., description="Lista de nombres exactos de los códigos atómicos pertenecientes a esta categoría")
    category_description: str = Field(
        ...,
        description=(
            "Desarrollo teórico-analítico exhaustivo, denso y profundo de la categoría (estilo perfil de ideas centrales). "
            "Debe articular con rigor académico los conceptos teóricos que sintetizan los códigos, explicitar los mecanismos y dinámicas "
            "socio-culturales o estructurales observados en el campo, analizar las tensiones/ambivalencias emic-etic y detallar el significado "
            "antropológico subyacente del fenómeno."
        )
    )
    theoretical_connection: str = Field(
        ...,
        description=(
            "Fundamentación y discusión teórica profunda: elabora cómo la categoría dialoga con los postulados, autores y paradigmas "
            "del marco teórico de referencia, cómo responde directamente a la pregunta de investigación y de qué manera operacionaliza "
            "o pone a prueba la hipótesis de trabajo."
        )
    )


class AnthropologicalGroupingOutput(BaseModel):
    """Esquema para la estructuración de categorías superiores a partir de los códigos."""
    categories: List[CategoryGroupingItem] = Field(
        default_factory=list, 
        description="Lista de categorías superiores que agrupan los códigos atómicos"
    )


class CodeConsolidationItem(BaseModel):
    """Esquema para unificar códigos atómicos similares en un código canónico contenedor (1:N)."""
    canonical_code: str = Field(..., description="Nombre del código atómico canónico unificado")
    description: str = Field(..., description="Descripción sintética del significado del código canónico")
    merged_codes: List[str] = Field(default_factory=list, description="Lista de nombres exactos de códigos creados preliminarmente que se unifican bajo este código canónico")


class AnthropologicalCodeConsolidationOutput(BaseModel):
    """Esquema para la consolidación de códigos atómicos en taxonomías compactas y reutilizables."""
    consolidated_codes: List[CodeConsolidationItem] = Field(
        default_factory=list,
        description="Lista de códigos canónicos unificados que agrupan múltiples citas"
    )
