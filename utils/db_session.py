# utils/db_session.py

"""
Módulo de Utilidad para la Gestión de Sesiones de Base de Datos.

Este módulo proporciona un gestor de contexto asíncrono (`DBSession`) que
simplifica enormemente el manejo de las sesiones de SQLAlchemy en una
aplicación asíncrona.

El uso de `async with` garantiza que:
1.  Se obtenga una nueva sesión de la base de datos del pool de conexiones.
2.  El bloque de código dentro del `with` se ejecute con esa sesión.
3.  Si el bloque se completa sin errores, se haga un `commit` para guardar
    los cambios de forma permanente.
4.  Si ocurre una excepción dentro del bloque, se haga un `rollback` para
    deshacer todos los cambios de esa transacción, manteniendo la base de
    datos en un estado consistente.
5.  Independientemente del resultado (éxito o error), la sesión se cierre
    correctamente y se devuelva al pool de conexiones, evitando fugas de
    recursos.

Este patrón es fundamental para escribir código de base de datos robusto y
fácil de mantener.
"""

import logging

logger = logging.getLogger(__name__)

class DBSession:
    """
    Un gestor de contexto asíncrono para manejar las sesiones de SQLAlchemy.
    """
    def __init__(self, session_factory):
        """
        Inicializa el gestor con una fábrica de sesiones de SQLAlchemy.

        Args:
            session_factory: La fábrica de sesiones configurada (ej. SessionLocal).
        """
        self.session_factory = session_factory
        self.session = None

    async def __aenter__(self):
        """
        Método de entrada del gestor de contexto. Crea y devuelve una nueva sesión.
        """
        try:
            self.session = self.session_factory()
            logger.debug("Sesión de base de datos adquirida del pool.")
            return self.session
        except Exception as e:
            logger.error(f"Error al adquirir una sesión de base de datos: {e}", exc_info=True)
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Método de salida del gestor de contexto. Realiza commit o rollback y
        cierra la sesión.
        """
        if self.session is not None:
            try:
                if exc_type is not None:
                    # Ocurrió una excepción, deshacer la transacción.
                    logger.warning(f"Ocurrió una excepción en el bloque 'with', realizando rollback: {exc_val}")
                    await self.session.rollback()
                else:
                    # No hubo errores, confirmar la transacción.
                    await self.session.commit()
                    logger.debug("Transacción completada exitosamente (commit).")
            except Exception as e:
                # Si el commit o el rollback fallan, es un problema serio.
                logger.error(f"Error durante el commit/rollback de la sesión: {e}", exc_info=True)
                # Volver a lanzar la excepción original si la hubo, o la nueva si no.
                if exc_type is None:
                    raise e
            finally:
                # Asegurarse de que la sesión siempre se cierre.
                await self.session.close()
                logger.debug("Sesión de base de datos cerrada y devuelta al pool.")
        return False  # Propaga la excepción si hubo una.
