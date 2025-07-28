'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Send, ArrowUp, Search, BookMarked, BrainCircuit, Upload, Mic, X, Paperclip, Plus, Headphones } from 'lucide-react';

interface ChatMessage {
  text: string;
  sender: 'user' | 'ai';
  created_at: string;
  image_base64?: string;
  document_url?: string;
}

interface ChatInputBarProps {
  newMessage: string;
  isResponding: boolean;
  isRecording: boolean;
  isUploadingFile: boolean;
  isKnowledgeAnalysisActive: boolean;
  isWebSearchActive: boolean;
  isComprehensiveAnalysisActive: boolean;
  files: File[];
  messages?: ChatMessage[];
  onMessageChange: (value: string) => void;
  onSendMessage: (e?: React.FormEvent) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onToggleKnowledgeAnalysis: () => void;
  onToggleWebSearch: () => void;
  onToggleComprehensiveAnalysis: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile: (index: number) => void;
  onPaste: (e: ClipboardEvent) => void;
  isFixedPosition?: boolean;
  onOpenSearch?: () => void;
}

export function ChatInputBar({
  newMessage,
  isResponding,
  isRecording,
  isUploadingFile,
  isKnowledgeAnalysisActive,
  isWebSearchActive,
  isComprehensiveAnalysisActive,
  files,
  onMessageChange,
  onSendMessage,
  onKeyDown,
  onToggleKnowledgeAnalysis,
  onToggleWebSearch,
  onToggleComprehensiveAnalysis,
  onStartRecording,
  onStopRecording,
  onFileUpload,
  onRemoveFile,
  onPaste,
  isFixedPosition = true,
  onOpenSearch
}: ChatInputBarProps) {
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textArea = textAreaRef.current;
    if (textArea) {
      const adjustHeight = () => {
        textArea.style.height = 'auto';
        const newHeight = Math.min(textArea.scrollHeight, 40); // Altura máxima de 40px
        textArea.style.height = `${newHeight}px`;
        textArea.style.overflowY = newHeight === 40 ? 'auto' : 'hidden';
      };
      adjustHeight();
      textArea.addEventListener('input', adjustHeight);
      return () => textArea.removeEventListener('input', adjustHeight);
    }
  }, []);

  useEffect(() => {
    const textArea = textAreaRef.current;
    if (textArea && onPaste) {
      textArea.addEventListener('paste', onPaste);
    }
    return () => {
      if (textArea && onPaste) {
        textArea.removeEventListener('paste', onPaste);
      }
    };
  }, [onPaste]);

  return (
    <div className={isFixedPosition ? "fixed bottom-0 right-0 p-3 bg-background z-30" : "relative w-full"} style={isFixedPosition ? { left: '320px' } : {}}>
      <div className="flex justify-center w-full">
        <form onSubmit={onSendMessage} className="relative w-full max-w-4xl">
          <div className="rounded-full bg-card border border-border p-2 shadow-medium hover:shadow-strong transition-shadow duration-300 flex items-center">
            {/* Botón de Añadir (Plus) */}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="rounded-full text-muted-foreground hover:text-foreground"
            >
              <Plus className="h-5 w-5" />
            </Button>

            {/* Input de texto y Botones de acción (Micrófono, Auriculares, Enviar) */}
            <div className="flex-1 flex items-center gap-2">
              <Textarea
                ref={textAreaRef}
                value={newMessage}
                onChange={(e) => onMessageChange(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="¿Cómo puedo ayudarte hoy?"
                autoComplete="off"
                disabled={isResponding}
                className="flex-1 resize-none bg-transparent border-0 focus:ring-0 p-0 text-base placeholder:text-muted-foreground/70 min-h-[20px] max-h-[40px] overflow-y-auto"
                rows={1}
              />
              
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={isRecording ? onStopRecording : onStartRecording}
                className={`rounded-full ${isRecording ? 'text-red-500 bg-red-50 dark:bg-red-950' : ''}`}
              >
                <Mic className="h-5 w-5" />
              </Button>

              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="rounded-full text-muted-foreground hover:text-foreground"
              >
                <Headphones className="h-5 w-5" />
              </Button>

              <Button
                type="submit"
                disabled={isResponding || (!newMessage.trim() && files.length === 0)}
                className="rounded-full w-10 h-10 p-0 flex items-center justify-center"
              >
                {isResponding ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-background border-t-transparent" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Archivos adjuntos - Mantenidos por si se necesitan */}
          {files.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {files.map((file, index) => (
                <div key={index} className="flex items-center gap-2 bg-muted rounded-full px-3 py-2 text-sm">
                  <Paperclip className="h-4 w-4 text-muted-foreground" />
                  <span className="text-foreground max-w-32 truncate">{file.name}</span>
                  <button
                    type="button"
                    onClick={() => onRemoveFile(index)}
                    className="text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Botones de modo y carga de archivos - Reubicados y simplificados */}
          <div className="flex items-center justify-between mt-2 px-2">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onToggleWebSearch}
                className={`rounded-full px-3 py-1 text-sm ${isWebSearchActive ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}
              >
                <Search className="h-4 w-4 mr-2" />
                Búsqueda Web
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onToggleComprehensiveAnalysis}
                className={`rounded-full px-3 py-1 text-sm ${isComprehensiveAnalysisActive ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}
              >
                <BrainCircuit className="h-4 w-4 mr-2" />
                Interpretación de Código
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
