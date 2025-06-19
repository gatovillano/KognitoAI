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
from typing import Optional

from telegram.ext import Application, ExtBot

logger = logging.getLogger(__name__)


class BotManager:
    """
    Una clase Singleton que mantiene una referencia a la instancia de la aplicación del bot.
    """
    _instance: Optional['BotManager'] = None
    _application: Optional[Application] = None
    _bot: Optional[ExtBot] = None

    def __new__(cls):
        """
        Implementación del patrón Singleton.
        """
        if cls._instance is None:
            cls._instance = super(BotManager, cls).__new__(cls)
            logger.debug("Creando nueva instancia de BotManager.")
        return cls._instance

    def initialize(self, application: Application):
        """
        Inicializa el gestor con la instancia de la aplicación del bot.
        Este método debe ser llamado una sola vez al inicio de la aplicación.
        """
        if self._application is not None:
            logger.warning("BotManager ya ha sido inicializado. Ignorando llamada.")
            return

        if not isinstance(application, Application):
            raise TypeError("El objeto proporcionado no es una instancia de telegram.ext.Application")

        self._application = application
        self._bot = application.bot
        logger.info("✅ BotManager inicializado con la aplicación de Telegram.")

    @property
    def application(self) -> Application:
        """
        Devuelve la instancia de la `Application`.
        Lanza un error si el gestor no ha sido inicializado.
        """
        if self._application is None:
            raise RuntimeError("BotManager no ha sido inicializado. Llama a `initialize()` primero.")
        return self._application

    @property
    def bot(self) -> ExtBot:
        """
        Devuelve la instancia del `ExtBot` para enviar mensajes.
        Lanza un error si el gestor no ha sido inicializado.
        """
        if self._bot is None:
            raise RuntimeError("BotManager no ha sido inicializado. Llama a `initialize()` primero.")
        return self._bot

    @property
    def job_queue(self):
        """

        Devuelve la `JobQueue` de la aplicación para programar tareas.
        Lanza un error si el gestor no ha sido inicializado.
        """
        if self._application is None or self._application.job_queue is None:
            raise RuntimeError("BotManager no ha sido inicializado o la JobQueue no está disponible.")
        return self._application.job_queue

    def get_user_data(self, user_id: int) -> dict:
        """
        Devuelve el diccionario `user_data` para un usuario específico.
        """
        if self._application is None or self._application.user_data is None:
             raise RuntimeError("BotManager no ha sido inicializado o la persistencia no está habilitada.")
        return self._application.user_data.get(user_id, {})

    async def flush_persistence(self):
        """
        Fuerza el guardado de todos los datos de persistencia (user_data, chat_data).
        """
        if self._application and self._application.persistence:
            await self._application.persistence.flush()
            logger.debug("Datos de persistencia guardados manualmente.")

# Se crea una única instancia global que será importada por otros módulos.
bot_manager = BotManager()
