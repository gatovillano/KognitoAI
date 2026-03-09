import { createContext, useContext, ReactNode, useMemo, useRef, useCallback } from 'react';
import { useWebSocket, WebSocketMessage } from '@/hooks/useWebSocket';
import { useAuth } from '@/contexts/AuthContext';

// Type for the handler function
type MessageHandler = (message: WebSocketMessage) => void;

interface WebSocketContextType {
  isConnected: boolean;
  connectionError: string | null;
  reconnect: () => void;
  disconnect: () => void;
  registerMessageHandler: (handler: MessageHandler) => () => void; // Takes a handler, returns an unregister function
  diagnostics?: {
    readyState?: number;
    url?: string;
    reconnectAttempts?: number;
    lastError?: string | null;
  };
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const { user, token } = useAuth();
  const handlersRef = useRef<Set<MessageHandler>>(new Set());

  const handleMessage = useCallback((message: WebSocketMessage) => {
    // Call all registered handlers
    handlersRef.current.forEach(handler => handler(message));
  }, []);

  const {
    isConnected,
    connectionError,
    reconnect,
    disconnect,
    diagnostics
  } = useWebSocket({ userId: user?.id, authToken: token || undefined, onMessage: handleMessage });

  const registerMessageHandler = useCallback((handler: MessageHandler) => {
    handlersRef.current.add(handler);
    // Return a cleanup function to unregister the handler
    return () => {
      handlersRef.current.delete(handler);
    };
  }, []);

  const contextValue = useMemo(() => {
    return {
      isConnected,
      connectionError,
      reconnect,
      disconnect,
      registerMessageHandler,
      diagnostics
    };
  }, [isConnected, connectionError, reconnect, disconnect, registerMessageHandler, diagnostics]);

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};
// Default no-op implementation when context is not available
const noopContext: WebSocketContextType = {
  isConnected: false,
  connectionError: null,
  reconnect: () => { },
  disconnect: () => { },
  registerMessageHandler: () => () => { },
  diagnostics: {
    readyState: WebSocket.CLOSED,
    url: undefined,
    reconnectAttempts: 0,
    lastError: undefined
  }
};

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  // Return no-op context instead of throwing error
  if (context === undefined) {
    return noopContext;
  }
  return context;
};