'use client';

import { useState, useRef, useEffect, memo, useCallback, useMemo } from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { ArrowUp, X, Paperclip, Loader2, Mic, Square, BookMarked } from 'lucide-react';
import { MoreActionsMenu } from './MoreActionsMenu';
import ContextSelectorDialog from './ContextSelectorDialog';
import { useAuth } from '@/contexts/AuthContext';

interface AutocompleteState {
  isVisible: boolean;
  trigger: '#' | '@' | null;
  query: string;
  options: string[];
  activeIndex: number;
  wordStartIndex: number;
}

interface SelectedContextItem {
  id: string;
  type: 'document' | 'collection';
  name: string;
  title?: string;
  topic?: string;
  file_name?: string;
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
  onStopResponding?: () => void;
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
  onContextSelected?: (items: SelectedContextItem[]) => void;
  inputPlaceholder?: string;
  activeRepositoryContext?: { type: 'github' | 'local', path: string, url?: string } | null;
  onClearRepositoryContext?: () => void;
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
  onStopResponding,
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
  inputPlaceholder,
  activeRepositoryContext,
  onClearRepositoryContext = () => {},
  onContextSelected = () => {},
}) => {
  const { token } = useAuth();
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const autocompleteAbortRef = useRef<AbortController | null>(null);
  const autocompleteTimerRef = useRef<number | null>(null);
  const repoTreeCacheRef = useRef<Map<string, string[]>>(new Map());
  const [isContextSelectorOpen, setIsContextSelectorOpen] = useState(false);
  const [isKnowledgeAnalysisForcedState, setIsKnowledgeAnalysisForcedState] = useState(false);
  const [isWebSearchForcedState, setIsWebSearchForcedState] = useState(false);
  const [isComprehensiveAnalysisForcedState, setIsComprehensiveAnalysisForcedState] = useState(false);
  const [isDeepResearchForcedState, setIsDeepResearchForcedState] = useState(false);

  const [autocomplete, setAutocomplete] = useState<AutocompleteState>({
    isVisible: false,
    trigger: null,
    query: '',
    options: [],
    activeIndex: 0,
    wordStartIndex: 0,
  });

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

  const updateAutocompleteOptions = useCallback(async (trigger: '#' | '@', query: string) => {
    autocompleteAbortRef.current?.abort();
    const controller = new AbortController();
    autocompleteAbortRef.current = controller;

    try {
      if (!token) {
        console.warn('Autocomplete: No auth token available in context');
        return;
      }
      
      if (trigger === '#') {
        const repoUrl = activeRepositoryContext?.type === 'github' ? activeRepositoryContext.url || activeRepositoryContext.path : null;
        if (!repoUrl) {
          setAutocomplete(prev => ({ ...prev, options: [], activeIndex: 0 }));
          return;
        }

        const cachedOptions = repoTreeCacheRef.current.get(repoUrl);
        let fullOptions: string[] = cachedOptions ?? [];
        if (!cachedOptions) {
          const res = await fetch(`/api/github/tree_flat?repo_url=${encodeURIComponent(repoUrl)}`, {
            headers: { 'Authorization': `Bearer ${token}` },
            signal: controller.signal,
          });
          const data = await res.json();
          fullOptions = Array.isArray(data.options) ? data.options : [];
          repoTreeCacheRef.current.set(repoUrl, fullOptions);
        }

        const filtered = fullOptions
          .filter(o => o.toLowerCase().includes(query.toLowerCase()))
          .slice(0, 50);

        setAutocomplete(prev => ({
          ...prev,
          options: filtered,
          activeIndex: 0,
        }));
        return;
      }

      // Local SSH options from new API
      const res = await fetch(`/api/files/tree_flat?query=${encodeURIComponent(query)}`, {
        headers: { 'Authorization': `Bearer ${token}` },
        signal: controller.signal,
      });
      const data = await res.json();
      const options = Array.isArray(data.options) ? data.options : [];
      
      setAutocomplete(prev => ({ 
        ...prev, 
        options, 
        activeIndex: 0 
      }));
    } catch (err: any) {
      if (err?.name !== 'AbortError') {
        console.error('Autocomplete fetch error', err);
      }
    }
  }, [activeRepositoryContext]);

  const scheduleAutocompleteUpdate = useCallback((trigger: '#' | '@', query: string) => {
    if (autocompleteTimerRef.current) {
      window.clearTimeout(autocompleteTimerRef.current);
    }

    autocompleteTimerRef.current = window.setTimeout(() => {
      void updateAutocompleteOptions(trigger, query);
    }, 150);
  }, [updateAutocompleteOptions]);

  const adjustTextareaHeight = useCallback(() => {
    const textArea = textAreaRef.current;
    if (!textArea) return;

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
  }, []);

  const handleMessageChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setNewMessage(val);
    
    // Autocomplete detection
    const cursorPosition = e.target.selectionStart;
    const textBeforeCursor = val.slice(0, cursorPosition);
    const match = /(#|@)([^\s]*)$/.exec(textBeforeCursor);
    
    if (match) {
      const trigger = match[1] as '#' | '@';
      const query = match[2];
      const wordStartIndex = match.index;
      setAutocomplete(prev => ({
        ...prev,
        isVisible: true,
        trigger,
        query,
        wordStartIndex,
      }));
      scheduleAutocompleteUpdate(trigger, query);
    } else {
      autocompleteAbortRef.current?.abort();
      if (autocompleteTimerRef.current) {
        window.clearTimeout(autocompleteTimerRef.current);
      }
      setAutocomplete(prev => ({ ...prev, isVisible: false }));
    }
  }, [setNewMessage, scheduleAutocompleteUpdate]);

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
    setIsContextSelectorOpen(false);
  }, [setNewMessage, newMessage]);

  const openContextDialog = useCallback(() => {
    setIsContextSelectorOpen(true);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (autocomplete.isVisible && autocomplete.options.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setAutocomplete(prev => ({ ...prev, activeIndex: (prev.activeIndex + 1) % prev.options.length }));
        return;
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setAutocomplete(prev => ({ ...prev, activeIndex: (prev.activeIndex - 1 + prev.options.length) % prev.options.length }));
        return;
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        const selectedOption = autocomplete.options[autocomplete.activeIndex];
        const before = newMessage.slice(0, autocomplete.wordStartIndex);
        const after = newMessage.slice(textAreaRef.current?.selectionStart || newMessage.length);
        
        // Insert the selected option
        const insertText = `${autocomplete.trigger}${selectedOption} `;
        setNewMessage(before + insertText + after);
        setAutocomplete(prev => ({ ...prev, isVisible: false }));
        
        // Move cursor asynchronously
        setTimeout(() => {
          if (textAreaRef.current) {
            const newPos = before.length + insertText.length;
            textAreaRef.current.selectionStart = newPos;
            textAreaRef.current.selectionEnd = newPos;
          }
        }, 0);
        return;
      } else if (e.key === 'Escape') {
        setAutocomplete(prev => ({ ...prev, isVisible: false }));
        return;
      }
    }

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
  }, [autocomplete, newMessage, currentContext.length, uploadedImagePreviews, onKeyDown]);

  const handleRemoveContextItem = useCallback((item: SelectedContextItem) => {
    onRemoveContextItem(item);
  }, [onRemoveContextItem]);

  useEffect(() => {
    adjustTextareaHeight();
  }, [newMessage, adjustTextareaHeight]);

  useEffect(() => {
    return () => {
      autocompleteAbortRef.current?.abort();
      if (autocompleteTimerRef.current) {
        window.clearTimeout(autocompleteTimerRef.current);
      }
    };
  }, []);

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
          fill
          style={{ objectFit: 'cover' }}
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
            {activeRepositoryContext && (
              <div className="mb-2 flex items-center justify-between bg-primary/10 border border-primary/20 rounded-md px-3 py-1.5 text-sm">
                <div className="flex items-center gap-2 overflow-hidden">
                  <span className="shrink-0 text-primary">
                    {activeRepositoryContext.type === 'github' ? '📍 Modo Repositorio:' : '🔑  SSH Local:'}
                  </span>
                  <span className="font-mono text-muted-foreground truncate" title={activeRepositoryContext.path}>
                    {activeRepositoryContext.path}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={onClearRepositoryContext}
                  className="shrink-0 ml-2 text-muted-foreground hover:text-destructive transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
            
            {autocomplete.isVisible && autocomplete.options.length > 0 && (
              <div className="absolute z-50 bottom-full mb-2 bg-popover text-popover-foreground border border-border shadow-lg rounded-md w-64 max-h-48 overflow-y-auto">
                <div className="p-1">
                  <div className="text-[10px] font-bold text-muted-foreground uppercase px-2 py-1">
                    {autocomplete.trigger === '#' ? 'Archivos del Repositorio' : 'Archivos Locales'}
                  </div>
                  {autocomplete.options.map((option, index) => (
                    <div 
                      key={option}
                      className={`px-2 py-1.5 text-sm cursor-pointer rounded-sm flex items-center gap-2 ${index === autocomplete.activeIndex ? 'bg-primary/20 text-primary' : 'hover:bg-muted'}`}
                      onMouseDown={(evt) => {
                        evt.preventDefault(); // prevent input blur
                        const selectedOption = option;
                        const before = newMessage.slice(0, autocomplete.wordStartIndex);
                        const after = newMessage.slice(textAreaRef.current?.selectionStart || newMessage.length);
                        const insertText = `${autocomplete.trigger}${selectedOption} `;
                        setNewMessage(before + insertText + after);
                        setAutocomplete(prev => ({ ...prev, isVisible: false }));
                      }}
                    >
                      <Paperclip className="h-3 w-3 shrink-0" />
                      <span className="truncate">{option}</span>
                    </div>
                  ))}
                </div>
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
              onInput={adjustTextareaHeight}
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
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="rounded-full text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  onClick={openContextDialog}
                  title="Añadir contexto"
                >
                  <BookMarked className="h-5 w-5" />
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    const action = isRecording ? onStopRecording : onStartRecording;
                    action?.();
                  }}
                  disabled={isProcessingAudio}
                  className={`rounded-full ${isRecording ? 'text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}`}
                >
                  {isProcessingAudio ? <Loader2 className="h-5 w-5 animate-spin" /> : <Mic className="h-5 w-5" />}
                </Button>
                {isResponding ? (
                  <Button
                    type="button"
                    size="icon"
                    onClick={onStopResponding}
                    title="Detener respuesta"
                    className="rounded-full bg-red-500 hover:bg-red-600 text-white"
                  >
                    <Square className="h-4 w-4 fill-current" />
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    size="icon"
                    disabled={isUploadingFile || isVectorizingFile || (!newMessage.trim() && currentContext.length === 0 && (!uploadedImagePreviews || uploadedImagePreviews.length === 0))}
                    className="rounded-full"
                  >
                    {(isUploadingFile || isVectorizingFile) ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
                  </Button>
                )}
              </div>
            </div>
          </div>

          <ContextSelectorDialog
            isOpen={isContextSelectorOpen}
            onClose={() => setIsContextSelectorOpen(false)}
            onSelectContext={onContextSelected}
            onSelectNote={handleAttachNote}
            currentContext={currentContext}
            workspaceId={workspaceId}
          />

        </form>
      </div>
    </div>
  );
};

export default memo(ChatInputBarComponent);


