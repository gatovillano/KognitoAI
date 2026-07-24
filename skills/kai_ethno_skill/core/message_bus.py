"""
Message Bus - Bus de mensajes asíncrono
Sistema de comunicación entre agentes
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Tipos de mensaje"""
    EVENT = "event"
    DATA = "data"
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"


@dataclass
class Message:
    """Mensaje en el bus"""
    topic: str
    payload: Any
    message_type: MessageType = MessageType.DATA
    sender: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageBus:
    """
    Bus de mensajes asíncrono para comunicación entre agentes.
    Implementa patrón pub/sub con colas por tópico.
    """

    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._queues: Dict[str, asyncio.Queue] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._message_history: List[Message] = []
        self._max_history = 500

    async def start(self):
        """Inicia el bus de mensajes"""
        if self._running:
            return

        self._running = True
        logger.info("MessageBus iniciado")

    async def shutdown(self):
        """Cierra el bus de mensajes"""
        self._running = False

        # Cancelar tareas
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Esperar finalización
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("MessageBus cerrado")

    def subscribe(self, topic: str, callback: Callable):
        """
        Suscribe una función a un tópico.

        Args:
            topic: Tópico a suscribir (soporta wildcards: * y ?)
            callback: Función async que procesa el mensaje
        """
        self._subscribers[topic].append(callback)
        logger.debug(f"Suscrito a tópico: {topic}")

    def unsubscribe(self, topic: str, callback: Callable):
        """Desuscribe una función de un tópico"""
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(callback)
            except ValueError:
                pass

    async def publish(
        self,
        topic: str,
        message: Any,
        message_type: MessageType = MessageType.DATA,
        sender: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Publica un mensaje en el bus.

        Args:
            topic: Tópico del mensaje
            message: Contenido del mensaje
            message_type: Tipo de mensaje
            sender: Nombre del agente que envía
            correlation_id: ID para correlación de mensajes
            metadata: Metadatos adicionales

        Returns:
            ID del mensaje publicado
        """
        if not self._running:
            logger.warning("MessageBus no está corriendo, mensaje encolado")
            # Asegurar que el bus esté corriendo
            await self.start()

        msg = Message(
            topic=topic,
            payload=message,
            message_type=message_type,
            sender=sender,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )

        # Guardar en historial
        self._message_history.append(msg)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history :]

        # Notificar a suscriptores
        await self._notify_subscribers(msg)

        return msg.correlation_id or msg.timestamp

    async def _notify_subscribers(self, message: Message):
        """Notifica a los suscriptores de un mensaje"""
        # Buscar suscriptores directos y por wildcard
        topics_to_notify = [message.topic]

        # Wildcard: *
        if "*" in self._subscribers:
            topics_to_notify.append("*")

        # Wildcard específico (ej: "agent.*")
        parts = message.topic.split(".")
        for i in range(len(parts)):
            wildcard = ".".join(parts[: i + 1]) + ".*"
            if wildcard in self._subscribers:
                topics_to_notify.append(wildcard)

        # Notificar a todos los suscriptores relevantes
        tasks = []
        for topic in topics_to_notify:
            if topic in self._subscribers:
                for callback in self._subscribers[topic]:
                    task = asyncio.create_task(
                        self._safe_callback(callback, message)
                    )
                    tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_callback(self, callback: Callable, message: Message):
        """Ejecuta callback de forma segura"""
        try:
            await callback(message)
        except Exception as e:
            logger.error(f"Error en callback: {e}", exc_info=True)

    async def request(
        self,
        topic: str,
        payload: Any,
        timeout: float = 30.0,
        sender: Optional[str] = None,
    ) -> Any:
        """
        Envía una solicitud y espera respuesta (request-reply pattern).

        Args:
            topic: Tópico de solicitud
            payload: Datos de la solicitud
            timeout: Timeout en segundos
            sender: Nombre del solicitante

        Returns:
            Respuesta del servicio
        """
        correlation_id = f"req_{datetime.now().timestamp()}"

        # Crear future para la respuesta
        response_future: asyncio.Future[Any] = asyncio.get_event_loop().create_future()

        # Suscribirse temporalmente al tópico de respuesta
        response_topic = f"response.{correlation_id}"

        async def response_handler(message: Message):
            if not response_future.done():
                response_future.set_result(message.payload)

        self.subscribe(response_topic, response_handler)

        try:
            # Publicar solicitud
            await self.publish(
                topic=topic,
                message=payload,
                message_type=MessageType.QUERY,
                sender=sender,
                correlation_id=correlation_id,
            )

            # Esperar respuesta
            result = await asyncio.wait_for(response_future, timeout=timeout)
            return result

        except asyncio.TimeoutError:
            logger.warning(f"Timeout en solicitud a tópico: {topic}")
            raise
        finally:
            # Desuscribirse
            self.unsubscribe(response_topic, response_handler)

    def get_history(
        self, topic: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Obtiene historial de mensajes"""
        messages = self._message_history

        if topic:
            messages = [m for m in messages if m.topic == topic]

        return [self._message_to_dict(m) for m in messages[-limit:]]

    def _message_to_dict(self, message: Message) -> Dict[str, Any]:
        """Convierte mensaje a diccionario"""
        return {
            "topic": message.topic,
            "payload": str(message.payload)[:200],  # Truncar para logs
            "type": message.message_type.value,
            "sender": message.sender,
            "timestamp": message.timestamp,
            "correlation_id": message.correlation_id,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del bus"""
        topics = defaultdict(int)
        for msg in self._message_history:
            topics[msg.topic] += 1

        return {
            "total_messages": len(self._message_history),
            "active_subscriptions": sum(len(v) for v in self._subscribers.values()),
            "topics": dict(topics),
            "running": self._running,
        }
