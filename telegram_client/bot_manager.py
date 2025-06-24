# telegram_bot/bot_manager.py

"""
Módulo del Gestor del Bot (Singleton).

Este módulo implementa un patrón Singleton para proporcionar un acceso global
y seguro a la instancia de la `Application` de `python-telegram-bot`.

En nuestra arquitectura desacoplada, diferentes partes del sistema (como los
`managers` que programan recordatorios) necesitan interactuar con componentes
específicos de la aplicación de Telegram, como la `JobQueue` o el propio `bot`
para enviar mensajes.

El `BotManager` actúa como un "mando a distancia" centralizado para estas
operaciones, asegurando que solo haya una instancia de la aplicación y que
sea accesible de manera consistente desde cualquier módulo que la necesite,
sin tener que pasar la instancia `application` como argumento a través de
múltiples capas de funciones.

Flujo de uso:
1.  En `main.py`, después de crear la `Application`, se llama a `bot_manager.initialize(application)`.
2.  En cualquier otro módulo, se puede importar `bot_manager` y acceder a sus
    propiedades (`bot_manager.bot`, `bot_manager.job_queue`, etc.).
"""

import logging
from typing import Any, Dict, Optional

from telegram.ext import Application, ExtBot
from telegram.ext import JobQueue  # <-- add this import

logger = logging.getLogger(__name__)


class BotManager:
    """
    Implementa un patrón Singleton para proporcionar acceso global a la instancia
    de la `Application` de `python-telegram-bot`.
    """
    _instance = None
    _application: Optional[Application] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotManager, cls).__new__(cls)
        return cls._instance

    def initialize(self, application: Application) -> None:
        """
        Inicializa el BotManager con la instancia de la aplicación.
        Este método debe ser llamado una sola vez al arrancar el bot.
        """
        if self._application is None:
            self._application = application
            logger.info("✅ BotManager inicializado con la aplicación de Telegram.")
        else:
            logger.warning("BotManager ya ha sido inicializado.")

    # ¡NUEVO MÉTODO!
    def is_initialized(self) -> bool:
        """
        Comprueba si el BotManager ha sido inicializado.

        Returns:
            True si la aplicación ha sido establecida, False en caso contrario.
        """
        return self._application is not None

    @property
    def application(self) -> Application:
        """
        Propiedad para acceder a la instancia completa de la aplicación.
        """
        if self._application is None:
            raise RuntimeError("BotManager no ha sido inicializado. Llama a `initialize()` primero.")
        return self._application

    @property
    def bot(self) -> Optional[ExtBot]:
        """
        Propiedad de conveniencia para acceder directamente al objeto `bot`.
        """
        if not self.is_initialized():
            logger.warning("No se puede acceder al bot: BotManager no ha sido inicializado.")
            return None
            
        return self.application.bot

    @property
    def job_queue(self) -> Optional[JobQueue]:
        """
        Propiedad de conveniencia para acceder directamente al objeto `job_queue`.
        """
        if not self.is_initialized():
            logger.warning("No se puede acceder a job_queue: BotManager no ha sido inicializado.")
            return None
            
        if self.application.job_queue is None:
            logger.error("La JobQueue no está disponible. Asegúrate de que no esté deshabilitada en la configuración.")
            return None
            
        return self.application.job_queue

    def get_user_data(self, user_id: int) -> Dict[Any, Any]:
        """
        Obtiene el `user_data` para un ID de usuario específico.
        """
        if not self.is_initialized():
            logger.warning(f"No se puede obtener user_data para {user_id}: BotManager no ha sido inicializado.")
            return {}
            
        return self.application.user_data.get(user_id, {})
    
    async def flush_persistence(self) -> None:
        """
        Fuerza el guardado de todos los datos de persistencia en el disco.
        """
        if not self.is_initialized():
            logger.warning("No se puede guardar la persistencia: BotManager no ha sido inicializado.")
            return
            
        if self.application.persistence:
            await self.application.persistence.flush()
            logger.info("Datos de persistencia guardados en el disco.")

# Crear la instancia única que será importada por otros módulos.
bot_manager = BotManager()
