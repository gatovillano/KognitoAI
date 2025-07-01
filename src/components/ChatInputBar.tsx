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
        if (newHeight !== textArea.clientHeight) {
          textArea.style.height = `${newHeight}px`;
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
            <div className="rounded-2xl bg-gray-300 dark:bg-card/90 p-4 shadow-lg w-[90%] mx-auto">
          {files.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
              {files.map((file, index) => (
                <div key={index} className="flex items-center gap-2 bg-gray-200 dark:bg-gray-700 rounded-full px-3 py-1 text-sm">
                  <Paperclip className="h-4 w-4" />
                  <span>{file.name}</span>
                  <button type="button" onClick={() => onRemoveFile(index)} className="text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
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
                type="button"
                onClick={onToggleKnowledgeAnalysis}
                className={`cursor-pointer flex items-center gap-1.5 text-sm px-2 py-1 rounded-md ${isKnowledgeAnalysisActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`}
              >
                <BookMarked className={`h-4 w-4 ${isKnowledgeAnalysisActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`} />
                Análisis de Conocimientos
              </button>
              <button
                type="button"
                onClick={onToggleWebSearch}
                className={`cursor-pointer flex items-center gap-1.5 text-sm px-2 py-1 rounded-md ${isWebSearchActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`}
              >
                <Search className={`h-4 w-4 ${isWebSearchActive ? 'text-blue-500' : 'text-gray-600 dark:text-muted-foreground/80'}`} />
                Búsqueda Web
              </button>
              <button
                type="button"
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
                    onFileUpload(e);
                    // Reset the input value to allow selecting the same file again
                    e.target.value = '';
                  }}
                  disabled={isUploadingFile}
                />
              </div>
              <button
                type="button"
                onClick={isRecording ? onStopRecording : onStartRecording}
                className={`cursor-pointer flex items-center text-sm ${isRecording ? 'text-red-500' : 'text-gray-600 dark:text-muted-foreground/80'}`}
              >
                <Mic className={`h-4 w-4 ${isRecording ? 'text-red-500' : 'text-gray-600 dark:text-muted-foreground/80'}`} />
              </button>
              <button
                type="submit"
                disabled={isResponding || (!newMessage.trim() && files.length === 0)}
                className={`cursor-pointer flex items-center text-sm ${isResponding || (!newMessage.trim() && files.length === 0) ? 'text-gray-400' : 'text-gray-700 hover:text-primary'} dark:${isResponding || (!newMessage.trim() && files.length === 0) ? 'text-gray-500' : 'text-gray-300 hover:text-primary'}`}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </form>
    </footer>
  );
};
