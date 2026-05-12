# utils/advanced_code_analyzer.py

import logging
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from langchain_core.language_models import LLM
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.llm_manager import get_fast_llm, get_llm_for_user

logger = logging.getLogger(__name__)

META_SUMMARY_MARKERS = (
    "analisis completo de",
    "análisis completo de",
    "archivos en",
    "partes del repositorio",
    "chunks del repositorio",
    "codigo analizado",
    "código analizado",
    "repositorio analizado",
)


def _is_meta_executive_summary(summary: str) -> bool:
    """Detecta resúmenes que describen el proceso de análisis en vez de la aplicación."""
    normalized = (summary or "").strip().lower()
    return any(marker in normalized for marker in META_SUMMARY_MARKERS)


def _normalize_executive_summary(summary: str) -> str:
    """Descarta resúmenes meta para forzar una síntesis funcional de la aplicación."""
    if not summary:
        return ""
    return "" if _is_meta_executive_summary(summary) else summary.strip()

# Modelos de datos para los resultados del análisis
class CodeAnalysisResult(BaseModel):
    """Modelo de datos para el resultado del análisis de un fragmento de código."""
    executive_summary: str = ""
    code_structure: List[Dict[str, Any]] = []
    design_patterns: List[Dict[str, Any]] = []
    dependencies: List[Dict[str, Any]] = []
    security_analysis: List[Dict[str, Any]] = []
    performance_analysis: List[Dict[str, Any]] = []
    refactoring_opportunities: List[Dict[str, Any]] = []
    documentation_health: List[Dict[str, Any]] = []
    potential_issues: List[Dict[str, Any]] = []
    recommendations: List[Dict[str, Any]] = []

async def analyze_code_content(
    code_content: str, 
    account_id: Optional[str] = None, 
    analysis_type: str = "all"
) -> CodeAnalysisResult:
    """Analiza un fragmento de código o contenido de repositorio.
    
    Args:
        code_content: El contenido del código a analizar.
        account_id: ID de cuenta del usuario.
        analysis_type: Tipo de análisis: 'all', 'security', 'performance', 'refactoring', 'documentation', 'structure'.
    """
    logger.info(f"Iniciando análisis avanzado de código (tipo={analysis_type})...")
    # Si es 'all', ejecutamos análisis modulares en paralelo para mayor velocidad
    if analysis_type == "all":
        logger.info("Ejecutando análisis modular en paralelo para optimizar el tiempo de respuesta...")
        
        tasks = [
            _analyze_module(code_content, "structure_and_summary", account_id),
            _analyze_module(code_content, "security_and_issues", account_id),
            _analyze_module(code_content, "performance_and_refactoring", account_id),
            _analyze_module(code_content, "documentation_and_recommendations", account_id)
        ]
        
        try:
            results = await asyncio.gather(*tasks)
            combined_result = CodeAnalysisResult()
            for res in results:
                if res.executive_summary: combined_result.executive_summary = res.executive_summary
                if res.code_structure: combined_result.code_structure.extend(res.code_structure)
                if res.design_patterns: combined_result.design_patterns.extend(res.design_patterns)
                if res.dependencies: combined_result.dependencies.extend(res.dependencies)
                if res.security_analysis: combined_result.security_analysis.extend(res.security_analysis)
                if res.performance_analysis: combined_result.performance_analysis.extend(res.performance_analysis)
                if res.refactoring_opportunities: combined_result.refactoring_opportunities.extend(res.refactoring_opportunities)
                if res.documentation_health: combined_result.documentation_health.extend(res.documentation_health)
                if res.potential_issues: combined_result.potential_issues.extend(res.potential_issues)
                if res.recommendations: combined_result.recommendations.extend(res.recommendations)
            
            logger.info("Análisis paralelo completado exitosamente.")
            return combined_result
        except Exception as e:
            logger.error(f"Error en análisis paralelo, reintentando modo secuencial: {e}")
            # Fallback al modo secuencial original si falla el paralelo

    # MODO ORIGINAL (Secuencial / Específico)
    try:
        # Obtener el LLM configurado por el usuario si tenemos account_id
        if account_id:
            llm = await get_llm_for_user(account_id, purpose="fast")
        else:
            llm = get_fast_llm()

        if not llm:
            raise ValueError("No se puede realizar el análisis de código sin un modelo de lenguaje.")
        
        # Validar que hay contenido de código
        if not code_content or code_content.strip() == "":
            logger.warning("No se proporcionó contenido de código para analizar.")
            return CodeAnalysisResult(
                executive_summary="No se proporcionó contenido de código para analizar.",
                potential_issues=[{"issue": "Sin código", "description": "No se proporcionó código para analizar."}]
            )
        
        # Definir las secciones del prompt basadas en el tipo de análisis
        sections_desc = ""
        if analysis_type == "all" or analysis_type == "structure":
            sections_desc += """
- executive_summary: (string) Un resumen ejecutivo detallado que proporcione una visión global del código analizado. Debe incluir: 1) Una definición clara de la aplicación (qué es y qué problema resuelve). 2) Una descripción de sus funcionalidades principales. 3) Una reseña de sus características generales de diseño (estilo arquitectónico, patrones globales, etc.). 4) Un análisis técnico específico y profundo de ESTE código.
- code_structure: Lista de objetos {component: string, description: string}
- design_patterns: Lista de objetos {pattern: string, description: string}
- dependencies: Lista de objetos {library: string, description: string}
"""
        
        if analysis_type == "all" or analysis_type == "security":
            sections_desc += """
- security_analysis: Lista de objetos {vulnerability: string, description: string, severity: string}
"""

        if analysis_type == "all" or analysis_type == "performance":
            sections_desc += """
- performance_analysis: Lista de objetos {area: string, issue: string, suggestion: string}
"""

        if analysis_type == "all" or analysis_type == "refactoring":
            sections_desc += """
- refactoring_opportunities: Lista de objetos {concept: string, description: string, benefit: string}
"""

        if analysis_type == "all" or analysis_type == "documentation":
            sections_desc += """
- documentation_health: Lista de objetos {item: string, status: string, recommendation: string}
"""

        if analysis_type == "all":
            sections_desc += """
- potential_issues: Lista de objetos {issue: string, description: string}
- recommendations: Lista de objetos {recommendation: string, rationale: string, application: string, implementation: string}
"""

        prompt_text = f"""Eres un experto en arquitectura. Analiza el código y responde en JSON.
FOCO: {analysis_type.upper()}

    Si devuelves executive_summary, debe describir la aplicacion: que es, que funcionalidades ofrece,
    como esta organizada su arquitectura y que decisiones tecnicas globales se observan.
    No describas el proceso de analisis. No menciones cantidad de archivos, chunks, partes del repositorio,
    ni frases meta como 'analisis completo de...'.

Código:
{{code_content}}

JSON keys:
{sections_desc}
"""
        prompt = ChatPromptTemplate.from_template(prompt_text)
        parser = JsonOutputParser(pydantic_object=CodeAnalysisResult)
        chain = prompt | llm | parser
        
        result = await chain.ainvoke({"code_content": code_content})
        final_result = CodeAnalysisResult(**result) if isinstance(result, dict) else result
        final_result.executive_summary = _normalize_executive_summary(final_result.executive_summary)
        return final_result
        
    except Exception as e:
        logger.error(f"Error en análisis: {e}")
        return CodeAnalysisResult(
            executive_summary="Error al analizar el código.",
            potential_issues=[{"issue": "Error de análisis", "description": str(e)}]
        )

async def _analyze_module(code_content: str, module_type: str, account_id: Optional[str]) -> CodeAnalysisResult:
    """Helper para análisis modular paralelo."""
    try:
        llm = await get_llm_for_user(account_id, purpose="fast") if account_id else get_fast_llm()
        
        sections = ""
        if "structure" in module_type:
            sections = "- executive_summary, - code_structure, - design_patterns, - dependencies"
        elif "security" in module_type:
            sections = "- security_analysis, - potential_issues"
        elif "performance" in module_type:
            sections = "- performance_analysis, - refactoring_opportunities"
        elif "documentation" in module_type:
            sections = "- documentation_health, - recommendations"

        module_instructions = f"Analiza el código enfocado en {module_type}. Responde JSON con llaves: {sections}."
        if module_type == "structure_and_summary":
            module_instructions += (
                " executive_summary debe ser una descripcion de la aplicacion, incluyendo su proposito, "
                "funcionalidades principales, arquitectura general y decisiones tecnicas visibles en el codigo. "
                "No describas el proceso de analisis y no menciones cantidad de archivos, chunks o partes del repositorio."
            )

        prompt = ChatPromptTemplate.from_template(
            f"{module_instructions}\n\nCódigo:\n{{code_content}}"
        )
        chain = prompt | llm | JsonOutputParser(pydantic_object=CodeAnalysisResult)
        res = await chain.ainvoke({"code_content": code_content})
        
        # Filtramos solo lo que viene en el diccionario y creamos la instancia
        if isinstance(res, dict):
            final_data = {field: res.get(field, "" if field == "executive_summary" else []) for field in CodeAnalysisResult.model_fields}
            final_data["executive_summary"] = _normalize_executive_summary(final_data["executive_summary"])
            return CodeAnalysisResult(**final_data)
        return CodeAnalysisResult()
    except Exception:
        return CodeAnalysisResult()
