import logging
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
import httpx
from core.config import settings

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, List[WebSocket]]] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}

    async def _send_message_to_telegram_via_http(self, account_id: str, message: Dict[str, Any]):
        """
        Envía un mensaje al cliente de Telegram a través de su endpoint HTTP interno.
        """
        telegram_bot_url = settings.telegram_bot_url
        internal_api_key = settings.internal_api_key_for_bot
        
        message_type = message.get("type")
        message_text = None

        if message_type == "stream_chunk":
            message_text = message.get("chunk")
        elif message_type == "final_response":
            message_text = message.get("response")
        elif message_type == "error":
            message_text = f"Error del sistema: {message.get('error_message', 'Desconocido')}"
        
        if not message_text:
            logger.debug(f"No hay texto para enviar a Telegram para el tipo de mensaje: {message_type}")
            return

        try:
            telegram_chat_id = int(account_id)
        except ValueError:
            logger.error(f"No se pudo convertir account_id '{account_id}' a un chat_id de Telegram numérico.")
            return

        payload = {
            "chat_id": telegram_chat_id,
            "text": message_text
        }
        headers = {
            "X-Internal-API-Key": internal_api_key,
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{telegram_bot_url}/internal/send-message", json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                logger.info(f"Mensaje enviado a Telegram via HTTP para chat_id {telegram_chat_id}: {message_text[:50]}...")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al enviar mensaje a Telegram para chat_id {telegram_chat_id}: {e.response.status_code} - {e.response.text}", exc_info=True)
        except Exception as e:
            logger.error(f"Error inesperado al enviar mensaje a Telegram via HTTP para chat_id {telegram_chat_id}: {e}", exc_info=True)
    async def _start_heartbeat(self, account_id: str):
        """Envía un ping a todos los clientes de una cuenta cada 20 segundos."""
        while account_id in self.active_connections:
            try:
                await asyncio.sleep(20)
                all_connections_for_account: List[WebSocket] = []
                if account_id in self.active_connections:
                    for conn_type_dict in self.active_connections[account_id].values():
                        all_connections_for_account.extend(conn_type_dict)
                
                connections_to_ping = list(all_connections_for_account)

                for connection in connections_to_ping:
                    try:
                        await connection.send_text("ping")
                    except (WebSocketDisconnect, RuntimeError) as e:
                        logger.warning(f"Heartbeat: No se pudo enviar ping a un cliente de {account_id}, desconectando. Error: {e}")
                        for c_type, conns in self.active_connections.get(account_id, {}).items():
                            if connection in conns:
                                self.disconnect(connection, account_id, c_type)
                                break
            except asyncio.CancelledError:
                logger.info(f"Heartbeat para la cuenta {account_id} cancelado.")
                break
            except Exception as e:
                logger.error(f"Error inesperado en el heartbeat para la cuenta {account_id}: {e}")
                await asyncio.sleep(5)

    async def connect(self, websocket: WebSocket, account_id: str, connection_type: str = "chat"):
        if account_id not in self.active_connections:
            self.active_connections[account_id] = {}
        if connection_type not in self.active_connections[account_id]:
            self.active_connections[account_id][connection_type] = []
        self.active_connections[account_id][connection_type].append(websocket)
        logger.info(f"WebSocket conectado para la cuenta: {account_id}, tipo: {connection_type}. Total de conexiones de este tipo: {len(self.active_connections[account_id][connection_type])}. Nueva conexión: {id(websocket)}")

        if account_id not in self.heartbeat_tasks:
            logger.info(f"Iniciando tarea de heartbeat para la cuenta: {account_id}")
            self.heartbeat_tasks[account_id] = asyncio.create_task(self._start_heartbeat(account_id))

    def disconnect(self, websocket: WebSocket, account_id: str, connection_type: str = "chat"):
        if account_id in self.active_connections and connection_type in self.active_connections[account_id] and websocket in self.active_connections[account_id][connection_type]:
            self.active_connections[account_id][connection_type].remove(websocket)
            logger.info(f"WebSocket desconectado para la cuenta: {account_id}, tipo: {connection_type}. Conexiones restantes de este tipo: {len(self.active_connections[account_id][connection_type])}. Conexión eliminada: {id(websocket)}")
            
            if not self.active_connections[account_id][connection_type]:
                del self.active_connections[account_id][connection_type]
                logger.info(f"Última conexión de tipo '{connection_type}' desconectada para la cuenta: {account_id}.")

            if not self.active_connections[account_id]:
                logger.info(f"Último cliente desconectado para la cuenta: {account_id}. Deteniendo heartbeat.")
                del self.active_connections[account_id]
                if account_id in self.heartbeat_tasks:
                    self.heartbeat_tasks[account_id].cancel()
                    del self.heartbeat_tasks[account_id]

    async def send_personal_message(self, message: Dict[str, Any], account_id: str, connection_type: Optional[str] = None):
        if account_id in self.active_connections:
            connections_to_send: List[WebSocket] = []
            if connection_type and connection_type in self.active_connections[account_id]:
                connections_to_send = self.active_connections[account_id][connection_type]
            elif not connection_type:
                for conn_list in self.active_connections[account_id].values():
                    connections_to_send.extend(conn_list)

            logger.info(f"DEBUG: Intentando enviar mensaje a {account_id} (tipo: {connection_type or 'todos'}). Conexiones activas: {len(connections_to_send)}")
            for connection in connections_to_send:
                try:
                    logger.info(f"DEBUG: Enviando mensaje a {account_id} via WebSocket (conexión {id(connection)}): {message}")
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    logger.warning(f"WebSocketDisconnect al enviar mensaje a {account_id} (conexión {id(connection)}). Desconectando.")
                    for c_type, conns in self.active_connections.get(account_id, {}).items():
                        if connection in conns:
                            self.disconnect(connection, account_id, c_type)
                            break
                except Exception as e:
                    logger.error(f"Error al enviar mensaje a {account_id} (conexión {id(connection)}): {e}")

    async def broadcast(self, message: Dict[str, Any]):
        for account_id, connections_by_type in self.active_connections.items():
            for connection_list in connections_by_type.values():
                for connection in connection_list:
                    try:
                        await connection.send_json(message)
                    except WebSocketDisconnect:
                        logger.warning(f"WebSocketDisconnect durante broadcast a {account_id}. La conexión será limpiada por el heartbeat.")
                    except Exception as e:
                        logger.error(f"Error al hacer broadcast a {account_id}: {e}")

manager = WebSocketManager()

def get_websocket_manager() -> WebSocketManager:
    return manager

async def send_personal_message(account_id: str, message: Dict[str, Any], connection_type: Optional[str] = None):
    await manager.send_personal_message(message, account_id, connection_type)

async def startup_event():
    logger.info("Ciclo de vida de inicio de WebSocket (en memoria) - No se requiere acción.")
    pass

async def shutdown_event():
    logger.info("Ciclo de vida de apagado de WebSocket (en memoria) - No se requiere acción.")
    pass