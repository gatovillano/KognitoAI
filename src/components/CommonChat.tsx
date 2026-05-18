'use client';
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useSearch } from '@/contexts/SearchContext';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ArrowLeft, FolderKanban, Bot, BrainCircuit, Search, X, Folder, File as FileIcon, Share2 } from 'lucide-react';
import { ChatMessage } from '@/components/ChatMessage';
import ChatInputBar from '@/components/ChatInputBar';
import { stripMarkdown } from '@/lib/chatUtils';
import { BackgroundTaskIndicator } from '@/components/BackgroundTaskIndicator';
import { EmptyChat } from '@/components/EmptyChat';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { WebSocketMessage } from '@/hooks/useWebSocket'; // Importar WebSocketMessage
import DeepResearchVisualizer from '@/components/DeepResearchVisualizer';
import { AnalysisDetailDialog } from '@/app/(dashboard)/analysis/analysis-detail-dialog';
import { Analysis } from '@/lib/models';
import { ShareChatDialog } from '@/components/ShareChatDialog';

const INITIAL_RENDERED_MESSAGES = 40;
const RENDER_BATCH_SIZE = 30;
const STREAM_SCROLL_THROTTLE_MS = 120;

// ... (interfaces remain the same) ...
interface ToolStatusMessage {
  thread_id: string;
  tool_name: string;
  status: 'start' | 'end' | 'error';
  timestamp: string;
  error?: string;
  task_id?: string;
  message?: string;
  result?: string;
  sources?: Source[];
}

interface Source {
  id: number | string;
  title: string;
  url: string;
  snippet: string;
  type: 'web' | 'document' | 'memory' | 'code' | 'database' | 'graph' | 'note' | 'github';
  metadata?: Record<string, any>;
}

interface MessageContentPart {
  type: 'text' | 'reasoning' | 'tool_call' | 'tool_result';
  content: string;
  id?: string;
  status?: 'start' | 'end' | 'error';
  tool_name?: string;
}

const hasPendingToolCall = (parts: MessageContentPart[], toolName?: string, content?: string): boolean => {
  if (!toolName) return false;

  return parts.some((part) =>
    part.type === 'tool_call' &&
    part.status === 'start' &&
    part.tool_name === toolName &&
    (content === undefined || part.content === content)
  );
};

const findLatestToolCallIndex = (parts: MessageContentPart[], toolName?: string): number => {
  for (let index = parts.length - 1; index >= 0; index--) {
    const part = parts[index];
    if (
      part.type === 'tool_call' &&
      part.status === 'start' &&
      (!toolName || part.tool_name === toolName)
    ) {
      return index;
    }
  }

  return parts.map((part) => part.type).lastIndexOf('tool_call');
};

interface ChatMessageType {
  text: string;
  sender: 'user' | 'ai';
  created_at: string;
  model_name?: string;
  images_base64?: string[];
  document_url?: string;
  ragContext?: SelectedContextItem[];
  sources?: Source[];
  chunks?: string[];
  reasoning?: string;
  reasoning_chunks?: string[];
  content_parts?: MessageContentPart[];
  tool_code?: string;
  taskId?: string;
}

interface IndexedResponse {
  message: ChatMessageType;
  index: number;
}

interface SingleRenderItem {
  type: 'single';
  key: string;
  message: ChatMessageType;
  index: number;
}

interface RetryGroupRenderItem {
  type: 'retry_group';
  key: string;
  userMessage: ChatMessageType;
  userIndex: number;
  responses: IndexedResponse[];
}

type ChatRenderItem = SingleRenderItem | RetryGroupRenderItem;

const normalizeRetryText = (text: string): string =>
  text.trim().replace(/\s+/g, ' ').toLowerCase();

const areImagesEqual = (first: string[] = [], second: string[] = []): boolean => {
  if (first.length !== second.length) return false;
  return first.every((img, idx) => img === second[idx]);
};

const areSameRetryPrompt = (first: ChatMessageType, second: ChatMessageType): boolean => {
  if (first.sender !== 'user' || second.sender !== 'user') return false;

  const sameText = normalizeRetryText(first.text) === normalizeRetryText(second.text);
  const sameContext = JSON.stringify(first.ragContext || []) === JSON.stringify(second.ragContext || []);
  const sameImages = areImagesEqual(first.images_base64 || [], second.images_base64 || []);

  return sameText && sameContext && sameImages;
};

interface SelectedContextItem {
  id: string;
  type: 'document' | 'collection';
  name: string;
  title?: string;
  topic?: string;
  file_name?: string;
}

interface Artifact {
  id: number;
  content: string;
  type: 'html' | 'css' | 'js' | 'svg' | 'webpage';
  version: number;
}

interface ThreadDetails {
  id: string;
  title: string;
  workspace_id?: string;
}

interface CommonChatProps {
  threadId: string;
  workspaceId?: string;
  initialMessage?: string;
  initialRagContext?: string;
}

function LoadingIndicator({
  isComprehensiveAnalysisActive = false,
  isKnowledgeAnalysisActive = false,
  isDeepResearchActive = false,
  toolName,
  reactState,
}: {
  isComprehensiveAnalysisActive?: boolean;
  isKnowledgeAnalysisActive?: boolean;
  isDeepResearchActive?: boolean;
  toolName?: string;
  reactState?: string;
}) {
  const [thoughtIndex, setThoughtIndex] = useState(0);

  const thoughts = useMemo(() => [
    "Descifrando intencionalidad...",
    "Explorando red semántica...",
    "Sintetizando vectores de conocimiento...",
    "Formulando respuesta lógica...",
    "Verificando consistencia cognitiva..."
  ], []);

  useEffect(() => {
    const interval = setInterval(() => {
      setThoughtIndex((prev) => (prev + 1) % thoughts.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [thoughts.length]);

  let text = 'Kognito está pensando';

  if (isDeepResearchActive) {
    text = 'Realizando investigación profunda';
  } else if (isComprehensiveAnalysisActive) {
    text = 'Realizando análisis comprensivo';
  } else if (isKnowledgeAnalysisActive) {
    text = 'Consultando la base de conocimiento';
  }

  if (toolName) {
    text = `Usando herramienta: ${toolName}`;
  }

  if (reactState) {
    text += ` - ${reactState}`;
  }

  // Define theme colors based on state
  const getStatusTheme = () => {
    if (isDeepResearchActive) {
      return {
        gradient: 'from-amber-500 via-orange-500 to-red-500',
        glow: 'shadow-orange-500/20',
        bgGlow: 'bg-orange-500/5 dark:bg-orange-500/10',
        border: 'border-orange-500/20 dark:border-orange-500/30',
        text: 'text-orange-600 dark:text-orange-400',
        subtext: 'text-orange-500/70 dark:text-orange-300/60',
        dotColor: 'bg-orange-500',
        iconColor: 'text-orange-500 dark:text-orange-400'
      };
    }
    if (isComprehensiveAnalysisActive) {
      return {
        gradient: 'from-emerald-400 via-teal-500 to-cyan-500',
        glow: 'shadow-emerald-500/20',
        bgGlow: 'bg-emerald-500/5 dark:bg-emerald-500/10',
        border: 'border-emerald-500/20 dark:border-emerald-500/30',
        text: 'text-emerald-600 dark:text-emerald-400',
        subtext: 'text-emerald-500/70 dark:text-emerald-300/60',
        dotColor: 'bg-emerald-500',
        iconColor: 'text-emerald-500 dark:text-emerald-400'
      };
    }
    if (isKnowledgeAnalysisActive) {
      return {
        gradient: 'from-cyan-400 via-blue-500 to-indigo-500',
        glow: 'shadow-cyan-500/20',
        bgGlow: 'bg-cyan-500/5 dark:bg-cyan-500/10',
        border: 'border-cyan-500/20 dark:border-cyan-500/30',
        text: 'text-cyan-600 dark:text-cyan-400',
        subtext: 'text-cyan-500/70 dark:text-cyan-300/60',
        dotColor: 'bg-cyan-500',
        iconColor: 'text-cyan-500 dark:text-cyan-400'
      };
    }
    if (toolName) {
      return {
        gradient: 'from-fuchsia-400 via-rose-500 to-violet-500',
        glow: 'shadow-fuchsia-500/20',
        bgGlow: 'bg-fuchsia-500/5 dark:bg-fuchsia-500/10',
        border: 'border-fuchsia-500/20 dark:border-fuchsia-500/30',
        text: 'text-fuchsia-600 dark:text-fuchsia-400',
        subtext: 'text-fuchsia-500/70 dark:text-fuchsia-300/60',
        dotColor: 'bg-fuchsia-500',
        iconColor: 'text-fuchsia-500 dark:text-fuchsia-400'
      };
    }
    return {
      gradient: 'from-indigo-500 via-purple-500 to-pink-500',
      glow: 'shadow-indigo-500/20',
      bgGlow: 'bg-indigo-500/5 dark:bg-indigo-500/10',
      border: 'border-indigo-500/20 dark:border-indigo-500/30',
      text: 'text-indigo-600 dark:text-indigo-400',
      subtext: 'text-indigo-500/70 dark:text-indigo-300/60',
      dotColor: 'bg-indigo-500',
      iconColor: 'text-indigo-500 dark:text-indigo-400'
    };
  };

  const theme = getStatusTheme();

  return (
    <div className="flex flex-col items-center py-4 w-full px-4">
      {/* Outer Container with dynamic glow */}
      <div className="relative group max-w-sm w-full">
        {/* Glow effect */}
        <div className={`absolute -inset-1 bg-gradient-to-r ${theme.gradient} opacity-20 blur-lg rounded-2xl animate-pulse transition duration-1000`} />
        
        {/* Main Glassmorphic Card */}
        <div className={`relative flex items-center space-x-4 p-4 rounded-2xl bg-white/40 dark:bg-slate-900/60 backdrop-blur-xl border ${theme.border} shadow-lg shadow-black/5 dark:shadow-black/20 overflow-hidden`}>
          
          {/* Orbital Neural Core */}
          <div className="relative flex items-center justify-center w-14 h-14 flex-shrink-0">
            {/* Pulsing Back Glow */}
            <span className={`absolute inline-flex h-10 w-10 rounded-full ${theme.dotColor} opacity-20 animate-ping`} />
            
            {/* Outer Spinning Ring (Dashed border) */}
            <motion.div
              className={`absolute inset-0 rounded-full border border-dashed border-t-transparent border-r-transparent ${theme.iconColor} opacity-70`}
              animate={{ rotate: 360 }}
              transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
            />
            
            {/* Inner Counter-spinning Gradient Ring */}
            <motion.div
              className={`absolute inset-1.5 rounded-full border border-t-transparent border-l-transparent bg-gradient-to-tr ${theme.gradient} opacity-25`}
              animate={{ rotate: -360 }}
              transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
            />
            
            {/* Floating Cognitive Particles */}
            {[...Array(3)].map((_, i) => (
              <motion.div
                key={i}
                className={`absolute w-1 h-1 rounded-full bg-gradient-to-tr ${theme.gradient}`}
                initial={{ x: 0, y: 0, opacity: 0 }}
                animate={{
                  x: [0, (i - 1) * 12, (i - 1) * 22, 0],
                  y: [0, -18 - i * 6, -35 - i * 4, 0],
                  opacity: [0, 0.9, 0.4, 0],
                  scale: [0.6, 1.3, 0.7, 0]
                }}
                transition={{
                  duration: 2.5 + i * 0.5,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: i * 0.7
                }}
              />
            ))}
            
            {/* Core Neural Icon */}
            <div className={`relative flex items-center justify-center w-9 h-9 rounded-full bg-white dark:bg-slate-950 border border-slate-100 dark:border-slate-800 shadow-inner z-10`}>
              <motion.div
                animate={{ scale: [0.95, 1.05, 0.95] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <BrainCircuit className={`w-5 h-5 ${theme.iconColor} stroke-[2.2px]`} />
              </motion.div>
            </div>
          </div>
          
          {/* Status Details */}
          <div className="flex flex-col flex-1 min-w-0 pr-1 select-none">
            {/* Primary Status Message (with subtle shimmer) */}
            <h4 className={`text-sm font-semibold tracking-wide ${theme.text} truncate`}>
              {text}
            </h4>
            
            {/* Secondary Rotating Thought Subtitle */}
            <div className="h-4 overflow-hidden mt-0.5">
              <AnimatePresence mode="wait">
                <motion.p
                  key={thoughtIndex}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.35, ease: "easeOut" }}
                  className={`text-[10px] sm:text-[11px] font-medium ${theme.subtext} tracking-wider uppercase font-mono`}
                >
                  {thoughts[thoughtIndex]}
                </motion.p>
              </AnimatePresence>
            </div>
          </div>
          
          {/* Subtle Activity Grid indicator (far right) */}
          <div className="flex items-center space-x-0.5 opacity-40">
            <span className={`w-1 h-3 rounded-full ${theme.dotColor} animate-pulse [animation-delay:0.2s]`} />
            <span className={`w-1 h-4 rounded-full ${theme.dotColor} animate-pulse [animation-delay:0.4s]`} />
            <span className={`w-1 h-2 rounded-full ${theme.dotColor} animate-pulse [animation-delay:0.6s]`} />
          </div>

        </div>
      </div>
    </div>
  );
}

export function CommonChat({ threadId, workspaceId, initialMessage, initialRagContext }: CommonChatProps) {
  const { user } = useAuth();
  const { settings } = useUserSettings();
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isResponding, setIsResponding] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isKnowledgeAnalysisActive, setIsKnowledgeAnalysisActive] = useState(false);
  const [isWebSearchActive, setIsWebSearchActive] = useState(false);
  const [isComprehensiveAnalysisActive, setIsComprehensiveAnalysisActive] = useState(false);
  const [isDeepResearchActive, setIsDeepResearchActive] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [isUploadingImages, setIsUploadingImages] = useState(false);
  const [uploadedImages, setUploadedImages] = useState<{ preview: string; base64: string }[]>([]);
  const [backgroundTasks, setBackgroundTasks] = useState<{ taskId: string; type: string }[]>([]);
  const [isProcessingAudio, setIsProcessingAudio] = useState(false);
  const [isVectorizingFile, setIsVectorizingFile] = useState(false); // Added isVectorizingFile
  const [isLoading, setIsLoading] = useState(true);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [selectedContext, setSelectedContext] = useState<SelectedContextItem[]>([]);
  const [toolName, setToolName] = useState<string | undefined>(undefined);
  const [reactState, setReactState] = useState<string | undefined>(undefined);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null); // Para almacenar el stream del micrófono
  const currentAudioRef = useRef<HTMLAudioElement | null>(null); // Para almacenar la instancia del objeto Audio
  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [isAudioPaused, setIsAudioPaused] = useState(false);
  const [researchProgress, setResearchProgress] = useState(0);
  const [researchStatus, setResearchStatus] = useState('Iniciando investigación...');
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [showScrollBottomButton, setShowScrollBottomButton] = useState(false);
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const [threadTitle, setThreadTitle] = useState<string>('');
  const [renderedMessageCount, setRenderedMessageCount] = useState(INITIAL_RENDERED_MESSAGES);
  const [activeRetryResponseMap, setActiveRetryResponseMap] = useState<Record<string, number>>({});

  const serializeSelectedContext = useCallback(
    (items: SelectedContextItem[]) => items.map((item) => ({
      type: item.type,
      id: item.id,
      name: item.name || item.title || item.file_name,
      title: item.title,
      topic: item.topic,
      file_name: item.file_name,
    })),
    []
  );

  const threadIdRef = useRef(threadId);
  useEffect(() => { threadIdRef.current = threadId; }, [threadId]);

  const newMessageRef = useRef(newMessage);
  useEffect(() => { newMessageRef.current = newMessage; }, [newMessage]);

  // Other refs
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const topSentinelRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const autoScrollRafRef = useRef<number | null>(null);
  const lastStreamScrollRef = useRef<number>(0);
  const currentTaskIdRef = useRef<string | null>(null);
  useEffect(() => { currentTaskIdRef.current = currentTaskId; }, [currentTaskId]);

  const handleScroll = useCallback(() => {
    const container = scrollAreaRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    // Un umbral de 100px para determinar si estamos en el fondo
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;

    setIsAutoScrollEnabled(isAtBottom);
    setShowScrollBottomButton(!isAtBottom);
  }, []);

  useEffect(() => {
    const container = scrollAreaRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  const scrollToBottom = useCallback((behavior: 'smooth' | 'auto' = 'auto', force: boolean = false) => {
    const container = scrollAreaRef.current;
    if (!container || (!isAutoScrollEnabled && !force)) return;

    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: behavior,
        block: 'end',
      });
    } else {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: behavior,
      });
    }
  }, [isAutoScrollEnabled]);

  const scheduleStreamScroll = useCallback((force: boolean = false) => {
    if (autoScrollRafRef.current !== null) return;

    autoScrollRafRef.current = requestAnimationFrame(() => {
      autoScrollRafRef.current = null;
      const now = performance.now();
      if (now - lastStreamScrollRef.current < STREAM_SCROLL_THROTTLE_MS) return;

      lastStreamScrollRef.current = now;
      scrollToBottom('auto', force);
    });
  }, [scrollToBottom]);

  useEffect(() => {
    return () => {
      if (autoScrollRafRef.current !== null) {
        cancelAnimationFrame(autoScrollRafRef.current);
      }
    };
  }, []);

  // Force scroll to bottom when loading indicators appear
  useEffect(() => {
    if (isResponding || toolName || isDeepResearchActive || backgroundTasks.length > 0) {
      // Use a small timeout to ensure the DOM has updated with the new indicator
      setTimeout(() => scrollToBottom('smooth', true), 100);
    }
  }, [isResponding, toolName, isDeepResearchActive, backgroundTasks.length, scrollToBottom]);

  const { registerMessageHandler } = useWebSocketContext();

  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      if (!message) return;

      const { type, taskId, ...data } = message;

      // Filtrar mensajes por thread_id para evitar que aparezcan en ventanas equivocadas
      const messageThreadId = data.thread_id || (data as any).thread_id;
      if (messageThreadId && threadIdRef.current && messageThreadId !== threadIdRef.current) {
        return;
      }

      // Filtrar por taskId para ignorar mensajes de tareas canceladas o anteriores
      if (taskId && currentTaskIdRef.current && taskId !== currentTaskIdRef.current) {
        return;
      }

      // Mover los side-effects fuera del updater de setMessages
      switch (type) {
        case 'stream_start':
          setIsResponding(true);
          setIsThinking(true);
          break;
        case 'reasoning_chunk':
        case 'stream_chunk':
          setIsThinking(false);
          break;
        case 'stream_end':
          setIsResponding(false);
          setIsThinking(false);
          setToolName(undefined);
          setReactState(undefined);
          setIsDeepResearchActive(false);
          if (taskId && taskId === currentTaskIdRef.current) {
            setCurrentTaskId(null);
          }
          break;
        case 'tool_start': {
          const toolStartMessage = data as ToolStatusMessage;
          if (toolStartMessage.tool_name === 'deep_research') {
            setIsDeepResearchActive(true);
          }
          setToolName(toolStartMessage.tool_name);
          setReactState('ejecutando');
          setIsThinking(true);

          if (toolStartMessage.task_id) {
            // Need to pass a messageIndex condition? No, just rely on task id.
            // In the original, it was `if (toolStartMessage.task_id && messageIndex === -1)` but `messageIndex` is only evaluated later.
            // It's fine to just add it here for now. Actually, if it's already running, it won't add it twice because of `.some` check.
            setBackgroundTasks((prev) => {
              const currentTaskId = toolStartMessage.task_id as string;
              return prev.some((task) => task.taskId === currentTaskId) ? prev : [...prev, { taskId: currentTaskId, type: toolStartMessage.tool_name }];
            });
            toast.info(`Iniciando ${toolStartMessage.tool_name || 'una herramienta'}...`, {
              description: toolStartMessage.message || "La tarea ha comenzado en segundo plano.",
              duration: 3000,
            });
          }
          break;
        }
        case 'tool_end':
        case 'tool_error': {
          const toolEndMessage = data as ToolStatusMessage;
          if (toolEndMessage.tool_name === 'deep_research') {
            setIsDeepResearchActive(false);
          }
          setToolName(undefined);
          setReactState(undefined);
          setIsThinking(false);
          
          if (toolEndMessage.task_id) {
            setBackgroundTasks((prev) => prev.filter((t) => t.taskId !== toolEndMessage.task_id));
          }
          
          if (toolEndMessage.tool_name !== 'deep_research') {
            toast[type === 'tool_end' ? 'success' : 'error'](`Herramienta ${toolEndMessage.tool_name || 'una herramienta'} ${type === 'tool_end' ? 'completada' : 'falló'}.`);
          }
          break;
        }
        case 'progress':
          if (data.progress !== undefined) {
            setResearchProgress(data.progress);
          }
          if (data.message) {
            setResearchStatus(data.message);
          }
          break;
      }

      setMessages(prevMessages => {
        let updatedMessages = [...prevMessages];

        // Note: findIndex is now inside the updater function to ensure it has the latest state
        let messageIndex = -1;
        if (taskId) {
          messageIndex = updatedMessages.findIndex(msg => msg.taskId === taskId);
        }

        switch (type) {
          case 'stream_start':
            if (taskId && messageIndex === -1) {
              updatedMessages.push({
                text: '',
                sender: 'ai',
                created_at: new Date().toISOString(),
                model_name: settings?.llm_model,
                sources: [],
                chunks: [],
                reasoning_chunks: [],
                content_parts: [],
                taskId: taskId,
              });
            }
            break;

          case 'reasoning_chunk': {
            let chunkMessageIndex = updatedMessages.findIndex(msg => msg.taskId === taskId);

              if (chunkMessageIndex === -1 && taskId) {
                updatedMessages.push({
                  text: '',
                  sender: 'ai',
                  created_at: new Date().toISOString(),
                  model_name: settings?.llm_model,
                  sources: [],
                  chunks: [],
                  reasoning_chunks: [],
                  content_parts: [],
                  taskId: taskId,
              });
              chunkMessageIndex = updatedMessages.length - 1;
            }

            if (taskId && (data.chunk !== undefined || (data as any).full_reasoning !== undefined) && chunkMessageIndex !== -1) {
              const existingMessage = updatedMessages[chunkMessageIndex];
              let newReasoning = existingMessage.reasoning || "";
              const chunk = data.chunk !== undefined ? data.chunk : "";

              if ((data as any).full_reasoning !== undefined) {
                newReasoning = (data as any).full_reasoning;
              } else {
                newReasoning += chunk;
              }

              // Update content_parts
              let newParts = [...(existingMessage.content_parts || [])];
              if (newParts.length > 0 && newParts[newParts.length - 1].type === 'reasoning') {
                newParts[newParts.length - 1].content = newReasoning;
              } else {
                newParts.push({ type: 'reasoning', content: newReasoning });
              }

              updatedMessages[chunkMessageIndex] = {
                ...existingMessage,
                reasoning: newReasoning,
                content_parts: newParts,
              };
            }
            scheduleStreamScroll();
            break;
          }

          case 'stream_chunk': {
            let chunkMessageIndex = updatedMessages.findIndex(msg => msg.taskId === taskId);

              if (chunkMessageIndex === -1 && taskId) {
                updatedMessages.push({
                  text: '',
                  sender: 'ai',
                  created_at: new Date().toISOString(),
                  model_name: settings?.llm_model,
                  sources: [],
                  chunks: [],
                  content_parts: [],
                  taskId: taskId,
                });
              chunkMessageIndex = updatedMessages.length - 1;
            }

            if (taskId && (data.chunk !== undefined || data.content !== undefined || (data as any).full_text !== undefined) && chunkMessageIndex !== -1) {
              const existingMessage = updatedMessages[chunkMessageIndex];
              let newText = existingMessage.text;
              const textChunk = data.chunk !== undefined ? data.chunk : (data.content !== undefined ? data.content : "");

              if ((data as any).full_text !== undefined) {
                newText = (data as any).full_text;
              } else {
                newText += textChunk;
              }

              // Update content_parts
              let newParts = [...(existingMessage.content_parts || [])];
              if (newParts.length > 0 && newParts[newParts.length - 1].type === 'text') {
                newParts[newParts.length - 1].content = newText;
              } else {
                newParts.push({ type: 'text', content: newText });
              }

              updatedMessages[chunkMessageIndex] = {
                ...existingMessage,
                text: newText,
                chunks: existingMessage.chunks || [],
                content_parts: newParts,
              };
            }
            scheduleStreamScroll();
            break;
          }

          case 'stream_end':
            if (taskId && messageIndex !== -1) {
              const finalMessage = updatedMessages[messageIndex];
              updatedMessages[messageIndex] = {
                ...finalMessage,
                text: (data as any).text || finalMessage.text,
                model_name: (data as any).model_name || finalMessage.model_name,
                chunks: undefined,
                taskId: undefined,
                sources: (data as any).sources || finalMessage.sources || [],
                reasoning: (data as any).reasoning || finalMessage.reasoning,
              };
            }
            break;

          case 'tool_start': {
            const toolStartMessage = data as ToolStatusMessage;
            const toolContent = toolStartMessage.message || `Usando ${toolStartMessage.tool_name}...`;

            // Handle background tasks inside setMessages? No, we moved it, but let's check if we missed something.
            // Wait, we need to setBackgroundTasks from inside setMessages? No, outside! Let's do it outside.
            // But I forgot to copy the toast and setBackgroundTasks for tool_start. I will add it to the outside switch.
            
            let chunkMessageIndex = updatedMessages.findIndex(msg => msg.taskId === taskId);
            if (chunkMessageIndex !== -1) {
              const existingMessage = updatedMessages[chunkMessageIndex];
              let newParts = [...(existingMessage.content_parts || [])];
              if (!hasPendingToolCall(newParts, toolStartMessage.tool_name, toolContent)) {
                newParts.push({
                  type: 'tool_call',
                  content: toolContent,
                  tool_name: toolStartMessage.tool_name,
                  status: 'start'
                });
                updatedMessages[chunkMessageIndex] = { ...existingMessage, content_parts: newParts };
              }
            }

            if (toolStartMessage.tool_name === 'deep_research') {
              return prevMessages;
            }
            break;
          }

          case 'tool_end':
          case 'tool_error': {
            const toolEndMessage = data as ToolStatusMessage;
            
            let chunkMessageIndex = updatedMessages.findIndex(msg => msg.taskId === taskId);
            if (chunkMessageIndex !== -1) {
              const existingMessage = updatedMessages[chunkMessageIndex];
              let newParts = [...(existingMessage.content_parts || [])];
              
              const lastPartIndex = findLatestToolCallIndex(newParts, toolEndMessage.tool_name);
              if (lastPartIndex !== -1) {
                 newParts[lastPartIndex] = {
                   ...newParts[lastPartIndex],
                   status: type === 'tool_error' ? 'error' : 'end',
                   content: toolEndMessage.result || toolEndMessage.error || newParts[lastPartIndex].content
                 };
              }

              updatedMessages[chunkMessageIndex] = {
                ...existingMessage,
                content_parts: newParts,
                sources: [...(existingMessage.sources || []), ...(toolEndMessage.sources || [])]
              };
            }
            break;
          }

          case 'tool_code':
            if (taskId && data.tool_code && messageIndex !== -1) {
              const existingMessage = updatedMessages[messageIndex];
              updatedMessages[messageIndex] = {
                ...existingMessage,
                tool_code: data.tool_code,
              };
            }
            break;
        }
        return updatedMessages;
      });
    };

    const unregister = registerMessageHandler(handleMessage);
    return unregister; // Cleanup on component unmount

  }, [registerMessageHandler, scheduleStreamScroll, settings?.llm_model]);

  const handleSendMessage = useCallback(
    async (e?: React.FormEvent, messageTextFromInput?: string) => {
      if (e) e.preventDefault();
      const messageToProcess = messageTextFromInput || newMessageRef.current;
      if (!messageToProcess.trim() && selectedContext.length === 0 && uploadedImages.length === 0) return;

      if (!user?.id) {
        toast.error('Error: Usuario no autenticado.');
        return;
      }

      if (!threadId) {
        setIsResponding(true);
        let newThreadId = '';
        try {
          const threadResponse = await apiClient.post('/api/threads', { workspace_id: workspaceId });
          newThreadId = threadResponse.data.id;

          const formData = new FormData();
          formData.append('thread_id', newThreadId);
          formData.append('account_id', user.id);
          formData.append('user_message', messageToProcess || '');
          if (selectedContext.length > 0) {
            formData.append('rag_context', JSON.stringify(serializeSelectedContext(selectedContext)));
          }
          if (uploadedImages.length > 0) {
            uploadedImages.forEach(image => {
              formData.append('images_base64', image.base64);
            });
          }
          await apiClient.post('/api/chat-form', formData); // CORRECTED ENDPOINT

          const newSearchParams = new URLSearchParams();
          if (selectedContext.length > 0) {
            newSearchParams.set('rag_context', JSON.stringify(serializeSelectedContext(selectedContext)));
          }

          if (workspaceId) {
            router.replace(`/workspaces/${workspaceId}/chat/${newThreadId}?${newSearchParams.toString()}`);
          } else {
            router.replace(`/chat/${newThreadId}?${newSearchParams.toString()}`);
          }
        } catch (error) {
          console.error('Error creando nuevo hilo de chat o enviando mensaje inicial:', error);
          toast.error('No se pudo iniciar una nueva conversación.');
          setIsResponding(false);
        }
        setNewMessage('');
        if (uploadedImages.length > 0) {
          uploadedImages.forEach(img => URL.revokeObjectURL(img.preview));
          setUploadedImages([]);
        }
        return;
      }

      const userMessage: ChatMessageType = {
        text: messageToProcess,
        sender: 'user',
        created_at: new Date().toISOString(),
        ragContext: selectedContext.length > 0 ? selectedContext : undefined,
        images_base64: uploadedImages.map(img => img.base64),
      };
      setMessages((prev) => [...prev, userMessage]);
      scheduleStreamScroll(true);
      setNewMessage('');
      if (uploadedImages.length > 0) {
        uploadedImages.forEach(img => URL.revokeObjectURL(img.preview));
        setUploadedImages([]);
      }
      setIsResponding(true);

      try {
        const formData = new FormData();
        formData.append('thread_id', threadId);
        formData.append('account_id', user.id);
        formData.append('user_message', messageToProcess || '');
        if (selectedContext.length > 0) {
          formData.append('rag_context', JSON.stringify(serializeSelectedContext(selectedContext)));
        }
        if (uploadedImages.length > 0) {
          uploadedImages.forEach(image => {
            formData.append('images_base64', image.base64);
          });
        }
        const response = await apiClient.post('/api/chat-form', formData); // CORRECTED ENDPOINT
        const responseTaskId = response.data?.taskId; // Captura el taskId de la respuesta

        if (responseTaskId) {
          setCurrentTaskId(responseTaskId);
          currentTaskIdRef.current = responseTaskId;
          // Opcional: inicializar un mensaje de streaming si el backend no envía stream_start inmediatamente
          // Ya no es necesario inicializar aquí, se maneja en stream_start dentro del useEffect de latestMessage
        }

      } catch (error: any) {
        console.error('Error sending message:', error);
        setMessages((prev) => [...prev, { text: 'Lo siento, ocurrió un error.', sender: 'ai', created_at: new Date().toISOString() }]);
        setIsResponding(false);
      }
    },
    [user, threadId, selectedContext, router, uploadedImages, scheduleStreamScroll, serializeSelectedContext]
  );

  const handleImageUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // Note: No size limits for image uploads - unlimited file sizes supported
    setIsUploadingImages(true);
    toast.info(`Cargando ${files.length} imagen(es)...`);

    const imagePromises = Array.from(files).map(file => {
      return new Promise<{ preview: string; base64: string }>((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64String = reader.result as string;
          resolve({
            preview: URL.createObjectURL(file),
            base64: base64String,
          });
        };
        reader.onerror = () => {
          reject(new Error(`Error al leer el archivo de imagen: ${file.name}`));
        };
        reader.readAsDataURL(file);
      });
    });

    try {
      const newImages = await Promise.all(imagePromises);
      setUploadedImages(prevImages => [...prevImages, ...newImages]);
      setIsUploadingImages(false);
      toast.success(`${files.length} imagen(es) lista(s) para enviar.`);
    } catch (error: any) {
      toast.error(error.message);
      setIsUploadingImages(false);
    }
  }, []);

  const handleRemoveImage = useCallback((index: number) => {
    setUploadedImages(prevImages => {
      const imageToRemove = prevImages[index];
      if (imageToRemove) {
        URL.revokeObjectURL(imageToRemove.preview);
      }
      return prevImages.filter((_, i) => i !== index);
    });
  }, []);

  const handleStartRecording = useCallback(async () => {
    try {
      console.log('DEBUG: Intentando acceder al micrófono...');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('DEBUG: Acceso al micrófono concedido.');
      audioStreamRef.current = stream;

      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/ogg',
      ];
      const supportedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type));

      if (!supportedMimeType) {
        toast.error('Tu navegador no soporta los formatos de audio necesarios para la grabación.');
        return;
      }

      console.log(`DEBUG: Usando el tipo de MIME soportado: ${supportedMimeType}`);
      const recorder = new MediaRecorder(stream, { mimeType: supportedMimeType });
      let localAudioChunks: Blob[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          console.log('DEBUG: ondataavailable event fired. Data size:', event.data.size, 'bytes');
          localAudioChunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        console.log('DEBUG: MediaRecorder onstop event fired.');
        const mimeType = recorder.mimeType;
        console.log(`DEBUG: Mime type obtenido del MediaRecorder: ${mimeType}`);

        setIsRecording(false);
        setIsProcessingAudio(true);
        toast.info('Deteniendo grabación de audio y procesando...');

        if (localAudioChunks.length > 0) {
          const audioBlob = new Blob(localAudioChunks, { type: mimeType });
          if (audioBlob.size === 0) {
            toast.error('El audio grabado está vacío. Intenta de nuevo.');
            setIsProcessingAudio(false);
            return;
          }

          const fileExtension = mimeType.split('/')[1].split(';')[0] || 'webm';
          const formData = new FormData();
          formData.append('file', audioBlob, `audio.${fileExtension}`);

          try {
            const response = await apiClient.post('/api/transcribe-audio', formData, {
              headers: { 'Content-Type': 'multipart/form-data' },
            });
            const { transcription } = response.data;
            setNewMessage(prev => prev + transcription); // Usar función de actualización para evitar problemas de closure
            toast.success('Audio transcrito y listo para enviar.');
          } catch (error: any) {
            console.error('DEBUG: Error en la llamada a /transcribe-audio:', error);
            toast.error('Error al transcribir el audio.');
          } finally {
            setIsProcessingAudio(false);
          }
        } else {
          toast.error('No se grabó audio.');
          setIsProcessingAudio(false);
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      toast.info('Iniciando grabación de audio...');
    } catch (error) {
      console.error('DEBUG: Error al acceder al micrófono:', error);
      toast.error('No se pudo acceder al micrófono. Asegúrate de dar permisos.');
      setIsRecording(false);
    }
  }, [setMediaRecorder, setIsRecording, setIsProcessingAudio]); // setNewMessage removido - es estable

  const handleStopRecording = useCallback(async () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      console.log('DEBUG: Deteniendo MediaRecorder. Estado actual:', mediaRecorder.state);
      mediaRecorder.stop();
      audioStreamRef.current?.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
      // La lógica de procesamiento se ha movido a recorder.onstop
    }
  }, [mediaRecorder]); // Dependencias actualizadas

  const handleCopyMessage = useCallback((text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success('Mensaje copiado al portapapeles');
    }).catch(() => {
      toast.error('Error al copiar el mensaje');
    });
  }, []);

  const handleRetry = useCallback(async (text: string) => {
    try {
      setIsResponding(true);

      const formData = new FormData();
      formData.append('thread_id', threadId);
      formData.append('account_id', user?.id || '');
      formData.append('user_message', text || '');
      if (selectedContext.length > 0) {
        formData.append('rag_context', JSON.stringify(serializeSelectedContext(selectedContext)));
      }

      await apiClient.post('/api/chat-form', formData);
    } catch (error: any) {
      console.error('Error retrying message:', error);
      toast.error('Error al reenviar el mensaje');
      setIsResponding(false);
    }
  }, [threadId, user?.id, selectedContext, serializeSelectedContext]);

  const handleDeleteMessage = useCallback(async (message: ChatMessageType) => {
    try {
      await apiClient.delete(`/api/threads/${threadId}/messages`, {
        data: {
          sender: message.sender,
          created_at: message.created_at,
          text: message.text,
        },
      });

      setMessages((prevMessages) => {
        const targetIndex = prevMessages.findIndex(
          (m) =>
            m.sender === message.sender &&
            m.created_at === message.created_at &&
            m.text === message.text
        );

        if (targetIndex === -1) {
          return prevMessages;
        }

        const nextMessages = [...prevMessages];
        nextMessages.splice(targetIndex, 1);
        return nextMessages;
      });

      toast.success('Mensaje eliminado');
    } catch (error: any) {
      console.error('Error deleting message:', error);
      toast.error(error?.response?.data?.detail || 'No se pudo eliminar el mensaje');
    }
  }, [threadId]);

  const handlePlayAudio = useCallback(async (text: string, index: number) => {
    if (isAudioLoading) return;

    // Si se hace clic en el mismo mensaje que ya está reproduciéndose o pausado
    if (playingMessageIndex === index) {
      if (currentAudioRef.current) {
        if (isAudioPaused) {
          // Si estaba pausado, reanudar
          currentAudioRef.current.play();
          setIsAudioPaused(false);
          toast.success('Reanudando audio.');
        } else {
          // Si estaba reproduciéndose, pausar
          currentAudioRef.current.pause();
          setIsAudioPaused(true);
          toast.info('Audio pausado.');
        }
      }
      return; // No hacer nada más, ya se manejó la pausa/reanudación
    }

    // Si se hace clic en un mensaje diferente mientras otro está reproduciéndose
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0; // Reiniciar el audio anterior
      URL.revokeObjectURL(currentAudioRef.current.src); // Liberar el objeto URL del audio anterior
      currentAudioRef.current = null;
    }

    setPlayingMessageIndex(index);
    setIsAudioLoading(true);
    setIsAudioPaused(false);
    toast.info('Generando audio...');

    try {
      const cleanText = stripMarkdown(text);

      // Construir payload con configuración TTS del usuario
      const ttsPayload: any = { text: cleanText };

      // Si el usuario tiene configuración TTS personalizada, usarla
      if (settings) {
        if (settings.tts_provider) {
          ttsPayload.provider = settings.tts_provider;
        }
        if (settings.tts_voice) {
          ttsPayload.voice = settings.tts_voice;
        }
        if (settings.tts_speed) {
          ttsPayload.speed = settings.tts_speed;
        }
        if (settings.tts_region) {
          ttsPayload.region = settings.tts_region;
        }
        if (settings.tts_api_base) {
          ttsPayload.api_base = settings.tts_api_base;
        }
        if (settings.tts_model) {
          ttsPayload.model = settings.tts_model;
        }
      }

      const response = await apiClient.post('/api/text-to-speech', ttsPayload, {
        responseType: 'blob', // Importante para recibir el audio como Blob
      });

      // Determinar el MIME type según el proveedor
      const isCoqui = ttsPayload.provider === 'coquitts' || ttsPayload.provider === 'coqui';
      const audioBlob = new Blob([response.data], { type: isCoqui ? 'audio/wav' : 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      currentAudioRef.current = audio; // Guardar la referencia al objeto Audio
      // Agregar event listeners para sincronizar el estado de pausa
      audio.onpause = () => {
        setIsAudioPaused(true);
      };

      audio.onplay = () => {
        setIsAudioPaused(false);
      };

      audio.onended = () => {
        setPlayingMessageIndex(null);
        setIsAudioLoading(false);
        setIsAudioPaused(false);
        if (currentAudioRef.current) {
          URL.revokeObjectURL(currentAudioRef.current.src); // Liberar el objeto URL
          currentAudioRef.current = null;
        }
      };

      audio.onerror = (e) => {
        console.error('Error al reproducir el audio:', e);
        toast.error('Error al reproducir el audio.');
        setPlayingMessageIndex(null);
        setIsAudioLoading(false);
        setIsAudioPaused(false);
        if (currentAudioRef.current) {
          URL.revokeObjectURL(currentAudioRef.current.src);
          currentAudioRef.current = null;
        }
      };

      await audio.play();
      toast.success('Reproduciendo audio.');

    } catch (error) {
      console.error('Error al obtener el audio TTS:', error);
      toast.error('Error al generar el audio. Verifica la configuración del servicio TTS y su disponibilidad.');
      setPlayingMessageIndex(null);
      setIsAudioLoading(false);
      setIsAudioPaused(false);
      if (currentAudioRef.current) {
        URL.revokeObjectURL(currentAudioRef.current.src);
        currentAudioRef.current = null;
      }
    }
  }, [isAudioLoading, playingMessageIndex, isAudioPaused, settings]);

  const handleRemoveContextItem = useCallback((itemToRemove: SelectedContextItem) => {
    setSelectedContext(prev => prev.filter(item => item.id !== itemToRemove.id));
    toast.info(`"${itemToRemove.name}" eliminado del contexto.`);
  }, []);

  const handleSourceClick = useCallback(async (source: Source) => {
    if (source.type === 'graph' && source.url.startsWith('analysis://')) {
      const analysisId = source.url.replace('analysis://', '');
      try {
        toast.info('Cargando detalles del insight...');
        const response = await apiClient.get(`/api/get-analysis-result/${analysisId}`);
        const analysisData = response.data;

        // Construct Analysis object from response
        const analysis: Analysis = {
          id: analysisData.id,
          file_name: analysisData.file_name,
          type: analysisData.analysis_type, // Map analysis_type to type
          title: analysisData.file_name, // Use file_name as title
          created_at: analysisData.created_at,
          status: analysisData.status,
          result_payload: analysisData.result_payload
        };

        setSelectedAnalysis(analysis);
      } catch (error) {
        console.error('Error fetching analysis details:', error);
        toast.error('No se pudieron cargar los detalles del insight.');
      }
    }
  }, []);

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploadingFile(true);
    toast.info(`Subiendo ${files.length} archivo(s)...`);

    const uploadPromises = Array.from(files).map(async (file) => {
      try {
        const formData = new FormData();
        formData.append('file', file);
        if (workspaceId) {
          formData.append('workspace_id', workspaceId);
          formData.append('topic', 'General'); // Usar un topic genérico para documentos de chat
        }
        if (threadId) {
          formData.append('thread_id', threadId);
        }

        const response = await apiClient.post('/api/documents/upload-chat-document', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        const newContextItem = response.data;
        return newContextItem;
      } catch (error) {
        console.error(`Error al subir el archivo ${file.name}:`, error);
        toast.error(`Error al subir el archivo ${file.name}.`);
        return null;
      }
    });

    const results = await Promise.all(uploadPromises);
    const newContextItems = results.filter(item => item !== null) as SelectedContextItem[];

    if (newContextItems.length > 0) {
      setSelectedContext(prev => [...prev, ...newContextItems]);
      toast.success(`${newContextItems.length} archivo(s) subido(s) y añadido(s) al contexto.`);
    }

    setIsUploadingFile(false);
  }, [workspaceId]);

  // Memoizar las previsualizaciones de imágenes para evitar recrear el array en cada render
  const uploadedImagePreviews = useMemo(() => {
    return uploadedImages.map(img => img.preview);
  }, [uploadedImages]);

  // Callbacks estables para funciones inline
  const handleKeyDown = useCallback(() => { }, []);
  const handleToggleKnowledgeAnalysis = useCallback(() => { }, []);
  const handleToggleWebSearch = useCallback(() => { }, []);
  const handleToggleComprehensiveAnalysis = useCallback(() => { }, []);
  const handleToggleDeepResearch = useCallback(() => { }, []);
  const handlePaste = useCallback(() => { }, []);

  const handleStopResponding = useCallback(async () => {
    if (!currentTaskId) return;
    try {
      await apiClient.post(`/api/tasks/${currentTaskId}/cancel`);
    } catch (error) {
      console.error('Error cancelling task:', error);
    } finally {
      setIsResponding(false);
      setCurrentTaskId(null);
      currentTaskIdRef.current = null;
    }
  }, [currentTaskId]);

  // Callback para remover imagen por índice
  const handleRemoveImageByIndex = useCallback((index: number) => {
    handleRemoveImage(index);
  }, [handleRemoveImage]);

  // Main effect for loading a thread's data
  useEffect(() => {
    const fetchChatData = async () => {
      if (threadId && user) {
        setIsLoading(true);
        setMessages([]);
        try {
          // Cargamos los últimos 100 mensajes por defecto.
          // La API ahora maneja la lógica de paginación de forma más robusta.
          const limit = 60;
          const [messagesRes, threadRes] = await Promise.all([
            apiClient.get(`/api/threads/${threadId}/messages`, { params: { skip: 0, limit: limit } }),
            apiClient.get(`/api/threads/${threadId}`).catch(() => null),
          ]);

          const { messages: newMessages, total } = messagesRes.data;

          setMessages(newMessages);
          setRenderedMessageCount(Math.min(INITIAL_RENDERED_MESSAGES, newMessages.length || INITIAL_RENDERED_MESSAGES));
          if (threadRes?.data?.title) {
            setThreadTitle(threadRes.data.title);
          }
          // Si el total es mayor que el límite, significa que hay más mensajes para cargar.
          setHasMoreMessages(total > limit);
        } catch (error) {
          console.error('Error fetching chat data:', error);
          setMessages([{ text: 'No se pudo cargar esta conversación.', sender: 'ai', created_at: new Date().toISOString() }]);
        } finally {
          setIsLoading(false);
        }
      }
    };
    fetchChatData();
  }, [threadId, user]);

  // Effect for handling the initial message on a new thread
  useEffect(() => {
    const sendInitialMessage = async () => {
      if (initialMessage && !isLoading && messages.length === 0) {
        let parsedRagContext = [];
        if (initialRagContext) {
          try {
            parsedRagContext = JSON.parse(initialRagContext);
          } catch (e) {
            console.error("Error parsing RAG context from URL", e);
          }
        }
        setSelectedContext(parsedRagContext);
        await handleSendMessage(undefined, initialMessage);
      }
    };
    sendInitialMessage();
  }, [initialMessage, initialRagContext, isLoading, messages.length, handleSendMessage]);

  // Effect to scroll to bottom when initial loading finishes
  useEffect(() => {
    if (!isLoading) {
      // Use a small timeout to ensure the DOM has updated with the messages
      setTimeout(() => scrollToBottom('smooth'), 150);
    }
  }, [isLoading, scrollToBottom]);

  // ... (other effects and handlers remain the same) ...

  const { searchTerm } = useSearch();
  const filteredMessages = useMemo(() => {
    if (!searchTerm) return messages;
    const normalizedTerm = searchTerm.toLowerCase();
    return messages.filter(msg => msg.text.toLowerCase().includes(normalizedTerm));
  }, [messages, searchTerm]);

  useEffect(() => {
    if (searchTerm) return;
    setRenderedMessageCount(prev => Math.min(Math.max(prev, INITIAL_RENDERED_MESSAGES), messages.length));
  }, [messages.length, searchTerm]);

  const renderedStartIndex = useMemo(() => {
    if (searchTerm) return 0;
    return Math.max(0, filteredMessages.length - renderedMessageCount);
  }, [filteredMessages.length, renderedMessageCount, searchTerm]);

  const renderedMessages = useMemo(() => {
    if (searchTerm) return filteredMessages;
    return filteredMessages.slice(renderedStartIndex);
  }, [filteredMessages, renderedStartIndex, searchTerm]);

  const chatRenderItems = useMemo<ChatRenderItem[]>(() => {
    const items: ChatRenderItem[] = [];

    let i = 0;
    while (i < renderedMessages.length) {
      const currentMessage = renderedMessages[i];
      const absoluteIndex = renderedStartIndex + i;

      if (currentMessage.sender !== 'user') {
        items.push({
          type: 'single',
          key: `single-${absoluteIndex}-${currentMessage.created_at || 'temp'}`,
          message: currentMessage,
          index: absoluteIndex,
        });
        i += 1;
        continue;
      }

      const baseUserMessage = currentMessage;
      let cursor = i + 1;
      const firstResponseBlock: IndexedResponse[] = [];

      while (cursor < renderedMessages.length && renderedMessages[cursor].sender === 'ai') {
        firstResponseBlock.push({
          message: renderedMessages[cursor],
          index: renderedStartIndex + cursor,
        });
        cursor += 1;
      }

      const mergedResponses: IndexedResponse[] = [...firstResponseBlock];
      let hasMergedRetry = false;

      while (cursor < renderedMessages.length) {
        const candidate = renderedMessages[cursor];
        if (candidate.sender !== 'user' || !areSameRetryPrompt(baseUserMessage, candidate)) {
          break;
        }

        hasMergedRetry = true;
        cursor += 1;

        while (cursor < renderedMessages.length && renderedMessages[cursor].sender === 'ai') {
          mergedResponses.push({
            message: renderedMessages[cursor],
            index: renderedStartIndex + cursor,
          });
          cursor += 1;
        }
      }

      if (hasMergedRetry) {
        const retryKeyBase = normalizeRetryText(baseUserMessage.text).slice(0, 80) || 'retry';
        items.push({
          type: 'retry_group',
          key: `retry-${absoluteIndex}-${retryKeyBase}`,
          userMessage: baseUserMessage,
          userIndex: absoluteIndex,
          responses: mergedResponses,
        });
      } else {
        items.push({
          type: 'single',
          key: `single-${absoluteIndex}-${baseUserMessage.created_at || 'temp'}`,
          message: baseUserMessage,
          index: absoluteIndex,
        });

        mergedResponses.forEach((response) => {
          items.push({
            type: 'single',
            key: `single-${response.index}-${response.message.created_at || 'temp'}`,
            message: response.message,
            index: response.index,
          });
        });
      }

      i = cursor;
    }

    return items;
  }, [renderedMessages, renderedStartIndex]);

  useEffect(() => {
    setActiveRetryResponseMap((prev) => {
      const retryItems = chatRenderItems.filter((item): item is RetryGroupRenderItem => item.type === 'retry_group');
      const validKeys = new Set(retryItems.map((item) => item.key));
      const next: Record<string, number> = {};
      let changed = false;

      retryItems.forEach((item) => {
        const previousIndex = prev[item.key];
        const maxIndex = Math.max(0, item.responses.length - 1);
        const nextIndex = previousIndex === undefined ? maxIndex : Math.min(previousIndex, maxIndex);
        next[item.key] = nextIndex;
        if (previousIndex !== nextIndex) {
          changed = true;
        }
      });

      Object.keys(prev).forEach((key) => {
        if (!validKeys.has(key)) {
          changed = true;
        }
      });

      if (!changed && Object.keys(prev).length === Object.keys(next).length) {
        return prev;
      }

      return next;
    });
  }, [chatRenderItems]);

  const hasMoreRenderedMessages = !searchTerm && renderedStartIndex > 0;

  useEffect(() => {
    const sentinel = topSentinelRef.current;
    const container = scrollAreaRef.current;
    if (!sentinel || !container || searchTerm) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry?.isIntersecting) return;
        if (!hasMoreRenderedMessages) return;

        setRenderedMessageCount(prev => Math.min(prev + RENDER_BATCH_SIZE, filteredMessages.length));
      },
      { root: container, threshold: 0.1 }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [searchTerm, hasMoreRenderedMessages, filteredMessages.length]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p>Cargando conversación...</p>
      </div>
    );
  }

  if (messages.length === 0 && !isResponding) {
        return <EmptyChat
          onSendMessage={handleSendMessage}
          newMessage={newMessage}
          setNewMessage={setNewMessage}
          isResponding={isResponding}
          isRecording={isRecording}
          isProcessingAudio={isProcessingAudio}
          isUploadingFile={isUploadingFile}
          isUploadingImages={isUploadingImages}
          uploadedImagePreviews={uploadedImagePreviews}
          isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
          isWebSearchActive={isWebSearchActive}
          isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
          isDeepResearchActive={isDeepResearchActive}
          onKeyDown={() => { }}
          onToggleKnowledgeAnalysis={() => { }}
          onToggleWebSearch={() => { }}
          onToggleComprehensiveAnalysis={() => { }}
          onToggleDeepResearch={() => { }}
          onStartRecording={handleStartRecording}
          onStopRecording={handleStopRecording}
          onFileUpload={handleFileUpload}
          onImageUpload={handleImageUpload}
          onRemoveImage={() => handleRemoveImage(0)}
          onRemoveContextItem={handleRemoveContextItem}
          onPaste={() => { }}
          workspaceId={workspaceId}
          selectedContext={selectedContext}
          onContextSelected={setSelectedContext}
          isVectorizingFile={isVectorizingFile} // Added isVectorizingFile
          onStopResponding={handleStopResponding}
        />;
  }

  return (
    <div className="flex h-full bg-transparent overflow-hidden">
      <div className="flex flex-col h-full w-full overflow-hidden">
        <div ref={scrollAreaRef} className="flex-1 overflow-y-auto min-h-0 relative">
          {/* Share Button */}
          {threadId && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={() => setIsShareDialogOpen(true)}
              className="absolute top-3 right-3 z-50 p-2.5 rounded-full bg-background/80 backdrop-blur-sm border border-border text-muted-foreground shadow-md hover:text-primary hover:bg-primary/10 hover:shadow-lg transition-all hover:scale-110 flex items-center justify-center"
              aria-label="Compartir conversación"
              title="Compartir conversación"
            >
              <Share2 className="w-4 h-4" />
            </motion.button>
          )}
          <div className="p-1 sm:p-4 md:p-6 space-y-3 sm:space-y-6 w-full md:max-w-6xl mx-auto">
            <div>
              {(hasMoreMessages || hasMoreRenderedMessages) && (
                <div ref={topSentinelRef} className="flex justify-center p-4">
                  {hasMoreRenderedMessages && !isLoadingMore && <p>Mostrando mensajes recientes. Desplaza arriba para cargar más.</p>}
                  {isLoadingMore && <p>Cargando más mensajes...</p>}
                </div>
              )}
              {chatRenderItems.map((item) => {
                if (item.type === 'single') {
                  return (
                    <div key={item.key}>
                      <ChatMessage
                        index={item.index}
                        msg={item.message}
                        handleCopyMessage={handleCopyMessage}
                        handleRetry={handleRetry}
                        handleDeleteMessage={handleDeleteMessage}
                        handlePlayAudio={handlePlayAudio}
                        isAudioLoading={isAudioLoading}
                        playingMessageIndex={playingMessageIndex}
                        isAudioPaused={isAudioPaused}
                        onSourceClick={handleSourceClick as (source: Source) => void}
                        scrollToBottom={scrollToBottom}
                      />
                    </div>
                  );
                }

                const totalResponses = item.responses.length;
                const activeResponseIndex = Math.min(
                  activeRetryResponseMap[item.key] ?? Math.max(0, totalResponses - 1),
                  Math.max(0, totalResponses - 1)
                );
                const activeResponse = totalResponses > 0 ? item.responses[activeResponseIndex] : null;

                return (
                  <div key={item.key}>
                    <ChatMessage
                      index={item.userIndex}
                      msg={item.userMessage}
                      handleCopyMessage={handleCopyMessage}
                      handleRetry={handleRetry}
                      handleDeleteMessage={handleDeleteMessage}
                      handlePlayAudio={handlePlayAudio}
                      isAudioLoading={isAudioLoading}
                      playingMessageIndex={playingMessageIndex}
                      isAudioPaused={isAudioPaused}
                      onSourceClick={handleSourceClick as (source: Source) => void}
                      scrollToBottom={scrollToBottom}
                    />

                    {activeResponse && (
                      <ChatMessage
                        index={activeResponse.index}
                        msg={activeResponse.message}
                        handleCopyMessage={handleCopyMessage}
                        handleRetry={handleRetry}
                        handleDeleteMessage={handleDeleteMessage}
                        handlePlayAudio={handlePlayAudio}
                        isAudioLoading={isAudioLoading}
                        playingMessageIndex={playingMessageIndex}
                        isAudioPaused={isAudioPaused}
                        onSourceClick={handleSourceClick as (source: Source) => void}
                        scrollToBottom={scrollToBottom}
                        responsePosition={{
                          current: activeResponseIndex + 1,
                          total: totalResponses,
                        }}
                        onPrevResponse={() => {
                          setActiveRetryResponseMap((prev) => ({
                            ...prev,
                            [item.key]: Math.max(0, activeResponseIndex - 1),
                          }));
                        }}
                        onNextResponse={() => {
                          setActiveRetryResponseMap((prev) => ({
                            ...prev,
                            [item.key]: Math.min(totalResponses - 1, activeResponseIndex + 1),
                          }));
                        }}
                      />
                    )}
                  </div>
                );
              })}
              {(isResponding || toolName) && (
                <div className="-mt-4">
                  {isDeepResearchActive ? (
                    <DeepResearchVisualizer
                      progress={researchProgress}
                      statusText={researchStatus}
                    />
                  ) : (
                    <LoadingIndicator
                      isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
                      isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
                      isDeepResearchActive={isDeepResearchActive}
                      toolName={toolName}
                      reactState={reactState}
                    />
                  )}
                </div>
              )}
              {backgroundTasks.map((task) => (
                <div key={task.taskId}>
                  <BackgroundTaskIndicator task={task} />
                </div>
              ))}
              <div ref={messagesEndRef} className="h-4 w-full" />
            </div>
          </div>
          
          {/* Scroll to Bottom Button */}
          <AnimatePresence>
            {showScrollBottomButton && (
              <motion.button
                initial={{ opacity: 0, y: 10, scale: 0.8 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.8 }}
                onClick={() => scrollToBottom('smooth', true)}
                className="absolute bottom-4 right-4 z-50 p-3 rounded-full bg-[#3B82F6] text-white shadow-xl hover:bg-blue-600 transition-all hover:scale-110 flex items-center justify-center group"
                aria-label="Ir al final"
              >
                <div className="relative flex items-center justify-center">
                  <ArrowLeft className="w-5 h-5 -rotate-90 stroke-[3px]" />
                  {isResponding && (
                    <span className="absolute -top-1 -right-1 flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                    </span>
                  )}
                </div>
              </motion.button>
            )}
          </AnimatePresence>
        </div>
        <div className="w-full md:max-w-6xl mx-auto px-1 pb-2 sm:px-4 sm:pb-6">
          <div className="relative">
            <ChatInputBar
              newMessage={newMessage}
              isResponding={isResponding}
              isRecording={isRecording}
              isProcessingAudio={isProcessingAudio}
              currentContext={selectedContext}
              isUploadingFile={isUploadingFile}
              isUploadingImages={isUploadingImages}
              uploadedImagePreviews={uploadedImagePreviews}
              isKnowledgeAnalysisActive={selectedContext.length > 0}
              isWebSearchActive={isWebSearchActive}
              isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
              isDeepResearchActive={isDeepResearchActive}
              setNewMessage={setNewMessage}
              onSendMessage={handleSendMessage}
              onStopResponding={handleStopResponding}
              onKeyDown={handleKeyDown}
              onToggleKnowledgeAnalysis={handleToggleKnowledgeAnalysis}
              onToggleWebSearch={handleToggleWebSearch}
              onToggleComprehensiveAnalysis={handleToggleComprehensiveAnalysis}
              onToggleDeepResearch={handleToggleDeepResearch}
              onStartRecording={handleStartRecording}
              onStopRecording={handleStopRecording}
              onFileUpload={handleFileUpload}
              onImageUpload={handleImageUpload}
              onRemoveImage={handleRemoveImageByIndex}
              onRemoveContextItem={handleRemoveContextItem}
              onPaste={handlePaste}
              isFixedPosition={false}
              workspaceId={workspaceId}
              onContextSelected={setSelectedContext}
            />
          </div>
        </div>
      </div>
      {/* Share Dialog */}
      {threadId && (
        <ShareChatDialog
          isOpen={isShareDialogOpen}
          onOpenChange={setIsShareDialogOpen}
          threadId={threadId}
          threadTitle={threadTitle || 'Conversación'}
        />
      )}
      {/* Analysis Detail Dialog */}
      {selectedAnalysis && (
        <AnalysisDetailDialog
          analysis={selectedAnalysis}
          isOpen={!!selectedAnalysis}
          onOpenChange={(open) => !open && setSelectedAnalysis(null)}
        />
      )}
    </div>
  );
}
