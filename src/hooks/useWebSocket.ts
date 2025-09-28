import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  taskId?: string; // Añadido para la nueva arquitectura de streaming
  [key: string]: any;
}

interface UseWebSocketOptions {
  userId?: string;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const { userId } = options;
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [latestMessage, setLatestMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    console.log('WS: Intentando conectar...');
    try {
      const token = localStorage.getItem('authToken');
      if (!token || !userId) {
        console.error('WS: No hay token de acceso o ID de usuario disponible. No se puede conectar.');
        setConnectionError('No hay token de acceso o ID de usuario disponible');
        return;
      }

      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || window.location.origin;
      let wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      let wsHost = window.location.host;

      try {
        const url = new URL(apiBaseUrl);
        wsProtocol = url.protocol === 'https:' ? 'wss' : 'ws';
        wsHost = url.host;
      } catch (e) {
        console.error("WS: Error parsing API_BASE_URL, falling back to window.location.origin", e);
      }

      const wsUrl = `${wsProtocol}://${wsHost}/ws/${userId}?token=${encodeURIComponent(token)}`;
      console.log(`WS: Intentando conectar a: ${wsUrl}`);
      
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WS: 🔌 WebSocket conectado exitosamente.');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        console.log('WS: onmessage triggered', event);
        console.log('WS: event.data (raw):', event.data);
        const msgStr = event.data as string;
        if (!msgStr) return;

        try {
          const message: WebSocketMessage = JSON.parse(msgStr);
          console.log('WS: 📨 Mensaje WebSocket recibido:', message);
          setLatestMessage(message);
          console.log('WS: setLatestMessage called with:', message);

        } catch (error) {
          // If JSON parsing fails, check if it's a known non-JSON message like 'pong' or 'ping'
          if (msgStr === 'pong') {
            console.log('WS: 💓 Recibido pong del servidor.');
          } else if (msgStr === 'ping') {
            console.log('WS: 💓 Recibido ping del servidor (inesperado, pero ignorado).');
          } else {
            console.error('WS: ❌ Error al procesar mensaje WebSocket (no JSON o formato inesperado):', error, 'Mensaje recibido:', msgStr);
          }
        }
      };


      wsRef.current.onclose = (event) => {
        console.log(`WS: 🔌 WebSocket desconectado. Código: ${event.code}, Razón: "${event.reason}", Limpio: ${event.wasClean}.`);
        setIsConnected(false);
        
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`WS: 🔄 Reintentando conexión en ${delay}ms (intento ${reconnectAttempts.current + 1}/${maxReconnectAttempts}).`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          const errorMessage = 'No se pudo reconectar al servidor después de varios intentos.';
          console.error(`WS: ${errorMessage}`);
          setConnectionError(errorMessage);
        }
      };

      wsRef.current.onerror = (event) => {
        console.error('WS: ❌ Se ha producido un error en la conexión WebSocket.', event);
        setConnectionError('Error en la conexión WebSocket. Revisa la consola para más detalles.');
      };

    } catch (error) {
      console.error('WS: ❌ Error al crear WebSocket:', error);
      setConnectionError('Error al crear conexión WebSocket');
    }
  }, [userId]);

  const disconnect = useCallback(() => {
    console.log('WS: Desconectando WebSocket...');
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Desconexión intencional');
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionError(null);
  }, []);

  useEffect(() => {
    let heartbeatInterval: NodeJS.Timeout | null = null;

    if (userId) {
      connect();

      // Iniciar el heartbeat del cliente
      heartbeatInterval = setInterval(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          console.log("WS: 💓 Enviando ping desde el cliente.");
          wsRef.current.send('ping');
        }
      }, 20000); // 20 segundos

    } else {
      console.log("WS: No userId available yet, skipping WebSocket connection attempt.");
    }

    return () => {
      // Limpiar el intervalo y desconectar
      if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
      }
      disconnect();
    };
  }, [userId, connect, disconnect]);

  return {
    isConnected,
    connectionError,
    latestMessage,
    reconnect: connect,
    disconnect
  };
};
