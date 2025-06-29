'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Send, ArrowUp, Search, BookMarked, BrainCircuit, Upload, Mic } from 'lucide-react';

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
    <footer className="p-4 w-full flex justify-center shrink-0 bg-transparent mb-2">
      <form onSubmit={onSendMessage} className="relative w-full max-w-4xl">
            <div className="rounded-2xl bg-gray-300 dark:bg-card/90 p-4 shadow-lg w-[90%] mx-auto">
          <Textarea
            ref={textAreaRef}
            value={newMessage}
            onChange={(e) => onMessageChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="¿Cómo puedo ayudarte hoy?"
            autoComplete="off"
            disabled={isResponding}
            className="w-full resize-none bg-transparent border-0 focus:ring-0 p-0 text-base text-gray-800 dark:text-white"
            rows={1}
          />
            <div className="mt-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="relative group">
                <button className="flex items-center justify-center text-2xl text-gray-600 dark:text-muted-foreground/80 cursor-pointer w-8 h-8">
                  +
                </button>
                <div className="absolute left-0 bottom-full mb-1 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                  <div
                    onClick={onToggleKnowledgeAnalysis}
                    className={`cursor-pointer flex items-center gap-1.5 text-sm px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 ${isKnowledgeAnalysisActive ? 'text-primary' : 'text-gray-600 dark:text-muted-foreground/80'}`}
                  >
                    <BookMarked className="h-4 w-4 text-gray-600 dark:text-muted-foreground/80" />
                    Análisis de Conocimientos
                  </div>
                  <div
                    onClick={onToggleWebSearch}
                    className={`cursor-pointer flex items-center gap-1.5 text-sm px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 ${isWebSearchActive ? 'text-primary' : 'text-gray-600 dark:text-muted-foreground/80'}`}
                  >
                    <Search className="h-4 w-4 text-gray-600 dark:text-muted-foreground/80" />
                    Búsqueda Web
                  </div>
                  <div
                    onClick={onToggleComprehensiveAnalysis}
                    className={`cursor-pointer flex items-center gap-1.5 text-sm px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 ${isComprehensiveAnalysisActive ? 'text-primary' : 'text-gray-600 dark:text-muted-foreground/80'}`}
                  >
                    <BrainCircuit className="h-4 w-4 text-gray-600 dark:text-muted-foreground/80" />
                    Busqueda y Analisis
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="cursor-pointer flex items-center text-sm text-gray-600 dark:text-muted-foreground/80">
                <Upload className="h-4 w-4 text-gray-600 dark:text-muted-foreground/80" />
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
                className={`cursor-pointer flex items-center text-sm ${isRecording ? 'text-red-500' : 'text-gray-600 dark:text-muted-foreground/80'}`}
              >
                <Mic className={`h-4 w-4 ${isRecording ? 'text-red-500' : 'text-gray-600 dark:text-muted-foreground/80'}`} />
              </div>
              <div
                onClick={onSendMessage}
                className={`cursor-pointer flex items-center text-sm ${isResponding || !newMessage.trim() ? 'text-gray-400' : 'text-gray-700 hover:text-primary'} dark:${isResponding || !newMessage.trim() ? 'text-gray-500' : 'text-gray-300 hover:text-primary'}`}
              >
                <Send className="h-4 w-4 text-gray-600 dark:text-muted-foreground/80" />
              </div>
            </div>
          </div>
        </div>
      </form>
    </footer>
  );
};
