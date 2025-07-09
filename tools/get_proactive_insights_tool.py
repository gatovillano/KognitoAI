# tools/get_proactive_insights_tool.py

"""
Herramienta de LangChain para recuperar y mostrar los insights proactivos generados por el sistema
de vinculación de conocimiento para una cuenta de usuario.

Esta herramienta permite al agente de IA acceder a los resultados almacenados por el
'proactive_knowledge_linker_tool' y presentarlos en el contexto de un chat, proporcionando
información sobre conexiones, sinergias, duplicidades, contradicciones y brechas de conocimiento.
"""

import logging
from typing import Type, Any, List, Dict, Optional
from pydantic import BaseModel, Field
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
    El account_id se obtiene automáticamente del contexto de la sesión.
    """
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

    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")
    workspace_id: str = Field(default="", description="ID del workspace asociado a esta herramienta.")

    def __init__(self, account_id: str = "", workspace_id: str = "", **kwargs):
        """Inicializa la herramienta con cualquier configuración necesaria."""
        super().__init__(**kwargs)
        self.account_id = account_id
        self.workspace_id = workspace_id
        logger.info("Inicializando GetProactiveInsightsTool")

    async def _arun(self, limit: int = 5, run_manager: Optional[Any] = None, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            limit: El número máximo de insights a recuperar (por defecto 5).
            run_manager: Gestor de ejecución para obtener configuración.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto con los insights proactivos formateados o un mensaje indicando que no hay insights.
        """
        # Obtener account_id del contexto de configuración o instancia
        account_id = None
        account_id_source = "unknown"

        # Intentar obtener del contexto del run_manager
        if run_manager and hasattr(run_manager, 'config'):
            config = getattr(run_manager, 'config', {})
            configurable = config.get('configurable', {})
            account_id = configurable.get('account_id')
            if account_id:
                account_id_source = "run_manager.config.configurable"

        # Fallback: obtener de la instancia
        if not account_id:
            account_id = getattr(self, 'account_id', "")
            if account_id:
                account_id_source = "self.account_id"

        # Debug logging
        logger.info(f"[DEBUG] GetProactiveInsightsTool account_id debug:")
        logger.info(f"[DEBUG]   - run_manager: {run_manager}")
        logger.info(f"[DEBUG]   - run_manager.config: {getattr(run_manager, 'config', None) if run_manager else None}")
        logger.info(f"[DEBUG]   - self.account_id: {getattr(self, 'account_id', 'NOT_SET')}")
        logger.info(f"[DEBUG]   - account_id obtenido: {account_id}")
        logger.info(f"[DEBUG]   - fuente: {account_id_source}")

        # Validar que tenemos account_id
        if not account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

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
                        # Extraer la lista de items del objeto related_items
                        # related_items puede ser un dict con estructura {"items": [...], "tool_used": "...", ...}
                        # o directamente una lista (para compatibilidad con datos antiguos)
                        if isinstance(insight.related_items, dict) and "items" in insight.related_items:
                            related_items_list = insight.related_items["items"]
                        elif isinstance(insight.related_items, list):
                            related_items_list = insight.related_items
                        else:
                            # Si no es ni dict ni list, convertir a lista
                            related_items_list = list(insight.related_items) if insight.related_items else []

                        for item in related_items_list[:2]:  # Limitar a 2 para no sobrecargar el chat
                            # Verificar que item sea un diccionario antes de usar .get()
                            if isinstance(item, dict):
                                item_title = item.get('title', 'Sin título')
                                item_type = item.get('type', 'N/A')
                                response_lines.append(f"     - {item_type}: {item_title}")
                            else:
                                # Si item no es un diccionario, mostrarlo como string
                                response_lines.append(f"     - {str(item)}")
                        if len(related_items_list) > 2:
                            response_lines.append(f"     - y {len(related_items_list) - 2} más...")

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
