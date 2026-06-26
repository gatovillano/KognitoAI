// ChatMessage.tsx
import React, { useState, useEffect, useMemo } from 'react';
import ReactDOMServer from 'react-dom/server';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion'; // Importar motion


import { ChatAvatar } from './ChatAvatar';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { BrainCircuit, ChevronDown, ChevronUp, Check, X, Edit3, ChevronLeft, ChevronRight, Trash2, ExternalLink } from 'lucide-react';
import { Copy, Play, Loader2, Pause, RefreshCw, Folder, File as FileIcon, Network, Download } from 'lucide-react';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { Source, SourceButton, ContentPart } from '@/components/SourceButton';
import { processMessageWithCitations, collectSourcesFromMessage, getSourceIdentityKey } from '@/lib/chatUtils';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import PtyTerminalEmbedded from '@/components/terminal/PtyTerminalEmbedded';
import { useAuth } from '@/contexts/AuthContext';

export interface Artifact {
  id: number;
  content: string;
  type: 'html' | 'css' | 'js' | 'svg' | 'webpage';
  version: number;
}

export interface MessageContentPart {
  type: 'text' | 'reasoning' | 'tool_call' | 'tool_result';
  content: string;
  id?: string;
  status?: 'start' | 'end' | 'error';
  tool_name?: string;
  pty_session?: { session_id: string; command?: string };
}

interface ChatMessageProps {
  msg: {
    text: string;
    sender: 'user' | 'ai';
    created_at: string;
    model_name?: string;
    image_base64?: string;
    images_base64?: string[];
    document_url?: string;
    artifact?: Artifact;
    ragContext?: any[];
    sources?: any[];
    chunks?: string[];
    reasoning?: string;
    reasoning_chunks?: string[];
    content_parts?: MessageContentPart[];
    pty_session?: any;
    tool_code?: string;
  };
  index: number;
  handleCopyMessage: (text: string) => void;
  handleRetry: (text: string) => void;
  handleDeleteMessage?: (msg: { text: string; sender: 'user' | 'ai'; created_at: string }) => void;
  handlePlayAudio: (text: string, index: number) => void;
  isAudioLoading: boolean;
  playingMessageIndex: number | null;
  isAudioPaused: boolean;
  children?: React.ReactNode; // Añadir la propiedad children
  onSourceClick?: (source: any) => void;
  scrollToBottom?: (behavior?: 'smooth' | 'auto', force?: boolean) => void;
  responsePosition?: {
    current: number;
    total: number;
  };
  onPrevResponse?: () => void;
  onNextResponse?: () => void;
}





const ReasoningBlock = ({ content, isThinkingOnly, scrollToBottom }: { content: string, isThinkingOnly: boolean, scrollToBottom?: (behavior?: 'smooth' | 'auto', force?: boolean) => void }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (isThinkingOnly || isExpanded) {
      scrollToBottom?.('auto');
    }
  }, [content, isExpanded, isThinkingOnly, scrollToBottom]);

  return (    <div className="mb-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 mb-2 hover:bg-primary/10 p-1 px-2 rounded-lg transition-all duration-300 group/thinking"
      >
        <motion.div
          className="relative p-1 rounded-md transition-colors"
          animate={isThinkingOnly ? {
            scale: [1, 1.05, 1],
          } : {}}
          transition={isThinkingOnly ? {
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          } : {}}
        >
          {isThinkingOnly && (
            <motion.div
              className="absolute inset-0 bg-primary/20 blur-md rounded-full"
              animate={{
                opacity: [0.2, 0.5, 0.2],
                scale: [0.8, 1.2, 0.8],
              }}
              transition={{
                duration: 3,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          )}
          <BrainCircuit className="h-3.5 w-3.5 text-primary relative z-10" />
        </motion.div>
        <p className="font-bold uppercase tracking-[0.2em] text-[9px] text-primary/70 flex items-center gap-1 min-w-[80px] ml-1">
          {isThinkingOnly ? (
            <span className="flex items-center">
              Pensando
              <span className="flex ml-0.5">
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{
                      duration: 1.5,
                      repeat: Infinity,
                      delay: i * 0.2,
                      ease: "easeInOut"
                    }}
                  >
                    .
                  </motion.span>
                ))}
              </span>
            </span>
          ) : (
            "Pensamiento"
          )}
        </p>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          <ChevronDown className="h-3 w-3 text-primary/60" />
        </motion.div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="pl-4 border-l-2 border-primary/20 py-1 mb-2">
              <MarkdownRenderer
                content={content}
                fontSize="text-[13px]"
                style={{ color: 'var(--primary)', opacity: 0.8 }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const stripHtml = (text: string) => {
  return text.replace(/<[^>]*>/g, '');
};

const ToolCallBlock = ({ part, scrollToBottom }: { part: MessageContentPart, scrollToBottom?: (behavior?: 'smooth' | 'auto', force?: boolean) => void }) => {
  const { user, token } = useAuth();
  const isTerminal = part.tool_name === 'terminal_executor' && !!part.pty_session;
  const [isExpanded, setIsExpanded] = useState(isTerminal);
  const hasContent = (!!part.content && part.status !== 'start') || isTerminal;

  useEffect(() => {
    if (isTerminal) {
      setIsExpanded(true);
    }
  }, [isTerminal]);

  useEffect(() => {
    if (isExpanded) {
      scrollToBottom?.('auto');
    }
  }, [isExpanded, scrollToBottom]);

  return (
    <div className="mb-4">
      <div 
        className={`flex flex-col bg-primary/5 rounded-lg border border-primary/10 overflow-hidden transition-all duration-300 ${isExpanded ? 'ring-1 ring-primary/20 shadow-sm' : ''}`}
      >
        <button
          onClick={() => hasContent && setIsExpanded(!isExpanded)}
          disabled={!hasContent}
          className={`flex items-center gap-2 p-2 w-full text-left transition-colors ${hasContent ? 'hover:bg-primary/10 cursor-pointer' : 'cursor-default'}`}
        >
          {part.status === 'start' ? (
            <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
          ) : part.status === 'error' ? (
            <X className="h-3.5 w-3.5 text-destructive" />
          ) : (
            <Folder className="h-3.5 w-3.5 text-primary" />
          )}
          <p className="text-[11px] font-medium text-primary/80 flex-1">
            {part.tool_name ? `Herramienta: ${part.tool_name}` : 'Ejecutando herramienta...'}
            {part.status === 'end' && ' - Completado'}
            {part.status === 'error' && ' - Falló'}
          </p>
          {hasContent && (
             <motion.div
               animate={{ rotate: isExpanded ? 180 : 0 }}
               transition={{ duration: 0.3 }}
             >
               <ChevronDown className="h-3 w-3 text-primary/60" />
             </motion.div>
          )}
        </button>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="px-4 py-3 border-t border-primary/10 bg-background/50">
                <div className="flex items-center gap-2 mb-2 text-[10px] font-bold uppercase tracking-widest text-primary/60">
                   <ExternalLink className="h-3 w-3" />
                   {isTerminal ? 'Terminal Interactiva en tiempo real' : 'Salida de la herramienta'}
                </div>
                {isTerminal ? (
                  <div className="mb-2">
                    <PtyTerminalEmbedded
                      accountId={(user?.account_id || user?.id) as string || ''}
                      token={token || ''}
                      sessionId={part.pty_session!.session_id}
                      apiBaseUrl={process.env.NEXT_PUBLIC_API_URL || ''}
                      initialCommand={part.pty_session!.command}
                    />
                  </div>
                ) : (
                  <div className="max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                    <MarkdownRenderer
                      content={part.content}
                      fontSize="text-[12px]"
                      style={{ color: 'var(--foreground)', opacity: 0.9 }}
                    />
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

const ChatMessageComponent: React.FC<ChatMessageProps> = ({
  msg,
  index,
  handleCopyMessage,
  handleRetry,
  handleDeleteMessage,
  handlePlayAudio,
  isAudioLoading,
  playingMessageIndex,
  isAudioPaused,
  children,
  onSourceClick,
  scrollToBottom,
  responsePosition,
  onPrevResponse,
  onNextResponse,
}) => {
  const { settings } = useUserSettings();
  const { user, token } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(msg.text);

  // Determinar si está pensando solamente (para el fallback)
  const hasReasoning = !!(msg.reasoning || (msg.reasoning_chunks && msg.reasoning_chunks.length > 0));
  const isThinkingOnly = !!(hasReasoning && !msg.text && msg.chunks !== undefined);

  const displayModelName = useMemo(() => {
    const rawModelName = msg.model_name || settings?.llm_model;
    return rawModelName
      ? rawModelName.split('/').pop()?.split(':')[0]
      : 'Assistant';
  }, [msg.model_name, settings?.llm_model]);

  const { citationSources, additionalSources } = useMemo(() => {
    return collectSourcesFromMessage(msg.sources, msg.ragContext);
  }, [msg.sources, msg.ragContext]);

  const citationText = useMemo(() => {
    if (msg.content_parts && msg.content_parts.length > 0) {
      return msg.content_parts
        .filter((part) => part.type === 'text')
        .map((part) => part.content)
        .join('\n\n');
    }

    return msg.text;
  }, [msg.content_parts, msg.text]);

  const { citedSources: parsedCitedSources, resolvedSources } = useMemo(() => {
    return processMessageWithCitations(citationText, citationSources);
  }, [citationText, citationSources]);

  const citationNumberBySource = useMemo(() => {
    return new Map(resolvedSources.map((source, index) => [getSourceIdentityKey(source), index + 1]));
  }, [resolvedSources]);

  const displaySources = parsedCitedSources.length > 0
    ? parsedCitedSources
    : (citationSources.length > 0 ? citationSources : additionalSources);

  const imagesToShow = useMemo(() => {
    const urls: string[] = [];
    
    // Extract images from markdown text
    if (msg.text) {
      const matches = msg.text.matchAll(/!\[.*?\]\((.*?)\)/g);
      for (const match of matches) {
        if (match[1]) {
          urls.push(match[1]);
        }
      }
    }
    
    // Extract images from content parts if any
    if (msg.content_parts) {
      msg.content_parts.forEach(part => {
        if (part.type === 'text' && part.content) {
          const matches = part.content.matchAll(/!\[.*?\]\((.*?)\)/g);
          for (const match of matches) {
            if (match[1]) {
              urls.push(match[1]);
            }
          }
        }
      });
    }

    const rawImages = Array.from(new Set([
      ...(msg.image_base64 ? [msg.image_base64] : []),
      ...(msg.images_base64 || []),
      ...urls,
    ]));

    // Prepend API URL to relative paths if necessary
    return rawImages.map(img => {
      if (img.startsWith('/tmp/') || img.startsWith('/media/')) {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        return `${apiUrl}${img}`;
      }
      return img;
    });
  }, [msg.image_base64, msg.images_base64, msg.text, msg.content_parts]);

  const handleEdit = () => setIsEditing(true);
  const handleSave = () => {
    msg.text = editedText;
    setIsEditing(false);
  };
  const handleCancel = () => {
    setEditedText(msg.text);
    setIsEditing(false);
  };

  return (
    <motion.div
      key={index}
      className="text-base sm:text-lg break-words font-sans p-1 sm:p-4 font-normal transition-all duration-500 group"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
    >
      {msg.sender === 'user' ? (
        <div className="flex flex-col items-end mb-2">
          <div className="flex items-start gap-3 max-w-[100%] mr-4" style={{ marginRight: '20px' }}>
            <div className="rounded-3xl rounded-br-none px-3 py-1.5 sm:px-4 sm:py-2 shadow-sm bg-muted/80 backdrop-blur-sm text-foreground border border-border/10 relative min-w-[100px]">
              {isEditing ? (
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  className="w-full min-h-[80px] p-3 border border-border rounded-2xl resize-y focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground"
                />
              ) : (
                <div className="text-sm sm:text-base break-words font-sans [&_p]:my-0">
                  <MarkdownRenderer content={msg.text} />
                </div>
              )}

              {/* Imágenes del usuario */}
              {imagesToShow.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2 justify-end">
                  {imagesToShow.map((img, imgIdx) => (
                    <Dialog key={imgIdx}>
                      <DialogTrigger asChild>
                        <img
                          src={img}
                          alt={`Imagen ${imgIdx + 1}`}
                          className="max-w-[200px] max-h-[200px] rounded-xl cursor-pointer hover:opacity-90 transition-all border border-border/20 shadow-sm object-cover"
                        />
                      </DialogTrigger>
                      <DialogContent className="max-w-[95vw] max-h-[95vh] p-0 overflow-hidden bg-black/80 backdrop-blur-sm border-none flex items-center justify-center">
                        <img src={img} alt={`Imagen ${imgIdx + 1}`} className="max-w-full max-h-full object-contain" />
                      </DialogContent>
                    </Dialog>
                  ))}
                </div>
              )}

              {msg.ragContext && msg.ragContext.length > 0 && (
                <div className="mt-3 border-t border-border/20 pt-3">
                  <div className="space-y-2">
                    {msg.ragContext.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm p-2 bg-background/50 rounded-lg">
                        {item.type === 'document' ? <FileIcon className="h-4 w-4" /> : <Folder className="h-4 w-4" />}
                        <span>{item.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1 mt-0 mr-12 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-all">
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => handleCopyMessage(msg.text)}><Copy className="h-3 w-3" /></Button>
            {isEditing ? (
              <>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-green-600" onClick={handleSave}><Check className="h-3 w-3" /></Button>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-600" onClick={handleCancel}><X className="h-3 w-3" /></Button>
              </>
            ) : (
              <>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => handleRetry(msg.text)}><RefreshCw className="h-3 w-3" /></Button>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={handleEdit}><Edit3 className="h-3 w-3" /></Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 text-red-600"
                  onClick={() => handleDeleteMessage?.({ text: msg.text, sender: msg.sender, created_at: msg.created_at })}
                  title="Eliminar mensaje"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-col mb-8">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 mt-1">
              <ChatAvatar sender="ai" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <div className="flex items-center gap-2 bg-primary/10 px-3 py-1 rounded-full border border-primary/20 shadow-sm">
                  <span className="font-black text-[10px] uppercase tracking-tighter text-primary">KAI Intelligence</span>
                </div>
                <span className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">{displayModelName}</span>
              </div>

              <div className="w-full">
                {msg.content_parts && msg.content_parts.length > 0 ? (
                  msg.content_parts.map((part, idx) => {
                    if (part.type === 'reasoning') {
                      const isLastReasoning = idx === msg.content_parts!.length - 1 && !msg.text && msg.chunks !== undefined;
                      return <ReasoningBlock key={idx} content={part.content} isThinkingOnly={isLastReasoning} scrollToBottom={scrollToBottom} />;
                    }
                    if (part.type === 'tool_call') {
                      return <ToolCallBlock key={idx} part={part} scrollToBottom={scrollToBottom} />;
                    }
                    if (part.type === 'text') {
                      const { contentParts: parts } = processMessageWithCitations(part.content, citationSources);
                      return (
                        <div key={idx} className="mb-4">
                          <MarkdownRenderer
                            contentParts={parts}
                            content={part.content}
                            fontSize="text-sm sm:text-base"
                            isStreaming={idx === msg.content_parts!.length - 1 && msg.chunks !== undefined}
                          />
                        </div>
                      );
                    }
                    return null;
                  })
                ) : (
                  <>
                    {(msg.reasoning || (msg.reasoning_chunks && msg.reasoning_chunks.length > 0)) && (
                      <ReasoningBlock 
                        content={msg.reasoning || msg.reasoning_chunks?.join('') || ""} 
                        isThinkingOnly={isThinkingOnly} 
                        scrollToBottom={scrollToBottom}
                      />
                    )}
                    <div className="mb-4">
                      {(() => {
                        const { contentParts: parts } = processMessageWithCitations(msg.text, citationSources);
                        return (
                          <MarkdownRenderer
                            contentParts={parts}
                            content={msg.text}
                            fontSize="text-sm sm:text-base"
                            isStreaming={msg.chunks !== undefined}
                          />
                        );
                      })()}
                    </div>
                  </>
                )}


                    {/* Embedded PTY terminal if the tool provided a session */}
                    {msg.pty_session && (
                      <div className="mb-4">
                        <PtyTerminalEmbedded
                          accountId={(user?.account_id || user?.id) as string}
                          token={token || ''}
                          sessionId={msg.pty_session.session_id}
                          apiBaseUrl={process.env.NEXT_PUBLIC_API_URL || ''}
                          initialCommand={msg.pty_session.command}
                        />
                      </div>
                    )}

                {/* Imágenes de la IA */}
                {imagesToShow.length > 0 && msg.sender === 'ai' && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {imagesToShow.map((img, imgIdx) => (
                      <Dialog key={imgIdx}>
                        <DialogTrigger asChild>
                          <img
                            src={img}
                            alt={`Imagen ${imgIdx + 1}`}
                            className="max-w-[200px] max-h-[200px] rounded-xl cursor-pointer hover:opacity-90 transition-all border border-border/20 shadow-sm object-cover"
                          />
                        </DialogTrigger>
                        <DialogContent className="max-w-[95vw] max-h-[95vh] p-0 overflow-hidden bg-black/80 backdrop-blur-sm border-none flex items-center justify-center">
                          <img src={img} alt={`Imagen ${imgIdx + 1}`} className="max-w-full max-h-full object-contain" />
                        </DialogContent>
                      </Dialog>
                    ))}
                  </div>
                )}

                {displaySources.length > 0 && (
                  <SourcesList
                    sources={displaySources}
                    citationNumberBySource={citationNumberBySource}
                    onSourceClick={onSourceClick}
                  />
                )}
              </div>
              
              <div className="flex items-center gap-1 mt-3 ml-2 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-all">
                {msg.sender === 'ai' && responsePosition && responsePosition.total > 1 && (
                  <div className="flex items-center gap-1 mr-2 px-2 py-1 rounded-xl border border-border/40 bg-muted/30">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 rounded-lg"
                      onClick={onPrevResponse}
                      disabled={!onPrevResponse || responsePosition.current <= 1}
                    >
                      <ChevronLeft className="h-3.5 w-3.5" />
                    </Button>
                    <span className="text-[11px] font-medium text-muted-foreground min-w-[52px] text-center">
                      {responsePosition.current}/{responsePosition.total}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 rounded-lg"
                      onClick={onNextResponse}
                      disabled={!onNextResponse || responsePosition.current >= responsePosition.total}
                    >
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}
                <Button variant="ghost" size="sm" className="h-9 w-9 p-0 rounded-xl" onClick={() => handleCopyMessage(msg.text)}><Copy className="h-3.5 w-3.5" /></Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-9 w-9 p-0 rounded-xl" 
                  onClick={() => {
                    const cleanText = stripHtml(msg.text);
                    if (playingMessageIndex === index && !isAudioLoading) {
                      // Si ya está sonando, el handlePlayAudio debería actuar como toggle de pausa/play
                      handlePlayAudio(cleanText, index);
                    } else {
                      handlePlayAudio(cleanText, index);
                    }
                  }}
                >
                  {playingMessageIndex === index ? (
                    isAudioLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : isAudioPaused ? (
                      <Play className="h-3.5 w-3.5" />
                    ) : (
                      <Pause className="h-3.5 w-3.5" />
                    )
                  ) : (
                    <Play className="h-3.5 w-3.5" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-9 w-9 p-0 rounded-xl text-red-600"
                  onClick={() => handleDeleteMessage?.({ text: msg.text, sender: msg.sender, created_at: msg.created_at })}
                  title="Eliminar mensaje"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
};

// ─── Sources toggle (OpenWebUI-inspired grouping, original SourceButton cards) ─
const SourcesList: React.FC<{
  sources: Source[];
  citationNumberBySource: Map<string, number>;
  onSourceClick?: (source: any) => void;
}> = ({ sources, citationNumberBySource, onSourceClick }) => {
  const [open, setOpen] = useState(false);

  const webSources = sources.filter(s => s.type === 'web' && s.url?.startsWith('http'));

  return (
    <div className="mt-3 -mx-0.5 w-full">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground px-3 h-8 rounded-full hover:bg-muted/60 transition-colors border border-border/30"
      >
        {webSources.length > 0 && (
          <span className="flex -space-x-1 items-center mr-0.5">
            {webSources.slice(0, 3).map((s, i) => (
              <img
                key={i}
                src={`https://www.google.com/s2/favicons?sz=16&domain=${s.url}`}
                alt=""
                className="w-4 h-4 rounded-full border border-background bg-muted"
                onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
            ))}
          </span>
        )}
        {sources.length === 1 ? '1 fuente' : `${sources.length} fuentes`}
        {open ? <ChevronUp className="h-3 w-3 ml-0.5" /> : <ChevronDown className="h-3 w-3 ml-0.5" />}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="sources-list"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.28, ease: 'easeInOut' }}
            className="overflow-hidden mt-3 pt-2"
          >
            <div className="flex flex-col gap-2 pl-1 max-w-xl w-full">
              {sources.map((source, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2, delay: idx * 0.03, ease: 'easeOut' }}
                >
                  <SourceButton
                    source={source}
                    citationNumber={citationNumberBySource.get(getSourceIdentityKey(source)) ?? idx + 1}
                    onSourceClick={onSourceClick}
                    showTitle={true}
                  />
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const ChatMessage = React.memo(ChatMessageComponent, (prevProps, nextProps) => {
  return (
    prevProps.msg === nextProps.msg &&
    prevProps.index === nextProps.index &&
    prevProps.isAudioLoading === nextProps.isAudioLoading &&
    prevProps.playingMessageIndex === nextProps.playingMessageIndex &&
    prevProps.isAudioPaused === nextProps.isAudioPaused &&
    prevProps.handleCopyMessage === nextProps.handleCopyMessage &&
    prevProps.handleRetry === nextProps.handleRetry &&
    prevProps.handleDeleteMessage === nextProps.handleDeleteMessage &&
    prevProps.handlePlayAudio === nextProps.handlePlayAudio &&
    prevProps.onSourceClick === nextProps.onSourceClick &&
    prevProps.scrollToBottom === nextProps.scrollToBottom &&
    prevProps.responsePosition?.current === nextProps.responsePosition?.current &&
    prevProps.responsePosition?.total === nextProps.responsePosition?.total &&
    prevProps.onPrevResponse === nextProps.onPrevResponse &&
    prevProps.onNextResponse === nextProps.onNextResponse
  );
});
