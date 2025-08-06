'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, MessageSquare, Quote, User, Bot, Calendar, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { InlineMarkdownRenderer } from './InlineMarkdownRenderer';

// Interfaces
interface ChatThread {
  id: string;
  title: string;
  created_at: string;
}

interface ChatMessage {
  text: string;
  sender: 'user' | 'ai';
  created_at: string;
  thread_id: string;
  thread_title: string;
}

interface MessageSearchResult {
  message: ChatMessage;
  context: string;
}

interface ChatSearchDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
}

// Componente para resaltar coincidencias
const HighlightMatch = ({ text, term }: { text: string; term: string }) => {
  if (!term) return <>{text}</>;
  const parts = text.split(new RegExp(`(${term})`, 'gi'));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === term.toLowerCase() ? (
          <mark key={i} className="bg-primary/20 text-primary font-medium rounded px-1">
            {part}
          </mark>
        ) : (
          part
        )
      )}
    </>
  );
};

export function ChatSearchDialog({
  isOpen,
  onOpenChange,
  searchTerm,
  setSearchTerm,
}: ChatSearchDialogProps) {
  const router = useRouter();
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [messages, setMessages] = useState<MessageSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const performSearch = useCallback(async (term: string) => {
    if (!term.trim() || term.length < 3) {
      setThreads([]);
      setMessages([]);
      return;
    }
    setIsSearching(true);
    try {
      // Asumimos un nuevo endpoint unificado para la búsqueda
      const response = await apiClient.get('/api/search/all', {
        params: { query: term },
      });
      setThreads(response.data.threads || []);
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Error performing search:', error);
      toast.error('Error al realizar la búsqueda.');
      setThreads([]);
      setMessages([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (isOpen) {
        performSearch(searchTerm);
      }
    }, 300); // Debounce para no buscar en cada pulsación

    return () => clearTimeout(debounceTimer);
  }, [searchTerm, isOpen, performSearch]);

  const handleThreadClick = (threadId: string) => {
    onOpenChange(false);
    setSearchTerm('');
    router.push(`/chat/${threadId}`);
  };
  
  const handleMessageClick = (threadId: string, messageText: string) => {
    onOpenChange(false);
    setSearchTerm('');
    // Navega al chat y pasa el texto del mensaje para resaltarlo (funcionalidad futura)
    router.push(`/chat/${threadId}?highlight=${encodeURIComponent(messageText)}`);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl h-[90vh] flex flex-col p-0">
        <DialogHeader className="p-4 border-b">
          <DialogTitle className="text-xl font-bold flex items-center gap-3">
            <Search className="h-5 w-5 text-primary" />
            Búsqueda Avanzada
          </DialogTitle>
          <div className="relative mt-2">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Buscar en todo el historial..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 h-11 text-base"
              autoFocus
            />
          </div>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1 overflow-hidden p-4">
          {/* Columna Izquierda: Hilos de Chat */}
          <div className="flex flex-col overflow-hidden md:col-span-1 bg-muted/50 rounded-lg border">
            <h3 className="text-base font-semibold p-3 border-b bg-background/50">
              Conversaciones ({threads.length})
            </h3>
            <ScrollArea className="flex-1">
              {isSearching && threads.length === 0 ? (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Buscando...
                </div>
              ) : threads.length > 0 ? (
                <div className="p-2 space-y-1">
                  {threads.map(thread => (
                    <div
                      key={thread.id}
                      onClick={() => handleThreadClick(thread.id)}
                      className="p-2 rounded-md hover:bg-primary/10 cursor-pointer transition-colors"
                    >
                      <div className="font-medium text-sm truncate">
                        <HighlightMatch text={thread.title} term={searchTerm} />
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(thread.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  {searchTerm.length < 3 ? "Escribe al menos 3 caracteres" : "No se encontraron chats."}
                </div>
              )}
            </ScrollArea>
          </div>

          {/* Columna Derecha: Mensajes */}
          <div className="flex flex-col overflow-hidden md:col-span-2 bg-muted/50 rounded-lg border">
            <h3 className="text-base font-semibold p-3 border-b bg-background/50">
              Mensajes ({messages.length})
            </h3>
            <ScrollArea className="flex-1">
              {isSearching && messages.length === 0 ? (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Buscando...
                </div>
              ) : messages.length > 0 ? (
                <div className="p-2 space-y-2">
                  {messages.map((result, index) => (
                    <div
                      key={`${result.message.thread_id}-${index}`}
                      onClick={() => handleMessageClick(result.message.thread_id, result.message.text)}
                      className="border rounded-lg p-3 hover:bg-background transition-colors group cursor-pointer"
                    >
                      <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
                        {result.message.sender === 'user' ? <User className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
                        <span className="font-medium">{result.message.sender === 'user' ? 'Tú' : 'KAI'}</span>
                        <span>en</span>
                        <span className="font-semibold text-primary truncate">
                          <HighlightMatch text={result.message.thread_title} term={searchTerm} />
                        </span>
                      </div>
                      <p className="text-sm text-foreground/90">
                        <HighlightMatch text={result.context} term={searchTerm} />
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  {searchTerm.length < 3 ? "Escribe para buscar mensajes." : "No se encontraron mensajes."}
                </div>
              )}
            </ScrollArea>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}