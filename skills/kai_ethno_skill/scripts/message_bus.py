"""
Message Bus - Sistema de comunicación asíncrona
Permite comunicación desacoplada entre agentes
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class Message:
    """Mensaje en el bus"""
    
    def __init__(self, topic: str, payload: Dict[str, Any], 
                 sender: str = "system", priority: int = 0):
        self.id = f"{topic}_{datetime.now().timestamp()}"
        self.topic = topic
        self.payload = payload
        self.sender = sender
        self.priority = priority
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "payload": self.payload,
            "sender": self.sender,
            "priority": self.priority,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        msg = cls(data["topic"], data["payload"], data["sender"], data["priority"])
        msg.id = data["id"]
        msg.timestamp = data["timestamp"]
        return msg


class MessageBus:
    """
    Bus de mensajes asíncrono para comunicación entre agentes
    
    Características:
    - Comunicación pub/sub desacoplada
    - Priorización de mensajes
    - Colas por tópico
    - Historial de mensajes
    - Soporte para callbacks
    """
    
    def __init__(self, max_history: int = 1000):
        self.queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.history: List[Message] = []
        self.max_history = max_history
        self.running = False
        self._consumers = []
    
    async def start(self):
        """Inicia el bus de mensajes"""
        self.running = True
        logger.info("Message Bus iniciado")
    
    async def stop(self):
        """Detiene el bus de mensajes"""
        self.running = False
        for consumer in self._consumers:
            consumer.cancel()
        logger.info("Message Bus detenido")
    
    async def publish(self, topic: str, payload: Dict[str, Any], 
                      sender: str = "system", priority: int = 0) -> str:
        """
        Publica un mensaje en un tópico
        
        Args:
            topic: Tópico del mensaje
            payload: Contenido del mensaje
            sender: Agente que envía el mensaje
            priority: Prioridad (mayor = más importante)
        
        Returns:
            ID del mensaje
        """
        message = Message(topic, payload, sender, priority)
        
        # Agregar a historial
        self.history.append(message)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # Encolar mensaje
        await self.queues[topic].put(message)
        
        # Notificar suscriptores
        for callback in self.subscribers.get(topic, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(message))
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Error en callback: {e}")
        
        logger.debug(f"Mensaje publicado: {topic} por {sender}")
        return message.id
    
    async def subscribe(self, topic: str, callback: Callable[[Message], None]):
        """
        Suscribe un callback a un tópico
        
        Args:
            topic: Tópico a suscribir
            callback: Función a llamar cuando llegue un mensaje
        """
        self.subscribers[topic].append(callback)
        logger.info(f"Callback suscrito a tópico: {topic}")
    
    async def consume(self, topic: str, handler: Callable[[Message], Any]) -> asyncio.Task:
        """
        Crea un consumidor para un tópico
        
        Args:
            topic: Tópico a consumir
            handler: Función que procesa el mensaje
        
        Returns:
            Task del consumidor
        """
        async def consumer():
            while self.running:
                try:
                    message = await asyncio.wait_for(
                        self.queues[topic].get(), 
                        timeout=1.0
                    )
                    await handler(message)
                    self.queues[topic].task_done()
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error en consumidor {topic}: {e}")
        
        task = asyncio.create_task(consumer())
        self._consumers.append(task)
        return task
    
    async def request_response(self, topic: str, payload: Dict[str, Any],
                               response_topic: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Patrón request-response
        
        Args:
            topic: Tópico de request
            payload: Payload del request
            response_topic: Tópico donde esperar respuesta
            timeout: Timeout en segundos
        
        Returns:
            Payload de la respuesta
        """
        response_future = asyncio.Future()
        
        async def response_handler(message: Message):
            if not response_future.done():
                response_future.set_result(message.payload)
        
        await self.subscribe(response_topic, response_handler)
        await self.publish(topic, payload)
        
        try:
            result = await asyncio.wait_for(response_future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"No response received on {response_topic} within {timeout}s")
    
    def get_history(self, topic: Optional[str] = None, 
                    limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene historial de mensajes"""
        messages = self.history
        if topic:
            messages = [m for m in messages if m.topic == topic]
        return [m.to_dict() for m in messages[-limit:]]
    
    def clear_history(self):
        """Limpia el historial de mensajes"""
        self.history.clear()
        logger.info("Historial de mensajes limpiado")
