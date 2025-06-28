// ChatMessage.tsx
import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { Avatar } from '@/components/ui/avatar';
import { ChatAvatar } from './ChatAvatar';
import { Button } from '@/components/ui/button';
import { Copy, Play, Loader2, Square } from 'lucide-react';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';

interface ChatMessageProps {
  msg: { text: string; sender: 'user' | 'ai' };
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
  return (
    <motion.div
      key={index}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      {msg.sender === 'user' ? (
        // Contenedor principal para mensajes de usuario
        <div className="flex flex-col items-center">
          <div className="w-full max-w-4xl mx-auto">
            <div className="flex items-start gap-4 justify-end">
                <div className="rounded-lg py-1 px-1 bg-secondary text-secondary-foreground min-w-10 max-w-[80%] overflow-hidden">
                <div className="text-lg whitespace-pre-wrap overflow-hidden leading-tight">
                  <div className="chat-markdown-content">
                    <MarkdownRenderer content={msg.text} />
                  </div>
                </div>
              </div>
              <ChatAvatar sender="user" />
            </div>
          </div>
        </div>
      ) : (
        // Contenedor principal para mensajes de la IA
        <div className="flex flex-col items-center">
          <div className="w-full max-w-4xl mx-auto">
            <div className="flex items-start gap-4">
              <ChatAvatar sender="ai" />
              <div className="flex-1 min-w-0">
                <div className="font-bold">Kognito</div>
                <div className="break-words mt-1 text-lg leading-tight">
                  <div className="chat-markdown-content">
                    <MarkdownRenderer content={msg.text} />
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={() => handleCopyMessage(msg.text)}>
                    <Copy className="h-4 w-4 mr-2 text-gray-600" /> Copiar
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handlePlayAudio(msg.text, index)}
                    disabled={isAudioLoading && playingMessageIndex === index}
                  >
                    {isAudioLoading && playingMessageIndex === index && (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin text-gray-600" />
                    )}
                    {playingMessageIndex === index && !isAudioLoading && (
                      <Square className="h-4 w-4 mr-2 text-gray-600" />
                    )}
                    {playingMessageIndex !== index && <Play className="h-4 w-4 mr-2 text-gray-600" />}
                    Escuchar
                  </Button>
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
