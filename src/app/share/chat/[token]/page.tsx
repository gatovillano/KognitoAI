'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Lock, Copy, Check, AlertTriangle, Send, ArrowLeft, Share2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { toast } from 'sonner';
import { ChatMessage as ChatMessageItem } from '@/components/ChatMessage';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Source } from '@/components/SourceButton';

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

const STREAM_SCROLL_THROTTLE_MS = 120;

export default function SharedChatPage() {
    const params = useParams();
    const searchParams = useSearchParams();
    const token = params?.token as string;
    const isEmbedded = searchParams?.get('embed') === 'true';

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
    const scrollAreaRef = useRef<HTMLDivElement>(null);
    const autoScrollRafRef = useRef<number | null>(null);
    const lastStreamScrollRef = useRef(0);
    const [showScrollBottomButton, setShowScrollBottomButton] = useState(false);
    const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);

    // Reply state
    const [replyMessage, setReplyMessage] = useState('');
    const [isSending, setIsSending] = useState(false);
    const [isWaitingResponse, setIsWaitingResponse] = useState(false);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
    const [isAudioLoading, setIsAudioLoading] = useState(false);
    const [isAudioPaused, setIsAudioPaused] = useState(false);
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

    const LIMIT = 50;

    const handleScroll = useCallback(() => {
        const container = scrollAreaRef.current;
        if (!container) return;

        const { scrollTop, scrollHeight, clientHeight } = container;
        const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;

        setIsAutoScrollEnabled(isAtBottom);
        setShowScrollBottomButton(!isAtBottom);
    }, []);

    const scrollToBottom = useCallback((behavior: 'smooth' | 'auto' = 'smooth', force: boolean = false) => {
        const container = scrollAreaRef.current;
        if (!container || (!isAutoScrollEnabled && !force)) return;

        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior, block: 'end' });
            return;
        }

        container.scrollTo({ top: container.scrollHeight, behavior });
    }, [isAutoScrollEnabled]);

    const scheduleStreamScroll = useCallback((force: boolean = false) => {
        if (autoScrollRafRef.current !== null) return;

        autoScrollRafRef.current = requestAnimationFrame(() => {
            autoScrollRafRef.current = null;
            const now = performance.now();
            if (now - lastStreamScrollRef.current < STREAM_SCROLL_THROTTLE_MS) return;

            lastStreamScrollRef.current = now;
            scrollToBottom('auto', force);
        });
    }, [scrollToBottom]);

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

            if (!response.ok) return false;

            const data: PaginatedMessages = await response.json();
            const newMessages = data.messages;
            const prevCount = messages.length;

            if (newMessages.length > 0) {
                // Check if we actually have new content or messages
                const lastNew = newMessages[newMessages.length - 1];
                const lastOld = messages.length > 0 ? messages[messages.length - 1] : null;

                if (newMessages.length !== prevCount || (lastOld && lastNew.text !== lastOld.text)) {
                    setMessages(newMessages);
                    setTotal(data.total);
                    setSkip(newMessages.length);
                    setTimeout(() => scrollToBottom('smooth', true), 50);
                    return true;
                }
            }

            return false;
        } catch {
            return false;
        }
    }, [token, password, messages, scrollToBottom]);

    // Check the status of the background task
    const fetchReplyStatus = useCallback(async () => {
        try {
            const response = await fetch(`${API_URL}/api/chat/share/${token}/reply-status`);
            if (!response.ok) return null;
            return await response.json();
        } catch {
            return null;
        }
    }, [token]);

    // Poll for new messages after sending a reply
    const startPolling = useCallback(() => {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

        let attempts = 0;
        const maxAttempts = 180; // 3 minutes at 1s intervals

        pollIntervalRef.current = setInterval(async () => {
            attempts++;
            
            // 1. Check task status
            const statusData = await fetchReplyStatus();
            
            // 2. Fetch messages to show progress
            await fetchLatestMessages();

            if (!statusData || statusData.status === 'completed' || statusData.status === 'error' || attempts >= maxAttempts) {
                if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                }
                
                setIsWaitingResponse(false);

                if (statusData?.status === 'error') {
                    toast.error('Hubo un error al generar la respuesta.');
                } else if (attempts >= maxAttempts) {
                    toast.info('La respuesta esta tardando. Recarga la pagina para ver los nuevos mensajes.');
                } else {
                    // One final fetch to be absolutely sure we have everything
                    await fetchLatestMessages();
                }
            }
        }, 1500); // Slightly slower polling to be more stable
    }, [fetchLatestMessages, fetchReplyStatus]);

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
        const container = scrollAreaRef.current;
        if (!container) return;

        container.addEventListener('scroll', handleScroll);
        return () => container.removeEventListener('scroll', handleScroll);
    }, [handleScroll]);

    useEffect(() => {
        return () => {
            if (autoScrollRafRef.current !== null) {
                cancelAnimationFrame(autoScrollRafRef.current);
            }
            if (utteranceRef.current) {
                window.speechSynthesis.cancel();
            }
        };
    }, []);

    useEffect(() => {
        if (isWaitingResponse) {
            setTimeout(() => scrollToBottom('smooth', true), 120);
        }
    }, [isWaitingResponse, scrollToBottom]);

    useEffect(() => {
        if (messages.length > 0 && !isWaitingResponse) {
            scrollToBottom('smooth');
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
        setTimeout(() => scrollToBottom('smooth', true), 50);

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

    const handleCopyMessage = useCallback((text: string) => {
        navigator.clipboard.writeText(text).then(() => {
            toast.success('Mensaje copiado al portapapeles');
        }).catch(() => {
            toast.error('Error al copiar el mensaje');
        });
    }, []);

    const handleRetry = useCallback((text: string) => {
        setReplyMessage(text);
        toast.info('Texto cargado en la caja de respuesta.');
    }, []);

    const handleDeleteMessage = useCallback(() => {
        toast.info('No se pueden eliminar mensajes en un chat compartido.');
    }, []);

    const handlePlayAudio = useCallback((text: string, index: number) => {
        if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
            toast.error('Tu navegador no soporta reproduccion de voz.');
            return;
        }

        const synthesis = window.speechSynthesis;

        if (playingMessageIndex === index) {
            if (synthesis.speaking && !synthesis.paused) {
                synthesis.pause();
                setIsAudioPaused(true);
                return;
            }
            if (synthesis.paused) {
                synthesis.resume();
                setIsAudioPaused(false);
                return;
            }
        }

        synthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'es-ES';
        utteranceRef.current = utterance;

        utterance.onstart = () => {
            setPlayingMessageIndex(index);
            setIsAudioLoading(false);
            setIsAudioPaused(false);
        };
        utterance.onend = () => {
            setPlayingMessageIndex(null);
            setIsAudioLoading(false);
            setIsAudioPaused(false);
            utteranceRef.current = null;
        };
        utterance.onerror = () => {
            setPlayingMessageIndex(null);
            setIsAudioLoading(false);
            setIsAudioPaused(false);
            utteranceRef.current = null;
            toast.error('Error al reproducir audio.');
        };

        setIsAudioLoading(true);
        synthesis.speak(utterance);
    }, [playingMessageIndex]);

    if (loading && !shareInfo) {
        return (
            <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                    className="flex flex-col items-center"
                >
                    <div className="relative mb-6 sm:mb-8 group">
                        <div className="absolute -inset-3 sm:-inset-4 bg-gradient-to-r from-primary/20 to-secondary/20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition duration-1000" />
                        <Image
                            src="/logo-simple.png"
                            alt="Kognito AI"
                            width={70}
                            height={70}
                            className="relative drop-shadow-2xl group-hover:scale-110 transition-transform duration-500 sm:w-[100px] sm:h-[100px]"
                        />
                    </div>
                    <p className="text-muted-foreground text-sm sm:text-base text-center max-w-xs">
                        Cargando conversacion compartida...
                    </p>
                </motion.div>
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
        <div className={`min-h-screen bg-transparent flex flex-col overflow-hidden ${isEmbedded ? 'h-full min-h-0' : ''}`}>
            {!isEmbedded && (
                <div className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
                    <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-2 sm:gap-4 px-2 py-2 sm:px-4 sm:py-4 md:px-6">
                        <div className="min-w-0 flex-1">
                            <div className="mb-0.5 sm:mb-1 hidden sm:flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/70">
                                <Share2 className="h-3 w-3 shrink-0" />
                                <span className="hidden md:inline">Conversacion compartida</span>
                            </div>
                            <h1 className="truncate text-sm sm:text-lg font-semibold" title={shareInfo.thread.title}>{shareInfo.thread.title}</h1>
                            <p className="text-xs text-muted-foreground line-clamp-1">
                                Compartido desde Kognito AI
                                {allowReply && ' · Respuestas habilitadas'}
                            </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-1 sm:gap-2">
                            <ThemeToggle />
                            <Button variant="outline" size="sm" onClick={copyLink} className="rounded-full h-9 w-9 sm:h-auto sm:w-auto sm:px-3" title="Copiar enlace">
                                {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                                <span className="hidden sm:inline ml-1.5 text-xs">{copied ? 'Copiado' : 'Copiar'}</span>
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            <div ref={scrollAreaRef} className="flex-1 overflow-y-auto min-h-0 relative">
                <div className="p-2 sm:p-4 md:p-6 space-y-2 sm:space-y-4 md:space-y-6 w-full md:max-w-6xl mx-auto">
                    {skip < total && (
                        <div className="flex justify-center p-2 sm:p-4">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={loadMoreMessages}
                                disabled={loadingMore}
                                className="rounded-full text-xs sm:text-sm"
                            >
                                {loadingMore && <Loader2 className="mr-1.5 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4 animate-spin" />}
                                <span className="hidden sm:inline">Cargar mensajes anteriores</span>
                                <span className="sm:hidden">Cargar más</span>
                            </Button>
                        </div>
                    )}

                    {messages.map((msg, index) => {
                        return (
                            <div key={`${index}-${msg.created_at}`}>
                                <ChatMessageItem
                                    index={index}
                                    msg={msg}
                                    handleCopyMessage={handleCopyMessage}
                                    handleRetry={handleRetry}
                                    handleDeleteMessage={handleDeleteMessage}
                                    handlePlayAudio={handlePlayAudio}
                                    isAudioLoading={isAudioLoading}
                                    playingMessageIndex={playingMessageIndex}
                                    isAudioPaused={isAudioPaused}
                                    onSourceClick={handleSourceClick}
                                    scrollToBottom={scrollToBottom}
                                />
                            </div>
                        );
                    })}

                    {isWaitingResponse && (
                        <div className="-mt-4">
                            <div className="flex flex-col items-center space-y-2 sm:space-y-3 py-2 sm:py-4 w-full">
                                <div className="flex space-x-1.5 sm:space-x-2">
                                    <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-[#3B82F6] shadow-sm shadow-blue-500/50 animate-bounce" />
                                    <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-[#6366F1] shadow-sm shadow-indigo-500/50 animate-bounce [animation-delay:150ms]" />
                                    <div className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-[#8B5CF6] shadow-sm shadow-violet-500/50 animate-bounce [animation-delay:300ms]" />
                                </div>
                                <p className="text-xs sm:text-sm font-medium text-muted-foreground/80 tracking-wide">Kognito esta pensando</p>
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

                <AnimatePresence>
                    {showScrollBottomButton && (
                        <motion.button
                            initial={{ opacity: 0, y: 10, scale: 0.8 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 10, scale: 0.8 }}
                            onClick={() => scrollToBottom('smooth', true)}
                            className="absolute bottom-3 right-3 sm:bottom-4 sm:right-4 z-50 p-2 sm:p-3 rounded-full bg-[#3B82F6] text-white shadow-lg hover:bg-blue-600 transition-all hover:scale-110 flex items-center justify-center"
                            aria-label="Ir al final"
                        >
                            <ArrowLeft className="w-4 h-4 sm:w-5 sm:h-5 -rotate-90 stroke-[3px]" />
                        </motion.button>
                    )}
                </AnimatePresence>
            </div>

            {allowReply && (
                <div className="w-full md:max-w-6xl mx-auto px-2 pb-3 sm:px-4 sm:pb-4 md:pb-6">
                    <form onSubmit={handleSendReply} className="relative flex gap-1.5 sm:gap-2 rounded-[2rem] border border-border/40 bg-card/40 p-1.5 sm:p-2 backdrop-blur-2xl shadow-lg sm:shadow-2xl shadow-primary/5">
                        <Input
                            value={replyMessage}
                            onChange={(e) => setReplyMessage(e.target.value)}
                            placeholder="Respuesta..."
                            className="flex-1 border-0 bg-transparent text-sm sm:text-base shadow-none focus-visible:ring-0 placeholder:text-xs sm:placeholder:text-sm"
                            disabled={isSending || isWaitingResponse}
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
                            className="rounded-full h-8 w-8 sm:h-9 sm:w-9"
                        >
                            {isSending ? (
                                <Loader2 className="h-3.5 w-3.5 sm:h-4 sm:w-4 animate-spin" />
                            ) : (
                                <Send className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                            )}
                        </Button>
                    </form>
                </div>
            )}
        </div>
    );
}
