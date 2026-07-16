# utils/advanced_code_analyzer.py

import logging
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
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
class CodeStructureItem(BaseModel):
    component: str = Field(description="Nombre del componente o módulo analizado.")
    description: str = Field(description="Descripción de las responsabilidades y funciones del componente.")

class DesignPatternItem(BaseModel):
    pattern: str = Field(description="Nombre del patrón de diseño identificado (ej. Singleton, Factory, Repository, etc.).")
    description: str = Field(description="Cómo se aplica este patrón en el código y en qué archivos/clases.")

class DependencyItem(BaseModel):
    library: str = Field(description="Nombre de la biblioteca, package o dependencia externa.")
    description: str = Field(description="Propósito e integración de esta dependencia en el proyecto.")

class SecurityAnalysisItem(BaseModel):
    vulnerability: str = Field(description="Descripción breve de la vulnerabilidad o riesgo de seguridad.")
    description: str = Field(description="Detalles del riesgo, archivos afectados y posible impacto.")
    severity: str = Field(description="Nivel de severidad: 'Critical', 'High', 'Medium', 'Low'.")

class PerformanceAnalysisItem(BaseModel):
    area: str = Field(description="Área de rendimiento afectada (ej. Database, CPU, Memoria, Red).")
    issue: str = Field(description="Descripción del problema de rendimiento u cuello de botella.")
    suggestion: str = Field(description="Recomendación técnica específica para optimizar el rendimiento.")

class RefactoringOpportunityItem(BaseModel):
    concept: str = Field(description="Concepto o parte del código a refactorizar.")
    description: str = Field(description="Descripción detallada de la oportunidad de refactorización y qué cambiar.")
    benefit: str = Field(description="Beneficio esperado (ej. Reducción de complejidad, SoC, testeabilidad).")

class DocumentationHealthItem(BaseModel):
    item: str = Field(description="Aspecto de documentación evaluado (ej. Docstrings, README, API Docs).")
    status: str = Field(description="Estado de salud: 'Good', 'Needs Improvement', 'Missing'.")
    recommendation: str = Field(description="Sugerencia específica para mejorar la documentación de este aspecto.")

class PotentialIssueItem(BaseModel):
    issue: str = Field(description="Descripción corta del problema potencial de arquitectura o bugs latentes.")
    description: str = Field(description="Detalles del problema, causas raíz y consecuencias si no se corrige.")

class RecommendationItem(BaseModel):
    recommendation: str = Field(description="Recomendación técnica general para mejorar el código.")
    rationale: str = Field(description="Justificación técnica de por qué se debe implementar esta recomendación.")
    application: str = Field(description="Dónde o cómo se debe aplicar en el proyecto.")
    implementation: str = Field(description="Ejemplo breve o guía de implementación (puede ser un fragmento de código).")

class CodeAnalysisResult(BaseModel):
    """Modelo de datos para el resultado del análisis de un fragmento de código."""
    executive_summary: str = ""
    code_structure: List[CodeStructureItem] = []
    design_patterns: List[DesignPatternItem] = []
    dependencies: List[DependencyItem] = []
    security_analysis: List[SecurityAnalysisItem] = []
    performance_analysis: List[PerformanceAnalysisItem] = []
    refactoring_opportunities: List[RefactoringOpportunityItem] = []
    documentation_health: List[DocumentationHealthItem] = []
    potential_issues: List[PotentialIssueItem] = []
    recommendations: List[RecommendationItem] = []

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
        
        parser = JsonOutputParser(pydantic_object=CodeAnalysisResult)
        format_instructions = parser.get_format_instructions()
        
        prompt = ChatPromptTemplate.from_template(
            "Eres un experto en arquitectura. Analiza el código y responde en JSON.\n"
            "FOCO: {analysis_type}\n\n"
            "Instrucciones sobre campos:\n"
            "- executive_summary: debe describir la aplicación (qué es, qué funcionalidades ofrece, "
            "cómo está organizada su arquitectura y qué decisiones técnicas globales se observan). "
            "No describas el proceso de análisis. No menciones cantidad de archivos, chunks, partes del repositorio, "
            "ni frases meta como 'analisis completo de...'.\n"
            "Focalízate principalmente en generar información relevante para el foco '{analysis_type}'. "
            "Las llaves no deseadas o irrelevantes pueden dejarse vacías (ej: listas vacías [] o strings vacíos '').\n\n"
            "Instrucciones de formato JSON:\n{format_instructions}\n\n"
            "Código:\n{code_content}"
        )
        chain = prompt | llm | parser
        
        result = await chain.ainvoke({
            "analysis_type": analysis_type.upper(),
            "format_instructions": format_instructions,
            "code_content": code_content
        })
        final_result = CodeAnalysisResult(**result) if isinstance(result, dict) else result
        final_result.executive_summary = _normalize_executive_summary(final_result.executive_summary)
        return final_result
        
    except Exception as e:
        logger.error(f"Error en análisis: {e}", exc_info=True)
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

        module_instructions = f"Analiza el código enfocado en {module_type}. Genera información en formato JSON para las llaves: {sections}."
        if module_type == "structure_and_summary":
            module_instructions += (
                " La llave executive_summary debe ser una descripción funcional de la aplicación, incluyendo su propósito, "
                "funcionalidades principales, arquitectura general y decisiones técnicas visibles en el código. "
                "No describas el proceso de análisis y no menciones cantidad de archivos, chunks o partes del repositorio."
            )
        else:
            module_instructions += " Deja las llaves no deseadas o irrelevantes vacías (ej: listas vacías [])."

        parser = JsonOutputParser(pydantic_object=CodeAnalysisResult)
        format_instructions = parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_template(
            "Eres un experto en arquitectura y desarrollo de software.\n"
            "{module_instructions}\n\n"
            "Instrucciones de formato JSON:\n{format_instructions}\n\n"
            "Código:\n{code_content}"
        )
        chain = prompt | llm | parser
        res = await chain.ainvoke({
            "module_instructions": module_instructions,
            "format_instructions": format_instructions,
            "code_content": code_content
        })
        
        # Filtramos solo lo que viene en el diccionario y creamos la instancia
        if isinstance(res, dict):
            final_data = {field: res.get(field, "" if field == "executive_summary" else []) for field in CodeAnalysisResult.model_fields}
            final_data["executive_summary"] = _normalize_executive_summary(final_data["executive_summary"])
            return CodeAnalysisResult(**final_data)
        return CodeAnalysisResult()
    except Exception as e:
        logger.error(f"Error en _analyze_module ({module_type}): {e}", exc_info=True)
        return CodeAnalysisResult()

