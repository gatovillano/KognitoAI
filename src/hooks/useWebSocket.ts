import { useEffect, useRef, useState, useCallback } from 'react';
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
  onLlmChunk?: (data: { chunk: string; thread_id: string; task_id: string; }) => void;
  onLlmStart?: (data: { thread_id: string; task_id: string; message: string; }) => void;
  onLlmEnd?: (data: { thread_id: string; task_id: string; message: string; tool_code?: string; sources?: any[]; }) => void;
  onLlmError?: (data: { thread_id: string; task_id: string; message: string; }) => void;
  onLlmStatus?: (data: { thread_id: string; task_id: string; message: string; }) => void; // Added
  onToolStatusUpdate?: (data: { thread_id: string; tool_name: string; status: 'start' | 'end' | 'error'; timestamp: string; message?: string; result?: string; error?: string; sources?: any[]; }) => void;
  onThreadTitleUpdated?: (data: { thread_id: string; new_title: string; }) => void; // Added
  onToolCode?: (data: { thread_id: string; task_id: string; tool_code: string; }) => void;
  userId?: string; // <--- AÑADIR ESTA PROP
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const { userId } = options; // <--- OBTENER EL USER ID DE LAS OPCIONES
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    console.log('WS: Intentando conectar...'); // Nuevo log
    try {
      const token = localStorage.getItem('authToken');
      // const userInfo = localStorage.getItem('userInfo'); // Ya no es necesario aquí si userId viene de props
      
      if (!token || !userId) { // <--- USAR userId DE LAS PROPS
        console.error('WS: No hay token de acceso o ID de usuario disponible. No se puede conectar.'); // Nuevo log
        setConnectionError('No hay token de acceso o ID de usuario disponible');
        return;
      }

      // const { id: userId } = JSON.parse(userInfo); // Ya no es necesario

      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || window.location.origin;
      console.log(`WS: apiBaseUrl (antes de parsear): ${apiBaseUrl}`); // Nuevo log para depuración
      let wsProtocol = 'ws';
      let wsHost = '';

      try {
        const url = new URL(apiBaseUrl);
        wsProtocol = url.protocol === 'https:' ? 'wss' : 'ws';
        wsHost = url.host;
      } catch (e) {
        console.error("WS: Error parsing API_BASE_URL, falling back to window.location.origin", e); // Nuevo log
        wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        wsHost = window.location.host;
      }
      
      

      const wsUrl = `${wsProtocol}://${wsHost}/ws/${userId}?token=${encodeURIComponent(token)}`;
      console.log(`WS: Intentando conectar a: ${wsUrl}`); // Log detallado de la URL
      
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WS: 🔌 WebSocket conectado exitosamente.'); // Log más claro
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('WS: 📨 Mensaje WebSocket recibido:', message);

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

            case 'llm_chunk':
                if (options.onLlmChunk) {
                    options.onLlmChunk(message as any);
                }
                break;
            case 'llm_start':
                if (options.onLlmStart) {
                    options.onLlmStart(message as any);
                }
                break;
            case 'llm_end':
                if (options.onLlmEnd) {
                    options.onLlmEnd(message as any);
                }
                break;
            case 'llm_error':
                if (options.onLlmError) {
                    options.onLlmError(message as any);
                }
                toast.error(`Error del LLM: ${message.message}`);
                break;
            case 'llm_status':
                if (options.onLlmStatus) {
                    options.onLlmStatus(message as any);
                }
                break;
            case 'tool_status':
                if (options.onToolStatusUpdate) {
                    options.onToolStatusUpdate(message as any);
                }
                break;
            case 'thread_title_updated':
                if (options.onThreadTitleUpdated) {
                    options.onThreadTitleUpdated(message as any);
                }
                break;
            case 'tool_code': // Added case for tool_code
                if (options.onToolCode) {
                    options.onToolCode(message as any);
                }
                break;

            default:
              console.log('WS: 📨 Mensaje WebSocket no manejado:', message);
          }
        } catch (error) {
          console.error('WS: ❌ Error al procesar mensaje WebSocket:', error);
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
          const errorMessage = 'No se pudo reconectar al servidor después de varios intentos. Verifica la conexión y la configuración del servidor.';
          console.error(`WS: ${errorMessage}`);
          setConnectionError(errorMessage);
          toast.error("Error de conexión", {
            description: errorMessage,
          });
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
  }, [options, userId]); // <--- AÑADIR userId A LAS DEPENDENCIAS DE useCallback

  const disconnect = useCallback(() => {
    console.log('WS: Desconectando WebSocket...'); // Nuevo log
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
    console.log('WS: useEffect: Montando useWebSocket hook.');
    if (userId) {
      connect();
    } else {
      console.log("WS: No userId available yet, skipping WebSocket connection attempt.");
    }

    return () => {
      console.log('WS: useEffect: Desmontando useWebSocket hook. Limpiando...');
      disconnect();
    };
  }, [userId, connect, disconnect]);

  return {
    isConnected,
    connectionError,
    reconnect: connect,
    disconnect
  };
};
