'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { Loader2, Lock, Copy, Check, AlertTriangle, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { toast } from 'sonner';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { ChatAvatar } from '@/components/ChatAvatar';
import { processMessageWithCitations } from '@/lib/chatUtils';
import { SourceButton, Source } from '@/components/SourceButton';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface SharedThreadInfo {
    thread: {
        id: string;
        title: string;
        created_at: string | null;
    };
    share_meta: {
        allow_reply: boolean;
        has_password: boolean;
        expiry_date: string | null;
        is_expired: boolean;
    };
}

interface ChatMessage {
    text: string;
    sender: 'user' | 'ai';
    created_at: string;
    image_base64?: string;
    images_base64?: string[];
    sources?: Source[];
    reasoning?: string;
}

interface PaginatedMessages {
    messages: ChatMessage[];
    total: number;
}

export default function SharedChatPage() {
    const params = useParams();
    const token = params?.token as string;

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [passwordRequired, setPasswordRequired] = useState(false);
    const [password, setPassword] = useState('');
    const [shareInfo, setShareInfo] = useState<SharedThreadInfo | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [total, setTotal] = useState(0);
    const [loadingMore, setLoadingMore] = useState(false);
    const [skip, setSkip] = useState(0);
    const [copied, setCopied] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Reply state
    const [replyMessage, setReplyMessage] = useState('');
    const [isSending, setIsSending] = useState(false);
    const [isWaitingResponse, setIsWaitingResponse] = useState(false);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const LIMIT = 50;

    const scrollToBottom = useCallback(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, []);

    const fetchShareInfo = useCallback(async () => {
        try {
            const response = await fetch(`${API_URL}/api/chat/share/${token}/info`);
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Error al cargar la informacion del enlace compartido');
            }
            const data: SharedThreadInfo = await response.json();
            setShareInfo(data);
            setPasswordRequired(data.share_meta.has_password);
        } catch (e: any) {
            setError(e.message);
        }
    }, [token]);

    const fetchMessages = useCallback(async (submitPassword?: string, currentSkip: number = 0, appendAtTop: boolean = true) => {
        if (currentSkip === 0) setLoading(true);
        else setLoadingMore(true);
        setError(null);

        try {
            const payload: { password?: string; skip: number; limit: number } = {
                skip: currentSkip,
                limit: LIMIT,
            };
            if (submitPassword) payload.password = submitPassword;

            const response = await fetch(`${API_URL}/api/chat/share/${token}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (response.status === 401) {
                setPasswordRequired(true);
                setLoading(false);
                setLoadingMore(false);
                return;
            }

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Error al cargar los mensajes');
            }

            const data: PaginatedMessages = await response.json();

            if (currentSkip === 0) {
                setMessages(data.messages);
                setSkip(data.messages.length);
            } else if (appendAtTop) {
                setMessages(prev => [...data.messages, ...prev]);
                setSkip(prev => prev + data.messages.length);
            }
            setTotal(data.total);
            setPasswordRequired(false);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    }, [token]);

    // Fetch latest messages (used after reply to check for new AI response)
    const fetchLatestMessages = useCallback(async () => {
        try {
            const payload: { password?: string; skip: number; limit: number } = {
                skip: 0,
                limit: LIMIT,
            };
            if (password) payload.password = password;

            const response = await fetch(`${API_URL}/api/chat/share/${token}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) return;

            const data: PaginatedMessages = await response.json();
            const newMessages = data.messages;
            const prevCount = messages.length;

            if (newMessages.length > prevCount) {
                setMessages(newMessages);
                setTotal(data.total);
                setSkip(newMessages.length);
                setIsWaitingResponse(false);
                scrollToBottom();
                return true; // New messages found
            }

            // Check if last message changed (AI response appeared)
            if (newMessages.length > 0 && messages.length > 0) {
                const lastNew = newMessages[newMessages.length - 1];
                const lastOld = messages[messages.length - 1];
                if (lastNew.text !== lastOld.text || lastNew.sender !== lastOld.sender) {
                    setMessages(newMessages);
                    setTotal(data.total);
                    setSkip(newMessages.length);
                    if (lastNew.sender === 'ai') {
                        setIsWaitingResponse(false);
                        scrollToBottom();
                        return true;
                    }
                }
            }

            return false;
        } catch {
            return false;
        }
    }, [token, password, messages, scrollToBottom]);

    // Poll for new messages after sending a reply
    const startPolling = useCallback(() => {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

        let attempts = 0;
        const maxAttempts = 120; // 2 minutes at 1s intervals

        pollIntervalRef.current = setInterval(async () => {
            attempts++;
            const found = await fetchLatestMessages();
            if (found || attempts >= maxAttempts) {
                if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                }
                if (attempts >= maxAttempts) {
                    setIsWaitingResponse(false);
                    toast.info('La respuesta esta tardando. Recarga la pagina para ver los nuevos mensajes.');
                }
            }
        }, 1000);
    }, [fetchLatestMessages]);

    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }
        };
    }, []);

    useEffect(() => {
        if (token) fetchShareInfo();
    }, [token, fetchShareInfo]);

    useEffect(() => {
        if (shareInfo && !shareInfo.share_meta.has_password) {
            fetchMessages();
        }
    }, [shareInfo, fetchMessages]);

    useEffect(() => {
        if (messages.length > 0 && !isWaitingResponse) {
            scrollToBottom();
        }
    }, [messages.length, isWaitingResponse, scrollToBottom]);

    const handlePasswordSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        fetchMessages(password);
    };

    const loadMoreMessages = () => {
        if (skip < total && !loadingMore) {
            fetchMessages(passwordRequired ? password : undefined, skip);
        }
    };

    const handleSendReply = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!replyMessage.trim() || isSending) return;

        const messageText = replyMessage.trim();
        setReplyMessage('');
        setIsSending(true);
        setIsWaitingResponse(true);

        // Optimistically add the user message
        const userMessage: ChatMessage = {
            text: messageText,
            sender: 'user',
            created_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, userMessage]);
        setTimeout(scrollToBottom, 50);

        try {
            const payload: { message: string; password?: string } = {
                message: messageText,
            };
            if (password) payload.password = password;

            const response = await fetch(`${API_URL}/api/chat/share/${token}/reply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Error al enviar la respuesta');
            }

            toast.success('Mensaje enviado. Esperando respuesta...');
            startPolling();
        } catch (e: any) {
            toast.error(e.message);
            // Remove the optimistic message on error
            setMessages(prev => prev.filter(m => m !== userMessage));
            setIsWaitingResponse(false);
        } finally {
            setIsSending(false);
        }
    };

    const copyLink = () => {
        navigator.clipboard.writeText(window.location.href);
        setCopied(true);
        toast.success('Enlace copiado al portapapeles');
        setTimeout(() => setCopied(false), 2000);
    };

    const handleSourceClick = (source: Source) => {
        if (source.url) {
            window.open(source.url, '_blank', 'noopener,noreferrer');
        }
    };

    if (loading && !shareInfo) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                    <p className="text-muted-foreground">Cargando conversacion compartida...</p>
                </div>
            </div>
        );
    }

    if (error && !shareInfo) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center p-4">
                <Alert variant="destructive" className="max-w-md">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            </div>
        );
    }

    if (passwordRequired) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center p-4">
                <Card className="w-full max-w-sm">
                    <CardHeader className="text-center">
                        <div className="mx-auto bg-muted p-3 rounded-full w-fit mb-4">
                            <Lock className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <CardTitle>Conversacion Protegida</CardTitle>
                        <p className="text-sm text-muted-foreground">
                            Introduce la contrasena para acceder a esta conversacion.
                        </p>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handlePasswordSubmit} className="space-y-4">
                            <Input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Contrasena"
                                required
                            />
                            {error && (
                                <p className="text-sm text-destructive">{error}</p>
                            )}
                            <Button type="submit" className="w-full">
                                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Acceder
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (!shareInfo) return null;

    const allowReply = shareInfo.share_meta.allow_reply;

    return (
        <div className="min-h-screen bg-background flex flex-col">
            {/* Header */}
            <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10">
                <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
                    <div>
                        <h1 className="text-lg font-semibold truncate">{shareInfo.thread.title}</h1>
                        <p className="text-xs text-muted-foreground">
                            Compartido desde Kognito AI
                            {allowReply && ' - Respuestas habilitadas'}
                        </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={copyLink}>
                        {copied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
                        {copied ? 'Copiado' : 'Copiar Enlace'}
                    </Button>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto pb-2">
                <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
                    {skip < total && (
                        <div className="flex justify-center">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={loadMoreMessages}
                                disabled={loadingMore}
                            >
                                {loadingMore && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Cargar mensajes anteriores
                            </Button>
                        </div>
                    )}

                    {messages.map((msg, index) => {
                        const isUser = msg.sender === 'user';
                        const { contentParts, citedSources, uncitedSources } = msg.sources
                            ? processMessageWithCitations(msg.text, msg.sources)
                            : { contentParts: undefined, citedSources: [], uncitedSources: [] };

                        return (
                            <div
                                key={`${index}-${msg.created_at}`}
                                className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                            >
                                {!isUser && (
                                    <div className="shrink-0 mt-1">
                                        <ChatAvatar sender="ai" />
                                    </div>
                                )}
                                <div
                                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                                        isUser
                                            ? 'bg-primary text-primary-foreground'
                                            : 'bg-muted/50 border'
                                    }`}
                                >
                                    {isUser ? (
                                        <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                                    ) : (
                                        <div className="text-sm">
                                            <MarkdownRenderer
                                                content={msg.text}
                                                contentParts={contentParts}
                                                fontSize="text-sm"
                                            />
                                        </div>
                                    )}

                                    {/* Sources for AI messages */}
                                    {!isUser && (citedSources.length > 0 || uncitedSources.length > 0) && (
                                        <div className="mt-3 pt-3 border-t border-border/30">
                                            <div className="flex flex-wrap gap-1.5">
                                                {citedSources.map((source: Source, idx: number) => (
                                                    <SourceButton
                                                        key={source.id || idx}
                                                        source={source}
                                                        citationNumber={idx + 1}
                                                        onSourceClick={handleSourceClick}
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Images */}
                                    {msg.images_base64 && msg.images_base64.length > 0 && (
                                        <div className="mt-2 flex flex-wrap gap-2">
                                            {msg.images_base64.map((img, imgIdx) => (
                                                <img
                                                    key={imgIdx}
                                                    src={img}
                                                    alt={`Imagen ${imgIdx + 1}`}
                                                    className="max-w-xs rounded-lg"
                                                />
                                            ))}
                                        </div>
                                    )}

                                    {/* Timestamp */}
                                    {msg.created_at && (
                                        <p className={`text-[10px] mt-2 ${isUser ? 'text-primary-foreground/60' : 'text-muted-foreground'}`}>
                                            {new Date(msg.created_at).toLocaleTimeString('es-ES', {
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                        </p>
                                    )}
                                </div>
                                {isUser && (
                                    <div className="shrink-0 mt-1">
                                        <ChatAvatar sender="user" />
                                    </div>
                                )}
                            </div>
                        );
                    })}

                    {/* AI thinking indicator */}
                    {isWaitingResponse && (
                        <div className="flex gap-3 justify-start">
                            <div className="shrink-0 mt-1">
                                <ChatAvatar sender="ai" />
                            </div>
                            <div className="bg-muted/50 border rounded-2xl px-4 py-3">
                                <div className="flex items-center gap-2">
                                    <div className="flex space-x-1">
                                        <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                    <span className="text-xs text-muted-foreground">Pensando...</span>
                                </div>
                            </div>
                        </div>
                    )}

                    {loading && messages.length === 0 && (
                        <div className="flex justify-center py-8">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    )}

                    {error && messages.length > 0 && (
                        <Alert variant="destructive" className="max-w-md mx-auto">
                            <AlertTriangle className="h-4 w-4" />
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Reply Input Bar */}
            {allowReply && (
                <div className="border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky bottom-0">
                    <form onSubmit={handleSendReply} className="max-w-4xl mx-auto px-4 py-3 flex gap-2">
                        <Input
                            value={replyMessage}
                            onChange={(e) => setReplyMessage(e.target.value)}
                            placeholder="Escribe una respuesta..."
                            disabled={isSending || isWaitingResponse}
                            className="flex-1"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSendReply(e);
                                }
                            }}
                        />
                        <Button
                            type="submit"
                            size="icon"
                            disabled={!replyMessage.trim() || isSending || isWaitingResponse}
                        >
                            {isSending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                        </Button>
                    </form>
                </div>
            )}
        </div>
    );
}
