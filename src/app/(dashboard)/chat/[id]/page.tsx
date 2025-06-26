// En: src/app/(dashboard)/chat/[id]/page.tsx

'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api';
import { motion } from 'framer-motion';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { toast } from 'sonner';

import { Send, User, Copy, Play, Loader2, Square } from 'lucide-react';

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
  const [isResponding, setIsResponding] = useState(false);
  
  // --- NUEVOS ESTADOS PARA EL AUDIO ---
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (threadId && user) {
      const fetchChatData = async () => {
        setIsResponding(true);
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
  
  useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector('div[data-radix-scroll-area-viewport]');
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [messages, isResponding]);

  useEffect(() => {
    if (textAreaRef.current) {
      textAreaRef.current.style.height = 'auto';
      textAreaRef.current.style.height = `${textAreaRef.current.scrollHeight}px`;
    }
  }, [newMessage]);

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!newMessage.trim() || !user || isResponding) return;
    const userMessage: Message = { text: newMessage, sender: 'user' };
    setMessages((prev) => [...prev, userMessage]);
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
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCopyMessage = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success('Respuesta copiada al portapapeles');
    }).catch(err => {
      console.error('Error al copiar el mensaje: ', err);
      toast.error('No se pudo copiar el mensaje.');
    });
  };

  // --- NUEVA FUNCIÓN PARA REPRODUCIR AUDIO ---
  const handlePlayAudio = async (text: string, index: number) => {
    // Si ya hay un audio reproduciéndose, lo detenemos
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlayingMessageIndex(null);
    }
    
    // Si se hace clic en el mismo botón de "reproduciendo", actúa como un botón de stop
    if (playingMessageIndex === index) {
      return;
    }

    setIsAudioLoading(true);
    setPlayingMessageIndex(index); // Marcamos este mensaje como "cargando/reproduciendo"

    try {
      const response = await apiClient.post('/api/text-to-speech', { text }, {
        responseType: 'blob' // ¡MUY IMPORTANTE para recibir audio!
      });
      
      const audioBlob = new Blob([response.data], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(audioBlob);
      
      audioRef.current = new Audio(audioUrl);
      audioRef.current.play();
      setIsAudioLoading(false);

      audioRef.current.onended = () => {
        setPlayingMessageIndex(null); // Limpiamos el estado cuando termina
        URL.revokeObjectURL(audioUrl); // Liberamos memoria
      };

    } catch (error) {
      toast.error("No se pudo generar el audio.");
      console.error("Error en TTS:", error);
      setIsAudioLoading(false);
      setPlayingMessageIndex(null);
    }
  };

  if (!user && !isResponding) {
    return <div className="flex h-full items-center justify-center"><p>Cargando conversación...</p></div>;
  }
  
  return (
    <div className="flex flex-col h-full">
      <div className="flex-grow overflow-y-hidden">
        <ScrollArea className="h-full" ref={scrollAreaRef}>
          <div className="p-4 md:p-6 space-y-6">
            {messages.map((msg, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
              >
                {/* --- CAMBIO DE FLUJO: RENDERIZADO CONDICIONAL --- */}
                
                {/* VISTA PARA EL MENSAJE DEL USUARIO */}
                {msg.sender === 'user' && (
                  <div className="flex items-start gap-4 justify-end">
                    <div className="rounded-lg p-3 max-w-3xl bg-primary text-primary-foreground">
                      <p className="text-base whitespace-pre-wrap">{msg.text}</p>
                    </div>
                    <Avatar className="h-8 w-8">
                      <AvatarFallback><User className="h-5 w-5"/></AvatarFallback>
                    </Avatar>
                  </div>
                )}

                {/* VISTA PARA EL MENSAJE DE LA IA */}
                {msg.sender === 'ai' && (
                  <div className="flex flex-col items-center">
                    <div className="w-full max-w-3xl mx-auto">
                      <div className="flex items-start gap-4">
                        <Avatar className="h-8 w-8 border">
                          <AvatarImage src="/logo-simple.png" alt="Kognito" />
                          <AvatarFallback>K</AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <div className="font-bold">Kognito</div>
                          <div className="break-words mt-1 text-base">
                            <MarkdownRenderer content={msg.text} />
                          </div>
                          {/* Barra de acciones para la IA */}
                          <div className="mt-2 flex items-center gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleCopyMessage(msg.text)}>
                              <Copy className="h-4 w-4 mr-2" /> Copiar
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handlePlayAudio(msg.text, index)} disabled={isAudioLoading && playingMessageIndex === index}>
                              {isAudioLoading && playingMessageIndex === index && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                              {playingMessageIndex === index && !isAudioLoading && <Square className="h-4 w-4 mr-2" />}
                              {playingMessageIndex !== index && <Play className="h-4 w-4 mr-2" />}
                              Escuchar
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
            {isResponding && 
              <div className="flex items-start gap-4 animate-pulse">
                 <Avatar className="h-8 w-8 border">
                    <AvatarImage src="/logo-simple.png" alt="Kognito" />
                    <AvatarFallback>K</AvatarFallback>
                  </Avatar>
                <div className="rounded-lg p-3 bg-secondary">
                    <p className="text-sm text-muted-foreground">Kognito está pensando...</p>
                </div>
              </div>
            }
          </div>
        </ScrollArea>
      </div>

      <footer className="p-4 border-t shrink-0 bg-background/95 backdrop-blur-sm">
        <form onSubmit={handleSendMessage} className="relative flex items-end gap-2">
          <Textarea
            ref={textAreaRef}
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe un mensaje a Kognito... (Shift + Enter para nueva línea)"
            autoComplete="off"
            disabled={isResponding}
            className="flex-grow resize-none overflow-y-auto pr-12 text-sm"
            rows={1}
            style={{ maxHeight: '200px' }}
          />
          <Button 
            type="submit" 
            size="icon" 
            disabled={isResponding || !newMessage.trim()}
            className="absolute bottom-2 right-2"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </footer>
    </div>
  );
}
