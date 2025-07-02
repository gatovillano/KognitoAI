// src/components/StreamingChatExample.tsx

import React, { useState } from 'react';
import { useStreamingChat } from '@/hooks/useStreamingChat';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface StreamingChatExampleProps {
  threadId: string;
  accountId: string;
}

export const StreamingChatExample: React.FC<StreamingChatExampleProps> = ({
  threadId,
  accountId,
}) => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<string[]>([]);

  const { sendMessage, isLoading, currentResponse } = useStreamingChat({
    onChunk: (chunk) => {
      // Actualización en tiempo real del texto que se está escribiendo
      console.log('Nuevo chunk recibido:', chunk);
    },
    onComplete: (fullResponse) => {
      // Cuando se completa la respuesta, agregarla al historial
      setChatHistory(prev => [...prev, `Usuario: ${message}`, `IA: ${fullResponse}`]);
      setMessage('');
    },
    onError: (error) => {
      console.error('Error en streaming:', error);
      setChatHistory(prev => [...prev, `Error: ${error}`]);
    },
  });

  const handleSendMessage = async () => {
    if (!message.trim() || isLoading) return;

    await sendMessage({
      thread_id: threadId,
      account_id: accountId,
      user_message: message,
    });
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>Chat con Streaming de Baja Latencia</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Historial de chat */}
        <div className="min-h-[300px] max-h-[400px] overflow-y-auto border rounded-lg p-4 bg-gray-50">
          {chatHistory.map((entry, index) => (
            <div key={index} className="mb-2 p-2 rounded">
              <div className={`${entry.startsWith('Usuario:') 
                ? 'text-blue-600 bg-blue-50' 
                : entry.startsWith('Error:')
                ? 'text-red-600 bg-red-50'
                : 'text-green-600 bg-green-50'
              } p-2 rounded`}>
                {entry}
              </div>
            </div>
          ))}
          
          {/* Respuesta en tiempo real */}
          {isLoading && currentResponse && (
            <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
              <div className="text-yellow-700 font-medium">IA escribiendo...</div>
              <div className="text-gray-700 mt-1">{currentResponse}</div>
              <div className="animate-pulse text-yellow-600">●</div>
            </div>
          )}
        </div>

        {/* Input para nuevo mensaje */}
        <div className="flex gap-2">
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Escribe tu mensaje aquí..."
            className="flex-1"
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
          />
          <Button 
            onClick={handleSendMessage}
            disabled={isLoading || !message.trim()}
            className="px-6"
          >
            {isLoading ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"></div>
                Enviando...
              </div>
            ) : (
              'Enviar'
            )}
          </Button>
        </div>

        {/* Indicadores de estado */}
        <div className="text-sm text-gray-500">
          {isLoading ? (
            <div className="flex items-center gap-2">
              <div className="animate-pulse h-2 w-2 bg-green-500 rounded-full"></div>
              Streaming activo - Recibiendo respuesta en tiempo real
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
              Listo para nueva consulta
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
