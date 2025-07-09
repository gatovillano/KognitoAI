# tools/set_reminder_tool.py

"""
Herramienta de LangChain para establecer recordatorios rápidos y simples para un usuario.

Esta herramienta está diseñada para manejar solicitudes de recordatorios con un
tiempo relativo o simple, como "en 20 minutos" o "a las 10pm". Se diferencia de
`schedule_event_tool` en que es para tareas más inmediatas o menos formales
que no necesariamente forman parte de una "agenda" de eventos complejos.

Al igual que el resto de herramientas de la arquitectura, utiliza el `account_id`
universal del usuario, permitiendo que la funcionalidad sea consistente a través
de cualquier interfaz.
"""

import logging
from typing import Type, Any

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de recordatorios.
from core.reminders_manager import set_simple_reminder

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

class SetReminderInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de recordatorios simples.
    Valida que todos los argumentos necesarios sean proporcionados por el LLM.
    """
    text: str = Field(
        ...,
        description="El texto o la acción específica que se debe recordar."
    )
    natural_language_time: str = Field(
        ...,
        description="Una descripción relativa o absoluta del tiempo para el recordatorio. Ejemplos: 'en 20 minutos', 'dentro de 3 horas', 'a las 10pm'."
    )
    # Cambiamos telegram_id por account_id para que sea universal.

    telegram_id: int = Field(
        ...,
        description="El ID numérico de Telegram del usuario. Es necesario para enviar el recordatorio."
    )

class SetReminderTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `set_simple_reminder`
    para programar un recordatorio rápido para el usuario.
    """
    name: str = "set_reminder_tool"
    description: str = (
        "Útil para cuando un usuario pide que le recuerdes algo en un marco de tiempo específico y simple. "
        "Es ideal para frases como 'recuérdame en 20 minutos que saque la basura' o 'avísame en 1 hora para llamar a Juan'. "
        "No uses esta herramienta para eventos complejos o citas con fechas lejanas; para eso usa `schedule_event_tool`."
    )
    args_schema: Type[BaseModel] = SetReminderInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, text: str, natural_language_time: str, run_manager = None, **kwargs) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            text: El contenido del recordatorio.
            natural_language_time: El texto con la descripción del tiempo.
            account_id: El ID universal de la cuenta del usuario.
            telegram_id: El ID de Telegram para programar la notificación.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto indicando el resultado de la operación.
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

        # Validar que tenemos account_id
        if not account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        # Obtener telegram_id de kwargs si está disponible
        telegram_id = kwargs.get('telegram_id', None)

        logger.info(f"Ejecutando SetReminderTool para la cuenta '{account_id}' con texto: '{text}'")
        try:
            # ¡CORREGIDO! Pasamos el `telegram_id` que ahora requiere la función.
            success, message = await set_simple_reminder(
                account_id=account_id,
                telegram_id=telegram_id,
                text=text,
                natural_language_time=natural_language_time
            )
            logger.info(f"Herramienta de recordatorio simple completada para la cuenta '{account_id}'. Mensaje: {message}")
            return message
        except Exception as e:
            logger.error(f"Error en SetReminderTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar programar tu recordatorio: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("set_reminder_tool no soporta ejecución síncrona.")