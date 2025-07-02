// src/hooks/useStreamingChat.ts

import { useState, useCallback, useRef } from 'react';

interface StreamingChatOptions {
  onChunk?: (chunk: string) => void;
  onComplete?: (fullResponse: string) => void;
  onError?: (error: string) => void;
}

interface StreamChatRequest {
  thread_id: string;
  account_id: string;
  user_message: string;
  image_base64?: string;
  document_url?: string;
  mode?: string;
}

export const useStreamingChat = (options: StreamingChatOptions = {}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const eventSourceRef = useRef<EventSource | null>(null);

  const sendMessage = useCallback(async (request: StreamChatRequest) => {
    setIsLoading(true);
    setCurrentResponse('');

    try {
      // Obtener token de auth
      const token = localStorage.getItem('auth_token');
      if (!token) {
        throw new Error('No auth token found');
      }

      // Crear URL con parámetros para el stream
      const url = new URL('/api/chat/stream', window.location.origin);
      
      // Enviar request inicial
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Leer stream de respuesta
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }

      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'chunk') {
                fullResponse += data.content;
                setCurrentResponse(fullResponse);
                options.onChunk?.(data.content);
              } else if (data.type === 'done') {
                options.onComplete?.(fullResponse);
                setIsLoading(false);
                return fullResponse;
              } else if (data.type === 'error') {
                throw new Error(data.message);
              }
            } catch (e) {
              // Ignorar líneas que no son JSON válido
              console.debug('Non-JSON line:', line);
            }
          }
        }
      }

    } catch (error) {
      console.error('Streaming error:', error);
      options.onError?.(error instanceof Error ? error.message : 'Unknown error');
      setIsLoading(false);
    }
  }, [options]);

  const cancelStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsLoading(false);
  }, []);

  return {
    sendMessage,
    cancelStream,
    isLoading,
    currentResponse,
  };
};
