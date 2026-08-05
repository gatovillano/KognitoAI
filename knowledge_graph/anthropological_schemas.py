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
    """Esquema para agrupar códigos atómicos en una categoría analítica superior."""
    category_name: str = Field(..., description="Nombre de la categoría analítica superior")
    codes: List[str] = Field(..., description="Lista de nombres exactos de los códigos atómicos pertenecientes a esta categoría")
    category_description: str = Field(..., description="Descripción detallada de la categoría y su relevancia cualitativa")
    theoretical_connection: str = Field(..., description="Explicación de cómo esta categoría dialoga con el marco teórico o responde a la pregunta de investigación/hipótesis")


class AnthropologicalGroupingOutput(BaseModel):
    """Esquema para la estructuración de categorías superiores a partir de los códigos."""
    categories: List[CategoryGroupingItem] = Field(
        default_factory=list, 
        description="Lista de categorías superiores que agrupan los códigos atómicos"
    )
