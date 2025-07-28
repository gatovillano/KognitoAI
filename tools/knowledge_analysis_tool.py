# tools/knowledge_analysis_tool.py

import logging
import asyncio
import datetime
from typing import Any, Optional, Type, Dict

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

# Importamos la función de bajo nivel que ejecuta el job.
from tools.proactive_knowledge_linker_tool import run_batch_analysis_job

logger = logging.getLogger(__name__)

# --- Singleton para el modelo de interpretación (se mantiene igual) ---
_interpreter_llm: Optional[ChatGoogleGenerativeAI] = None

async def get_interpreter_llm() -> ChatGoogleGenerativeAI:
    global _interpreter_llm
    if _interpreter_llm is None:
        logger.info("Inicializando modelo Gemini para la herramienta de análisis...")
        _interpreter_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
    return _interpreter_llm


# (CAMBIO CLAVE 1) - Añadimos `account_id` al esquema de entrada.
class KnowledgeAnalysisInput(BaseModel):
    """Esquema de entrada para la Herramienta de Análisis de Conocimiento."""
    query: str = Field(
        ...,
        description="La petición completa del usuario en lenguaje natural, por ejemplo: 'ejecuta un análisis completo de mis notas'.",
        json_schema_extra={"type": "string"}
    )


class KnowledgeAnalysisTool(BaseTool):
    name: str = "knowledge_base_analyzer"
    # (CAMBIO CLAVE 2) - Descripción más directa y con instrucciones para el LLM.
    description: str = (
        "Se utiliza para iniciar un análisis profundo de la base de conocimiento de un usuario (notas, documentos) para encontrar conexiones. "
        "Activa esta herramienta si el usuario pide 'analizar mis notas', 'buscar nuevas conexiones', o 'revisar mis documentos sobre un tema'. "
        "Tu trabajo es pasar la petición del usuario en el campo 'query'."
    )
    args_schema: Type[BaseModel] = KnowledgeAnalysisInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    return_direct: bool = False

    async def _interpret_request(self, user_query: str) -> Dict[str, Any]:
        """Usa un LLM para traducir la petición del usuario a una acción estructurada."""
        llm = await get_interpreter_llm()
        prompt = f"""
        Eres un despachador de tareas para un sistema de análisis de conocimiento. Analiza la petición del usuario y tradúcela a una de las siguientes acciones en formato JSON.

        Petición del usuario: "{user_query}"

        Acciones disponibles:
        1. `run_full_analysis`: Para peticiones generales como "analiza todo", "busca nuevas conexiones".
        2. `analyze_recent_items`: Para peticiones como "revisa lo último", "analiza mis notas de hoy".
        3. `analyze_specific_topic`: Para peticiones como "analiza mis notas sobre 'Proyecto Hydra'".

        Hoy es: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}

        Responde únicamente en formato JSON: {{"action": "...", "parameters": {{"days_ago": null, "topic_keywords": null}}}}
        """
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            import json
            import re
            
            # Extract JSON from response content if it's embedded in text
            raw_content = response.content
            
            if isinstance(raw_content, dict):
                return raw_content
            elif isinstance(raw_content, str):
                json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if json_match:
                    content_to_parse = json_match.group(0)
                else:
                    content_to_parse = raw_content
                return json.loads(content_to_parse)
            elif isinstance(raw_content, list):
                for item in raw_content:
                    if isinstance(item, dict):
                        return item
                    elif isinstance(item, str):
                        json_match = re.search(r'\{.*\}', item, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group(0))
                        else:
                            try:
                                return json.loads(item)
                            except json.JSONDecodeError:
                                continue
                raise ValueError("No se pudo encontrar un objeto JSON válido en la lista de contenido.")
            else:
                raise TypeError(f"Tipo de contenido inesperado de la respuesta del LLM: {type(raw_content)}")
        except Exception as e:
            logger.error(f"Error interpretando la petición del usuario: {e}", exc_info=True)
            return {"action": "error", "details": str(e)}

    async def _arun(
        self,
        query: str,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """
        Ejecuta la herramienta de forma asíncronas.
        1. Interpreta la petición.
        2. Llama a la función de análisis con los parámetros correctos.
        3. Devuelve un mensaje de confirmación al usuario.
        """

        # Validar que tenemos account_id (ahora se inyecta en el constructor)
        if not self.account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        logger.info(f"KnowledgeAnalysisTool activada para la cuenta {self.account_id} con la consulta: '{query}'")
        
        # 1. Interpretar la intención del usuario
        intent = await self._interpret_request(query)
        action = intent.get("action")
        params = intent.get("parameters", {})
        logger.info(f"Intención interpretada para la cuenta {self.account_id}: {intent}")

        # 2. Disparar la acción de análisis en segundo plano
        response_message = "Se ha producido un error inesperado al procesar tu solicitud."
        
        if action == "run_full_analysis":
            start_time = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            asyncio.create_task(run_batch_analysis_job(account_id_filter=self.account_id, since_timestamp=start_time))
            response_message = "¡Entendido! He iniciado un análisis completo de tu base de conocimiento en segundo plano."

        elif action == "analyze_recent_items":
            days = params.get("days_ago", 1)
            start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
            asyncio.create_task(run_batch_analysis_job(account_id_filter=self.account_id, since_timestamp=start_time))
            response_message = f"¡Claro! Estoy analizando tus notas de los últimos {days} días en segundo plano."

        elif action == "analyze_specific_topic":
            keywords = params.get("topic_keywords")
            if not keywords:
                return "No pude identificar un tema específico en tu petición."
            start_time = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            asyncio.create_task(run_batch_analysis_job(account_id_filter=self.account_id, since_timestamp=start_time, topic_keywords=keywords))
            response_message = f"¡Perfecto! He comenzado a buscar conexiones sobre '{', '.join(keywords)}' en segundo plano."
        
        return response_message

    # (CAMBIO CLAVE 4) - Adoptamos el mismo patrón de _run que tu herramienta RAG.
    def _run(self, **kwargs: Any) -> str:
        """La ejecución síncrona no está soportada para esta herramienta."""
        raise NotImplementedError("KnowledgeAnalysisTool está diseñada para ser usada de forma asíncrona.")
