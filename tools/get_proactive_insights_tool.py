# tools/get_proactive_insights_tool.py

"""
Herramienta de LangChain para recuperar y mostrar los insights proactivos generados por el sistema
de vinculación de conocimiento para una cuenta de usuario.

Esta herramienta permite al agente de IA acceder a los resultados almacenados por el
'proactive_knowledge_linker_tool' y presentarlos en el contexto de un chat, proporcionando
información sobre conexiones, sinergias, duplicidades, contradicciones y brechas de conocimiento.
"""

import logging
from typing import Type, Any, List, Dict
from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import select
from core.database import ProactiveInsight, SessionLocal
from utils.db_session import DBSession
import uuid
import datetime

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)




class GetProactiveInsightsInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de recuperación de insights proactivos.
    Valida que el argumento necesario sea proporcionado por el LLM.
    """
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    limit: int = Field(
        5,
        description="El número máximo de insights a recuperar. Por defecto es 5."
    )


class GetProactiveInsightsTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la base de datos para recuperar los insights
    proactivos asociados a una cuenta de usuario y los formatea para su visualización en un chat.
    """
    name: str = "get_proactive_insights_tool"
    description: str = (
        "Útil para recuperar y mostrar los insights proactivos generados por el sistema de vinculación "
        "de conocimiento para el usuario. Estos insights incluyen conexiones, sinergias, duplicidades, "
        "contradicciones y brechas de conocimiento basadas en la información del usuario."
    )
    args_schema: Type[BaseModel] = GetProactiveInsightsInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    def __init__(self, **kwargs):
        """Inicializa la herramienta con cualquier configuración necesaria."""
        super().__init__(**kwargs)
        logger.info("Inicializando GetProactiveInsightsTool")

    async def _arun(self, account_id: str, limit: int = 5, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            limit: El número máximo de insights a recuperar (por defecto 5).
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto con los insights proactivos formateados o un mensaje indicando que no hay insights.
        """
        logger.info(f"Ejecutando GetProactiveInsightsTool para la cuenta '{account_id}' con límite de {limit} insights.")
        try:
            async with DBSession(SessionLocal) as db:
                account_uuid = uuid.UUID(account_id)
                stmt = (
                    select(ProactiveInsight)
                    .where(ProactiveInsight.account_id == account_uuid)
                    .order_by(ProactiveInsight.created_at.desc())
                    .limit(limit)
                )
                result = await db.execute(stmt)
                insights = result.scalars().all()

                if not insights:
                    logger.info(f"No se encontraron insights para la cuenta '{account_id}'.")
                    return "No se encontraron insights proactivos en tu base de conocimiento. ¡A medida que añadas más información, generaré conexiones y sugerencias!"

                response_lines = ["Aquí están los insights proactivos más recientes generados a partir de tu información:"]
                for idx, insight in enumerate(insights, 1):
                    response_lines.append(f"\n{idx}. **{insight.type.upper()}** (Confianza: {insight.confidence_score:.2f}) - {insight.created_at.strftime('%Y-%m-%d %H:%M')}")
                    response_lines.append(f"   - **Insight**: {insight.insight_message}")
                    if insight.action_suggestion:
                        response_lines.append(f"   - **Sugerencia**: {insight.action_suggestion}")
                    if insight.related_items:
                        response_lines.append("   - **Elementos Relacionados**:")
                        for item in insight.related_items[:2]:  # Limitar a 2 para no sobrecargar el chat
                            item_title = item.get('title', 'Sin título')
                            item_type = item.get('type', 'N/A')
                            response_lines.append(f"     - {item_type}: {item_title}")
                        if len(insight.related_items) > 2:
                            response_lines.append(f"     - y {len(insight.related_items) - 2} más...")

                if len(insights) == limit:
                    response_lines.append(f"\n(Mostrando los {limit} más recientes. Si deseas ver más, puedo buscarlos.)")

                logger.info(f"Recuperados {len(insights)} insights para la cuenta '{account_id}'.")
                return "\n".join(response_lines)
        except Exception as e:
            logger.error(f"Error en GetProactiveInsightsTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar recuperar tus insights proactivos: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("get_proactive_insights_tool no soporta ejecución síncrona.")
