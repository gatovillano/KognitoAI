import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

interface UseWebSocketOptions {
  onTitleUpdated?: (data: { file_name: string; new_title: string; progress: number; total: number }) => void;
  onTitleExtractionStarted?: (data: { total_documents: number; message: string }) => void;
  onTitleExtractionCompleted?: (data: { updated_count: number; total_processed: number; message: string }) => void;
  onUploadStarted?: (data: { task_id: string; file_names: string[]; topic: string; created_at: string; }) => void;
  onUploadProgress?: (data: { task_id: string; progress: number; message: string; }) => void;
  onUploadCompleted?: (data: { task_id: string; message: string; }) => void;
  onUploadFailed?: (data: { task_id: string; error_message: string; }) => void;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = () => {
    try {
      const token = localStorage.getItem('authToken');
      if (!token) {
        setConnectionError('No hay token de acceso disponible');
        return;
      }

      // Usar NEXT_PUBLIC_API_URL para la conexión WebSocket
      // Reemplazar http/https por ws/wss
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8889'; // Fallback por si no está definida
      const wsProtocol = apiBaseUrl.startsWith('https') ? 'wss' : 'ws';
      const wsHost = apiBaseUrl.replace(/^https?:\/\//, '');
      const wsUrl = `${wsProtocol}://${wsHost}/ws?token=${encodeURIComponent(token)}`;
      
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('🔌 WebSocket conectado');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('📨 Mensaje WebSocket recibido:', message);

          switch (message.type) {
            case 'title_updated':
              if (options.onTitleUpdated) {
                options.onTitleUpdated({
                  file_name: message.file_name,
                  new_title: message.new_title,
                  progress: message.progress,
                  total: message.total
                });
              }
              // Mostrar toast con el título actualizado
              toast.success(`📄 Título actualizado: ${message.file_name}`, {
                description: `Nuevo título: "${message.new_title}"`
              });
              break;

            case 'title_extraction_started':
              if (options.onTitleExtractionStarted) {
                options.onTitleExtractionStarted({
                  total_documents: message.total_documents,
                  message: message.message
                });
              }
              toast.info(`🚀 ${message.message}`);
              break;

            case 'title_extraction_completed':
              if (options.onTitleExtractionCompleted) {
                options.onTitleExtractionCompleted({
                  updated_count: message.updated_count,
                  total_processed: message.total_processed,
                  message: message.message
                });
              }
              toast.success(`✅ Extracción completada`, {
                description: `${message.updated_count} títulos actualizados`
              });
              break;

            case 'upload_started':
              if (options.onUploadStarted) {
                options.onUploadStarted({
                  task_id: message.task_id,
                  file_names: message.file_names,
                  topic: message.topic,
                  created_at: message.created_at
                });
              }
              toast.info(`📤 Subida iniciada: ${message.file_names.join(', ')} a la colección ${message.topic}`);
              break;

            case 'upload_progress':
              if (options.onUploadProgress) {
                options.onUploadProgress({
                  task_id: message.task_id,
                  progress: message.progress,
                  message: message.message
                });
              }
              // Opcional: mostrar progreso si es relevante
              // toast.info(`Progreso de subida para ${message.task_id}: ${message.progress}%`);
              break;

            case 'upload_completed':
              if (options.onUploadCompleted) {
                options.onUploadCompleted({
                  task_id: message.task_id,
                  message: message.message
                });
              }
              toast.success(`✅ Subida completada: ${message.message}`);
              break;

            case 'upload_failed':
              if (options.onUploadFailed) {
                options.onUploadFailed({
                  task_id: message.task_id,
                  error_message: message.error_message
                });
              }
              toast.error(`❌ Subida fallida: ${message.error_message}`);
              break;

            default:
              console.log('📨 Mensaje WebSocket no manejado:', message);
          }
        } catch (error) {
          console.error('❌ Error al procesar mensaje WebSocket:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('🔌 WebSocket desconectado:', event.code, event.reason);
        setIsConnected(false);
        
        // Intentar reconectar si no fue un cierre intencional
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`🔄 Reintentando conexión en ${delay}ms (intento ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setConnectionError('No se pudo reconectar al servidor');
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('❌ Error en WebSocket:', error);
        setConnectionError('Error de conexión WebSocket');
      };

    } catch (error) {
      console.error('❌ Error al crear WebSocket:', error);
      setConnectionError('Error al crear conexión WebSocket');
    }
  };

  const disconnect = () => {
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
  };

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, []);

  return {
    isConnected,
    connectionError,
    reconnect: connect,
    disconnect
  };
};
