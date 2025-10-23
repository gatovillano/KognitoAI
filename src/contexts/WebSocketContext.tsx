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
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const { user } = useAuth();
  const handlersRef = useRef<Set<MessageHandler>>(new Set());

  const handleMessage = useCallback((message: WebSocketMessage) => {
    // Call all registered handlers
    handlersRef.current.forEach(handler => handler(message));
  }, []);

  const {
    isConnected,
    connectionError,
    reconnect,
    disconnect
  } = useWebSocket({ userId: user?.id, onMessage: handleMessage });

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
      registerMessageHandler
    };
  }, [isConnected, connectionError, reconnect, disconnect, registerMessageHandler]);

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};
export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};