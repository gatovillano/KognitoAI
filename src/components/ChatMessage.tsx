// ChatMessage.tsx
import React, { memo, useState } from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion'; // Importar motion

import { ChatAvatar } from './ChatAvatar';
import { Button } from '@/components/ui/button';
import { Copy, Play, Loader2, Pause, RefreshCw, Folder, File } from 'lucide-react';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import TypewriterMarkdown from './TypewriterMarkdown';

interface Artifact {
  id: number;
  content: string;
  type: 'html' | 'css' | 'js' | 'svg' | 'webpage';
  version: number;
}

interface ChatMessageProps {
  msg: {
    text: string;
    sender: 'user' | 'ai';
    image?: string;
    document_url?: string;
    artifact?: Artifact;
    ragContext?: any[];
  };
  index: number;
  handleCopyMessage: (text: string) => void;
  handleRetry: (text: string) => void;
  handlePlayAudio: (text: string, index: number) => void;
  isAudioLoading: boolean;
  playingMessageIndex: number | null;
  isAudioPaused: boolean;
  isLastMessage: boolean; // Nueva prop
  children?: React.ReactNode; // Añadir la propiedad children
}

export const ChatMessage: React.FC<ChatMessageProps> = memo(({
  msg,
  index,
  handleCopyMessage,
  handleRetry,
  handlePlayAudio,
  isAudioLoading,
  playingMessageIndex,
  isAudioPaused,
  isLastMessage, // Recibir la nueva prop
  children, // Recibir children en las props
}) => {
  ChatMessage.displayName = 'ChatMessage';
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(msg.text);

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

  return (
    <motion.div
      key={index}
      initial={{ opacity: 0, y: 0 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="group"
    >
      {msg.sender === 'user' ? (
        // Mensaje del usuario
        <div
          className="flex flex-col items-end mb-2"
        >
          <div className="flex items-start gap-3 max-w-[100%] mr-4" style={{ marginRight: '20px' }}>
            <div
              className="rounded-3xl px-2 py-0 shadow-sm bg-muted/80 backdrop-blur-sm text-foreground border border-border/10 max-w-[calc(100%-4rem)] md:max-w-lg"
            >
              {isEditing ? (
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  className="w-full min-h-[80px] p-3 border border-border rounded-2xl resize-y focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground"
                  placeholder="Edita tu mensaje aquí..."
                />
              ) : (
                <div className="text-sm break-words font-sans">
                  <MarkdownRenderer content={msg.text} />
                </div>
              )}

              {/* Contexto RAG utilizado */}
              {msg.ragContext && msg.ragContext.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border/20">
                  <h4 className="text-xs font-semibold text-muted-foreground mb-2">Contexto Utilizado:</h4>
                  <div className="flex flex-wrap gap-2">
                    {msg.ragContext.map(item => (
                      <div key={`${item.type}-${item.id}`} className="flex items-center gap-2 bg-background/50 p-1 px-2 rounded-md text-xs">
                        {item.type === 'collection' ? <Folder className="h-3 w-3 text-primary" /> : <File className="h-3 w-3 text-secondary" />}
                        <span>{item.name || item.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Archivos adjuntos */}
              {msg.image && (
                <div className="mt-3">
                  <Image
                    src={msg.image}
                    alt="Imagen adjunta"
                    className="max-w-full h-auto rounded-2xl cursor-pointer shadow-sm"
                    onClick={() => window.open(msg.image, '_blank')}
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
                  <span className="text-sm">{msg.document_url.split('/').pop() || 'Documento'}</span>
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
        <motion.div
          initial={{ opacity: 0, y: 0 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex flex-col mb-8"
        >
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div
                className="flex items-center gap-2 mb-3"
              >
                <span className="font-semibold text-foreground">KAI</span>
                <span className="text-xs text-muted-foreground">Assistant</span>
              </div>
              
              <div className="py-2 w-full">
                {isEditing ? (
                  <textarea
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    className="w-full min-h-[100px] p-3 border border-border rounded-2xl resize-y focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground"
                    placeholder="Edita tu mensaje aquí..."
                  />
                ) : (
                  <div className="text-sm text-foreground break-words font-sans">
                    {msg.sender === 'ai' ? (
                      <TypewriterMarkdown content={msg.text} shouldAnimate={isLastMessage} />
                    ) : (
                      <MarkdownRenderer content={msg.text} />
                    )}
                  </div>
                )}
                
                {/* Archivos adjuntos */}
                {msg.image && (
                  <div className="mt-4">
                    <Image 
                      src={msg.image} 
                      alt="Imagen generada" 
                      className="max-w-full h-auto rounded-2xl cursor-pointer shadow-sm" 
                      onClick={() => window.open(msg.image, '_blank')}
                      width={500} // Asumiendo un ancho razonable
                      height={500} // Asumiendo una altura razonable
                    />
                  </div>
                )}
                {msg.document_url && (
                  <div className="mt-3 flex items-center gap-2 text-muted-foreground hover:text-foreground cursor-pointer" onClick={() => window.open(msg.document_url, '_blank')}>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm">{msg.document_url.split('/').pop() || 'Documento'}</span>
                  </div>
                )}
                {msg.artifact && (
                  <div className="mt-3 flex items-center gap-2 text-muted-foreground hover:text-foreground cursor-pointer">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                      <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm">Ver Artefacto</span>
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
                  disabled={isAudioLoading && playingMessageIndex === index}
                >
                  {isAudioLoading && playingMessageIndex === index ? (
                    <Loader2 className="h-3 w-3" />
                  ) : playingMessageIndex === index ? (
                    isAudioPaused ? (
                      <Play className="h-3 w-3" />
                    ) : (
                      <Pause className="h-3 w-3" />
                    )
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
        </motion.div>
      )}
    </motion.div>
  );
});