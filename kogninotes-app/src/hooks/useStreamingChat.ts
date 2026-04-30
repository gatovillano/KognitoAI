// src/hooks/useStreamingChat.ts
import { useState, useCallback, useRef, useEffect } from 'react';
import * as SecureStore from 'expo-secure-store';
import { API_URL } from '../api/config';

interface StreamingChatOptions {
  onChunk?: (chunk: string) => void;
  onComplete?: (fullResponse: string) => void;
  onError?: (error: string) => void;
}

interface StreamChatRequest {
  thread_id: string;
  account_id: string;
  user_message: string;
  mode?: string;
}

export const useStreamingChat = (options: StreamingChatOptions = {}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentReasoning, setCurrentReasoning] = useState(''); // Estado para pensamiento
  const wsRef = useRef<WebSocket | null>(null);
  const responseBuffer = useRef('');
  const reasoningBuffer = useRef(''); // Buffer para pensamiento
  const currentTaskId = useRef<string | null>(null);

  // Limpiar WebSocket al desmontar
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connectWebSocket = useCallback(async (accountId: string, token: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return wsRef.current;
    }

    // Construir URL del WebSocket correctamente a partir del origen del API
    // API_URL: 'https://apibase.cuerpolibre.cl/api' -> WS: 'wss://apibase.cuerpolibre.cl'
    const httpBase = API_URL.endsWith('/api')
      ? API_URL.slice(0, -4)  // quita el '/api' final
      : API_URL;
    const wsBase = httpBase.replace(/^http/, 'ws');
    const wsUrl = `${wsBase}/ws/${accountId}?token=${token}`;
    
    return new Promise<WebSocket>((resolve, reject) => {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Chat WebSocket connected');
        wsRef.current = ws;
        resolve(ws);
      };

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          
          // Solo procesar si es el taskId actual o si no hay taskId (broadcast)
          if (currentTaskId.current && data.taskId && data.taskId !== currentTaskId.current) return;

          if (data.type === 'stream_chunk') {
            responseBuffer.current += data.chunk;
            setCurrentResponse(responseBuffer.current);
            options.onChunk?.(data.chunk);
          } else if (data.type === 'reasoning_chunk') {
            reasoningBuffer.current += data.chunk;
            setCurrentReasoning(reasoningBuffer.current);
            options.onChunk?.(data.chunk);
          } else if (data.type === 'stream_end') {
            const final = responseBuffer.current;
            options.onComplete?.(final);
            setIsLoading(false);
            currentTaskId.current = null;
          } else if (data.type === 'error') {
            options.onError?.(data.message);
            setIsLoading(false);
          }
        } catch (err) {
          console.debug('WS Non-JSON message:', e.data);
        }
      };

      ws.onerror = (e) => {
        console.error('WS Error:', e);
        options.onError?.('Error en la conexión en tiempo real');
        setIsLoading(false);
        reject(e);
      };

      ws.onclose = () => {
        console.log('WS Shared Connection closed');
        wsRef.current = null;
      };
    });
  }, [options]);

  const sendMessage = useCallback(async (request: StreamChatRequest) => {
    setIsLoading(true);
    setCurrentResponse('');
    setCurrentReasoning('');
    responseBuffer.current = '';
    reasoningBuffer.current = '';

    try {
      const token = await SecureStore.getItemAsync('userToken');
      if (!token) throw new Error('No auth token found');

      // 1. Asegurar conexión WebSocket
      await connectWebSocket(request.account_id, token);

      // 2. Enviar petición inicial via HTTP
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const resData = await response.json();
      currentTaskId.current = resData.taskId;
      
      return resData.taskId;

    } catch (error) {
      console.error('Streaming error:', error);
      options.onError?.(error instanceof Error ? error.message : 'Unknown error');
      setIsLoading(false);
    }
  }, [connectWebSocket, options]);

  const cancelStream = useCallback(() => {
    if (wsRef.current) {
        // Enviar cancelación si el backend lo soporta, o simplemente cerrar
        wsRef.current.close();
        wsRef.current = null;
    }
    setIsLoading(false);
  }, []);

  return {
    sendMessage,
    cancelStream,
    isLoading,
    currentResponse,
    currentReasoning,
  };
};

