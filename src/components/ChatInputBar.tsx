'use client';

import { useState, useRef, useEffect, memo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Send, ArrowUp, Search, BookMarked, BrainCircuit, Upload, Mic, X, Paperclip } from 'lucide-react';
import { ContextSelectorButton } from '@/components/ContextSelectorButton';

interface SelectedContextItem {
  id: string;
  type: 'document' | 'collection';
  name: string;
  title?: string;
}

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
  isRecording?: boolean;
  isUploadingFile?: boolean;
  isKnowledgeAnalysisActive: boolean;
  isWebSearchActive: boolean;
  isComprehensiveAnalysisActive: boolean;
  files: File[];
  messages?: ChatMessage[];
  onMessageChange: (value: string) => void;
  onSendMessage: (e?: React.FormEvent) => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onToggleKnowledgeAnalysis?: () => void;
  onToggleWebSearch?: () => void;
  onToggleComprehensiveAnalysis?: () => void;
  onStartRecording?: () => void;
  onStopRecording?: () => void;
  onFileUpload?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile?: (index: number) => void;
  onPaste?: (e: ClipboardEvent) => void;
  currentContext: SelectedContextItem[];
  isFixedPosition?: boolean;
  onOpenSearch?: () => void;
  children?: React.ReactNode;
  workspaceId?: string;
  inputPlaceholder?: string;
}

const ChatInputBarComponent: React.FC<ChatInputBarProps> = ({
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
  onKeyDown = () => {},
  onToggleKnowledgeAnalysis = () => {},
  onToggleWebSearch = () => {},
  onToggleComprehensiveAnalysis = () => {},
  onStartRecording = () => {},
  onStopRecording = () => {},
  onFileUpload = () => {},
  onRemoveFile = () => {},
  onPaste = () => {},
  currentContext,
  isFixedPosition = true,
  onOpenSearch,
  children,
  workspaceId,
  inputPlaceholder
}) => {
  const textAreaRef = useRef<HTMLTextAreaElement>(null);



  useEffect(() => {
    const textArea = textAreaRef.current;
    if (textArea) {
      const adjustHeight = () => {
        textArea.style.height = 'auto';
        const newHeight = textArea.scrollHeight;
        const maxHeight = 100; // Altura máxima en píxeles
        if (newHeight > maxHeight) {
          textArea.style.height = `${maxHeight}px`;
          textArea.style.overflowY = 'auto';
        } else {
          textArea.style.height = `${newHeight}px`;
          textArea.style.overflowY = 'hidden';
        }
      };
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
    <div className={isFixedPosition ? "fixed bottom-0 w-full md:w-[calc(100%-320px)] right-0 p-4 md:p-6 bg-background z-30" : "relative w-full"}>
      <div className="flex justify-center w-full">
      <form onSubmit={onSendMessage} className="relative w-full max-w-4xl">
        <div className="rounded-3xl bg-card border border-border px-4 py-3 shadow-medium hover:shadow-strong transition-shadow duration-300">
          {/* Archivos adjuntos */}
          {files.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
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
            onKeyDown={onKeyDown}
            placeholder={inputPlaceholder || (currentContext.length > 0 ? "Escribe tu mensaje..." : "Escribe tu mensaje o selecciona contexto...")}
            autoComplete="on"
            disabled={isResponding}
            className="w-full resize-none bg-transparent border-0 focus:ring-0 p-0 text-lg placeholder:text-muted-foreground/70"
            rows={1}
            onChange={(e) => onMessageChange(e.target.value)}
          />
          
          {/* Barra de acciones */}
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/50">
            {/* Botones de modo */}
            <div className="flex items-center gap-2">
              {children}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onToggleWebSearch}
                className={`rounded-full overflow-hidden transition-all duration-300 ease-in-out hover:w-auto w-8 h-8 p-0 hover:px-3 group flex items-center justify-center ${isWebSearchActive ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}>
                <Search className="h-4 w-4 flex-shrink-0" />
                <span className="ml-2 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-300 max-w-0 group-hover:max-w-xs overflow-hidden">
                  Búsqueda Web
                </span>
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onToggleComprehensiveAnalysis}
                className={`rounded-full overflow-hidden transition-all duration-300 ease-in-out hover:w-auto w-8 h-8 p-0 hover:px-3 group flex items-center justify-center ${isComprehensiveAnalysisActive ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}>
                <BrainCircuit className="h-4 w-4 flex-shrink-0" />
                <span className="ml-2 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-300 max-w-0 group-hover:max-w-xs overflow-hidden">
                  Búsqueda Analítica
                </span>
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
                className={`cursor-pointer p-2 rounded-full hover:bg-muted transition-colors flex items-center justify-center ${isUploadingFile ? 'opacity-50' : ''}`}
              >
                <Upload className="h-5 w-5 text-muted-foreground" />
              </label>

              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={isRecording ? onStopRecording : onStartRecording}
                className={`rounded-full flex items-center justify-center ${isRecording ? 'text-red-500 bg-red-50 dark:bg-red-950' : ''}`}
              >
                <Mic className="h-5 w-5" />
              </Button>
              
              <Button
                type="submit"
                disabled={isResponding || (!newMessage.trim() && files.length === 0)}
                className="group rounded-full overflow-hidden transition-all duration-300 ease-in-out hover:w-auto w-10 h-10 p-0 hover:px-3 flex items-center relative"
              >
                <div className="absolute inset-0 flex items-center justify-center w-10 h-10 flex-shrink-0">
                  {isResponding ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-background border-t-transparent" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </div>
                <span className="absolute left-10 ml-2 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-300 max-w-0 group-hover:max-w-xs overflow-hidden">
                  {isResponding ? 'Enviando...' : 'Enviar'}
                </span>
              </Button>
            </div>
          </div>
        </div>
      </form>
      </div>
    </div>
  );
};

export default memo(ChatInputBarComponent);
