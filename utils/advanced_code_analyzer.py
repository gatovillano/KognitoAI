# utils/advanced_code_analyzer.py

import logging
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from langchain_core.language_models import LLM
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.llm_manager import get_fast_llm

logger = logging.getLogger(__name__)

# Modelos de datos para los resultados del análisis
class CodeAnalysisResult(BaseModel):
    """Modelo de datos para el resultado del análisis de un fragmento de código."""
    executive_summary: str
    code_structure: List[Dict[str, Any]]
    design_patterns: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    potential_issues: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]

async def analyze_code_content(code_content: str) -> CodeAnalysisResult:
    """Analiza un fragmento de código o contenido de repositorio."""
    logger.info("Iniciando análisis avanzado de código...")
    
    try:
        # Obtener el LLM solo cuando se necesite para el análisis
        llm = get_fast_llm()
        if not llm:
            logger.error("No hay LLM disponible para realizar el análisis de código.")
            raise ValueError("No se puede realizar el análisis de código sin un modelo de lenguaje.")
        
        # Validar que hay contenido de código
        if not code_content or code_content.strip() == "":
            logger.warning("No se proporcionó contenido de código para analizar.")
            return CodeAnalysisResult(
                executive_summary="No se proporcionó contenido de código para analizar.",
                code_structure=[],
                design_patterns=[],
                dependencies=[],
                potential_issues=[{"issue": "Sin código", "description": "No se proporcionó código para analizar."}],
                recommendations=[{"recommendation": "Proporcionar código", "rationale": "Se necesita código para realizar el análisis.", "application": "Incluir el contenido del código en la solicitud.", "implementation": "Verificar que el parámetro code_content contenga código válido."}]
            )

        # Configuración de prompts para análisis de código
        code_analysis_prompt = ChatPromptTemplate.from_template(
            """Eres un experto en análisis de código y arquitectura de software. Analiza ÚNICAMENTE el siguiente fragmento de código o repositorio real y proporciona un informe detallado ESPECÍFICO para este código.

IMPORTANTE: Solo analiza el código proporcionado. NO generes un análisis genérico.

Contenido del código:
{code_content}

Proporciona un análisis estructurado en formato JSON con las siguientes secciones, cada una debe ser una lista de objetos con las propiedades especificadas:

- executive_summary: (string) Un resumen extendido y detallado específico de ESTE código.

- code_structure: Lista de objetos con propiedades:
  * component: (string) Nombre del componente (ej. "UserService class", "authenticate function")
  * description: (string) Descripción específica del componente

- design_patterns: Lista de objetos con propiedades:
  * pattern: (string) Nombre del patrón identificado
  * description: (string) Cómo se implementa en este código específico

- dependencies: Lista de objetos con propiedades:
  * library: (string) Nombre de la dependencia/biblioteca
  * description: (string) Cómo se usa en este código

- potential_issues: Lista de objetos con propiedades:
  * issue: (string) Nombre del problema
  * description: (string) Descripción específica del problema en este código

- recommendations: Lista de objetos con propiedades:
  * recommendation: (string) Recomendación específica
  * rationale: (string) Por qué es necesaria para ESTE código
  * application: (string) Dónde aplicarla en ESTE código específico
  * implementation: (string) Cómo implementarla en ESTE código

Responde solo con el objeto JSON, sin texto adicional."""
        )
        
        # Configurar el parser de salida
        parser = JsonOutputParser(pydantic_object=CodeAnalysisResult)
        
        # Preparar la cadena de procesamiento
        chain = code_analysis_prompt | llm | parser
        
        # Ejecutar el análisis
        result = await chain.ainvoke({"code_content": code_content})
        
        # Convertir el diccionario a objeto Pydantic si es necesario
        if isinstance(result, dict):
            result = CodeAnalysisResult(**result)
        
        logger.info("Análisis de código completado exitosamente.")
        return result
        
    except Exception as e:
        logger.error(f"Error durante el análisis de código: {e}", exc_info=True)
        # Retornar un resultado por defecto en caso de error
        return CodeAnalysisResult(
            executive_summary="Error al analizar el código. No se pudo generar un resumen.",
            code_structure=[],
            design_patterns=[],
            dependencies=[],
            potential_issues=[{"issue": "Error de análisis", "description": "Error en el análisis. Revise el contenido del código."}],
            recommendations=[{"recommendation": "Reintentar análisis", "rationale": "El análisis falló por un error técnico.", "application": "Verificar el código y las conexiones.", "implementation": "Intente nuevamente o contacte soporte técnico."}]
        )
