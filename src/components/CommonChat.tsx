'use client';
import { useState, useEffect, useRef, useCallback, useMemo, useLayoutEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { motion } from 'framer-motion';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useSearch } from '@/contexts/SearchContext';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ArrowLeft, FolderKanban, Bot, BrainCircuit, Search, X, Folder, File as FileIcon } from 'lucide-react';
import { ChatMessage } from '@/components/ChatMessage';
import ChatInputBar from '@/components/ChatInputBar';
import { BackgroundTaskIndicator } from '@/components/BackgroundTaskIndicator';
import { EmptyChat } from '@/components/EmptyChat';
import { ContextSelectorButton } from '@/components/ContextSelectorButton';
import { useWebSocketContext } from '@/contexts/WebSocketContext';

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
  id: number;
  title: string;
  url: string;
  snippet: string;
  type: 'web' | 'document' | 'memory' | 'code' | 'database';
  metadata?: Record<string, any>;
}

interface ChatMessageType {
  text: string;
  sender: 'user' | 'ai';
  created_at: string;
  image_base64?: string;
  document_url?: string;
  ragContext?: SelectedContextItem[];
  sources?: Source[];
  chunks?: string[];
  tool_code?: string;
}

interface SelectedContextItem {
  id: string;
  type: 'document' | 'collection';
  name: string;
  title?: string;
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
  toolName,
  reactState,
}: {
  isComprehensiveAnalysisActive?: boolean;
  isKnowledgeAnalysisActive?: boolean;
  toolName?: string;
  reactState?: string;
}) {
  let text = 'Kognito está pensando';
  let Icon = Bot;

  if (isComprehensiveAnalysisActive) {
    text = 'Realizando análisis comprensivo';
    Icon = BrainCircuit;
  } else if (isKnowledgeAnalysisActive) {
    text = 'Consultando la base de conocimiento';
    Icon = Search;
  }

  if (toolName) {
    text = `Usando herramienta: ${toolName}`;
  }

  if (reactState) {
    text += ` - Estado ReAct: ${reactState}`;
  }

  return (
    <div className="flex items-start space-x-4">
      <div className="flex-shrink-0">
        <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="flex-1 bg-muted p-3 rounded-lg max-w-[70%] relative">
        <p className="text-base text-muted-foreground flex items-center">
          {text}
          <span className="animate-pulse delay-0 inline-block ml-1">.</span>
          <span className="animate-pulse delay-150 inline-block">.</span>
          <span className="animate-pulse delay-300 inline-block">.</span>
        </p>
        <div className="absolute left-[-8px] top-3 h-4 w-4 bg-muted rotate-45 transform origin-bottom-left"></div>
      </div>
    </div>
  );
}

export function CommonChat({ threadId, workspaceId, initialMessage, initialRagContext }: CommonChatProps) {
  const { user } = useAuth();
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isResponding, setIsResponding] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isKnowledgeAnalysisActive, setIsKnowledgeAnalysisActive] = useState(false);
  const [isWebSearchActive, setIsWebSearchActive] = useState(false);
  const [isComprehensiveAnalysisActive, setIsComprehensiveAnalysisActive] = useState(false);
  const [isDeepResearchActive, setIsDeepResearchActive] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [uploadedImage, setUploadedImage] = useState<{ preview: string; base64: string } | null>(null);
  const [backgroundTasks, setBackgroundTasks] = useState<{ taskId: string; type: string }[]>([]);
  const [isProcessingAudio, setIsProcessingAudio] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [selectedContext, setSelectedContext] = useState<SelectedContextItem[]>([]);
  const [toolName, setToolName] = useState<string | undefined>(undefined);
  const [reactState, setReactState] = useState<string | undefined>(undefined);
  const [recordingMimeType, setRecordingMimeType] = useState<string>('');
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [audioChunks, setAudioChunks] = useState<Blob[]>([]);
  const audioStreamRef = useRef<MediaStream | null>(null); // Para almacenar el stream del micrófono
  const currentAudioRef = useRef<HTMLAudioElement | null>(null); // Para almacenar la instancia del objeto Audio
  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [isAudioPaused, setIsAudioPaused] = useState(false);

  // Refs to hold latest values for stable callbacks
  const isRespondingRef = useRef(isResponding);
  useEffect(() => { isRespondingRef.current = isResponding; }, [isResponding]);

  const threadIdRef = useRef(threadId);
  useEffect(() => { threadIdRef.current = threadId; }, [threadId]);

  const toolNameRef = useRef(toolName);
  useEffect(() => { toolNameRef.current = toolName; }, [toolName]);

  const newMessageRef = useRef(newMessage);
  useEffect(() => { newMessageRef.current = newMessage; }, [newMessage]);

  // Other refs
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const topSentinelRef = useRef(null);
  const justRestoredScrollRef = useRef(false);
  const prevScrollHeightRef = useRef<number | null>(null);

  const scrollToBottom = useCallback((smooth: boolean) => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({
        top: scrollAreaRef.current.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
      });
    }
  }, []);

  const { registerMessageHandler } = useWebSocketContext();

  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      if (!message) return;

      console.log('[CommonChat] Received message from WebSocket context:', message);
      console.log('[CommonChat] Message type:', message.type);

      const { type, taskId, ...data } = message;

      if (data.thread_id !== threadIdRef.current) {
        console.log('[CommonChat] Thread ID mismatch, ignoring message.');
        return;
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
                  setIsResponding(true);
                  setIsThinking(true);
                  if (taskId && messageIndex === -1) { // Solo añadir si no existe ya
                      updatedMessages.push({
                          text: '',
                          sender: 'ai',
                          created_at: new Date().toISOString(),
                          sources: [],
                          chunks: [],
                          taskId: taskId, // Añadir taskId al mensaje
                      });
                  }
                  break;

              case 'stream_chunk': {
                  setIsThinking(false);
                  if (toolNameRef.current) {
                      setToolName(undefined);
                      setReactState(undefined);
                  }

                  console.log("[CommonChat DEBUG] Received stream_chunk:", data);

                  let chunkMessageIndex = updatedMessages.findIndex(msg => msg.taskId === taskId);
                  console.log(`[CommonChat DEBUG] findIndex for taskId "${taskId}" returned: ${chunkMessageIndex}`);

                  if (chunkMessageIndex === -1 && taskId) {
                      console.log(`[CommonChat DEBUG] Race condition: creating placeholder for taskId "${taskId}"`);
                      updatedMessages.push({
                          text: '',
                          sender: 'ai',
                          created_at: new Date().toISOString(),
                          sources: [],
                          chunks: [],
                          taskId: taskId,
                      });
                      chunkMessageIndex = updatedMessages.length - 1; // Update index
                  }

                  if (taskId && (data.chunk !== undefined || data.content !== undefined) && chunkMessageIndex !== -1) {
                      const textChunk = data.chunk !== undefined ? data.chunk : data.content;
                      console.log(`[CommonChat DEBUG] Appending chunk to message at index ${chunkMessageIndex}: "${textChunk}"`);
                      const existingMessage = updatedMessages[chunkMessageIndex];
                      const newText = existingMessage.text + textChunk;
                      updatedMessages[chunkMessageIndex] = {
                          ...existingMessage,
                          text: newText,
                          chunks: [...(existingMessage.chunks || []), textChunk],
                      };
                  } else {
                      console.error("[CommonChat DEBUG] Dropping chunk. Data:", data, `Index: ${chunkMessageIndex}`);
                  }
                  requestAnimationFrame(() => scrollToBottom(true));
                  break;
              }

              case 'stream_end':
                  console.log(`Stream finalizado. thread_id="${data.thread_id}", task_id="${taskId}"`);
                  setIsResponding(false);
                  setIsThinking(false);
                  if (taskId && messageIndex !== -1) {
                      const finalMessage = updatedMessages[messageIndex];
                      updatedMessages[messageIndex] = {
                          ...finalMessage,
                          chunks: undefined, // Eliminar chunks una vez finalizado
                          taskId: undefined, // Eliminar taskId una vez finalizado
                      };
                  }
                  break;

              case 'tool_start': {
                  const toolStartMessage = data as ToolStatusMessage;
                  setToolName(toolStartMessage.tool_name);
                  setReactState('ejecutando');
                  if (toolStartMessage.task_id && messageIndex === -1) {
                      setBackgroundTasks((prev) => {
                          const currentTaskId = toolStartMessage.task_id as string;
                          return prev.some((task) => task.taskId === currentTaskId) ? prev : [...prev, { taskId: currentTaskId, type: toolStartMessage.tool_name }];
                      });
                      toast.info(`Iniciando ${toolStartMessage.tool_name || 'una herramienta'}...`, {
                          description: toolStartMessage.message || "La tarea ha comenzado en segundo plano.",
                          duration: 3000,
                      });
                      updatedMessages.push({
                          text: `Usando herramienta: ${toolStartMessage.tool_name || 'desconocida'}...`,
                          sender: 'ai',
                          created_at: new Date().toISOString(),
                          sources: [],
                          tool_code: undefined,
                          taskId: toolStartMessage.task_id, // Añadir taskId al mensaje de herramienta
                      });
                  }
                  break;
              }

              case 'tool_end': {
                  const toolEndMessage = data as ToolStatusMessage;
                  setToolName(undefined);
                  setReactState(undefined);
                  if (toolEndMessage.task_id) {
                      setBackgroundTasks((prev) => prev.filter((t) => t.taskId !== toolEndMessage.task_id));
                      const toolMessageIndex = updatedMessages.findIndex(msg => msg.taskId === toolEndMessage.task_id);
                      if (toolMessageIndex !== -1) {
                          const finalToolMessage = updatedMessages[toolMessageIndex];
                          updatedMessages[toolMessageIndex] = {
                              ...finalToolMessage,
                              text: toolEndMessage.status === 'end' ? toolEndMessage.result || `Herramienta ${toolEndMessage.tool_name} finalizada.` : `Error en herramienta ${toolEndMessage.tool_name}: ${toolEndMessage.error || "Error desconocido."}`,
                              sources: toolEndMessage.sources || [],
                              taskId: undefined, // Eliminar taskId una vez finalizado
                          };
                      }
                  }
                  toast[toolEndMessage.status === 'end' ? 'success' : 'error'](`Herramienta ${toolEndMessage.tool_name || 'una herramienta'} ${toolEndMessage.status === 'end' ? 'completada' : 'falló'}.`);
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

              default:
                  console.log('[CommonChat] Unhandled message type:', type);
          }
          return updatedMessages;
      });
    };

    const unregister = registerMessageHandler(handleMessage);
    return unregister; // Cleanup on component unmount

  }, [registerMessageHandler, scrollToBottom, threadIdRef, toolNameRef]);

  const handleSendMessage = useCallback(
    async (e?: React.FormEvent, messageTextFromInput?: string) => {
      if (e) e.preventDefault();
      const messageToProcess = messageTextFromInput || newMessageRef.current;
      if ((!messageToProcess.trim() && selectedContext.length === 0 && !uploadedImage) || isRespondingRef.current) return;

      if (!user?.id) {
        toast.error('Error: Usuario no autenticado.');
        return;
      }

      if (!threadId) {
        setIsResponding(true);
        let newThreadId = '';
        try {
          const threadResponse = await apiClient.post('/api/threads', {});
          newThreadId = threadResponse.data.id;

          const formData = new FormData();
          formData.append('thread_id', newThreadId);
          formData.append('account_id', user.id);
          formData.append('user_message', messageToProcess);
          if (selectedContext.length > 0) {
            formData.append('rag_context', JSON.stringify(selectedContext.map(item => ({ type: item.type, id: item.id }))));
          }
          if (uploadedImage) {
            formData.append('image_base64', uploadedImage.base64);
          }
          await apiClient.post('/api/chat', formData); // CORRECTED ENDPOINT

          const newSearchParams = new URLSearchParams();
          if (selectedContext.length > 0) {
            newSearchParams.set('rag_context', JSON.stringify(selectedContext.map(item => ({ type: item.type, id: item.id }))));
          }
          router.replace(`/chat/${newThreadId}?${newSearchParams.toString()}`);
        } catch (error) {
          console.error('Error creando nuevo hilo de chat o enviando mensaje inicial:', error);
          toast.error('No se pudo iniciar una nueva conversación.');
          setIsResponding(false);
        }
        setNewMessage('');
        if (uploadedImage) {
            URL.revokeObjectURL(uploadedImage.preview);
            setUploadedImage(null);
        }
        return;
      }

      const userMessage: ChatMessageType = {
        text: messageToProcess,
        sender: 'user',
        created_at: new Date().toISOString(),
        ragContext: selectedContext.length > 0 ? selectedContext : undefined,
        image_base64: uploadedImage?.base64,
      };
      setMessages((prev) => [...prev, userMessage]);
      requestAnimationFrame(() => scrollToBottom(true));
      setNewMessage('');
      if (uploadedImage) {
        URL.revokeObjectURL(uploadedImage.preview);
        setUploadedImage(null);
      }
      setIsResponding(true);

      try {
        const formData = new FormData();
        formData.append('thread_id', threadId);
        formData.append('account_id', user.id);
        formData.append('user_message', messageToProcess);
        if (selectedContext.length > 0) {
          formData.append('rag_context', JSON.stringify(selectedContext.map(item => ({ type: item.type, id: item.id }))));
        }
        if (uploadedImage) {
            formData.append('image_base64', uploadedImage.base64);
        }
        const response = await apiClient.post('/api/chat', formData); // CORRECTED ENDPOINT
        const responseTaskId = response.data?.taskId; // Captura el taskId de la respuesta

        if (responseTaskId) {
          // Opcional: inicializar un mensaje de streaming si el backend no envía stream_start inmediatamente
          // Ya no es necesario inicializar aquí, se maneja en stream_start dentro del useEffect de latestMessage
        }

      } catch (error: any) {
        console.error('Error sending message:', error);
        setMessages((prev) => [...prev, { text: 'Lo siento, ocurrió un error.', sender: 'ai', created_at: new Date().toISOString() }]);
        setIsResponding(false);
      }
    },
    [user, threadId, selectedContext, router, scrollToBottom, setNewMessage, uploadedImage]
  );

  const handleImageUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingImage(true);
    toast.info(`Cargando imagen: ${file.name}`);

    try {
        const reader = new FileReader();
        reader.onloadend = () => {
            const base64String = reader.result as string;
            setUploadedImage({
                preview: URL.createObjectURL(file),
                base64: base64String,
            });
            setIsUploadingImage(false);
            toast.success(`Imagen '${file.name}' lista para enviar.`);
        };
        reader.onerror = () => {
            toast.error("Error al leer el archivo de imagen.");
            setIsUploadingImage(false);
        };
        reader.readAsDataURL(file);
    } catch (error) {
        toast.error("Error al procesar la imagen.");
        setIsUploadingImage(false);
    }
  }, []);

  const handleRemoveImage = useCallback(() => {
      if (uploadedImage) {
          URL.revokeObjectURL(uploadedImage.preview);
          setUploadedImage(null);
      }
  }, [uploadedImage]);

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
      
      setRecordingMimeType(supportedMimeType); // Guardar el mime type en el estado
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
  }, [setRecordingMimeType, setMediaRecorder, setIsRecording, setIsProcessingAudio, setNewMessage]); // Se añaden las dependencias para evitar closures viciados

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
    if (isRespondingRef.current) return;

    try {
      setIsResponding(true);

      const formData = new FormData();
      formData.append('thread_id', threadId);
      formData.append('account_id', user?.id || '');
      formData.append('user_message', text);
      if (selectedContext.length > 0) {
        formData.append('rag_context', JSON.stringify(selectedContext.map(item => ({ type: item.type, id: item.id }))));
      }

      await apiClient.post('/api/chat', formData);
    } catch (error: any) {
      console.error('Error retrying message:', error);
      toast.error('Error al reenviar el mensaje');
      setIsResponding(false);
    }
  }, [threadId, user?.id, selectedContext]);

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
      const response = await apiClient.post('/api/text-to-speech', { text }, {
        responseType: 'blob', // Importante para recibir el audio como Blob
      });

      const audioBlob = new Blob([response.data], { type: 'audio/mpeg' }); // Asumiendo que el TTS devuelve MP3
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      currentAudioRef.current = audio; // Guardar la referencia al objeto Audio

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
      toast.error('Error al generar el audio. Asegúrate de que el servicio TTS esté funcionando en el puerto 5050.');
      setPlayingMessageIndex(null);
      setIsAudioLoading(false);
      setIsAudioPaused(false);
      if (currentAudioRef.current) {
        URL.revokeObjectURL(currentAudioRef.current.src);
        currentAudioRef.current = null;
      }
    }
  }, [isAudioLoading, playingMessageIndex, isAudioPaused]);

  const handleRemoveContextItem = useCallback((itemToRemove: SelectedContextItem) => {
    setSelectedContext(prev => prev.filter(item => item.id !== itemToRemove.id));
    toast.info(`"${itemToRemove.name}" eliminado del contexto.`);
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

  // Main effect for loading a thread's data
  useEffect(() => {
    const fetchChatData = async () => {
      if (threadId && user) {
        setIsLoading(true);
        setMessages([]);
        try {
          // Primero, obtenemos el total de mensajes para calcular la paginación correcta.
          const initialRes = await apiClient.get(`/api/threads/${threadId}/messages`, { params: { limit: 1 } });
          const total = initialRes.data.total;
          const limit = 100;
          const skip = Math.max(0, total - limit);

          // Ahora, traemos la última página de mensajes.
          const messagesRes = await apiClient.get(`/api/threads/${threadId}/messages`, { params: { skip, limit } });
          
          const { messages: newMessages } = messagesRes.data;

          setMessages(newMessages);
          setHasMoreMessages(skip > 0);
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

  // ... (other effects and handlers remain the same) ...

  const { searchTerm } = useSearch();
  const filteredMessages = searchTerm
    ? messages.filter(msg => msg.text.toLowerCase().includes(searchTerm.toLowerCase()))
    : messages;

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
          isUploadingImage={isUploadingImage}
          uploadedImagePreview={uploadedImage?.preview}
          isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
          isWebSearchActive={isWebSearchActive}
          isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
          isDeepResearchActive={isDeepResearchActive}
          onKeyDown={() => {}}
          onToggleKnowledgeAnalysis={() => {}}
          onToggleWebSearch={() => {}}
          onToggleComprehensiveAnalysis={() => {}}
          onToggleDeepResearch={() => {}}
          onStartRecording={handleStartRecording}
          onStopRecording={handleStopRecording}
          onFileUpload={handleFileUpload}
          onImageUpload={handleImageUpload}
          onRemoveImage={handleRemoveImage}
          onRemoveContextItem={handleRemoveContextItem}
          onPaste={() => {}}
          workspaceId={workspaceId}
          selectedContext={selectedContext}
          onContextSelected={setSelectedContext}
      />;
  }

  return (
    <div className="flex h-screen bg-background overflow-x-hidden">
      <div className="flex flex-col h-full w-full">
        <div ref={scrollAreaRef} className="flex-1 overflow-y-auto">
          <div className="p-4 md:p-6 space-y-6 w-full md:max-w-6xl mx-auto">
            <div>
              {hasMoreMessages && (
                <div ref={topSentinelRef} className="flex justify-center p-4">
                  {isLoadingMore && <p>Cargando más mensajes...</p>}
                </div>
              )}
              {filteredMessages.map((msg, index) => (
                <div key={`msg-${index}-${msg.created_at || 'temp'}`}>
                  <ChatMessage
                    msg={{
                      text: msg.text,
                      sender: msg.sender,
                      image_base64: msg.image_base64 || '',
                      document_url: msg.document_url || '',
                      ragContext: msg.ragContext,
                      sources: msg.sources,
                      chunks: msg.chunks,
                      tool_code: msg.tool_code,
                    }}
                    index={index}
                    handleCopyMessage={handleCopyMessage}
                    handleRetry={handleRetry}
                    handlePlayAudio={handlePlayAudio}
                    isAudioLoading={isAudioLoading}
                    playingMessageIndex={playingMessageIndex}
                    isAudioPaused={isAudioPaused}
                  />
                </div>
              ))}
              {isThinking && ( // Mostrar si está pensando, ya que los mensajes en streaming ahora están en `messages`
                <div>
                  <LoadingIndicator
                    isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
                    isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
                    toolName={toolName}
                    reactState={reactState}
                  />
                </div>
              )}
              {backgroundTasks.map((task) => (
                <div key={task.taskId}>
                  <BackgroundTaskIndicator task={task} />
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="w-full md:max-w-6xl mx-auto px-4 pb-4">
          <div className="relative">
            <ChatInputBar
                newMessage={newMessage}
                isResponding={isResponding}
                isRecording={isRecording}
                isProcessingAudio={isProcessingAudio}
                currentContext={selectedContext}
                isUploadingFile={isUploadingFile}
                isUploadingImage={isUploadingImage}
                uploadedImagePreview={uploadedImage?.preview}
                isKnowledgeAnalysisActive={selectedContext.length > 0}
                isWebSearchActive={isWebSearchActive}
                isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
                isDeepResearchActive={isDeepResearchActive}
                onMessageChange={setNewMessage}
                setNewMessage={setNewMessage}
                onSendMessage={handleSendMessage}
                onKeyDown={() => {}}
                onToggleKnowledgeAnalysis={() => {}}
                onToggleWebSearch={() => {}}
                onToggleComprehensiveAnalysis={() => {}}
                onToggleDeepResearch={() => {}}
                onStartRecording={handleStartRecording}
                onStopRecording={handleStopRecording}
                onFileUpload={handleFileUpload}
                onImageUpload={handleImageUpload}
                onRemoveImage={handleRemoveImage}
                onRemoveContextItem={handleRemoveContextItem}
                onPaste={() => {}}
                isFixedPosition={false}
                workspaceId={workspaceId}
            >
              <ContextSelectorButton
                onContextSelected={setSelectedContext}
                currentContext={selectedContext}
                workspaceId={workspaceId}
              />
            </ChatInputBar>
          </div>
        </div>
      </div>
    </div>
  );
}

// Modificar la definición de ChatMessageType para incluir taskId
interface ChatMessageType {
  text: string;
  sender: 'user' | 'ai';
  created_at: string;
  image_base64?: string;
  document_url?: string;
  ragContext?: SelectedContextItem[];
  sources?: Source[];
  chunks?: string[];
  tool_code?: string;
  taskId?: string; // Añadir taskId
}