// ChatMessage.tsx
import React, { memo, useState } from 'react';
import { motion } from 'framer-motion';
import { Avatar } from '@/components/ui/avatar';
import { ChatAvatar } from './ChatAvatar';
import { Button } from '@/components/ui/button';
import { Copy, Play, Loader2, Square } from 'lucide-react';
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
  handlePlayAudio: (text: string, index: number) => void;
  isAudioLoading: boolean;
  playingMessageIndex: number | null;
}

const ChatMessage: React.FC<ChatMessageProps> = memo(({
  msg,
  index,
  handleCopyMessage,
  handlePlayAudio,
  isAudioLoading,
  playingMessageIndex,
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
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      {msg.sender === 'user' ? (
        // Contenedor principal para mensajes de usuario
        <div className="flex flex-col items-center mb-16">
          <div className="w-full max-w-4xl mx-auto">
            <div className="flex flex-col items-end gap-4 ">
              <div className="flex items-start gap-4 justify-end ">
                <div className="rounded-lg py-0 px-4 bg-[hsl(var(--user-bubble))] min-w-5 max-w-4xl overflow-hidden flex items-center w-full">
                  <div className="text-sm [&>*:first-child]:mt-0 py-0 w-full">
                    <div className="chat-markdown-content text-foreground flex flex-col justify-center w-full">
                      {isEditing ? (
                        <textarea
                          value={editedText}
                          onChange={(e) => setEditedText(e.target.value)}
                          className="w-full min-h-[100px] p-2 border rounded-md resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
                          style={{ height: 'auto', minHeight: '100px', width: '100%', minWidth: '900px', boxSizing: 'border-box', maxWidth: '100%' }}
                          placeholder="Edita tu mensaje aquí..."
                        />
                      ) : (
                        <MarkdownRenderer content={msg.text} />
                      )}
                    </div>
                    {msg.image && (
                      <div className="mt-2">
                        <img 
                          src={msg.image} 
                          alt="Imagen adjunta" 
                          className="max-w-full h-auto rounded-lg cursor-pointer" 
                          onClick={() => window.open(msg.image, '_blank')}
                        />
                      </div>
                    )}
                    {msg.document_url && (
                      <div className="mt-2 flex items-center gap-2 text-blue-300 hover:text-blue-500 cursor-pointer" onClick={() => window.open(msg.document_url, '_blank')}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                        </svg>
                        <span className="text-sm">{msg.document_url.split('/').pop() || 'Documento'}</span>
                      </div>
                    )}
                  </div>
                </div>
                <ChatAvatar sender="user" />
              </div>
              <div className="flex items-center gap-2 mr-10">
                <Button variant="ghost" size="sm" className="p-1" onClick={() => handleCopyMessage(msg.text)}>
                  <Copy className="h-3 w-3 text-gray-600" />
                </Button>
                {isEditing ? (
                  <>
                    <Button variant="ghost" size="sm" className="p-1" onClick={handleSave}>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 11.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </Button>
                    <Button variant="ghost" size="sm" className="p-1" onClick={handleCancel}>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </Button>
                  </>
                ) : (
                  <Button variant="ghost" size="sm" className="p-1" onClick={handleEdit}>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                    </svg>
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        // Contenedor principal para mensajes de la IA
        <div className="flex flex-col items-center mb-16">
          <div className="w-full max-w-4xl mx-auto">
            <div className="flex items-start gap-4">
              <ChatAvatar sender="ai" />
              <div className="flex-0 min-w-0 w-full">
                <div className="font-bold">Kognito</div>
                <div className="break-words mt-0 text-sm text-gray-200 leading-none [&>p]:my-0 [&>*:last-child]:mb-0 [&>*:first-child]:mt-0 w-full">
                  <div className="chat-markdown-content w-full">
                    {isEditing ? (
                      <textarea
                        value={editedText}
                        onChange={(e) => setEditedText(e.target.value)}
                        className="w-full min-h-[100px] p-2 border rounded-md resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
                        style={{ height: 'auto', minHeight: '100px', width: '100%', minWidth: '700px', boxSizing: 'border-box', maxWidth: '100%' }}
                        placeholder="Edita tu mensaje aquí..."
                      />
                    ) : (
                      <MarkdownRenderer content={msg.text} />
                    )}
                  </div>
                  {msg.image && (
                    <div className="mt-2">
                      <img 
                        src={msg.image} 
                        alt="Mapa mental" 
                        className="max-w-full h-auto rounded-lg cursor-pointer" 
                        onClick={() => window.open(msg.image, '_blank')}
                      />
                    </div>
                  )}
                  {msg.document_url && (
                    <div className="mt-2 flex items-center gap-2 text-blue-500 hover:text-blue-700 cursor-pointer" onClick={() => window.open(msg.document_url, '_blank')}>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-sm">{msg.document_url.split('/').pop() || 'Documento'}</span>
                    </div>
                  )}
                  {msg.artifact && (
                    <div className="mt-2 flex items-center gap-2 text-blue-500 hover:text-blue-700 cursor-pointer">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                        <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                      </svg>
                      <span className="text-sm">Ver Artefacto</span>
                    </div>
                  )}
                </div>
                <div className="mt-1 flex items-center gap-1">
                  <Button variant="ghost" size="sm" className="p-1" onClick={() => handleCopyMessage(msg.text)}>
                    <Copy className="h-3 w-3 text-gray-600" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="p-1"
                    onClick={() => handlePlayAudio(msg.text, index)}
                    disabled={isAudioLoading && playingMessageIndex === index}
                  >
                    {isAudioLoading && playingMessageIndex === index && (
                      <Loader2 className="h-3 w-3 animate-spin text-gray-600" />
                    )}
                    {playingMessageIndex === index && !isAudioLoading && (
                      <Square className="h-3 w-3 text-gray-600" />
                    )}
                    {playingMessageIndex !== index && <Play className="h-3 w-3 text-gray-600" />}
                  </Button>
                  {isEditing ? (
                    <>
                      <Button variant="ghost" size="sm" className="p-1" onClick={handleSave}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 11.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </Button>
                      <Button variant="ghost" size="sm" className="p-1" onClick={handleCancel}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </Button>
                    </>
                  ) : (
                    <Button variant="ghost" size="sm" className="p-1" onClick={handleEdit}>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                      </svg>
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
});

export { ChatMessage };
