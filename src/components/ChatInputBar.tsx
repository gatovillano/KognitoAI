'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { ArrowUp, Search, BookMarked, BrainCircuit, Upload, Mic } from 'lucide-react';

interface ChatInputBarProps {
  newMessage: string;
  isResponding: boolean;
  isRecording: boolean;
  isUploadingFile: boolean;
  isKnowledgeAnalysisActive: boolean;
  isWebSearchActive: boolean;
  isComprehensiveAnalysisActive: boolean;
  onMessageChange: (value: string) => void;
  onSendMessage: (e?: React.FormEvent) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onToggleKnowledgeAnalysis: () => void;
  onToggleWebSearch: () => void;
  onToggleComprehensiveAnalysis: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
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
  onMessageChange,
  onSendMessage,
  onKeyDown,
  onToggleKnowledgeAnalysis,
  onToggleWebSearch,
  onToggleComprehensiveAnalysis,
  onStartRecording,
  onStopRecording,
  onFileUpload,
  onPaste
}: ChatInputBarProps) {
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textArea = textAreaRef.current;
    if (textArea) {
      textArea.style.height = 'auto';
      const newHeight = textArea.scrollHeight;
      if (newHeight !== textArea.clientHeight) {
        textArea.style.height = `${newHeight}px`;
      }
    }
  }, [newMessage]);

  useEffect(() => {
    const textArea = textAreaRef.current;
    if (textArea) {
      textArea.addEventListener('paste', onPaste);
    }
    return () => {
      if (textArea) {
        textArea.removeEventListener('paste', onPaste);
      }
    };
  }, [onPaste]);

  return (
    <footer className="p-4 w-full flex justify-center shrink-0 bg-transparent">
      <form onSubmit={onSendMessage} className="relative w-full max-w-3xl">
        <div className="rounded-2xl bg-card p-4 shadow-lg">
          <Textarea
            ref={textAreaRef}
            value={newMessage}
            onChange={(e) => onMessageChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="¿Cómo puedo ayudarte hoy?"
            autoComplete="off"
            disabled={isResponding}
            className="w-full resize-none bg-transparent border-0 focus:ring-0 p-0 text-base"
            rows={1}
          />
          <div className="mt-3 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div 
                onClick={onToggleKnowledgeAnalysis}
                className={`cursor-pointer flex items-center gap-1.5 text-sm ${isKnowledgeAnalysisActive ? 'text-primary' : 'text-muted-foreground'}`}
              >
                <BookMarked className="h-4 w-4" />
                Análisis de Conocimientos
              </div>
              <div 
                onClick={onToggleWebSearch}
                className={`cursor-pointer flex items-center gap-1.5 text-sm ${isWebSearchActive ? 'text-primary' : 'text-muted-foreground'}`}
              >
                <Search className="h-4 w-4" />
                Búsqueda Web
              </div>
              <div
                onClick={onToggleComprehensiveAnalysis}
                className={`cursor-pointer flex items-center gap-1.5 text-sm ${isComprehensiveAnalysisActive ? 'text-primary' : 'text-muted-foreground'}`}
              >
                <BrainCircuit className="h-4 w-4" />
                Busqueda y Analisis
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="cursor-pointer flex items-center text-sm text-muted-foreground">
                <Upload className="h-4 w-4" />
                <label htmlFor="file-upload" className="cursor-pointer sr-only">Subir Archivo</label>
                <input
                  id="file-upload"
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.gif"
                  className="hidden"
                  onChange={onFileUpload}
                  disabled={isUploadingFile}
                />
              </div>
              <div
                onClick={isRecording ? onStopRecording : onStartRecording}
                className={`cursor-pointer flex items-center text-sm ${isRecording ? 'text-red-500' : 'text-muted-foreground'}`}
              >
                <Mic className="h-4 w-4" />
              </div>
              <Button 
                type="submit" 
                size="icon" 
                variant="ghost"
                disabled={isResponding || !newMessage.trim()}
              >
                <ArrowUp className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>
      </form>
    </footer>
  );
};
