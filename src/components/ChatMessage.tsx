// ChatMessage.tsx
import React, { useState } from 'react';
import ReactDOMServer from 'react-dom/server';
import Image from 'next/image';
import { motion } from 'framer-motion'; // Importar motion
import { v4 as uuidv4 } from 'uuid'; // Importar uuid

import { ChatAvatar } from './ChatAvatar';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import { ExternalLink } from 'lucide-react';
import { Copy, Play, Loader2, Pause, RefreshCw, Folder, File as FileIcon, Notebook, Network } from 'lucide-react';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';

export interface Source {
  id: number | string;
  title: string;
  url: string;
  snippet: string;
  type: 'web' | 'document' | 'memory' | 'code' | 'database' | 'note' | 'graph';
  metadata?: Record<string, any>;
  name?: string; // Añadir esta línea para el nombre del documento/memoria
}

export interface Artifact {
  id: number;
  content: string;
  type: 'html' | 'css' | 'js' | 'svg' | 'webpage';
  version: number;
}

export interface ContentPart {
  type: 'text' | 'citation';
  content?: string;
  source?: Source;
  citationNumber?: number;
}

interface ChatMessageProps {
  msg: {
    text: string;
    sender: 'user' | 'ai';
    image_base64?: string;
    document_url?: string;
    artifact?: Artifact;
    ragContext?: any[];
    sources?: Source[];
    chunks?: string[]; // Añadir esta línea
    tool_code?: string;
  };
  index: number;
  handleCopyMessage: (text: string) => void;
  handleRetry: (text: string) => void;
  handlePlayAudio: (text: string, index: number) => void;
  isAudioLoading: boolean;
  playingMessageIndex: number | null;
  isAudioPaused: boolean;
  children?: React.ReactNode; // Añadir la propiedad children
}

export const SourceButton: React.FC<{ source: Source; citationNumber: number }> = ({ source, citationNumber }) => {
  const getIcon = () => {
    switch (source.type) {
      case 'web':
        return <ExternalLink className="h-3 w-3 mr-1" />;
      case 'document':
        return <FileIcon className="h-3 w-3 mr-1" />;
      case 'memory':
        return <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>;
      case 'code':
        return <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>;
      case 'database':
        return <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
        </svg>;
      case 'note':
        return <Notebook className="h-3 w-3 mr-1" />;
      case 'graph':
        return <Network className="h-3 w-3 mr-1" />;
      default:
        return <FileIcon className="h-3 w-3 mr-1" />;
    }
  };

  const getButtonContent = () => {
    if (source.type === 'web') {
      return (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center text-xl bg-primary/10 text-primary font-bold rounded-full px-2 mx-0.5 focus:outline-none focus:ring-2 focus:ring-primary/50 leading-normal flex-shrink-0 hover:bg-primary/20 transition-colors"
        >
          {getIcon()}
          {citationNumber}
        </a>
      );
    }

    return (
      <Dialog>
        <DialogTrigger asChild>
          <button className="inline-flex items-center text-xl bg-primary/10 text-primary font-bold rounded-full px-2 mx-0.5 focus:outline-none focus:ring-2 focus:ring-primary/50 leading-normal flex-shrink-0 hover:bg-primary/20 transition-colors">
            {getIcon()}
            {citationNumber}
          </button>
        </DialogTrigger>
        <DialogContent className="w-80 text-sm">
          <div className="flex items-center gap-2 mb-2">
            {getIcon()}
            <div className="font-bold whitespace-normal break-words">{source.title}</div>
          </div>
          <div className="text-xs text-muted-foreground mb-2 capitalize">
            Tipo: {source.type}
          </div>
          <p className="text-muted-foreground">
            {source.snippet}
          </p>
          {source.metadata?.similarity_score && (
            <div className="text-xs text-primary/80 mt-2">
              Relevancia: {Math.round(source.metadata.similarity_score * 100)}%
            </div>
          )}
          {source.url && (source.type === 'document' || source.type === 'memory' || source.type === 'code' || source.type === 'database' || source.type === 'note' || source.type === 'graph') && (
            <div className="text-xs text-muted-foreground mt-2 break-all">
              Fuente: {source.type === 'note' && source.url.startsWith('note://') ? (
                <a href={`/notes/${source.url.replace('note://', '')}`} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  {source.title}
                </a>
              ) : (
                source.url
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    );
  };

  return getButtonContent();
};

const processMessageWithCitations = (text: string, allSources: Source[] | undefined): { contentParts: ContentPart[]; uncitedSources: Source[] } => {
  if (!allSources || allSources.length === 0) {
    return { contentParts: [{ type: 'text', content: text }], uncitedSources: [] };
  }

  const contentParts: ContentPart[] = [];
  let lastIndex = 0;
  const citedSourceIds = new Set<string | number>();

  // Expresión regular para buscar citas individuales como [1], [2], etc.
  const citationRegex = /\[(\d+)\]/g;
  let match: RegExpExecArray | null;

  while ((match = citationRegex.exec(text)) !== null) {
    const citationNumber = parseInt(match[1], 10);
    const fullMatch = match[0];
    const index = match.index!;

    const source = allSources.find(s => s.id == citationNumber); // Usar == para comparar string | number

    if (source) {
      // Añadir el texto antes de la cita
      if (index > lastIndex) {
        contentParts.push({ type: 'text', content: text.substring(lastIndex, index) });
      }

      // Añadir la cita como un componente
      contentParts.push({ type: 'citation', source: source, citationNumber: citationNumber });
      citedSourceIds.add(source.id);

      lastIndex = index + fullMatch.length;
    }
  }

  // Añadir cualquier texto restante después de la última cita
  if (lastIndex < text.length) {
    contentParts.push({ type: 'text', content: text.substring(lastIndex) });
  }

  const uncitedSources = allSources.filter(s => !citedSourceIds.has(s.id));

  return { contentParts, uncitedSources };
};

export const ChatMessage: React.FC<ChatMessageProps> = ({
  msg,
  index,
  handleCopyMessage,
  handleRetry,
  handlePlayAudio,
  isAudioLoading,
  playingMessageIndex,
  isAudioPaused,
  children, // Recibir children en las props
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(msg.text);

  const additionalSourcesToDisplay: Source[] = [];
  const seenSourceIdentifiers = new Set<string | number>(); // Para deduplicación

  // Helper para añadir fuentes y evitar duplicados
  const addSourceToDisplay = (source: Source) => {
    const identifier = source.url ? source.url : `${source.type}-${source.name || source.title}-${source.id}`;
    if (!seenSourceIdentifiers.has(identifier)) {
      additionalSourcesToDisplay.push(source);
      seenSourceIdentifiers.add(identifier);
    }
  };

  // Procesar msg.ragContext
  msg.ragContext?.forEach((ragItem) => {
    let ragId: number | string;
    if (typeof ragItem.id === 'number') {
      ragId = ragItem.id;
    } else {
      ragId = uuidv4(); // Generar un ID de cadena único si no es numérico
    }

    const newSource: Source = {
      id: ragId,
      title: ragItem.name || ragItem.title || 'Contexto RAG',
      url: ragItem.url || '',
      snippet: ragItem.snippet || ragItem.content || '',
      type: ragItem.type || 'document',
      metadata: ragItem.metadata || {},
      name: ragItem.name || ragItem.title || 'Contexto RAG',
    };
    addSourceToDisplay(newSource);
  });

  // Procesar msg.sources (las que serán citadas por el LLM)
  // Las citas numéricas se gestionarán en processMessageWithCitations.
  // Aquí, solo las añadimos a additionalSourcesToDisplay para mostrarlas si no están ya.
  msg.sources?.forEach((source) => {
    addSourceToDisplay(source);
  });

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleSave = () => {
    // Actualizar el texto del mensaje con el texto editado
    msg.text = editedText;
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedText(msg.text);
    setIsEditing(false);
  };

  // Procesar el mensaje con las citas y las fuentes de msg.sources
  const allSources = [...(msg.sources || []), ...additionalSourcesToDisplay];
  // The backend is now responsible for sending the final, unique list of sources.
  // The frontend should not perform its own de-duplication.
  const uniqueSources = allSources;

  const { contentParts, uncitedSources } = processMessageWithCitations(
    msg.chunks?.join('') || msg.text,
    uniqueSources
  );

  // Determinar si el mensaje está en streaming
  const isStreaming = msg.chunks !== undefined && msg.chunks.length > 0;

  return (
    <motion.div
      key={index}
      initial={{ opacity: 0, y: 10 }}
      animate={{
        opacity: 1,
        y: 0
      }}
      transition={{
        duration: 0.6,
        ease: "easeOut"
      }}
      className="group"
    >
      {msg.sender === 'user' ? (
        // Mensaje del usuario
        <div
          className="flex flex-col items-end mb-2"
        >
          <div className="flex items-start gap-3 max-w-[100%] mr-4" style={{ marginRight: '20px' }}>
            <div
              className="rounded-3xl rounded-br-none px-4 py-2 shadow-sm bg-muted/80 backdrop-blur-sm text-foreground border border-border/10 relative min-w-[100px]">
              {/* Cola de la burbuja */}

              {isEditing ? (
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  className="w-full min-h-[80px] p-3 border border-border rounded-2xl resize-y focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground"
                  placeholder="Edita tu mensaje aquí..."
                />
              ) : (
                <div className="text-base break-words font-sans [&_p]:my-0 [&_ul]:my-0 [&_ol]:my-0 [&_li]:my-0 [&_h1]:my-0 [&_h2]:my-0 [&_h3]:my-0 [&_h4]:my-0 [&_h5]:my-0 [&_h6]:my-0">
                  <MarkdownRenderer content={msg.text} />
                </div>
              )}

              {/* Archivos adjuntos */}
              {msg.ragContext && msg.ragContext.length > 0 && (
                <div className="mt-3 border-t border-border/20 pt-3">
                  <p className="text-xs font-semibold text-muted-foreground mb-2">Archivos Adjuntos:</p>
                  <div className="space-y-2">
                    {msg.ragContext.map((item, index) => (
                      <div key={index} className="flex items-center gap-2 text-sm p-2 bg-background/50 rounded-lg">
                        {item.type === 'document' ? <FileIcon className="h-4 w-4 flex-shrink-0" /> : <Folder className="h-4 w-4 flex-shrink-0" />}
                        <span className="truncate" title={item.name}>{item.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {msg.image_base64 && (
                <div className="mt-3">
                  <Image
                    src={msg.image_base64}
                    alt="Imagen adjunta"
                    className="max-w-full h-auto rounded-2xl cursor-pointer shadow-sm"
                    onClick={() => window.open(msg.image_base64, '_blank')}
                    width={500} // Asumiendo un ancho razonable
                    height={500} // Asumiendo una altura razonable
                  />
                </div>
              )}
              {msg.document_url && (
                <div className="mt-3 flex items-center gap-2 text-white/80 hover:text-white cursor-pointer" onClick={() => window.open(msg.document_url, '_blank')}>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-base">{msg.document_url.split('/').pop() || 'Documento'}</span>
                </div>
              )}
            </div>
            <ChatAvatar sender="user" />
          </div>

          {/* Botones de acción */}
          <div className="flex items-center gap-1 mt-0 mr-12 opacity-0 group-hover:opacity-100">
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full" onClick={() => handleCopyMessage(msg.text)}>
              <Copy className="h-3 w-3" />
            </Button>
            {isEditing ? (
              <>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full text-green-600" onClick={handleSave}>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 11.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </Button>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full text-red-600" onClick={handleCancel}>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full" onClick={() => handleRetry(msg.text)}>
                  <RefreshCw className="h-3 w-3" />
                </Button>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full" onClick={handleEdit}>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                  </svg>
                </Button>
              </>
            )}
          </div>
        </div>
      ) : (
        // Mensaje de la IA
        <div
          className="flex flex-col mb-4"
        >
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div
                className="flex items-center gap-2 mb-3"
              >
                <span className="font-semibold text-foreground">KAI</span>
                <span className="text-lg text-muted-foreground">Assistant</span>
              </div>

              <div className="w-full">
                {msg.tool_code && (
                  <div className="bg-blue-900/20 p-3 rounded-lg text-sm text-blue-200 font-mono mb-4">
                    <p className="font-bold mb-1">⚙️ Herramienta utilizada:</p>
                    <pre className="whitespace-pre-wrap break-all">{JSON.stringify(JSON.parse(msg.tool_code), null, 2)}</pre>
                  </div>
                )}

                {isEditing ? (
                  <textarea
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    className="w-full min-h-[100px] p-3 border border-border rounded-2xl resize-y focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground"
                    placeholder="Edita tu mensaje aquí..."
                  />
                ) : (
                  <motion.div
                    className="text-foreground break-words font-sans p-4 font-normal"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{
                      duration: 0.5,
                      ease: "easeInOut"
                    }}
                  >
                    {msg.sender === 'ai' && (msg.sources && msg.sources.length > 0 || additionalSourcesToDisplay.length > 0) && /\[(\d+)\]/.test(msg.chunks?.join('') || msg.text) ? (
                      (() => {
                        // processMessageWithCitations ahora devuelve contentParts
                        const { contentParts, uncitedSources } = processMessageWithCitations(msg.chunks?.join('') || msg.text, uniqueSources);

                        // Combina las fuentes no citadas de msg.sources con las fuentes RAG adicionales
                        const allAdditionalSources = [...uncitedSources, ...additionalSourcesToDisplay];

                        return (
                          <>
                            <MarkdownRenderer contentParts={contentParts} fontSize="text-xl" isStreaming={msg.chunks !== undefined} />
                          </>
                        );
                      })()
                    ) : (
                      <MarkdownRenderer content={msg.chunks?.join('') || msg.text} fontSize="text-xl" isStreaming={msg.chunks !== undefined} />
                    )}
                  </motion.div>
                )}

                {msg.document_url && (
                  <div className="mt-3 flex items-center gap-2 text-muted-foreground hover:text-foreground cursor-pointer" onClick={() => window.open(msg.document_url, '_blank')}>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                    </svg>
                    <span className="text-base">{msg.document_url.split('/').pop() || 'Documento'}</span>
                  </div>
                )}
                {msg.artifact && (
                  <div className="mt-3 flex items-center gap-2 text-muted-foreground hover:text-foreground cursor-pointer">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                      <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-base">Ver Artefacto</span>
                  </div>
                )}

              </div>

              {/* Botones de acción */}
              <div className="flex items-center gap-1 mt-0 ml-3 opacity-0 group-hover:opacity-100">
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full" onClick={() => handleCopyMessage(msg.text)}>
                  <Copy className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 rounded-full"
                  onClick={() => handlePlayAudio(msg.text, index)}
                  disabled={isAudioLoading && playingMessageIndex !== index}
                >
                  {isAudioLoading && playingMessageIndex === index ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : playingMessageIndex === index && isAudioPaused ? (
                    <Play className="h-3 w-3" />
                  ) : playingMessageIndex === index ? (
                    <Pause className="h-3 w-3" />
                  ) : (
                    <Play className="h-3 w-3" />
                  )}
                </Button>
                {isEditing ? (
                  <>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full text-green-600" onClick={handleSave}>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 11.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </Button>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full text-red-600" onClick={handleCancel}>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </Button>
                  </>
                ) : (
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full" onClick={handleEdit}>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                    </svg>
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
};
