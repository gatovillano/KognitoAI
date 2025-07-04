// ChatMessage.tsx
import React, { memo, useState } from 'react';
import { motion } from 'framer-motion';

import { ChatAvatar } from './ChatAvatar';
import { Button } from '@/components/ui/button';
import { Copy, Play, Loader2, Pause, RefreshCw } from 'lucide-react';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';

interface Artifact {
  id: number;
  content: string;
  type: 'html' | 'css' | 'js' | 'svg' | 'webpage';
  version: number;
}

interface ChatMessageProps {
  msg: { text: string; sender: 'user' | 'ai'; image?: string; document_url?: string; artifact?: Artifact };
  index: number;
  handleCopyMessage: (text: string) => void;
  handleRetry: (text: string) => void;
  handlePlayAudio: (text: string, index: number) => void;
  isAudioLoading: boolean;
  playingMessageIndex: number | null;
  isAudioPaused: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = memo(({
  msg,
  index,
  handleCopyMessage,
  handleRetry,
  handlePlayAudio,
  isAudioLoading,
  playingMessageIndex,
  isAudioPaused,
}) => {
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
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.4,
        ease: [0.25, 0.46, 0.45, 0.94],
        type: "spring",
        stiffness: 100,
        damping: 15
      }}
      className="group"
    >
      {msg.sender === 'user' ? (
        // Mensaje del usuario
        <motion.div
          className="flex flex-col items-end mb-6"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{
            duration: 0.4,
            ease: [0.25, 0.46, 0.45, 0.94],
            type: "spring",
            stiffness: 120,
            damping: 20
          }}
        >
          <div className="flex items-start gap-3 max-w-[100%] mr-4" style={{ marginRight: '20px' }}>
            <motion.div
              className="rounded-2xl px-4 py-3 shadow-sm bg-muted/80 backdrop-blur-sm text-foreground border border-border/30"
              style={{ maxWidth: '800px' }}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                duration: 0.3,
                ease: "easeOut",
                delay: 0.1
              }}
            >
              {isEditing ? (
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  className="w-full min-h-[70px] p-3 border border-border rounded-2xl resize-y focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground"
                  placeholder="Edita tu mensaje aquí..."
                />
              ) : (
                <div className="text-sm">
                  <MarkdownRenderer content={msg.text} />
                </div>
              )}
              
              {/* Archivos adjuntos */}
              {msg.image && (
                <div className="mt-3">
                  <img 
                    src={msg.image} 
                    alt="Imagen adjunta" 
                    className="max-w-full h-auto rounded-2xl cursor-pointer shadow-sm" 
                    onClick={() => window.open(msg.image, '_blank')}
                  />
                </div>
              )}
              {msg.document_url && (
                <div className="mt-3 flex items-center gap-2 text-white/80 hover:text-white cursor-pointer transition-colors" onClick={() => window.open(msg.document_url, '_blank')}>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm">{msg.document_url.split('/').pop() || 'Documento'}</span>
                </div>
              )}
            </motion.div>
            <ChatAvatar sender="user" />
          </div>

          {/* Botones de acción */}
          <div className="flex items-center gap-1 mt-0 mr-12 opacity-0 group-hover:opacity-100 transition-opacity">
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
        </motion.div>
      ) : (
        // Mensaje de la IA
        <motion.div
          className="flex flex-col mb-8"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{
            duration: 0.5,
            ease: [0.25, 0.46, 0.45, 0.94],
            delay: 0.1
          }}
        >
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <motion.div
                className="flex items-center gap-2 mb-3"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: 0.3,
                  ease: "easeOut",
                  delay: 0.2
                }}
              >
                <span className="font-semibold text-foreground">Kognito</span>
                <span className="text-xs text-muted-foreground">AI Assistant</span>
              </motion.div>
              
              <div className="py-2">
                {isEditing ? (
                  <textarea
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    className="w-full min-h-[100px] p-3 border border-border rounded-2xl resize-y focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground"
                    placeholder="Edita tu mensaje aquí..."
                  />
                ) : (
                  <div className="text-sm text-foreground">
                    <MarkdownRenderer content={msg.text} />
                  </div>
                )}
                
                {/* Archivos adjuntos */}
                {msg.image && (
                  <div className="mt-4">
                    <img 
                      src={msg.image} 
                      alt="Imagen generada" 
                      className="max-w-full h-auto rounded-2xl cursor-pointer shadow-sm" 
                      onClick={() => window.open(msg.image, '_blank')}
                    />
                  </div>
                )}
                {msg.document_url && (
                  <div className="mt-3 flex items-center gap-2 text-muted-foreground hover:text-foreground cursor-pointer transition-colors" onClick={() => window.open(msg.document_url, '_blank')}>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm">{msg.document_url.split('/').pop() || 'Documento'}</span>
                  </div>
                )}
                {msg.artifact && (
                  <div className="mt-3 flex items-center gap-2 text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                      <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm">Ver Artefacto</span>
                  </div>
                )}
              </div>
              
              {/* Botones de acción */}
              <div className="flex items-center gap-1 mt-0 ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
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
                    <Loader2 className="h-3 w-3 animate-spin" />
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

export { ChatMessage };
