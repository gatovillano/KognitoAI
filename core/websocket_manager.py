import logging
from typing import Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Diccionario para almacenar las conexiones activas.
# La clave será el account_id (str) y el valor será el objeto WebSocket.
# En un entorno de producción con múltiples instancias de la API,
# esto DEBERÍA ser reemplazado por un sistema de Pub/Sub como Redis.
active_connections: Dict[str, WebSocket] = {}

async def connect_websocket(account_id: str, websocket: WebSocket):
    """Maneja la conexión de un nuevo WebSocket."""
    await websocket.accept()
    active_connections[account_id] = websocket
    logger.info(f"WebSocket conectado para la cuenta: {account_id}")

async def disconnect_websocket(account_id: str):
    """Maneja la desconexión de un WebSocket."""
    if account_id in active_connections:
        del active_connections[account_id]
        logger.info(f"WebSocket desconectado para la cuenta: {account_id}")

async def send_personal_message(account_id: str, message: Dict[str, Any]):
    """Envía un mensaje JSON a un usuario específico a través de su WebSocket."""
    if account_id in active_connections:
        websocket = active_connections[account_id]
        try:
            await websocket.send_json(message)
            logger.info(f"Mensaje enviado a la cuenta {account_id}: {message.get('type', 'desconocido')}")
        except Exception as e:
            logger.error(f"Error al enviar mensaje a la cuenta {account_id}: {e}", exc_info=True)
            # Si falla el envío, asumimos que la conexión está rota y la eliminamos
            await disconnect_websocket(account_id)
    else:
        logger.debug(f"No se encontró conexión WebSocket activa para la cuenta: {account_id}. Mensaje no enviado.")

# Puedes añadir una función para enviar a todos los conectados si fuera necesario
# async def broadcast_message(message: Dict[str, Any]):
#     for account_id, websocket in list(active_connections.items()): # Usar list() para evitar RuntimeError durante la iteración si se modifica el dict
#         try:
#             await websocket.send_json(message)
#         except Exception as e:
#             logger.error(f"Error al hacer broadcast a {account_id}: {e}")
#             await disconnect_websocket(account_id)
