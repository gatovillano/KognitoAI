# utils/patches.py

import logging
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from utils.postgres_chat_history import close_postgres_chat_message_history

logger = logging.getLogger(__name__)

def apply_patches():
    """
    Aplica parches preventivos a librerías externas para corregir bugs conocidos
    o mejorar la estabilidad.
    """
    print("🛠️ Aplicando parches de estabilidad...")
    patch_postgres_chat_history_del()


def patch_postgres_chat_history_del():
    """
    Parchea el método __del__ de PostgresChatMessageHistory para evitar:
    AttributeError: 'PostgresChatMessageHistory' object has no attribute 'cursor'
    
    Este error ocurre si la inicialización (__init__) falla antes de crear el cursor,
    y el recolector de basura intenta limpiar el objeto.
    """
    original_del = PostgresChatMessageHistory.__del__

    def safe_del(self):
        if hasattr(self, 'cursor') and self.cursor:
            try:
                original_del(self)
                return
            except Exception:
                logger.debug("Fallo el __del__ original de PostgresChatMessageHistory; usando cierre seguro.")

        close_postgres_chat_message_history(self, logger=logger)

    PostgresChatMessageHistory.__del__ = safe_del
    print("✅ Patched PostgresChatMessageHistory.__del__ for safety.")
    logger.info("✅ Patched PostgresChatMessageHistory.__del__ for safety.")
