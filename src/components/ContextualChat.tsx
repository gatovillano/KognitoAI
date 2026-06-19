'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { MessageSquare, Send, X, Minimize2, Maximize2, Loader2, Sparkles, Settings, Notebook } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { useAuth } from '@/contexts/AuthContext';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { Source, SourceButton } from '@/components/SourceButton';
import { processMessageWithCitations, collectSourcesFromMessage, getSourceIdentityKey } from '@/lib/chatUtils';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface Message {
    text: string;
    sender: 'user' | 'ai';
    timestamp: Date;
    sources?: Source[];
    ragContext?: any[]; // Para contexto RAG adicional
    chunks?: string[]; // Para soporte de streaming
    tool_code?: string; // Para código de herramientas
    document_url?: string; // Para documentos adjuntos
}

interface ContextualChatProps {
    isOpen: boolean;
    onClose: () => void;
    context: {
        type: 'table' | 'graph' | 'analysis' | 'collection' | 'note';
        id: string;
        snapshot?: any;
        full_text?: string;
    };
    title: string;
}

export function ContextualChat({ isOpen, onClose, context, title }: ContextualChatProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isMinimized, setIsMinimized] = useState(false);
    const [isSending, setIsSending] = useState(false);
    const [threadId, setThreadId] = useState<string | null>(null);

    const scrollRef = useRef<HTMLDivElement>(null);
    const { registerMessageHandler } = useWebSocketContext();
    const { user } = useAuth();

    // Inicializar hilo de chat
    useEffect(() => {
        const initChat = async () => {
            try {
                const enrichedContext = { ...context };
                if (enrichedContext.type === 'analysis' && enrichedContext.snapshot) {
                    enrichedContext.full_text = typeof enrichedContext.snapshot === 'string'
                        ? enrichedContext.snapshot
                        : JSON.stringify(enrichedContext.snapshot, null, 2);
                } else if (enrichedContext.type === 'note' && enrichedContext.snapshot) {
                    enrichedContext.full_text = `Título: ${enrichedContext.snapshot.title || 'Sin título'}\n\nContenido:\n${enrichedContext.snapshot.content || ''}`;
                }

                const response = await apiClient.post('/api/threads', {
                    title: `Chat: ${title}`,
                    context: enrichedContext // Enviar contexto enriquecido al crear el hilo
                });
                setThreadId(response.data.id);
            } catch (error) {
                console.error('Error creating thread:', error);
            }
        };
        if (isOpen && !threadId) {
            initChat();
        }
    }, [isOpen, threadId, title, context]);

    // Manejar mensajes de WebSocket
    useEffect(() => {
        if (!threadId) return;

        const unregister = registerMessageHandler((message) => {
            if (!message || (message.thread_id && message.thread_id !== threadId)) return;

            switch (message.type) {
                case 'stream_start':
                    setIsSending(true);
                    // Crear mensaje placeholder para el streaming
                    setMessages(prev => [...prev, {
                        text: '',
                        sender: 'ai',
                        timestamp: new Date(),
                        sources: [],
                        ragContext: [],
                        chunks: [] // Inicializar chunks para compatibilidad con MarkdownRenderer
                    }]);
                    break;

                case 'stream_chunk':
                    // Acumular chunks en el último mensaje
                    setMessages(prev => {
                        if (prev.length === 0) return prev;
                        const lastMessage = prev[prev.length - 1];
                        if (lastMessage.sender !== 'ai') return prev;

                        const chunk = message.chunk || message.content || '';
                        return [
                            ...prev.slice(0, -1),
                            {
                                ...lastMessage,
                                text: lastMessage.text + chunk,
                                chunks: [...(lastMessage.chunks || []), chunk] // Acumular chunks
                            }
                        ];
                    });
                    break;

                case 'stream_end':
                    // Actualizar el último mensaje con las fuentes y ragContext recibidos
                    if (message.sources !== undefined || message.ragContext !== undefined) {
                        setMessages(prev => {
                            if (prev.length === 0) return prev;
                            const lastMessage = prev[prev.length - 1];
                            if (lastMessage.sender !== 'ai') return prev;

                            return [
                                ...prev.slice(0, -1),
                                {
                                    ...lastMessage,
                                    sources: message.sources || [],
                                    ragContext: message.ragContext || []
                                }
                            ];
                        });
                    }
                    setIsSending(false);
                    break;

                case 'agent_response':
                    // Fallback para respuestas no-streaming
                    setMessages(prev => {
                        // Verificar si ya existe un mensaje en streaming
                        const lastMessage = prev[prev.length - 1];
                        if (lastMessage?.sender === 'ai' && lastMessage.text === '') {
                            // Actualizar el mensaje placeholder
                            return [
                                ...prev.slice(0, -1),
                                {
                                    text: message.response_text,
                                    sender: 'ai',
                                    timestamp: new Date(),
                                    sources: message.sources || [],
                                    ragContext: message.ragContext || []
                                }
                            ];
                        }
                        // Si no hay placeholder, crear nuevo mensaje
                        return [...prev, {
                            text: message.response_text,
                            sender: 'ai',
                            timestamp: new Date(),
                            sources: message.sources || [],
                            ragContext: message.ragContext || []
                        }];
                    });
                    setIsSending(false);
                    break;
            }
        });

        return unregister;
    }, [threadId, registerMessageHandler]);

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || !threadId || isSending) return;

        if (!user?.id) {
            toast.error('Error: Usuario no autenticado.');
            return;
        }

        const userMsg = input.trim();
        setInput('');
        setMessages(prev => [...prev, { text: userMsg, sender: 'user', timestamp: new Date() }]);
        setIsSending(true);

        try {
            const enrichedContext = { ...context };
            if (enrichedContext.type === 'analysis' && enrichedContext.snapshot) {
                enrichedContext.full_text = typeof enrichedContext.snapshot === 'string'
                    ? enrichedContext.snapshot
                    : JSON.stringify(enrichedContext.snapshot, null, 2);
            } else if (enrichedContext.type === 'note' && enrichedContext.snapshot) {
                enrichedContext.full_text = `Título: ${enrichedContext.snapshot.title || 'Sin título'}\n\nContenido:\n${enrichedContext.snapshot.content || ''}`;
            }

            await apiClient.post('/api/chat', {
                thread_id: threadId,
                user_message: userMsg,
                context: enrichedContext, // Enviar el contexto enriquecido!
                account_id: user.id // Usar el ID real del usuario autenticado
            });
        } catch (error) {
            toast.error('Error al enviar mensaje.');
            setIsSending(false);
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: 100, scale: 0.9 }}
                animate={{
                    opacity: 1,
                    y: 0,
                    scale: 1,
                    height: isMinimized ? '60px' : '500px',
                    width: isMinimized ? '250px' : '400px'
                }}
                exit={{ opacity: 0, y: 100, scale: 0.9 }}
                className="fixed bottom-6 right-6 z-[110] shadow-2xl rounded-2xl overflow-hidden border bg-background contextual-chat-container"
                onClick={(e) => e.stopPropagation()}
                onMouseDown={(e) => e.stopPropagation()}
                onMouseUp={(e) => e.stopPropagation()}
                onPointerDown={(e) => e.stopPropagation()}
                onPointerUp={(e) => e.stopPropagation()}
                onFocus={(e) => e.stopPropagation()}
            >
                <Card className="h-full border-0 rounded-none flex flex-col">
                    <CardHeader className="p-4 bg-primary text-primary-foreground flex flex-row items-center justify-between space-y-0">
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-4 w-4" />
                            <CardTitle className="text-sm font-bold">
                                Analista IA: {title}
                            </CardTitle>
                        </div>
                        <div className="flex items-center gap-1">
                            <Button variant="ghost" size="icon" className="h-7 w-7 hover:bg-white/20" onClick={() => setIsMinimized(!isMinimized)}>
                                {isMinimized ? <Maximize2 className="h-4 w-4" /> : <Minimize2 className="h-4 w-4" />}
                            </Button>
                            <Button variant="ghost" size="icon" className="h-7 w-7 hover:bg-white/20" onClick={onClose}>
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    </CardHeader>

                    {!isMinimized && (
                        <>
                            <CardContent className="flex-1 overflow-y-auto p-4 space-y-4" ref={scrollRef}>
                                {messages.length === 0 && (
                                    <div className="text-center py-10 text-muted-foreground">
                                        <MessageSquare className="h-10 w-10 mx-auto mb-2 opacity-20" />
                                        <p className="text-xs">Pregúntame cualquier cosa sobre estos datos.</p>
                                    </div>
                                )}
                                {messages.map((msg, i) => {
                                    // Usar las funciones utilitarias para recolectar fuentes, igual que en ChatMessage.tsx
                                    const { citationSources, additionalSources } = collectSourcesFromMessage(msg.sources, msg.ragContext);

                                    const fullText = msg.chunks?.join('') || msg.text;
                                    const { contentParts, citedSources, uncitedSources, resolvedSources } = processMessageWithCitations(
                                        fullText,
                                        citationSources
                                    );

                                    const citationNumberBySource = new Map(
                                        resolvedSources.map((source, index) => [getSourceIdentityKey(source), index + 1])
                                    );

                                    const displaySources = citedSources.length > 0
                                        ? citedSources
                                        : (citationSources.length > 0 ? citationSources : additionalSources);

                                    const hasSources = msg.sender === 'ai' && displaySources.length > 0;
                                    
                                    return (
                                        <motion.div
                                            key={i}
                                            initial={{ opacity: 0, y: 5 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'} mb-4`}
                                        >
                                            {msg.sender === 'ai' && (msg.text || msg.tool_code) && (
                                                <div className="flex items-center gap-2 mb-1.5 ml-1">
                                                    <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center">
                                                        <Sparkles className="h-3 w-3 text-primary" />
                                                    </div>
                                                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">KAI Assistant</span>
                                                </div>
                                            )}
                                            
                                            <div className={`${msg.sender === 'user'
                                                ? 'max-w-[85%] p-3 rounded-2xl text-sm bg-primary text-primary-foreground rounded-tr-none shadow-sm'
                                                : 'w-full px-1'
                                                }`}>
                                                {msg.sender === 'ai' ? (
                                                    <div className="w-full">
                                                        {msg.tool_code && (
                                                            <div className="bg-blue-900/5 p-2 rounded-lg text-[10px] text-blue-600 font-mono mb-3 border border-blue-200/30">
                                                                <p className="font-bold mb-1 flex items-center gap-1">
                                                                    <Settings className="h-3 w-3" />
                                                                    Herramienta utilizada:
                                                                </p>
                                                                <pre className="whitespace-pre-wrap break-all opacity-80">
                                                                    {JSON.stringify(JSON.parse(msg.tool_code), null, 2)}
                                                                </pre>
                                                            </div>
                                                        )}
                                                        <div className="text-foreground break-words font-sans text-sm leading-relaxed">
                                                            {hasSources ? (
                                                                <MarkdownRenderer
                                                                    contentParts={contentParts}
                                                                    content={fullText}
                                                                    fontSize="text-sm"
                                                                    isStreaming={msg.chunks !== undefined}
                                                                />
                                                            ) : (
                                                                <MarkdownRenderer
                                                                    content={fullText}
                                                                    fontSize="text-sm"
                                                                    isStreaming={msg.chunks !== undefined}
                                                                />
                                                            )}
                                                        </div>

                                                        {/* Sección de Fuentes al final */}
                                                        {hasSources && (
                                                            <motion.div
                                                                initial={{ opacity: 0, y: 5 }}
                                                                animate={{ opacity: 1, y: 0 }}
                                                                transition={{ delay: 0.2 }}
                                                                className="mt-3 pt-3 border-t border-border/10"
                                                            >
                                                                <div className="flex items-center gap-2 mb-2">
                                                                    <div className="p-1 rounded-md bg-primary/10">
                                                                        <Notebook className="h-3 w-3 text-primary" />
                                                                    </div>
                                                                    <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">Fuentes</span>
                                                                </div>
                                                                <div className="flex flex-wrap gap-1.5">
                                                                    {displaySources.map((source, idx) => (
                                                                        <SourceButton
                                                                            key={idx}
                                                                            source={source}
                                                                            citationNumber={citationNumberBySource.get(getSourceIdentityKey(source)) || idx + 1}
                                                                        />
                                                                    ))}
                                                                </div>
                                                            </motion.div>
                                                        )}
                                                    </div>
                                                ) : (
                                                    msg.text
                                                )}
                                            </div>
                                        </motion.div>
                                    );
                                })}
                                {isSending && (
                                    <div className="flex justify-start">
                                        <div className="bg-muted p-3 rounded-2xl rounded-tl-none">
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                            <CardFooter className="p-4 border-t">
                                <form className="flex w-full gap-2" onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
                                    <Input
                                        placeholder="Escribe tu duda..."
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        disabled={isSending}
                                        className="rounded-full"
                                    />
                                    <Button type="submit" size="icon" disabled={isSending || !input.trim()} className="rounded-full shrink-0">
                                        <Send className="h-4 w-4" />
                                    </Button>
                                </form>
                            </CardFooter>
                        </>
                    )}
                </Card>
            </motion.div>
        </AnimatePresence>
    );
}
