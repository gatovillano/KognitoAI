import logging
import asyncio
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}

    async def _start_heartbeat(self, account_id: str):
        """Envía un ping a todos los clientes de una cuenta cada 20 segundos."""
        while account_id in self.active_connections:
            try:
                await asyncio.sleep(20)
                # Prepara una copia de las conexiones para iterar de forma segura
                connections = list(self.active_connections.get(account_id, []))
                for connection in connections:
                    try:
                        await connection.send_text("ping")
                    except (WebSocketDisconnect, RuntimeError) as e:
                        logger.warning(f"Heartbeat: No se pudo enviar ping a un cliente de {account_id}, desconectando. Error: {e}")
                        self.disconnect(connection, account_id)
            except asyncio.CancelledError:
                logger.info(f"Heartbeat para la cuenta {account_id} cancelado.")
                break
            except Exception as e:
                logger.error(f"Error inesperado en el heartbeat para la cuenta {account_id}: {e}")
                # Espera un poco antes de reintentar para no entrar en un bucle de errores rápidos
                await asyncio.sleep(5)


    async def connect(self, websocket: WebSocket, account_id: str):
        await websocket.accept()
        if account_id not in self.active_connections:
            self.active_connections[account_id] = []
        self.active_connections[account_id].append(websocket)
        logger.info(f"WebSocket conectado para la cuenta: {account_id}. Total de conexiones: {len(self.active_connections[account_id])}. Nueva conexión: {id(websocket)}")

        # Inicia el heartbeat solo si es la primera conexión para esta cuenta
        if account_id not in self.heartbeat_tasks:
            logger.info(f"Iniciando tarea de heartbeat para la cuenta: {account_id}")
            self.heartbeat_tasks[account_id] = asyncio.create_task(self._start_heartbeat(account_id))


    def disconnect(self, websocket: WebSocket, account_id: str):
        if account_id in self.active_connections and websocket in self.active_connections[account_id]:
            self.active_connections[account_id].remove(websocket)
            logger.info(f"WebSocket desconectado para la cuenta: {account_id}. Conexiones restantes: {len(self.active_connections[account_id])}. Conexión eliminada: {id(websocket)}")
            if not self.active_connections[account_id]:
                logger.info(f"Último cliente desconectado para la cuenta: {account_id}. Deteniendo heartbeat.")
                del self.active_connections[account_id]
                # Cancela la tarea de heartbeat si ya no hay clientes
                if account_id in self.heartbeat_tasks:
                    self.heartbeat_tasks[account_id].cancel()
                    del self.heartbeat_tasks[account_id]

    async def send_personal_message(self, message: Dict[str, Any], account_id: str):
        if account_id in self.active_connections:
            logger.info(f"DEBUG: Intentando enviar mensaje a {account_id}. Conexiones activas: {len(self.active_connections[account_id])}")
            for connection in self.active_connections[account_id]:
                try:
                    logger.info(f"DEBUG: Enviando mensaje a {account_id} via WebSocket (conexión {id(connection)}): {message}")
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    logger.warning(f"WebSocketDisconnect al enviar mensaje a {account_id} (conexión {id(connection)}). Desconectando.")
                    self.disconnect(connection, account_id)
                except Exception as e:
                    logger.error(f"Error al enviar mensaje a {account_id} (conexión {id(connection)}): {e}")

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
