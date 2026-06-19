"""
Pydantic schemas for structured LLM outputs in ConceptualGraphProcessor.
These replace manual JSON parsing with type-safe structured output.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ConceptualQuote(BaseModel):
    """Schema for a single conceptual quote extracted by LLM."""
    text: str = Field(..., description="Cita exacta del texto original")
    concept: str = Field(..., description="Concepto principal que expresa la cita")
    importance: Literal["alta", "media"] = Field(default="media", description="Importancia de la cita")
    category: Literal[
        "teoría", "metodología", "conclusión", "definición",
        "definición_conceptual", "enfoque_metodológico", "marco_teórico",
        "hallazgo_empírico", "ejemplo_práctico", "análisis_crítico", "desarrollo_teórico"
    ] = Field(default="general", description="Categoría conceptual de la cita")


class QuotesExtractionOutput(BaseModel):
    """Schema for the complete quotes extraction response."""
    quotes: List[ConceptualQuote] = Field(default_factory=list, description="Lista de citas conceptuales extraídas")


class ThematicRelationshipOutput(BaseModel):
    """Schema for a single thematic relationship between two quotes."""
    type: Literal[
        "CONCEPTOS_RELACIONADOS", "MARCOS_TEORICOS_AFINES", "ENFOQUES_METODOLOGICOS",
        "HALLAZGOS_CONVERGENTES", "FUNDAMENTACION_TEORICA", "APLICACION_METODOLOGICA",
        "VALIDACION_EMPIRICA", "CONFIRMACION_CONCEPTUAL", "ALTA_CONVERGENCIA_TEMATICA",
        "CONVERGENCIA_TEMATICA", "RELACION_TEMATICA"
    ] = Field(..., description="Tipo de relación temática")
    description: str = Field(..., description="Descripción detallada de la relación")
    confidence: Literal["alta", "media", "baja"] = Field(default="media", description="Nivel de confianza")


class CentralConceptOutput(BaseModel):
    """Schema for central concept identification."""
    concept: str = Field(..., description="Concepto central altamente granular y específico")


class ProfileDescriptionOutput(BaseModel):
    """Schema for idea profile description generation."""
    description: str = Field(..., description="Descripción detallada y completa del perfil de ideas")