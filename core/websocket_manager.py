import logging
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, account_id: str):
        await websocket.accept()
        if account_id not in self.active_connections:
            self.active_connections[account_id] = []
        self.active_connections[account_id].append(websocket)
        logger.info(f"WebSocket conectado para la cuenta: {account_id}")

    def disconnect(self, websocket: WebSocket, account_id: str):
        if account_id in self.active_connections:
            self.active_connections[account_id].remove(websocket)
            if not self.active_connections[account_id]:
                del self.active_connections[account_id]
        logger.info(f"WebSocket desconectado para la cuenta: {account_id}")

    async def send_personal_message(self, message: Dict[str, Any], account_id: str):
        if account_id in self.active_connections:
            for connection in self.active_connections[account_id]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    self.disconnect(connection, account_id)
                except Exception as e:
                    logger.error(f"Error al enviar mensaje a {account_id}: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        for account_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    self.disconnect(connection, account_id)
                except Exception as e:
                    logger.error(f"Error al hacer broadcast a {account_id}: {e}")

# Instancia única del gestor de WebSockets
manager = WebSocketManager()

# Dependencia de FastAPI para obtener el gestor
def get_websocket_manager() -> WebSocketManager:
    return manager

# Para mantener la compatibilidad con el código existente que llama a send_personal_message
async def send_personal_message(account_id: str, message: Dict[str, Any]):
    await manager.send_personal_message(message, account_id)

# Funciones de ciclo de vida (ahora vacías, pero se mantienen por si se necesitan en el futuro)
async def startup_event():
    logger.info("Ciclo de vida de inicio de WebSocket (en memoria) - No se requiere acción.")
    pass

async def shutdown_event():
    logger.info("Ciclo de vida de apagado de WebSocket (en memoria) - No se requiere acción.")
    pass
