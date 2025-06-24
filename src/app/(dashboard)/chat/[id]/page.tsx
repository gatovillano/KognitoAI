// En: src/app/(dashboard)/chat/[id]/page.tsx
'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Send, User } from 'lucide-react';

// Tipos para los datos que manejaremos
interface Message {
  text: string;
  sender: 'user' | 'ai';
}

interface ThreadDetails {
    id: string;
    title: string;
}

export default function ChatPage() {
  const params = useParams();
  const threadId = params.id as string;
  const { user } = useAuth();

  const [threadDetails, setThreadDetails] = useState<ThreadDetails | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isResponding, setIsResponding] = useState(false); // Para saber si la IA está "escribiendo"
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Efecto para cargar los mensajes cuando el ID del hilo cambia
  useEffect(() => {
    if (threadId && user) {
      const fetchChatData = async () => {
        setIsResponding(true); // Muestra el loader mientras carga
        try {
          const [threadRes, messagesRes] = await Promise.all([
            apiClient.get(`/api/threads/${threadId}`),
            apiClient.get(`/api/threads/${threadId}/messages`)
          ]);
          setThreadDetails(threadRes.data);
          setMessages(messagesRes.data);
        } catch (error) {
          console.error('Error fetching chat data:', error);
          setMessages([{ text: 'No se pudo cargar esta conversación.', sender: 'ai' }]);
        } finally {
          setIsResponding(false);
        }
      };
      fetchChatData();
    }
  }, [threadId, user]);
  
  // Efecto para hacer scroll automático al final cuando llegan mensajes
  useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector('div[data-radix-scroll-area-viewport]');
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !user || isResponding) return;

    const userMessage: Message = { text: newMessage, sender: 'user' };
    setMessages((prev) => [...prev, userMessage]); // Añade el mensaje del usuario al instante
    const messageToSend = newMessage;
    setNewMessage('');
    setIsResponding(true);

    try {
      const response = await apiClient.post('/api/chat', {
        thread_id: threadId,
        account_id: user.id,
        user_message: messageToSend,
      });

      const aiMessage: Message = { text: response.data.response_text, sender: 'ai' };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = { text: 'Lo siento, ocurrió un error al procesar tu mensaje.', sender: 'ai' };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
        setIsResponding(false);
    }
  };
  
  return (
    <div className="flex flex-col h-full bg-card">
      <header className="p-4 border-b shrink-0">
        <h1 className="text-xl font-semibold">{threadDetails?.title || 'Cargando Chat...'}</h1>
      </header>
      
      <div className="flex-grow overflow-y-auto">
        <ScrollArea className="h-full" ref={scrollAreaRef}>
          <div className="p-4 md:p-6 space-y-6">
            {messages.map((msg, index) => (
              <div key={index} className={`flex items-start gap-4 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
                {msg.sender === 'ai' && (
                  <Avatar className="h-8 w-8 border">
                    <AvatarImage src="/logo-simple.png" alt="Kognito" />
                    <AvatarFallback>K</AvatarFallback>
                  </Avatar>
                )}
                <div className={`rounded-lg p-3 max-w-[75%] ${msg.sender === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary'}`}>
                  <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                </div>
                {msg.sender === 'user' && (
                  <Avatar className="h-8 w-8">
                    <AvatarFallback><User className="h-5 w-5"/></AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}
            {isResponding && messages.length > 0 && 
              <div className="flex items-start gap-4">
                 <Avatar className="h-8 w-8 border">
                    <AvatarImage src="/logo-simple.png" alt="Kognito" />
                    <AvatarFallback>K</AvatarFallback>
                  </Avatar>
                <div className="rounded-lg p-3 bg-secondary animate-pulse">
                    <p className="text-sm text-muted-foreground">Kognito está pensando...</p>
                </div>
              </div>
            }
          </div>
        </ScrollArea>
      </div>

      <footer className="p-4 border-t shrink-0">
        <form onSubmit={handleSendMessage} className="flex items-center gap-2">
          <Input
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Escribe un mensaje a Kognito..."
            autoComplete="off"
            disabled={isResponding}
            className="flex-grow"
          />
          <Button type="submit" size="icon" disabled={isResponding}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </footer>
    </div>
  );
}
