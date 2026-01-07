import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  taskId?: string; // Añadido para la nueva arquitectura de streaming
  [key: string]: any;
}

interface UseWebSocketOptions {
  userId?: string;
  onMessage?: (message: WebSocketMessage) => void;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const { userId, onMessage } = options;
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Usar ref para onMessage para evitar reconexiones innecesarias si la función cambia
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    console.log('WS: Intentando conectar...');
    try {
      const token = localStorage.getItem('authToken');
      if (!token || !userId) {
        console.error('WS: No hay token de acceso o ID de usuario disponible. No se puede conectar.');
        setConnectionError('No hay token de acceso o ID de usuario disponible');
        return;
      }

      // Verificar conectividad básica antes de intentar WebSocket
      if (!navigator.onLine) {
        console.error('WS: No hay conexión a internet disponible.');
        setConnectionError('No hay conexión a internet. Verifica tu conexión y vuelve a intentar.');
        return;
      }

      if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
        console.log('WS: Cerrando conexión WebSocket existente antes de abrir una nueva.');
        wsRef.current.close(1000, 'Reconexión');
        wsRef.current = null;
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

        // Smart Reset: No resetear intentos inmediatamente para evitar bucles de flapping.
        // Solo resetear si la conexión permanece estable por 5 segundos.
        setTimeout(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            reconnectAttempts.current = 0;
            console.log('WS: Conexión estable por 5s, reseteando contador de intentos.');
          }
        }, 5000);
      };

      wsRef.current.onmessage = (event) => {
        const msgStr = event.data as string;
        if (!msgStr) return;

        if (msgStr === 'ping') {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send('pong');
          }
          return;
        }

        if (msgStr === 'pong') {
          return;
        }

        try {
          const message: WebSocketMessage = JSON.parse(msgStr);
          if (onMessageRef.current) {
            onMessageRef.current(message);
          }
        } catch (error) {
          console.error('WS: ❌ ERROR CRÍTICO al parsear mensaje WebSocket:', error, 'Mensaje RAW recibido:', msgStr);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log(`WS: 🔌 WebSocket desconectado. Código: ${event.code}, Razón: "${event.reason}", Limpio: ${event.wasClean}.`);
        setIsConnected(false);

        // Log detallado del evento de cierre
        console.warn('WS: Detalles del cierre:', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
          timestamp: new Date().toISOString(),
          attempts: reconnectAttempts.current
        });

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
        console.error('WS: ❌ Se ha producido un error en la conexión WebSocket.', {
          event,
          readyState: wsRef.current?.readyState,
          url: wsRef.current?.url,
          timestamp: new Date().toISOString()
        });

        // Determinar tipo de error basado en readyState
        let errorMessage = 'Error en la conexión WebSocket.';
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          errorMessage = 'La conexión WebSocket se cerró inesperadamente. Verifica tu conexión a internet.';
        } else if (wsRef.current?.readyState === WebSocket.CONNECTING) {
          errorMessage = 'Error durante la conexión inicial. Verifica la URL del servidor.';
        } else {
          errorMessage = 'Error desconocido en WebSocket. Revisa la consola para más detalles.';
        }

        setConnectionError(errorMessage);
      };

    } catch (error) {
      console.error('WS: ❌ Error al crear WebSocket:', error);
      setConnectionError('Error al crear conexión WebSocket');
    }
  }, [userId]); // Removed onMessage from dependencies

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

      heartbeatInterval = setInterval(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send('ping');
        }
      }, 20000);

    } else {
      console.log("WS: No userId available yet, skipping WebSocket connection attempt.");
    }

    return () => {
      if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
      }
      disconnect();
    };
  }, [userId, connect, disconnect]);

  return {
    isConnected,
    connectionError,
    reconnect: connect,
    disconnect,
    // Información de diagnóstico
    diagnostics: {
      readyState: wsRef.current?.readyState,
      url: wsRef.current?.url,
      reconnectAttempts: reconnectAttempts.current,
      lastError: connectionError
    }
  };
}
