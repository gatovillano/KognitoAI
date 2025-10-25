import logging
import asyncio
from typing import Dict, Any, List, Optional # Añadido Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, List[WebSocket]]] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}

    async def _start_heartbeat(self, account_id: str):
        """Envía un ping a todos los clientes de una cuenta cada 20 segundos."""
        while account_id in self.active_connections:
            try:
                await asyncio.sleep(20)
                # Recopila todas las conexiones activas para esta cuenta, de todos los tipos
                all_connections_for_account: List[WebSocket] = []
                if account_id in self.active_connections:
                    for conn_type_dict in self.active_connections[account_id].values():
                        all_connections_for_account.extend(conn_type_dict)
                
                # Prepara una copia de las conexiones para iterar de forma segura
                connections_to_ping = list(all_connections_for_account)

                for connection in connections_to_ping:
                    try:
                        await connection.send_text("ping")
                    except (WebSocketDisconnect, RuntimeError) as e:
                        logger.warning(f"Heartbeat: No se pudo enviar ping a un cliente de {account_id}, desconectando. Error: {e}")
                        # Necesitamos encontrar el tipo de conexión para desconectar correctamente
                        for c_type, conns in self.active_connections.get(account_id, {}).items():
                            if connection in conns:
                                self.disconnect(connection, account_id, c_type)
                                break
            except asyncio.CancelledError:
                logger.info(f"Heartbeat para la cuenta {account_id} cancelado.")
                break
            except Exception as e:
                logger.error(f"Error inesperado en el heartbeat para la cuenta {account_id}: {e}")
                # Espera un poco antes de reintentar para no entrar en un bucle de errores rápidos
                await asyncio.sleep(5)


    async def connect(self, websocket: WebSocket, account_id: str, connection_type: str = "chat"):
        # No llamar a websocket.accept() aquí, ya que FastAPI lo hace automáticamente.
        if account_id not in self.active_connections:
            self.active_connections[account_id] = {}
        if connection_type not in self.active_connections[account_id]:
            self.active_connections[account_id][connection_type] = []
        self.active_connections[account_id][connection_type].append(websocket)
        logger.info(f"WebSocket conectado para la cuenta: {account_id}, tipo: {connection_type}. Total de conexiones de este tipo: {len(self.active_connections[account_id][connection_type])}. Nueva conexión: {id(websocket)}")

        # Inicia el heartbeat solo si es la primera conexión para esta cuenta
        # El heartbeat ahora monitorea si hay *alguna* conexión para la cuenta, no solo un tipo específico
        if account_id not in self.heartbeat_tasks:
            logger.info(f"Iniciando tarea de heartbeat para la cuenta: {account_id}")
            self.heartbeat_tasks[account_id] = asyncio.create_task(self._start_heartbeat(account_id))


    def disconnect(self, websocket: WebSocket, account_id: str, connection_type: str = "chat"):
        if account_id in self.active_connections and connection_type in self.active_connections[account_id] and websocket in self.active_connections[account_id][connection_type]:
            self.active_connections[account_id][connection_type].remove(websocket)
            logger.info(f"WebSocket desconectado para la cuenta: {account_id}, tipo: {connection_type}. Conexiones restantes de este tipo: {len(self.active_connections[account_id][connection_type])}. Conexión eliminada: {id(websocket)}")
            
            # Si no quedan conexiones de este tipo, eliminar la entrada del tipo
            if not self.active_connections[account_id][connection_type]:
                del self.active_connections[account_id][connection_type]
                logger.info(f"Última conexión de tipo '{connection_type}' desconectada para la cuenta: {account_id}.")

            # Verificar si no quedan *ningún* tipo de conexión para esta cuenta
            if not self.active_connections[account_id]:
                logger.info(f"Último cliente desconectado para la cuenta: {account_id}. Deteniendo heartbeat.")
                del self.active_connections[account_id]
                # Cancela la tarea de heartbeat si ya no hay clientes
                if account_id in self.heartbeat_tasks:
                    self.heartbeat_tasks[account_id].cancel()
                    del self.heartbeat_tasks[account_id]

    async def send_personal_message(self, message: Dict[str, Any], account_id: str, connection_type: Optional[str] = None):
        if account_id in self.active_connections:
            # Si se especifica un tipo de conexión, enviar solo a esas conexiones
            if connection_type and connection_type in self.active_connections[account_id]:
                connections_to_send: List[WebSocket] = self.active_connections[account_id][connection_type]
            # Si no se especifica un tipo, o el tipo no existe, enviar a todas las conexiones de la cuenta
            else:
                connections_to_send: List[WebSocket] = []
                for conn_type_dict in self.active_connections[account_id].values():
                    connections_to_send.extend(conn_type_dict)

            logger.info(f"DEBUG: Intentando enviar mensaje a {account_id} (tipo: {connection_type if connection_type else 'todos'}). Conexiones activas: {len(connections_to_send)}")
            for connection in connections_to_send:
                try:
                    logger.info(f"DEBUG: Enviando mensaje a {account_id} via WebSocket (conexión {id(connection)}): {message}")
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    logger.warning(f"WebSocketDisconnect al enviar mensaje a {account_id} (conexión {id(connection)}). Desconectando.")
                    # Necesitamos saber el tipo de conexión para desconectar correctamente
                    # Esto es un poco más complejo, por ahora, asumimos que si se desconecta, se desconecta de todos los tipos
                    # Una solución más robusta implicaría almacenar el tipo de conexión en el objeto WebSocket o buscarlo.
                    # Por simplicidad, si se desconecta, lo eliminamos de todos los tipos donde se encuentre.
                    for c_type, conns in self.active_connections[account_id].items():
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
                        # Aquí la desconexión es más compleja, ya que no tenemos el tipo de conexión directamente.
                        # Podríamos iterar sobre los tipos para encontrarla o simplemente dejar que el heartbeat la limpie.
                        logger.warning(f"WebSocketDisconnect durante broadcast a {account_id}. La conexión será limpiada por el heartbeat.")
                    except Exception as e:
                        logger.error(f"Error al hacer broadcast a {account_id}: {e}")

# Instancia única del gestor de WebSockets
manager = WebSocketManager()

# Dependencia de FastAPI para obtener el gestor
def get_websocket_manager() -> WebSocketManager:
    return manager

# Para mantener la compatibilidad con el código existente que llama a send_personal_message
async def send_personal_message(account_id: str, message: Dict[str, Any], connection_type: Optional[str] = None):
    await manager.send_personal_message(message, account_id, connection_type)

# Funciones de ciclo de vida (ahora vacías, pero se mantienen por si se necesitan en el futuro)
async def startup_event():
    logger.info("Ciclo de vida de inicio de WebSocket (en memoria) - No se requiere acción.")
    pass

async def shutdown_event():
    logger.info("Ciclo de vida de apagado de WebSocket (en memoria) - No se requiere acción.")
    pass
