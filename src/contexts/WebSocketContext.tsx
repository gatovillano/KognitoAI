'use client';

import { createContext, useContext, ReactNode, useMemo } from 'react';
import { useWebSocket, WebSocketMessage } from '@/hooks/useWebSocket';
import { useAuth } from '@/contexts/AuthContext';

interface WebSocketContextType {
  latestMessage: WebSocketMessage | null;
  isConnected: boolean;
  connectionError: string | null;
  reconnect: () => void;
  disconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const { user } = useAuth();
  const { 
    isConnected,
    connectionError,
    latestMessage,
    reconnect,
    disconnect
  } = useWebSocket({ userId: user?.id });

  const contextValue = useMemo(() => {
    console.log('[WebSocketContext] Context value updated. Latest message:', latestMessage);
    return {
      latestMessage,
      isConnected,
      connectionError,
      reconnect,
      disconnect
    };
  }, [latestMessage, isConnected, connectionError, reconnect, disconnect]);

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