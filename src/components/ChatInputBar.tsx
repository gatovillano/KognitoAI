'use client';

import { useState, useRef, useEffect, memo, useCallback, useMemo } from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Send, ArrowUp, X, Paperclip, Upload, Loader2, Mic, NotebookText, Image as ImageIcon } from 'lucide-react';
import { ContextSelectorButton } from '@/components/ContextSelectorButton';
import { MoreActionsMenu } from './MoreActionsMenu';
import NoteSelectorDialog from './NoteSelectorDialog';

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
  images_base64?: string[];
  document_url?: string;
}

interface ChatInputBarProps {
  newMessage: string;
  isResponding: boolean;
  isRecording?: boolean;
  isProcessingAudio?: boolean;
  isUploadingFile?: boolean;
  isVectorizingFile?: boolean; // Nueva prop para indicar la vectorización
  isUploadingImages?: boolean;
  uploadedImagePreviews?: string[] | null;
  isKnowledgeAnalysisActive: boolean;
  isWebSearchActive: boolean;
  isComprehensiveAnalysisActive: boolean;
  isDeepResearchActive: boolean;
  selectedToolName?: string;
  messages?: ChatMessage[];

  setNewMessage: (value: string) => void;
  onSendMessage: (e?: React.FormEvent, message?: string) => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onToggleKnowledgeAnalysis?: () => void;
  onToggleWebSearch?: () => void;
  onToggleComprehensiveAnalysis?: () => void;
  onToggleDeepResearch?: () => void;
  onStartRecording?: () => void;
  onStopRecording?: () => void;
  onFileUpload?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onImageUpload?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveImage?: (index: number) => void;
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
  isVectorizingFile = false, // Nueva prop
  isUploadingImages = false,
  uploadedImagePreviews = null,
  isKnowledgeAnalysisActive,
  isWebSearchActive,
  isComprehensiveAnalysisActive,
  isDeepResearchActive,
  selectedToolName,
  setNewMessage,
  onSendMessage,
  onKeyDown = () => { },
  onToggleKnowledgeAnalysis = () => { },
  onToggleWebSearch = () => { },
  onToggleComprehensiveAnalysis = () => { },
  onToggleDeepResearch = () => { },
  onStartRecording = () => { },
  onStopRecording = () => { },
  onFileUpload = () => { },
  onImageUpload = () => { },
  onRemoveImage = () => { },
  onRemoveContextItem = () => { },
  onPaste = () => { },
  currentContext,
  isFixedPosition = true,
  onOpenSearch,
  children,
  workspaceId,
  inputPlaceholder
}) => {
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const [isNoteSelectorOpen, setIsNoteSelectorOpen] = useState(false);
  const [isKnowledgeAnalysisForcedState, setIsKnowledgeAnalysisForcedState] = useState(false);
  const [isWebSearchForcedState, setIsWebSearchForcedState] = useState(false);
  const [isComprehensiveAnalysisForcedState, setIsComprehensiveAnalysisForcedState] = useState(false);
  const [isDeepResearchForcedState, setIsDeepResearchForcedState] = useState(false);

  const onToggleKnowledgeAnalysisForced = useCallback(() => {
    setIsKnowledgeAnalysisForcedState(prev => !prev);
  }, []);

  const onToggleWebSearchForced = useCallback(() => {
    setIsWebSearchForcedState(prev => !prev);
  }, []);

  const onToggleComprehensiveAnalysisForced = useCallback(() => {
    setIsComprehensiveAnalysisForcedState(prev => !prev);
  }, []);

  const onToggleDeepResearchForced = useCallback(() => {
    setIsDeepResearchForcedState(prev => !prev);
  }, []);

  const handleMessageChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setNewMessage(e.target.value);
  }, [setNewMessage]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    let messageText = newMessage;
    let forcedTool = '';

    if (isWebSearchForcedState) {
      forcedTool = 'web_search_tool';
    } else if (isComprehensiveAnalysisForcedState) {
      forcedTool = 'comprehensive_analysis_tool';
    } else if (isDeepResearchForcedState) {
      forcedTool = 'deep_research_tool';
    }

    if (forcedTool) {
      messageText = `[USE_TOOL:${forcedTool}] ${newMessage}`;
    } else if (selectedToolName) {
      messageText = `[USE_TOOL:${selectedToolName}] ${newMessage}`;
    }

    onSendMessage(e, messageText);
  }, [
    newMessage,
    selectedToolName,
    onSendMessage,
    isWebSearchForcedState,
    isComprehensiveAnalysisForcedState,
    isDeepResearchForcedState,
  ]);

  const handleAttachNote = useCallback((note: { title?: string; content: string }) => {
    const noteText = note.title ? `Nota: ${note.title}\n${note.content}` : `Nota: ${note.content}`;
    setNewMessage(newMessage + '\n' + noteText);
    setIsNoteSelectorOpen(false);
  }, [setNewMessage, newMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (newMessage.trim() || currentContext.length > 0 || (uploadedImagePreviews && uploadedImagePreviews.length > 0)) {
        const form = (e.target as HTMLTextAreaElement).form;
        if (form) {
          form.requestSubmit();
        }
      }
    }
    onKeyDown(e);
  }, [newMessage, currentContext.length, uploadedImagePreviews, onKeyDown]);

  const handleRemoveContextItem = useCallback((item: SelectedContextItem) => {
    onRemoveContextItem(item);
  }, [onRemoveContextItem]);

  // Ajuste de altura del textarea - optimizado
  useEffect(() => {
    const textArea = textAreaRef.current;
    if (!textArea) return;

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

    adjustHeight(); // Ajustar al montar y cuando cambia el mensaje
    textArea.addEventListener('input', adjustHeight);
    return () => textArea.removeEventListener('input', adjustHeight);
  }, [newMessage]); // Solo cuando cambia el mensaje

  // Manejo de paste - optimizado
  useEffect(() => {
    const textArea = textAreaRef.current;
    if (!textArea || !onPaste) return;

    textArea.addEventListener('paste', onPaste);
    return () => {
      textArea.removeEventListener('paste', onPaste);
    };
  }, [onPaste]);

  useEffect(() => {
    if (isProcessingAudio) {
      toast.info("Iniciando transcripción...");
    }
  }, [isProcessingAudio]);

  // Memoizar elementos del contexto para evitar re-renderizados
  const contextItems = useMemo(() => {
    return currentContext.map((item, index) => (
      <div key={`${item.id}-${index}`} className="flex-shrink-0 flex items-center gap-2 bg-muted rounded-full px-3 py-1 text-sm">
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
    ));
  }, [currentContext, handleRemoveContextItem]);

  // Memoizar previsualizaciones de imágenes
  const imagePreviews = useMemo(() => {
    if (!uploadedImagePreviews || uploadedImagePreviews.length === 0) return null;

    return uploadedImagePreviews.map((preview, index) => (
      <div key={`img-${index}`} className="relative w-24 h-24">
        <Image
          src={preview}
          alt={`Previsualización de imagen ${index + 1}`}
          layout="fill"
          objectFit="cover"
          className="rounded-md"
        />
        <button
          type="button"
          onClick={() => onRemoveImage(index)}
          className="absolute top-1 right-1 bg-gray-900/50 text-white rounded-full p-1 hover:bg-gray-900/75 transition-colors"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    ));
  }, [uploadedImagePreviews, onRemoveImage]);


  return (
    <div className={isFixedPosition ? "fixed bottom-0 w-full md:w-[calc(100%-320px)] right-0 p-2 sm:p-4 md:p-6 bg-transparent z-30" : "relative w-full"}>
      <div className="flex justify-center w-full">
        <form onSubmit={handleSubmit} className="relative w-full">

          <div className="rounded-3xl bg-card border border-border px-2 py-1 sm:px-4 sm:py-2 shadow-medium hover:shadow-strong transition-shadow duration-300">
            {currentContext.length > 0 && (
              <div className="mb-2 flex gap-2 overflow-x-auto pb-2">
                {contextItems}
              </div>
            )}
            {uploadedImagePreviews && uploadedImagePreviews.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {imagePreviews}
              </div>
            )}
            <Textarea
              ref={textAreaRef}
              value={newMessage}
              onKeyDown={handleKeyDown}
              placeholder={inputPlaceholder || (currentContext.length > 0 ? "Escribe tu mensaje..." : "Escribe tu mensaje o selecciona contexto...")}
              autoComplete="on"
              className="w-full resize-none bg-transparent border-0 focus:ring-0 p-0 text-base sm:text-lg placeholder:text-muted-foreground/70"
              rows={1}
              onChange={handleMessageChange}
            />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/50">
              <div className="flex items-center gap-2">
                <MoreActionsMenu
                  isWebSearchActive={isWebSearchActive}
                  isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
                  isDeepResearchActive={isDeepResearchActive}
                  isUploadingFile={isUploadingFile || isVectorizingFile}
                  isUploadingImage={isUploadingImages}
                  onToggleWebSearch={onToggleWebSearch}
                  onToggleComprehensiveAnalysis={onToggleComprehensiveAnalysis}
                  onToggleDeepResearch={onToggleDeepResearch}
                  isKnowledgeAnalysisForced={isKnowledgeAnalysisForcedState}
                  isWebSearchForced={isWebSearchForcedState}
                  isComprehensiveAnalysisForced={isComprehensiveAnalysisForcedState}
                  isDeepResearchForced={isDeepResearchForcedState}
                  onToggleKnowledgeAnalysisForced={onToggleKnowledgeAnalysisForced}
                  onToggleWebSearchForced={onToggleWebSearchForced}
                  onToggleComprehensiveAnalysisForced={onToggleComprehensiveAnalysisForced}
                  onToggleDeepResearchForced={onToggleDeepResearchForced}
                  onFileUpload={onFileUpload}
                  onImageUpload={onImageUpload}
                />
                {children}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="rounded-full text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  onClick={() => setIsNoteSelectorOpen(true)}
                >
                  <NotebookText className="h-5 w-5" />
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    console.log('Mic button clicked. isRecording:', isRecording);
                    const action = isRecording ? onStopRecording : onStartRecording;
                    action?.();
                  }}
                  disabled={isProcessingAudio}
                  className={`rounded-full ${isRecording ? 'text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}`}
                >
                  {isProcessingAudio ? <Loader2 className="h-5 w-5 animate-spin" /> : <Mic className="h-5 w-5" />}
                </Button>
                <Button
                  type="submit"
                  size="icon"
                  disabled={isUploadingFile || isVectorizingFile || (!newMessage.trim() && currentContext.length === 0 && (!uploadedImagePreviews || uploadedImagePreviews.length === 0))}
                  className="rounded-full"
                >
                  {(isUploadingFile || isVectorizingFile) ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </div>

          <NoteSelectorDialog
            isOpen={isNoteSelectorOpen}
            onClose={() => setIsNoteSelectorOpen(false)}
            onSelectNote={handleAttachNote}
            workspaceId={workspaceId}
          />

        </form>
      </div>
    </div>
  );
};

export default memo(ChatInputBarComponent);



