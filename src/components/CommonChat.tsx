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
import { SelectedContextItem } from '@/types/context';

const INITIAL_RENDERED_MESSAGES = 40;
const RENDER_BATCH_SIZE = 30;

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
    "Descifrando intencionalidad",
    "Explorando red semántica",
    "Sintetizando vectores de conocimiento",
    "Formulando respuesta lógica",
    "Verificando consistencia cognitiva",
    "Mapeando conexiones neuronales",
    "Procesando patrones contextuales",
    "Optimizando árbol de inferencia",
    "Analizando grafo de conocimiento",
    "Recuperando memorias asociativas",
  ], []);

  useEffect(() => {
    const thoughtTimer = setInterval(() => {
      setThoughtIndex((prev) => (prev + 1) % thoughts.length);
    }, 3000);
    return () => {
      clearInterval(thoughtTimer);
    };
  }, [thoughts.length]);

  const palette = useMemo(() => {
    // Usando el color primario real de la app: hsl(200, 100%, 50%) ≈ #00aaff
    if (isDeepResearchActive)          return { c1: '#00aaff', c2: '#0077cc', label: 'Investigación Profunda' };
    if (isComprehensiveAnalysisActive) return { c1: '#00ccff', c2: '#00aaff', label: 'Análisis Comprensivo' };
    if (isKnowledgeAnalysisActive)     return { c1: '#0088dd', c2: '#005faa', label: 'Consultando Conocimiento' };
    if (toolName)                      return { c1: '#33bbff', c2: '#0099ee', label: `Ejecutando: ${toolName}` };
    return                                    { c1: '#00aaff', c2: '#0088cc', label: 'Kognito está pensando' };
  }, [isDeepResearchActive, isComprehensiveAnalysisActive, isKnowledgeAnalysisActive, toolName]);

  return (
    <div className="flex flex-col items-center py-5 w-full select-none">

      {/* --- Diffuse Plasma Orb --- */}
      <motion.div
        className="relative flex-shrink-0"
        style={{ width: 44, height: 44 }}
        animate={{ y: [0, -2.5, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      >
        {/* Far outer atmospheric bleed */}
        <motion.div
          className="absolute rounded-full"
          style={{
            inset: '-60%',
            background: `radial-gradient(circle, ${palette.c1}18 0%, transparent 70%)`,
            filter: 'blur(12px)',
          }}
          animate={{ scale: [1, 1.15, 1], opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        />

        {/* Secondary color cloud — offset, slower */}
        <motion.div
          className="absolute rounded-full"
          style={{
            inset: '-40%',
            background: `radial-gradient(circle at 60% 40%, ${palette.c2}22 0%, transparent 65%)`,
            filter: 'blur(10px)',
          }}
          animate={{ scale: [1.1, 0.9, 1.1], opacity: [0.5, 0.9, 0.5] }}
          transition={{ duration: 3.8, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
        />

        {/* Core plasma body — rotating energy blob */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            background: `conic-gradient(from 0deg, ${palette.c1}cc, ${palette.c2}99, ${palette.c1}55, ${palette.c2}bb, ${palette.c1}cc)`,
            filter: 'blur(8px)',
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
        />

        {/* Inner hot core — brightest point */}
        <motion.div
          className="absolute rounded-full"
          style={{
            inset: '20%',
            background: `radial-gradient(circle, ${palette.c2}ff 0%, ${palette.c1}88 50%, transparent 100%)`,
            filter: 'blur(5px)',
          }}
          animate={{ scale: [0.85, 1.2, 0.85], opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        />

        {/* Chromatic fringe */}
        <motion.div
          className="absolute rounded-full"
          style={{
            inset: '-8%',
            background: `radial-gradient(circle at 42% 42%, ${palette.c1}33 0%, transparent 60%)`,
            filter: 'blur(6px)',
          }}
          animate={{ rotate: [-15, 15, -15], scale: [1, 1.08, 1] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        />
      </motion.div>

      {/* --- Text below orb, centered --- */}
      <div className="flex flex-col items-center mt-3 gap-1">

        {/* Primary label */}
        <div className="flex items-center gap-1.5">
          <AnimatePresence mode="wait">
            <motion.span
              key={palette.label}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.25 }}
              className="text-[13px] font-medium tracking-tight"
              style={{ color: palette.c1 }}
            >
              {palette.label}
            </motion.span>
          </AnimatePresence>

          {reactState && (
            <span className="text-[8px] font-mono tracking-widest text-neutral-400 dark:text-neutral-500 uppercase px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 border border-neutral-200/30 dark:border-neutral-700/30">
              {reactState}
            </span>
          )}
        </div>

        {/* Rotating thought subtitle */}
        <div className="h-[14px] relative overflow-hidden flex items-center">
          <AnimatePresence mode="wait">
            <motion.p
              key={thoughtIndex}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 0.45, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="text-[10px] font-mono tracking-wider uppercase text-neutral-600 dark:text-neutral-400"
            >
              {thoughts[thoughtIndex]}
            </motion.p>
          </AnimatePresence>
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
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const [threadTitle, setThreadTitle] = useState<string>('');
  const [renderedMessageCount, setRenderedMessageCount] = useState(INITIAL_RENDERED_MESSAGES);
  const [activeRetryResponseMap, setActiveRetryResponseMap] = useState<Record<string, number>>({});
  const [researchCompletedEvent, setResearchCompletedEvent] = useState(false);

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
  const currentTaskIdRef = useRef<string | null>(null);
  useEffect(() => { currentTaskIdRef.current = currentTaskId; }, [currentTaskId]);

  const handleScroll = useCallback(() => {
    const container = scrollAreaRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    // Un umbral de 100px para determinar si estamos en el fondo
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;

    setShowScrollBottomButton(!isAtBottom);
  }, []);

  useEffect(() => {
    const container = scrollAreaRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  const scrollToBottom = useCallback((behavior: 'smooth' | 'auto' = 'auto') => {
    const container = scrollAreaRef.current;
    if (!container) return;

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
  }, []);

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
          
          if (taskId && taskId === currentTaskIdRef.current) {
            setCurrentTaskId(null);
          }
          break;
        case 'tool_start': {
          const toolStartMessage = data as ToolStatusMessage;
          if (toolStartMessage.tool_name === 'deep_research') {
            setIsDeepResearchActive(true);
            if (threadIdRef.current) {
              localStorage.setItem('deep_research_active_' + threadIdRef.current, 'true');
            }
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
          const isBackgroundCompletion = (data as any).background_completion === true;

          // Si es deep_research pero NO es la finalización del hilo de fondo (es decir, es el retorno síncrono inicial), lo ignoramos.
          if (toolEndMessage.tool_name === 'deep_research' && !isBackgroundCompletion) {
            setToolName(undefined);
            setReactState(undefined);
            setIsThinking(false);
            break;
          }

          if (toolEndMessage.tool_name === 'deep_research') {
            setIsDeepResearchActive(false);
            if (threadIdRef.current) {
              localStorage.removeItem('deep_research_active_' + threadIdRef.current);
            }
          }
          setToolName(undefined);
          setReactState(undefined);
          setIsThinking(false);
          
          if (toolEndMessage.task_id) {
            setBackgroundTasks((prev) => prev.filter((t) => t.taskId !== toolEndMessage.task_id));
          }
          
          if (toolEndMessage.tool_name !== 'deep_research') {
            toast[type === 'tool_end' ? 'success' : 'error'](`Herramienta ${toolEndMessage.tool_name || 'una herramienta'} ${type === 'tool_end' ? 'completada' : 'falló'}.`);
          } else {
            if (type === 'tool_end') {
              toast.success("Investigación profunda completada de forma exitosa.", { duration: 5000 });
              setResearchCompletedEvent(true);
            } else {
              toast.error("La investigación profunda falló o fue cancelada.");
            }
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
        case 'error': {
          setIsResponding(false);
          setIsThinking(false);
          setToolName(undefined);
          setReactState(undefined);
          
          if (taskId && taskId === currentTaskIdRef.current) {
            setCurrentTaskId(null);
          }
          const errMsg = (data as any).message || (data as any).detail || (data as any).error || "Error al procesar la solicitud.";
          toast.error(`Error: ${errMsg}`, { duration: 6000 });
          break;
        }
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

            let chunkMessageIndex = updatedMessages.findIndex(msg => msg.taskId === taskId);
            if (chunkMessageIndex !== -1) {
              const existingMessage = updatedMessages[chunkMessageIndex];
              let newParts = [...(existingMessage.content_parts || [])];
              if (!hasPendingToolCall(newParts, toolStartMessage.tool_name, toolContent)) {
                newParts.push({
                  type: 'tool_call',
                  content: toolContent,
                  tool_name: toolStartMessage.tool_name,
                  status: 'start',
                  pty_session: (toolStartMessage as any).pty_session
                } as any);
                updatedMessages[chunkMessageIndex] = { ...existingMessage, content_parts: newParts };
              } else {
                const lastPartIndex = findLatestToolCallIndex(newParts, toolStartMessage.tool_name);
                if (lastPartIndex !== -1 && (toolStartMessage as any).pty_session) {
                  newParts[lastPartIndex] = {
                    ...newParts[lastPartIndex],
                    pty_session: (toolStartMessage as any).pty_session,
                  } as any;
                  updatedMessages[chunkMessageIndex] = { ...existingMessage, content_parts: newParts };
                }
              }

              // Adjuntar metadata de pty_session si la herramienta la provee (p. ej. terminal_executor)
              if ((toolStartMessage as any).pty_session) {
                updatedMessages[chunkMessageIndex] = {
                  ...updatedMessages[chunkMessageIndex],
                  pty_session: (toolStartMessage as any).pty_session,
                } as any;
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

          case 'error': {
            const errMsg = (data as any).message || (data as any).detail || (data as any).error || "Error al procesar la solicitud.";
            let errorMsgIndex = updatedMessages.findIndex(msg => msg.taskId === taskId);
            if (errorMsgIndex === -1 && taskId) {
              errorMsgIndex = updatedMessages.length - 1;
            }
            if (errorMsgIndex !== -1) {
              const existingMessage = updatedMessages[errorMsgIndex];
              let newParts = [...(existingMessage.content_parts || [])];
              newParts.push({ type: 'text', content: `\n\n> ⚠️ **Error en el procesamiento:** ${errMsg}` });
              updatedMessages[errorMsgIndex] = {
                ...existingMessage,
                text: existingMessage.text ? `${existingMessage.text}\n\n⚠️ **Error:** ${errMsg}` : `⚠️ **Error:** ${errMsg}`,
                chunks: undefined,
                taskId: undefined,
                content_parts: newParts,
              };
            } else {
              updatedMessages.push({
                text: `⚠️ **Error:** ${errMsg}`,
                sender: 'ai',
                created_at: new Date().toISOString(),
                model_name: settings?.llm_model,
                sources: [],
                chunks: undefined,
                content_parts: [{ type: 'text', content: `⚠️ **Error:** ${errMsg}` }],
              });
            }
            break;
          }
        }
        return updatedMessages;
      });
    };

    const unregister = registerMessageHandler(handleMessage);
    return unregister; // Cleanup on component unmount

  }, [registerMessageHandler, settings?.llm_model]);

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
          console.error('Error creating chat thread:', error);
          toast.error('Error al crear la conversación');
          return;
        }
      }

      if (isResponding) {
        return;
      }

      if (!threadId) {
        console.error("No threadId available to send message");
        toast.error("Error: No hay una conversación activa.");
        return;
      }

      // Reiniciar estado de investigación cuando el usuario envía un nuevo mensaje explícito
      setIsDeepResearchActive(false);
      if (threadIdRef.current) {
        localStorage.removeItem('deep_research_active_' + threadIdRef.current);
      }

      if (uploadedImages.length === 0) {
        setIsResponding(true);
        setIsThinking(true);
      } else {
        setIsResponding(true);
      }

      if (selectedContext.length > 0) {
        setIsKnowledgeAnalysisActive(true);
      }

      if (messageToProcess.startsWith('/research ') || messageToProcess.startsWith('/investigar ')) {
        setIsDeepResearchActive(true);
        if (threadIdRef.current) {
          localStorage.setItem('deep_research_active_' + threadIdRef.current, 'true');
        }
        setResearchProgress(5);
        setResearchStatus('Iniciando investigación profunda...');
      }

      if (messageToProcess.startsWith('/analyze ') || messageToProcess.startsWith('/analizar ')) {
        setIsComprehensiveAnalysisActive(true);
      }

      if (messageToProcess.startsWith('/web ') || messageToProcess.startsWith('/buscar ')) {
        setIsWebSearchActive(true);
      }

      const userMessage: ChatMessageType = {
        text: messageToProcess,
        sender: 'user',
        created_at: new Date().toISOString(),
        ragContext: selectedContext.length > 0 ? selectedContext : undefined,
        images_base64: uploadedImages.map(img => img.base64),
      };
      setMessages((prev) => [...prev, userMessage]);
      setNewMessage('');
      if (uploadedImages.length > 0) {
        uploadedImages.forEach(img => URL.revokeObjectURL(img.preview));
        setUploadedImages([]);
      }

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
<<<<<<< Updated upstream
    [user, threadId, selectedContext, router, uploadedImages, serializeSelectedContext, workspaceId]
=======
    [user, threadId, selectedContext, router, uploadedImages, scheduleStreamScroll, serializeSelectedContext, workspaceId]
>>>>>>> Stashed changes
  );

  const handleImageUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement> | { target: { files: FileList | File[] | null } }) => {
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
        stream.getTracks().forEach(track => track.stop());
        audioStreamRef.current = null;
        return;
      }

      console.log(`DEBUG: Usando el tipo de MIME soportado: ${supportedMimeType}`);
      const recorder = new MediaRecorder(stream, { mimeType: supportedMimeType });
      let localAudioChunks: Blob[] = [];
      const finalizeRecording = async () => {
        const mimeType = recorder.mimeType || supportedMimeType;
        const totalBytes = localAudioChunks.reduce((sum, chunk) => sum + chunk.size, 0);
        console.log(`DEBUG: Finalizando grabación. Chunks: ${localAudioChunks.length}, tamaño total: ${totalBytes} bytes, mime: ${mimeType}`);

        setIsRecording(false);
        setIsProcessingAudio(true);
        toast.info('Deteniendo grabación de audio y procesando...');

        if (totalBytes <= 110) {
          toast.error('La grabación quedó incompleta. Mantén presionado un poco más e intenta de nuevo.');
          setIsProcessingAudio(false);
          audioStreamRef.current?.getTracks().forEach(track => track.stop());
          audioStreamRef.current = null;
          return;
        }

        const audioBlob = new Blob(localAudioChunks, { type: mimeType });
        if (audioBlob.size === 0) {
          toast.error('El audio grabado está vacío. Intenta de nuevo.');
          setIsProcessingAudio(false);
          audioStreamRef.current?.getTracks().forEach(track => track.stop());
          audioStreamRef.current = null;
          return;
        }

        const fileExtension = mimeType.split('/')[1]?.split(';')[0] || 'webm';
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
          audioStreamRef.current?.getTracks().forEach(track => track.stop());
          audioStreamRef.current = null;
        }
      };

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          console.log('DEBUG: ondataavailable event fired. Data size:', event.data.size, 'bytes');
          localAudioChunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        console.log('DEBUG: MediaRecorder onstop event fired.');
        await new Promise(resolve => window.setTimeout(resolve, 0));
        if (localAudioChunks.length > 0) {
          await finalizeRecording();
        } else {
          toast.error('No se grabó audio.');
          setIsProcessingAudio(false);
          audioStreamRef.current?.getTracks().forEach(track => track.stop());
          audioStreamRef.current = null;
        }
      };

      recorder.start(500);
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
      mediaRecorder.requestData();
      mediaRecorder.stop();
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
  }, [workspaceId, threadId]);

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


  // Effect to automatically send a message when deep research completes
  useEffect(() => {
    if (researchCompletedEvent) {
      setResearchCompletedEvent(false);
      handleSendMessage(undefined, "*(Sistema)*: La investigación profunda ha concluido en segundo plano. Por favor, notifícame un breve resumen de los hallazgos principales.");
    }
  }, [researchCompletedEvent, handleSendMessage]);

  // Effect to load persistent deep research state across reloads
  useEffect(() => {
    if (threadId) {
      const isPersistent = localStorage.getItem('deep_research_active_' + threadId) === 'true';
      if (isPersistent) {
        setIsDeepResearchActive(true);
      } else {
        setIsDeepResearchActive(false);
      }
    }
  }, [threadId]);

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
              {(isResponding || toolName || isDeepResearchActive) && (
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
                onClick={() => scrollToBottom('smooth')}
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
