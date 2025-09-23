'use client';

import { useState, useRef, useEffect, memo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Send, ArrowUp, X, Paperclip, Upload, Loader2, Mic } from 'lucide-react';
import { ContextSelectorButton } from '@/components/ContextSelectorButton';
import { MoreActionsMenu } from './MoreActionsMenu';

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
  isProcessingAudio?: boolean;
  isUploadingFile?: boolean;
  isKnowledgeAnalysisActive: boolean;
  isWebSearchActive: boolean;
  isComprehensiveAnalysisActive: boolean;
  isDeepResearchActive: boolean; // Nueva prop
  selectedToolName?: string; // Nueva prop para forzar la ejecución de una herramienta
  messages?: ChatMessage[];
  onMessageChange: (value: string) => void;
  onSendMessage: (e?: React.FormEvent, message?: string) => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onToggleKnowledgeAnalysis?: () => void;
  onToggleWebSearch?: () => void;
  onToggleComprehensiveAnalysis?: () => void;
  onToggleDeepResearch?: () => void; // Nueva prop
  onStartRecording?: () => void;
  onStopRecording?: () => void;
  onFileUpload?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onPaste?: (e: ClipboardEvent) => void;
  currentContext: SelectedContextItem[];
  onRemoveContextItem?: (item: SelectedContextItem) => void;
  isFixedPosition?: boolean;
  onOpenSearch?: () => void;
  children?: React.ReactNode;
  workspaceId?: string;
  inputPlaceholder?: string;
}

const ChatInputBarComponent: React.FC<ChatInputBarProps> = ({
  newMessage,
  isResponding,
  isRecording = false,
  isProcessingAudio = false,
  isUploadingFile = false,
  isKnowledgeAnalysisActive,
  isWebSearchActive,
  isComprehensiveAnalysisActive,
  isDeepResearchActive,
  selectedToolName,
  onMessageChange,
  onSendMessage,
  onKeyDown = () => {},
  onToggleKnowledgeAnalysis = () => {},
  onToggleWebSearch = () => {},
  onToggleComprehensiveAnalysis = () => {},
  onToggleDeepResearch = () => {},
  onStartRecording = () => {},
  onStopRecording = () => {},
  onFileUpload = () => {},
  onRemoveContextItem = () => {},
  onPaste = () => {},
  currentContext,
  isFixedPosition = true,
  onOpenSearch,
  children,
  workspaceId,
  inputPlaceholder
}) => {
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  const handleMessageChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onMessageChange(e.target.value);
  }, [onMessageChange]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    let messageText = newMessage;

    if (selectedToolName) {
      messageText = `[USE_TOOL:${selectedToolName}] ${newMessage}`;
    }

    if (currentContext.length > 0) {
      const contextNames = currentContext.map(item => item.name).join(', ');
      messageText = `${messageText.trim()}. Considerando el siguiente contexto: ${contextNames}. Mi pregunta es: ${newMessage}`;
    }

    onSendMessage(e, messageText);
    onMessageChange('');
  }, [newMessage, selectedToolName, currentContext, onSendMessage, onMessageChange]);

  const handleRemoveContextItem = useCallback((item: SelectedContextItem) => {
    onRemoveContextItem(item);
  }, [onRemoveContextItem]);

  const handleFileUploadChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onFileUpload(e);
    e.target.value = '';
  }, [onFileUpload]);

  useEffect(() => {
    const textArea = textAreaRef.current;
    if (textArea) {
      const adjustHeight = () => {
        textArea.style.height = 'auto';
        const newHeight = textArea.scrollHeight;
        const maxHeight = 60;
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

  useEffect(() => {
    if (isProcessingAudio) {
      toast.info("Iniciando transcripción...");
    }
  }, [isProcessingAudio]);

  return (
    <div className={isFixedPosition ? "fixed bottom-0 w-full md:w-[calc(100%-320px)] right-0 p-4 md:p-6 bg-background z-30" : "relative w-full"}>
      <div className="flex justify-center w-full">
        <form onSubmit={handleSubmit} className="relative w-full">

          <div className="rounded-3xl bg-card border border-border px-4 py-2 shadow-medium hover:shadow-strong transition-shadow duration-300">
            {currentContext.length > 0 && (
              <div className="mb-2 flex gap-2 overflow-x-auto pb-2">
                {currentContext.map((item, index) => (
                  <div key={index} className="flex-shrink-0 flex items-center gap-2 bg-muted rounded-full px-3 py-1 text-sm">
                    <Paperclip className="h-4 w-4 text-muted-foreground" />
                    <span className="text-foreground">{item.name}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveContextItem(item)}
                      className="text-muted-foreground hover:text-destructive transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <Textarea
              ref={textAreaRef}
              value={newMessage}
              onKeyDown={onKeyDown}
              placeholder={inputPlaceholder || (currentContext.length > 0 ? "Escribe tu mensaje..." : "Escribe tu mensaje o selecciona contexto...")}
              autoComplete="on"
              disabled={isResponding}
              className="w-full resize-none bg-transparent border-0 focus:ring-0 p-0 text-lg placeholder:text-muted-foreground/70"
              rows={1}
              onChange={handleMessageChange}
            />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/50">
              <div className="flex items-center gap-2">
                {children}
                <MoreActionsMenu
                  isWebSearchActive={isWebSearchActive}
                  isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
                  isDeepResearchActive={isDeepResearchActive}
                  isRecording={isRecording}
                  isUploadingFile={isUploadingFile}
                  onToggleWebSearch={onToggleWebSearch}
                  onToggleComprehensiveAnalysis={onToggleComprehensiveAnalysis}
                  onToggleDeepResearch={onToggleDeepResearch}
                  onFileUpload={onFileUpload}
                  onStartRecording={onStartRecording}
                  onStopRecording={onStopRecording}
                />
              </div>
              <div className="flex items-center gap-3">
                <input
                  id="file-upload-chat-bar"
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.gif"
                  className="hidden"
                  onChange={handleFileUploadChange}
                  disabled={isUploadingFile}
                />
                <label htmlFor="file-upload-chat-bar" className="flex items-center justify-center h-9 w-9 rounded-full text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
                  {isUploadingFile ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
                </label>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={`rounded-full ${isRecording && !isProcessingAudio ? 'text-red-500 animate-pulse' : 'text-muted-foreground'} hover:bg-accent hover:text-accent-foreground`}
                  onClick={isRecording ? onStopRecording : onStartRecording}
                  disabled={isUploadingFile || isResponding || isProcessingAudio}
                >
                  {isProcessingAudio ? <Loader2 className="h-5 w-5 animate-spin" /> : isRecording ? <Mic className="h-5 w-5 text-red-500" /> : <Mic className="h-5 w-5" />}
                </Button>
                <Button
                  type="submit"
                  size="icon"
                  disabled={isResponding || (!newMessage.trim() && currentContext.length === 0)}
                  className="rounded-full"
                >
                  {isResponding ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
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



