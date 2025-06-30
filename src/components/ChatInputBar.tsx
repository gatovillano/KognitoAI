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
              <button
                onClick={onToggleKnowledgeAnalysis}
                className={`cursor-pointer flex items-center gap-1.5 text-sm px-2 py-1 rounded-md ${isKnowledgeAnalysisActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`}
              >
                <BookMarked className={`h-4 w-4 ${isKnowledgeAnalysisActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`} />
                Análisis de Conocimientos
              </button>
              <button
                onClick={onToggleWebSearch}
                className={`cursor-pointer flex items-center gap-1.5 text-sm px-2 py-1 rounded-md ${isWebSearchActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`}
              >
                <Search className={`h-4 w-4 ${isWebSearchActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`} />
                Búsqueda Web
              </button>
              <button
                onClick={onToggleComprehensiveAnalysis}
                className={`cursor-pointer flex items-center gap-1.5 text-sm px-2 py-1 rounded-md ${isComprehensiveAnalysisActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`}
              >
                <BrainCircuit className={`h-4 w-4 ${isComprehensiveAnalysisActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`} />
                Búsqueda y Análisis
              </button>
            </div>
            <div className="flex items-center gap-3">
              <div className="cursor-pointer flex items-center text-sm text-gray-600 dark:text-muted-foreground/80" onClick={() => {
                const fileInput = document.getElementById('file-upload');
                if (fileInput) {
                  fileInput.click();
                }
              }}>
                <Upload className="h-4 w-4 text-gray-600 dark:text-muted-foreground/80" />
                <label htmlFor="file-upload" className="cursor-pointer sr-only">Subir Archivo</label>
                <input
                  id="file-upload"
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.gif"
                  className="hidden"
                  onChange={(e) => {
                    console.log("Evento de subida de archivo disparado", e.target.files);
                    if (e.target.files && e.target.files.length > 0) {
                      alert("Archivo seleccionado: " + e.target.files.length + " archivo(s)");
                      onFileUpload(e);
                    }
                  }}
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
