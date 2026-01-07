// ChatMessage.tsx
import React, { useState } from 'react';
import ReactDOMServer from 'react-dom/server';
import Image from 'next/image';
import { motion } from 'framer-motion'; // Importar motion


import { ChatAvatar } from './ChatAvatar';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import { ExternalLink } from 'lucide-react';
import { Copy, Play, Loader2, Pause, RefreshCw, Folder, File as FileIcon, Notebook, Network, Download } from 'lucide-react';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { Source, SourceButton, ContentPart } from '@/components/SourceButton';
import { processMessageWithCitations, collectSourcesFromMessage } from '@/lib/chatUtils';

export interface Artifact {
  id: number;
  content: string;
  type: 'html' | 'css' | 'js' | 'svg' | 'webpage';
  version: number;
}

interface ChatMessageProps {
  msg: {
    text: string;
    sender: 'user' | 'ai';
    image_base64?: string;
    images_base64?: string[];
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
  onSourceClick?: (source: Source) => void;
}





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
  onSourceClick,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(msg.text);

  // Usar las funciones utilitarias para recolectar fuentes
  const { additionalSources, processedRagContext } = collectSourcesFromMessage(msg.sources, msg.ragContext);

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
  const allSources = [...(msg.sources || []), ...additionalSources];
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
      className="text-base sm:text-lg break-words font-sans p-2 sm:p-4 font-normal transition-all duration-500"
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
                <div className="text-sm sm:text-base break-words font-sans [&_p]:my-0 [&_ul]:my-0 [&_ol]:my-0 [&_li]:my-0 [&_h1]:my-0 [&_h2]:my-0 [&_h3]:my-0 [&_h4]:my-0 [&_h5]:my-0 [&_h6]:my-0">
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

              {(msg.image_base64 || (msg.images_base64 && msg.images_base64.length > 0)) && (
                <div className="mt-3">
                  {msg.image_base64 && (
                    <Image
                      src={msg.image_base64}
                      alt="Imagen adjunta"
                      className="max-w-full h-auto rounded-2xl cursor-pointer shadow-sm"
                      onClick={() => window.open(msg.image_base64, '_blank')}
                      width={500} // Asumiendo un ancho razonable
                      height={500} // Asumiendo una altura razonable
                    />
                  )}
                  {msg.images_base64 && msg.images_base64.length > 0 && (
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      {msg.images_base64.map((image, index) => (
                        <Image
                          key={index}
                          src={image}
                          alt={`Imagen adjunta ${index + 1}`}
                          className="w-full h-auto rounded-2xl cursor-pointer shadow-sm"
                          onClick={() => window.open(image, '_blank')}
                          width={500}
                          height={500}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
              {msg.document_url && (
                <div className="mt-4">
                  <Button
                    variant="default"
                    size="sm"
                    className="rounded-full gap-2 shadow-md hover:shadow-lg transition-all"
                    onClick={() => window.open(msg.document_url, '_blank')}
                  >
                    <Download className="h-4 w-4" />
                    <span>{msg.document_url.split('/').pop() || 'Descargar PDF'}</span>
                  </Button>
                </div>
              )}
            </div>

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
          className="flex flex-col mb-8"
        >
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 mt-1">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-primary to-secondary rounded-full blur opacity-25 group-hover:opacity-50 transition duration-500" />
                <ChatAvatar sender="ai" />
              </div>
            </div>
            <div className="flex-1 min-w-0">
              {(msg.text || msg.tool_code) && (
                <div
                  className="flex items-center gap-2 mb-2"
                >
                  <div className="flex items-center gap-2 bg-primary/10 px-3 py-1 rounded-full border border-primary/20 shadow-sm">
                    <span className="font-black text-[10px] uppercase tracking-tighter text-primary">KAI Intelligence</span>
                    <div className="h-1 w-1 rounded-full bg-primary animate-pulse" />
                  </div>
                  <span className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">Assistant</span>
                </div>
              )}

              <div className="w-full">
                {msg.tool_code && (
                  <div className="bg-blue-500/5 backdrop-blur-md p-4 rounded-2xl border border-blue-500/20 text-xs text-blue-600 dark:text-blue-300 font-mono mb-4 shadow-inner">
                    <div className="flex items-center gap-2 mb-2 opacity-70">
                      <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                      <p className="font-black uppercase tracking-widest text-[9px]">System Execution</p>
                    </div>
                    <pre className="whitespace-pre-wrap break-all leading-relaxed opacity-90">{JSON.stringify(JSON.parse(msg.tool_code), null, 2)}</pre>
                  </div>
                )}

                {isEditing ? (
                  <textarea
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    className="w-full min-h-[100px] p-4 border border-border/40 rounded-2xl resize-y focus:outline-none focus:ring-2 focus:ring-primary/20 bg-background/50 backdrop-blur-sm text-foreground"
                    placeholder="Edita tu mensaje aquí..."
                  />
                ) : (
                  <motion.div
                    className="text-foreground break-words font-sans p-2 sm:p-4 font-normal transition-all duration-500"
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{
                      duration: 0.5,
                      ease: "easeOut"
                    }}
                  >
                    {msg.sender === 'ai' && uniqueSources.length > 0 ? (
                      (() => {
                        const fullText = msg.chunks?.join('') || msg.text;
                        const { contentParts } = processMessageWithCitations(fullText, uniqueSources);

                        // Si no se encontraron citas en el texto, pero hay fuentes, 
                        // MarkdownRenderer manejará el texto normal, y nosotros mostramos la sección de fuentes abajo.
                        return (
                          <MarkdownRenderer
                            contentParts={contentParts}
                            content={fullText}
                            fontSize="text-sm sm:text-base"
                            isStreaming={msg.chunks !== undefined}
                          />
                        );
                      })()
                    ) : (
                      <MarkdownRenderer
                        content={msg.chunks?.join('') || msg.text}
                        fontSize="text-sm sm:text-base"
                        isStreaming={msg.chunks !== undefined}
                      />
                    )}
                  </motion.div>
                )}

                {/* Sección de Fuentes al final */}
                {msg.sender === 'ai' && uniqueSources.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="mt-4 pt-4 border-t border-border/10"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <div className="p-1 rounded-md bg-primary/10">
                        <Notebook className="h-3 w-3 text-primary" />
                      </div>
                      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Fuentes y Resultados RAG</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {uniqueSources.map((source, idx) => (
                        <SourceButton key={idx} source={source} citationNumber={idx + 1} onSourceClick={onSourceClick} />
                      ))}
                    </div>
                  </motion.div>
                )}

                {msg.document_url && (
                  <div className="mt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      className="rounded-2xl gap-2 bg-card/40 backdrop-blur-md border-border/40 hover:bg-primary/5 transition-all shadow-sm"
                      onClick={() => window.open(msg.document_url, '_blank')}
                    >
                      <Download className="h-4 w-4 text-primary" />
                      <span className="font-bold text-xs">{msg.document_url.split('/').pop() || 'Descargar PDF'}</span>
                    </Button>
                  </div>
                )}

                {msg.artifact && (
                  <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-2xl bg-primary/5 border border-primary/20 text-primary hover:bg-primary/10 cursor-pointer transition-all group/artifact">
                    <ExternalLink className="h-4 w-4 group-hover/artifact:rotate-12 transition-transform" />
                    <span className="text-xs font-bold uppercase tracking-wider">Ver Artefacto Interactivo</span>
                  </div>
                )}

              </div>

              {(msg.text || msg.tool_code) && (
                <div className="flex items-center gap-1 mt-3 ml-2 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-2 group-hover:translate-y-0">
                  <Button variant="ghost" size="sm" className="h-9 w-9 p-0 rounded-xl hover:bg-primary/10 hover:text-primary transition-all" onClick={() => handleCopyMessage(msg.text)} title="Copiar mensaje">
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-9 w-9 p-0 rounded-xl hover:bg-primary/10 hover:text-primary transition-all"
                    onClick={() => handlePlayAudio(msg.text, index)}
                    disabled={isAudioLoading && playingMessageIndex !== index}
                    title="Escuchar mensaje"
                  >
                    {isAudioLoading && playingMessageIndex === index ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : playingMessageIndex === index && isAudioPaused ? (
                      <Play className="h-3.5 w-3.5" />
                    ) : playingMessageIndex === index ? (
                      <Pause className="h-3.5 w-3.5" />
                    ) : (
                      <Play className="h-3.5 w-3.5" />
                    )}
                  </Button>
                  {isEditing ? (
                    <>
                      <Button variant="ghost" size="sm" className="h-9 w-9 p-0 rounded-xl text-green-600 hover:bg-green-50" onClick={handleSave}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 11.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </Button>
                      <Button variant="ghost" size="sm" className="h-9 w-9 p-0 rounded-xl text-red-600 hover:bg-red-50" onClick={handleCancel}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </Button>
                    </>
                  ) : (
                    <Button variant="ghost" size="sm" className="h-9 w-9 p-0 rounded-xl hover:bg-primary/10 hover:text-primary transition-all" onClick={handleEdit} title="Editar mensaje">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                      </svg>
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
};
