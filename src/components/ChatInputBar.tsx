'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Send, ArrowUp, Search, BookMarked, BrainCircuit, Upload, Mic, X, Paperclip } from 'lucide-react';

interface ChatInputBarProps {
  newMessage: string;
  isResponding: boolean;
  isRecording: boolean;
  isUploadingFile: boolean;
  isKnowledgeAnalysisActive: boolean;
  isWebSearchActive: boolean;
  isComprehensiveAnalysisActive: boolean;
  files: File[];
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
  onPaste
}: ChatInputBarProps) {
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textArea = textAreaRef.current;
    if (textArea) {
      const adjustHeight = () => {
        textArea.style.height = 'auto';
        const newHeight = textArea.scrollHeight;
        const maxHeight = 120; // Altura máxima en píxeles
        if (newHeight > maxHeight) {
          textArea.style.height = `${maxHeight}px`;
          textArea.style.overflowY = 'auto';
        } else {
          textArea.style.height = `${newHeight}px`;
          textArea.style.overflowY = 'hidden';
        }
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
    <footer className="p-4 w-full flex justify-center shrink-0 bg-transparent mb-2">
      <form onSubmit={onSendMessage} className="relative w-full max-w-4xl">
        <div className="rounded-3xl bg-card border border-border p-6 shadow-sm">
          {/* Archivos adjuntos */}
          {files.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-2">
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

          {/* Input de texto */}
          <Textarea
            ref={textAreaRef}
            value={newMessage}
            onChange={(e) => onMessageChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Escribe tu mensaje..."
            autoComplete="off"
            disabled={isResponding}
            className="w-full resize-none bg-transparent border-0 focus:ring-0 p-0 text-lg placeholder:text-muted-foreground/70"
            rows={1}
          />
          
          {/* Barra de acciones */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/50">
            {/* Botones de modo */}
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant={isKnowledgeAnalysisActive ? "default" : "outline"}
                size="sm"
                onClick={onToggleKnowledgeAnalysis}
                className="rounded-full"
              >
                <BookMarked className="h-4 w-4 mr-2" />
                Conocimientos
              </Button>
              <Button
                type="button"
                variant={isWebSearchActive ? "default" : "outline"}
                size="sm"
                onClick={onToggleWebSearch}
                className="rounded-full"
              >
                <Search className="h-4 w-4 mr-2" />
                Web
              </Button>
              <Button
                type="button"
                variant={isComprehensiveAnalysisActive ? "default" : "outline"}
                size="sm"
                onClick={onToggleComprehensiveAnalysis}
                className="rounded-full"
              >
                <BrainCircuit className="h-4 w-4 mr-2" />
                Análisis
              </Button>
            </div>

            {/* Botones de acción */}
            <div className="flex items-center gap-3">
              <input
                id="file-upload"
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.gif"
                className="hidden"
                onChange={(e) => {
                  onFileUpload(e);
                  e.target.value = '';
                }}
                disabled={isUploadingFile}
              />
              <label
                htmlFor="file-upload"
                className={`cursor-pointer p-2 rounded-full hover:bg-muted transition-colors ${isUploadingFile ? 'opacity-50' : ''}`}
              >
                <Upload className="h-5 w-5 text-muted-foreground" />
              </label>
              
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
                type="submit"
                disabled={isResponding || (!newMessage.trim() && files.length === 0)}
                className="rounded-full px-6"
              >
                {isResponding ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-background border-t-transparent" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                {isResponding ? 'Enviando...' : 'Enviar'}
              </Button>
            </div>
          </div>
        </div>
      </form>
    </footer>
  );
};
