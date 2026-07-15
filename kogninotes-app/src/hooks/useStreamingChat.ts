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
  workspace_id?: string;
}

export const useStreamingChat = (options: StreamingChatOptions = {}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentReasoning, setCurrentReasoning] = useState('');
  
  // Nuevos estados para alineación con web
  const [toolName, setToolName] = useState<string | undefined>(undefined);
  const [reactState, setReactState] = useState<string | undefined>(undefined);
  const [isDeepResearchActive, setIsDeepResearchActive] = useState(false);
  const [researchProgress, setResearchProgress] = useState(0);
  const [researchStatus, setResearchStatus] = useState('Iniciando investigación...');
  const [isThinking, setIsThinking] = useState(false);
  const [researchCompletedEvent, setResearchCompletedEvent] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const responseBuffer = useRef('');
  const reasoningBuffer = useRef('');
  const currentTaskId = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connectWebSocket = useCallback(async (accountId: string, token: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return wsRef.current;
    }

    const httpBase = API_URL.endsWith('/api')
      ? API_URL.slice(0, -4)
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
          
          if (currentTaskId.current && data.taskId && data.taskId !== currentTaskId.current) return;

          switch (data.type) {
            case 'stream_start':
              setIsLoading(true);
              setIsThinking(true);
              break;
            case 'reasoning_chunk':
              setIsThinking(false);
              reasoningBuffer.current += data.chunk;
              setCurrentReasoning(reasoningBuffer.current);
              options.onChunk?.(data.chunk);
              break;
            case 'stream_chunk':
              setIsThinking(false);
              responseBuffer.current += data.chunk;
              setCurrentResponse(responseBuffer.current);
              options.onChunk?.(data.chunk);
              break;
            case 'tool_start':
              setToolName(data.tool_name);
              setReactState('ejecutando');
              setIsThinking(true);
              if (data.tool_name === 'deep_research') {
                setIsDeepResearchActive(true);
              }
              break;
            case 'tool_end':
            case 'tool_error':
              if (data.tool_name === 'deep_research') {
                const isBackground = data.background_completion === true;
                if (isBackground || data.type === 'tool_error') {
                  setIsDeepResearchActive(false);
                  if (data.type === 'tool_end') {
                    setResearchCompletedEvent(true);
                  }
                }
              }
              setToolName(undefined);
              setReactState(undefined);
              setIsThinking(false);
              break;
            case 'progress':
              if (data.progress !== undefined) {
                setResearchProgress(data.progress);
              }
              if (data.message) {
                setResearchStatus(data.message);
              }
              break;
            case 'stream_end':
              const final = responseBuffer.current;
              options.onComplete?.(final);
              setIsLoading(false);
              setIsThinking(false);
              setToolName(undefined);
              setReactState(undefined);
              currentTaskId.current = null;
              break;
            case 'error':
              options.onError?.(data.message || 'Error en la respuesta.');
              setIsLoading(false);
              setIsThinking(false);
              setToolName(undefined);
              setReactState(undefined);
              break;
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
    setIsThinking(true);
    setCurrentResponse('');
    setCurrentReasoning('');
    setToolName(undefined);
    setReactState(undefined);
    setResearchProgress(0);
    setResearchStatus('Iniciando investigación...');
    responseBuffer.current = '';
    reasoningBuffer.current = '';

    try {
      const token = await SecureStore.getItemAsync('userToken');
      if (!token) throw new Error('No auth token found');

      await connectWebSocket(request.account_id, token);

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
      setIsThinking(false);
    }
  }, [connectWebSocket, options]);

  const cancelStream = useCallback(() => {
    if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
    }
    setIsLoading(false);
    setIsThinking(false);
  }, []);

  return {
    sendMessage,
    cancelStream,
    isLoading,
    currentResponse,
    currentReasoning,
    toolName,
    reactState,
    isDeepResearchActive,
    researchProgress,
    researchStatus,
    isThinking,
    researchCompletedEvent,
    setResearchCompletedEvent,
  };
};
