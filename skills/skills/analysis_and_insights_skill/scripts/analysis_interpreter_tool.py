import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from core.llm_manager import get_main_llm

logger = logging.getLogger(__name__)

class AnalysisInterpreterInput(BaseModel):
    analysis_results: str = Field(..., description="Los resultados del análisis en formato JSON (estadísticas, predicciones, etc.)")
    user_question: Optional[str] = Field(None, description="La pregunta original del usuario para orientar la interpretación.")
    context_description: Optional[str] = Field(None, description="Descripción del contexto de los datos (ej: 'Ventas del Q3').")

class AnalysisInterpreterTool(BaseTool):
    name: str = "analysis_interpreter_tool"
    description: str = "Intérprete de Análisis de Datos. Toma resultados técnicos y estadísticos y los traduce a un lenguaje natural comprensible, extrayendo insights y conclusiones clave."
    args_schema: Type[BaseModel] = AnalysisInterpreterInput
    account_id: Optional[str] = None # Add account_id as an attribute

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("AnalysisInterpreterTool no soporta ejecución síncrona.")

    async def _create_litellm_compatible_config(
        self,
        max_iterations: int = 6,
        max_concurrent_units: int = 3
    ) -> Dict[str, Any]:
        from core.llm_manager import get_llm_for_user
        
        # Obtener los LLMs de Kognito adaptados al usuario
        if self.account_id:
            main_llm = await get_llm_for_user(self.account_id, purpose="main")
            fast_llm = await get_llm_for_user(self.account_id, purpose="fast")
        else:
            main_llm = get_main_llm()
            fast_llm = get_fast_llm()
        
        # This config structure is typically for tools that use LiteLLM directly
        # For AnalysisInterpreterTool, we primarily need the main_llm for ainvoking
        return {
            "main_llm": main_llm,
            "fast_llm": fast_llm,
            "max_iterations": max_iterations,
            "max_concurrent_units": max_concurrent_units
        }

    async def _arun(
        self,
        analysis_results: str,
        user_question: Optional[str] = None,
        context_description: Optional[str] = None,
        account_id: Optional[str] = None,
        max_iterations: int = 6, # Added for _create_litellm_compatible_config
        max_concurrent_units: int = 3, # Added for _create_litellm_compatible_config
        **kwargs
    ) -> str:
        # Store account_id for use in _create_litellm_compatible_config
        self.account_id = account_id
        
        # Create configuration using Kognito LLMs
        config = await self._create_litellm_compatible_config(
            max_iterations=max_iterations,
            max_concurrent_units=max_concurrent_units
        )
        llm = config["main_llm"] # Get the main LLM from the config

        prompt = f"""
        Eres un Analista de Datos Senior y Consultor Estratégico. 
        Tu objetivo es interpretar los siguientes resultados técnicos de un análisis de datos y presentarlos de forma clara, profesional y accionable.

        CONTEXTO DE LOS DATOS: {context_description or 'No especificado'}
        PREGUNTA DEL USUARIO: {user_question or 'Análisis general'}
        
        RESULTADOS DEL ANÁLISIS (JSON):
        {analysis_results}

        INSTRUCCIONES:
        1. **Resumen Ejecutivo**: Comienza con una conclusión principal en una sola frase.
        2. **Hallazgos Clave**: Identifica tendencias, anomalías o valores atípicos significativos.
        3. **Interpretación Estadística**: Explica qué significan los números (ej: 'La desviación estándar alta sugiere mucha volatilidad').
        4. **Predicciones (si existen)**: Comenta sobre la fiabilidad de las predicciones basadas en el R-cuadrado u otras métricas.
        5. **Recomendaciones**: Sugiere próximos pasos basados en los datos.
        6. **Tono**: Mantén un tono profesional, objetivo pero cercano.
        7. **Formato**: Usa Markdown para una presentación impecable (negritas, listas, tablas si es necesario).

        Interpretación:
        """

        try:
            response = await llm.ainvoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error en AnalysisInterpreterTool: {e}", exc_info=True)
            return f"Error al interpretar los resultados: {str(e)}"
