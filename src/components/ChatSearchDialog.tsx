'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Search, Copy, Quote, User, Bot, Calendar } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';

interface ChatMessage {
  text: string;
  sender: 'user' | 'ai';
  created_at: string;
  image_base64?: string;
  document_url?: string;
}

interface SearchResult {
  message: ChatMessage;
  matchedText: string;
  context: string;
  messageIndex: number;
}

interface ChatSearchDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  messages: ChatMessage[];
  onSelectQuote?: (quote: string, context: string) => void;
}

export function ChatSearchDialog({ 
  isOpen, 
  onOpenChange, 
  messages, 
  onSelectQuote 
}: ChatSearchDialogProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Función para buscar en los mensajes
  const searchMessages = (term: string) => {
    if (!term.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    const results: SearchResult[] = [];
    const searchLower = term.toLowerCase();

    messages.forEach((message, index) => {
      const messageText = message.text.toLowerCase();
      const searchIndex = messageText.indexOf(searchLower);
      
      if (searchIndex !== -1) {
        // Extraer contexto alrededor de la coincidencia
        const contextStart = Math.max(0, searchIndex - 50);
        const contextEnd = Math.min(message.text.length, searchIndex + term.length + 50);
        const context = message.text.substring(contextStart, contextEnd);
        
        // Texto coincidente
        const matchStart = Math.max(0, searchIndex);
        const matchEnd = Math.min(message.text.length, searchIndex + term.length);
        const matchedText = message.text.substring(matchStart, matchEnd);

        results.push({
          message,
          matchedText,
          context: contextStart > 0 ? '...' + context : context,
          messageIndex: index
        });
      }
    });

    setSearchResults(results);
    setIsSearching(false);
  };

  // Efecto para buscar cuando cambia el término
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      searchMessages(searchTerm);
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [searchTerm, messages]);

  // Función para copiar cita
  const handleCopyQuote = (result: SearchResult) => {
    const quote = `"${result.context.replace(/^\.\.\./, '').replace(/\.\.\.$/, '')}"`;
    const sender = result.message.sender === 'user' ? 'Usuario' : 'Kognito';
    const date = new Date(result.message.created_at).toLocaleDateString();
    const fullQuote = `${quote}\n\n— ${sender}, ${date}`;
    
    navigator.clipboard.writeText(fullQuote).then(() => {
      toast.success('Cita copiada al portapapeles');
    }).catch(() => {
      toast.error('Error al copiar la cita');
    });
  };

  // Función para seleccionar cita (si se proporciona callback)
  const handleSelectQuote = (result: SearchResult) => {
    if (onSelectQuote) {
      onSelectQuote(result.matchedText, result.context);
    }
    onOpenChange(false);
  };

  // Función para resaltar texto coincidente
  const highlightMatch = (text: string, searchTerm: string) => {
    if (!searchTerm) return text;
    
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <mark key={index} className="bg-primary/20 text-primary font-medium rounded px-1">
          {part}
        </mark>
      ) : part
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
        <DialogHeader className="pb-4">
          <DialogTitle className="text-2xl font-bold flex items-center gap-2">
            <Search className="h-6 w-6 text-primary" />
            Buscar en el Chat
          </DialogTitle>
        </DialogHeader>

        {/* Barra de búsqueda */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Buscar mensajes, citas o contenido específico..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 h-12 text-base"
            autoFocus
          />
        </div>

        {/* Estadísticas de búsqueda */}
        {searchTerm && (
          <div className="flex items-center gap-4 mb-4 text-sm text-muted-foreground">
            <span>
              {isSearching ? 'Buscando...' : `${searchResults.length} resultado${searchResults.length !== 1 ? 's' : ''} encontrado${searchResults.length !== 1 ? 's' : ''}`}
            </span>
            {searchResults.length > 0 && (
              <Badge variant="outline" className="text-xs">
                {searchResults.filter(r => r.message.sender === 'user').length} del usuario, {' '}
                {searchResults.filter(r => r.message.sender === 'ai').length} de Kognito
              </Badge>
            )}
          </div>
        )}

        {/* Resultados de búsqueda */}
        <ScrollArea className="flex-1">
          <AnimatePresence>
            {searchResults.length > 0 ? (
              <div className="space-y-4">
                {searchResults.map((result, index) => (
                  <motion.div
                    key={`${result.messageIndex}-${index}`}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.2, delay: index * 0.05 }}
                    className="border border-border rounded-lg p-4 hover:bg-muted/50 transition-colors group"
                  >
                    <div className="flex items-start gap-3">
                      {/* Avatar del remitente */}
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        result.message.sender === 'user' 
                          ? 'bg-muted text-foreground' 
                          : 'bg-primary/10 text-primary'
                      }`}>
                        {result.message.sender === 'user' ? (
                          <User className="h-4 w-4" />
                        ) : (
                          <Bot className="h-4 w-4" />
                        )}
                      </div>

                      {/* Contenido del mensaje */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-medium text-sm">
                            {result.message.sender === 'user' ? 'Usuario' : 'Kognito'}
                          </span>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Calendar className="h-3 w-3" />
                            {new Date(result.message.created_at).toLocaleDateString('es-ES', {
                              day: 'numeric',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </div>
                        </div>
                        
                        <p className="text-sm leading-relaxed mb-3">
                          {highlightMatch(result.context, searchTerm)}
                        </p>

                        {/* Botones de acción */}
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleCopyQuote(result)}
                            className="h-8 px-3 text-xs"
                          >
                            <Copy className="h-3 w-3 mr-1" />
                            Copiar Cita
                          </Button>
                          {onSelectQuote && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleSelectQuote(result)}
                              className="h-8 px-3 text-xs"
                            >
                              <Quote className="h-3 w-3 mr-1" />
                              Usar Cita
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : searchTerm && !isSearching ? (
              <div className="text-center py-12">
                <Search className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No se encontraron resultados</h3>
                <p className="text-muted-foreground">
                  Intenta con otros términos de búsqueda o verifica la ortografía.
                </p>
              </div>
            ) : !searchTerm ? (
              <div className="text-center py-12">
                <Quote className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">Buscar en el Chat</h3>
                <p className="text-muted-foreground">
                  Escribe algo en el campo de búsqueda para encontrar mensajes, citas o contenido específico.
                </p>
              </div>
            ) : null}
          </AnimatePresence>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
