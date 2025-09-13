'use client';
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation'; // Mantener esta importación
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
import { PanelRightOpen, PanelRightClose } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';

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
  chunks?: string[]; // Nueva propiedad para los chunks del LLM
  tool_code?: string; // Nueva propiedad para el código de la herramienta
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

// Nuevo componente de indicador de carga con animación de escritura
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
  let text = 'Kognito está pensando'; // Texto base sin puntos
  let Icon = Bot; // Icono por defecto

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
        {/* Cola de la burbuja */}
        <div className="absolute left-[-8px] top-3 h-4 w-4 bg-muted rotate-45 transform origin-bottom-left"></div>
      </div>
    </div>
  );
}

export function CommonChat({ threadId, workspaceId, initialMessage, initialRagContext }: CommonChatProps) {
  const { user, token } = useAuth();
  const router = useRouter(); // Usar useRouter directamente
  const [threadDetails, setThreadDetails] = useState<ThreadDetails | null>(null);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isResponding, setIsResponding] = useState(false);
  const [isThinking, setIsThinking] = useState(false); // Añadida declaración
  const [isRecording, setIsRecording] = useState(false);
  const [isKnowledgeAnalysisActive, setIsKnowledgeAnalysisActive] = useState(false);
  const [isWebSearchActive, setIsWebSearchActive] = useState(false);
  const [isComprehensiveAnalysisActive, setIsComprehensiveAnalysisActive] = useState(false);
  const [isDeepResearchActive, setIsDeepResearchActive] = useState(false); // Nuevo estado para Deep Research
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [backgroundTasks, setBackgroundTasks] = useState<{ taskId: string; type: string }[]>([]);
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [isProcessingAudio, setIsProcessingAudio] = useState(false); // Nuevo estado para el procesamiento de audio
  const [isLoading, setIsLoading] = useState(true);
  const [isContextSelectorOpen, setIsContextSelectorOpen] = useState(false);

  const [selectedContext, setSelectedContext] = useState<SelectedContextItem[]>([]);
  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  const [isAudioPaused, setIsAudioPaused] = useState(false);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const [toolName, setToolName] = useState<string | undefined>(undefined);
  const [reactState, setReactState] = useState<string | undefined>(undefined);
  const wsRef = useRef<WebSocket | null>(null);
  const aiMessageIndexRef = useRef<number | null>(null); // Definición de aiMessageIndexRef

  const scrollToBottom = useCallback((smooth: boolean) => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTo({
          top: scrollElement.scrollHeight,
          behavior: smooth ? 'smooth' : 'auto',
        });
      }
    }
  }, []);

  const handleCopyMessage = useCallback((text: string) => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        toast.success('Respuesta copiada al portapapeles');
      })
      .catch((err) => {
        console.error('Error al copiar el mensaje: ', err);
        toast.error('No se pudo copiar el mensaje.');
      });
  }, []);

  const handleLlmChunk = useCallback((data: { chunk: string; thread_id: string; task_id: string; }) => {
    if (data.thread_id === threadId) {
      setIsThinking(false);
      // If a tool status is being displayed, we need to clear it
      // and ensure we start a new message bubble.
      if (toolName) {
        setToolName(undefined);
        setReactState(undefined);
        aiMessageIndexRef.current = null;
      }

      setMessages((prev) => {
        const newMessages = [...prev];

        let currentMessageIndex = aiMessageIndexRef.current;

        if (currentMessageIndex === null || newMessages[currentMessageIndex]?.sender !== 'ai') {
          newMessages.push({
            text: data.chunk, // Initialize text with the first chunk
            tool_code: undefined, // Ensure tool_code is reset for new message,
            sender: 'ai' as const,
            created_at: new Date().toISOString(),
            sources: [],
            chunks: [data.chunk], // Inicializar chunks con el primer chunk
          });
          aiMessageIndexRef.current = newMessages.length - 1; // Update ref to current message index
        } else if (aiMessageIndexRef.current !== null) {
          const updatedChunks = [...(newMessages[aiMessageIndexRef.current].chunks || []), data.chunk];
          const aiMessageToUpdate = {
            ...newMessages[aiMessageIndexRef.current],
            chunks: updatedChunks, // Añadir al array de chunks
            text: updatedChunks.join(''), // Actualizar el texto con todos los chunks
          };
          newMessages[aiMessageIndexRef.current] = aiMessageToUpdate;
        }
        return newMessages;
      });
      
      requestAnimationFrame(() => {
        scrollToBottom(true);
      });
    }
  }, [threadId, scrollToBottom, toolName, setToolName, setReactState]);

  const handleLlmStart = useCallback((data: { thread_id: string; task_id: string; }) => {
    console.log("CommonChat: handleLlmStart recibido. Data:", data); // Nuevo log
    if (data.thread_id === threadId) {
      setIsResponding(true);
      aiMessageIndexRef.current = null; // Resetear el índice al inicio de una nueva respuesta del LLM
    }
  }, [threadId]);

  const handleLlmEnd = useCallback((data: { thread_id: string; task_id: string; }) => {
    console.log("CommonChat: handleLlmEnd recibido. Data:", data); // Nuevo log
    if (data.thread_id === threadId) {
      setIsResponding(false);
      setIsThinking(false);
      // Consolidar los chunks en el texto final del mensaje de la IA
      setMessages((prev) => {
        const newMessages = [...prev];
        if (aiMessageIndexRef.current !== null && newMessages[aiMessageIndexRef.current]?.sender === 'ai') {
          const aiMessageToUpdate = {
            ...newMessages[aiMessageIndexRef.current],
            text: (newMessages[aiMessageIndexRef.current].chunks || []).join(''), // Unir todos los chunks para el texto final
            chunks: undefined, // Remove chunks after consolidation,
          };
          newMessages[aiMessageIndexRef.current] = aiMessageToUpdate;
        }
        return newMessages;
      });
      aiMessageIndexRef.current = null; // Resetear el índice al finalizar la respuesta del LLM
    }
  }, [threadId]);

  const handleToolStatusUpdate = useCallback((message: ToolStatusMessage) => {
    if (message.thread_id === threadId) {
      if (message.status === 'start') {
        setToolName(message.tool_name);
        setReactState('ejecutando');
        if (message.task_id) { // Asegura que task_id no es undefined
          setBackgroundTasks((prev) => {
            if (!prev.some(task => task.taskId === message.task_id)) {
              return [...prev, { taskId: message.task_id as string, type: message.tool_name }];
            }
            return prev;
          });
        toast.info(`Iniciando ${message.tool_name}...`, {
          description: message.message || "La tarea ha comenzado en segundo plano.",
          duration: 3000, // Show for 3 seconds
        });
        }
      } else if (message.status === 'end' || message.status === 'error') {
        setToolName(undefined);
        setReactState(undefined);
        if (message.task_id) { // Asegura que task_id no es undefined
          setBackgroundTasks((prev) => prev.filter((t) => t.taskId !== (message.task_id as string)));
        }

        let completionMessage: ChatMessageType;
        if (message.status === 'end') {
          completionMessage = {
            text: message.result || "La tarea en segundo plano ha finalizado.",
            sender: 'ai',
            created_at: new Date().toISOString(),
            sources: message.sources || [],
          };
          toast.success(`Herramienta ${message.tool_name} completada.`);
        } else { // status === 'error'
          completionMessage = {
            text: `Error en herramienta ${message.tool_name}: ${message.error || "Error desconocido."}`,
            sender: 'ai',
            created_at: new Date().toISOString(),
          };
          toast.error(`Error en herramienta ${message.tool_name}: ${message.error}`);
        }
        setMessages((prev) => [...prev, completionMessage]);

        
      }
    }
  }, [threadId, setMessages, setBackgroundTasks, setReactState, setToolName]);

  const handleToolCode = useCallback((data: { thread_id: string; task_id: string; tool_code: string; }) => {
    console.log("CommonChat: handleToolCode recibido. Data:", data); // Nuevo log
    if (data.thread_id === threadId) {
      setMessages((prev) => {
        const newMessages = [...prev];
        if (aiMessageIndexRef.current !== null && newMessages[aiMessageIndexRef.current]?.sender === 'ai') {
          const aiMessageToUpdate = {
            ...newMessages[aiMessageIndexRef.current],
            tool_code: data.tool_code, // Añadir el tool_code al mensaje de IA existente
          };
          newMessages[aiMessageIndexRef.current] = aiMessageToUpdate;
        }
        return newMessages;
      });
    }
  }, [threadId]);

  const webSocketOptions = useMemo(() => ({
    onToolStatusUpdate: handleToolStatusUpdate,
    onLlmChunk: handleLlmChunk,
    onLlmStart: handleLlmStart,
    onLlmEnd: handleLlmEnd,
    onToolCode: handleToolCode,
    userId: user?.id,
  }), [handleToolStatusUpdate, handleLlmChunk, handleLlmStart, handleLlmEnd, handleToolCode, user?.id]);

  useWebSocket(webSocketOptions);

  const toggleContextSelector = useCallback(() => {
    setIsContextSelectorOpen((prev) => !prev);
  }, []);

  const handleSendMessage = useCallback(
    async (e?: React.FormEvent, retryMessage?: string) => {
      let imageBase64: string | null = null;
      let documentUrl: string | null = null;
      if (e) e.preventDefault();
      // Procesar imágenes pegadas
      if (files.length > 0) {
        const imageFile = files.find(file => file.type.startsWith('image/'));
        if (imageFile) {
          const reader = new FileReader();
          reader.readAsDataURL(imageFile);
          await new Promise<void>((resolve) => {
            reader.onloadend = () => {
              if (typeof reader.result === 'string') {
                imageBase64 = `data:${imageFile.type};base64,${reader.result.split(',')[1]}`; // Incluir el prefijo y el tipo MIME real
              }
              resolve();
            };
          });
          // Limpiar los archivos después de procesarlos para este mensaje
          setFiles([]);
        }
      }
      const messageText = retryMessage || newMessage;
      if ((!messageText.trim() && selectedContext.length === 0) || isResponding) return;

      if (!user || !user.id) {
        toast.error('Error: Usuario no autenticado o ID de usuario faltante.');
        setIsResponding(false);
        return;
      }

      // Si no hay threadId, es un nuevo chat. Creamos el hilo y redirigimos.
      if (!threadId) {
        setIsResponding(true);
        try {
          const response = await apiClient.post('/api/threads', {});
          const newThread = response.data;
          if (!newThread || !newThread.id) {
            throw new Error('No se pudo crear un nuevo hilo de chat.');
          }
          
          let queryString = `initial_message=${encodeURIComponent(messageText)}`;
          if (selectedContext && selectedContext.length > 0) {
            queryString += `&rag_context=${encodeURIComponent(JSON.stringify(selectedContext))}`;
          }
          // Redirigir a la página del nuevo chat con el mensaje como parámetro
          router.replace(`/chat/${newThread.id}?${queryString}`);

        } catch (error) {
          console.error('Error creando nuevo hilo de chat:', error);
          toast.error('No se pudo iniciar una nueva conversación.');
          setIsResponding(false);
        }
        return;
      }

      // Lógica existente para un chat ya creado
      const userMessage: ChatMessageType = {
        text: messageText,
        sender: 'user' as const,
        created_at: new Date().toISOString(),
        image_base64: '',
        document_url: '',
        ragContext: selectedContext,
      };
      setMessages((prev) => [...prev, userMessage]);

      // Mantener scroll al final inmediatamente después de agregar el mensaje del usuario
      requestAnimationFrame(() => {
        scrollToBottom(true);
      });

      const messageToSend = messageText;
      if (!retryMessage) {
        setNewMessage('');
      }
      // setSelectedContext([]); // Keep context persistent
      setIsResponding(true);

      const currentComprehensiveAnalysisActive = isComprehensiveAnalysisActive;

      try {

        const mode = isKnowledgeAnalysisActive
          ? 'knowledgeAnalysis'
          : isWebSearchActive
          ? 'webSearch'
          : isComprehensiveAnalysisActive
          ? 'comprehensiveAnalysis'
          : isDeepResearchActive // NUEVO: Si el modo Deep Research está activo
          ? 'deepResearch' // NUEVO: Establecer el modo a 'deepResearch'
          : '';

        const formData = new FormData();
        formData.append('thread_id', threadId);
        formData.append('account_id', user.id);
        formData.append('user_message', messageToSend);
        // Procesar imágenes pegadas
        if (files.length > 0) {
          const imageFile = files.find(file => file.type.startsWith('image/'));
          if (imageFile) {
            const reader = new FileReader();
            reader.readAsDataURL(imageFile);
            await new Promise<void>((resolve) => {
              reader.onloadend = () => {
                if (typeof reader.result === 'string') {
                  imageBase64 = `data:${imageFile.type};base64,${reader.result.split(',')[1]}`; // Incluir el prefijo y el tipo MIME real
                }
                resolve();
              };
            });
            // Limpiar los archivos después de procesarlos para este mensaje
            setFiles([]);
          }
        }
        if (imageBase64) formData.append('image_base64', imageBase64);
        if (documentUrl) formData.append('document_url', documentUrl);
        if (mode) formData.append('mode', mode);
        if (selectedContext.length > 0) {
          formData.append('rag_context', JSON.stringify(selectedContext.map((item: SelectedContextItem) => ({ type: item.type, id: item.id }))));
        }

        // Enviar el mensaje al backend. La respuesta del LLM se manejará por WebSocket.
        await apiClient.post('/api/chat', formData);

      } catch (error: any) {
        console.error('Error sending message:', error);
        let errorText = 'Lo siento, ocurrió un error al procesar tu mensaje.';
        const errorMessage = {
          text: errorText,
          sender: 'ai' as const,
          created_at: new Date().toISOString()
        };
        setMessages((prev) => [...prev, errorMessage]);
        setIsResponding(false); // Asegurarse de que el estado de respuesta se desactive en caso de error
      } finally {
        // Los estados de isResponding, isComprehensiveAnalysisActive, isDeepResearchActive
        // se manejan en handleLlmStart y handleLlmEnd, o en caso de error en el catch.
        // Aquí solo nos aseguramos de resetear el modo de análisis si estaba activo.
        if (currentComprehensiveAnalysisActive) {
          setIsComprehensiveAnalysisActive(false);
        }
        setIsDeepResearchActive(false); // Desactivar Deep Research después de enviar
      }
    },
    [
      newMessage,
      files,
      user,
      isResponding,
      isKnowledgeAnalysisActive,
      isWebSearchActive,
      isComprehensiveAnalysisActive,
      isDeepResearchActive, // NUEVO: Añadir al array de dependencias
      threadId,
      selectedContext,
      router,
      scrollToBottom
    ]
  );


  const handleRetry = useCallback((text: string) => {
    handleSendMessage(undefined, text);
  }, [handleSendMessage]);

  const handleCopyArtifactContent = useCallback((content: string) => {
    navigator.clipboard
      .writeText(content)
      .then(() => {
        toast.success('Contenido del artefacto copiado al portapapeles');
      })
      .catch((err) => {
        console.error('Error al copiar el contenido del artefacto: ', err);
        toast.error('No se pudo copiar el contenido del artefacto.');
      });
  }, []);

  const handlePlayAudio = useCallback(
    async (text: string, index: number) => {
      if (playingMessageIndex === index && audioRef.current) {
        if (isAudioPaused) {
          audioRef.current.play();
          setIsAudioPaused(false);
        } else {
          audioRef.current.pause();
          setIsAudioPaused(true);
        }
        return;
      }

      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }

      setIsAudioPaused(false);
      setIsAudioLoading(true);
      setPlayingMessageIndex(index);

      try {
        const response = await apiClient.post('/api/text-to-speech', { text }, {
          responseType: 'blob',
        });
        const audioBlob = new Blob([response.data], { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        audioRef.current = new Audio(audioUrl);
        audioRef.current.play();
        setIsAudioLoading(false);

        audioRef.current.onended = () => {
          setPlayingMessageIndex(null);
          setIsAudioPaused(false);
          URL.revokeObjectURL(audioUrl);
        };
      } catch (error) {
        toast.error('No se pudo generar el audio.');
        console.error('Error en TTS:', error);
        setIsAudioLoading(false);
        setPlayingMessageIndex(null);
        setIsAudioPaused(false);
      }
    },
    [playingMessageIndex, isAudioPaused]
  );

  const handlePaste = useCallback((e: ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (items) {
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
          e.preventDefault();
          const blob = items[i].getAsFile();
          if (blob) {
            const imageFile = new File([blob], 'pasted-image.png', { type: blob.type });
            setFiles((prevFiles) => [...prevFiles, imageFile]);
          }
        }
      }
    }
  }, []);


  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const handleContextSelect = useCallback((selectedItems: SelectedContextItem[]) => {
    setSelectedContext(selectedItems);
  }, []);

  const handleRemoveContextItem = useCallback((itemToRemove: SelectedContextItem) => {
    setSelectedContext((prev) => prev.filter(item => !(item.id === itemToRemove.id && item.type === itemToRemove.type)));
  }, []);

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      e.target.value = ''; // Reset input

      setIsUploadingFile(true);
      const uploadPromises = newFiles.map(file => {
        const formData = new FormData();
        formData.append('file', file);
        if (workspaceId) {
          formData.append('workspace_id', workspaceId);
        }

        return apiClient.post('/api/upload-chat-document', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      });

      try {
        const results = await Promise.all(uploadPromises);
        const newContextItems = results.map(res => res.data);
        
        setSelectedContext(prev => [...prev, ...newContextItems]);
        toast.success(`${newFiles.length} archivo(s) subido(s) y añadido(s) al contexto.`);

      } catch (error) {
        console.error("Error al subir el archivo de chat:", error);
        toast.error('Error al subir uno o más archivos. Inténtalo de nuevo.');
      } finally {
        setIsUploadingFile(false);
      }
    }
  }, [workspaceId]);

  const toggleKnowledgeAnalysis = useCallback(() => {
    setIsKnowledgeAnalysisActive((prev) => !prev);
    setIsWebSearchActive(false);
    setIsComprehensiveAnalysisActive(false);
  }, []);

  const toggleWebSearch = useCallback(() => {
    setIsWebSearchActive((prev) => !prev);
    setIsKnowledgeAnalysisActive(false);
    setIsComprehensiveAnalysisActive(false);
  }, []);

  const toggleComprehensiveAnalysis = useCallback(() => {
    setIsComprehensiveAnalysisActive((prev) => !prev);
    setIsKnowledgeAnalysisActive(false);
    setIsWebSearchActive(false);
    setIsDeepResearchActive(false); // Desactivar Deep Research
  }, []);

  const toggleDeepResearch = useCallback(() => {
    // Toggle the deep research state first
    setIsDeepResearchActive((prev) => {
      const newState = !prev;
      console.log("Deep Research new state:", newState); // DEBUG: Añadido para verificar el estado
      // If deep research is being activated, deactivate others
      if (newState) {
        setIsKnowledgeAnalysisActive(false);
        setIsWebSearchActive(false);
        setIsComprehensiveAnalysisActive(false);
        // Clear message only if it's being activated and there's text
        if (newMessage.trim()) {
          setNewMessage('');
        }
      }
      return newState;
    });
  }, [newMessage]); // newMessage es la única dependencia que cambia fuera de los setters de estado

  const startRecording = useCallback(async () => {
    if (isRecording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        try {
          const response = await apiClient.post('/api/transcribe-audio', formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });
          const transcribedText = response.data.transcription;
          setNewMessage(transcribedText);
          toast.success('Transcripción completada con éxito.');
        } catch (error) {
          console.error('Error transcribing audio:', error);
          toast.error('Error al transcribir el audio. Inténtalo de nuevo.');
        } finally {
          setIsRecording(false);
          setIsProcessingAudio(false); // Detener el spinner de carga
          stream.getTracks().forEach((track) => track.stop());
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      toast.error('Error al acceder al micrófono. Verifica los permisos.');
    }
  }, [isRecording]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  useEffect(() => {
    const fetchChatData = async () => {
      if (threadId && user) {
        setIsLoading(true);
        try {
          console.log('CommonChat: Iniciando fetch de datos del chat para threadId:', threadId);
          const [threadRes, messagesRes] = await Promise.all([
            apiClient.get(`/api/threads/${threadId}`).catch(error => {
              console.error(`CommonChat: Error fetching thread details for ${threadId}:`, error);
              throw error; // Re-throw para que el catch externo lo maneje
            }),
            apiClient.get(`/api/threads/${threadId}/messages`).catch(error => {
              console.error(`CommonChat: Error fetching messages for ${threadId}:`, error);
              throw error; // Re-throw para que el catch externo lo maneje
            }),
          ]);
          console.log('CommonChat: threadDetails response:', threadRes.data);
          console.log('CommonChat: messages response:', messagesRes.data);
          setThreadDetails(threadRes.data);
          
          // Solo procesar initial_message y initial_rag_context si el chat es nuevo (no hay mensajes previos)
          if (messagesRes.data.length === 0 && initialMessage) {
            let parsedRagContext = [];
            if (initialRagContext) {
              try {
                parsedRagContext = JSON.parse(initialRagContext);
              } catch (e) {
                console.error("CommonChat: Error parsing RAG context from URL", e);
              }
            }
            setSelectedContext(parsedRagContext);
            await handleSendMessage(undefined, initialMessage);
            
            // Limpiar los parámetros de la URL para no reenviar el mensaje al recargar
            // Esto se maneja en page.tsx ahora, no es necesario aquí.
          }
          
          // Ordenar mensajes por fecha, los más recientes primero
          const sortedMessages = messagesRes.data.sort((a: ChatMessageType, b: ChatMessageType) => {
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
          });
          setMessages(sortedMessages);

        } catch (error) {
          console.error('Error fetching chat data:', error);
          setMessages([{ text: 'No se pudo cargar esta conversación.', sender: 'ai', created_at: new Date().toISOString() }]);
        } finally {
          setIsLoading(false);
        }
      } else if (user) {
        setIsLoading(false);
      }
    };
    
    fetchChatData();
  }, [threadId, user, initialMessage, initialRagContext]); // Añadir initialMessage y initialRagContext a las dependencias

  const { searchTerm } = useSearch();
  const filteredMessages = searchTerm
    ? messages.filter(msg => msg.text.toLowerCase().includes(searchTerm.toLowerCase()))
    : messages;

  // Efecto para scroll inicial (cuando se cargan los mensajes por primera vez)
  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom(true); // Scroll inmediato para carga inicial
    }
  }, [messages.length > 0, scrollToBottom]);

  // Efecto para mantener el scroll al final cuando se agregan nuevos mensajes
  useEffect(() => {
    if (messages.length > 0) {
      // Usar requestAnimationFrame para asegurar que el DOM se haya actualizado
      requestAnimationFrame(() => {
        scrollToBottom(false); // Scroll suave para nuevos mensajes
      });
    }
  }, [messages.length, scrollToBottom]);

  // Efecto separado para búsqueda
  useEffect(() => {
    if (searchTerm && messages.length > 0) {
      requestAnimationFrame(() => {
        scrollToBottom(true); // Scroll inmediato para búsqueda
      });
    }
  }, [searchTerm, scrollToBottom]);

  useEffect(() => {
    const checkTaskStatus = async () => {
      if (backgroundTasks.length === 0) return;
      for (const task of backgroundTasks) {
        try {
          const response = await apiClient.get(`/api/get-mindmap-result/${task.taskId}`);
          if (response.data.status === 'completed') {
            const result = response.data.result;
            if (result && result.base64_image) {
              const completionMessage = {
                text: 'Mapa mental completado. Haz clic para ver la imagen.',
                sender: 'ai' as const,
                created_at: new Date().toISOString(),
                image_base64: result.base64_image
              };
              setMessages((prev) => [...prev, completionMessage]);
            } else {
              const completionMessage = {
                text: 'Mapa mental completado, pero no se encontró imagen.',
                sender: 'ai' as const,
                created_at: new Date().toISOString()
              };
              setMessages((prev) => [...prev, completionMessage]);
            }
            setBackgroundTasks((prev) => prev.filter((t) => t.taskId !== task.taskId));
            toast.success('Mapa mental completado: La generación del mapa mental ha finalizado.');
          } else if (response.data.status === 'failed') {
            const errorMsg = response.data.error || 'Error desconocido al generar el mapa mental.';
            const errorMessage = { text: `Error al generar el mapa mental: ${errorMsg}`, sender: 'ai' as const, created_at: new Date().toISOString() };
            setMessages((prev) => [...prev, errorMessage]);
            setBackgroundTasks((prev) => prev.filter((t) => t.taskId !== task.taskId));
            toast.error('Error en mapa mental: ' + errorMsg);
          }
        } catch (error) {
          console.error('Error checking task status:', error);
        }
      }
    };

    const intervalId = setInterval(checkTaskStatus, 5000);
    return () => clearInterval(intervalId);
  }, [backgroundTasks]);

  const exampleQuestions = [
    "¿Cuáles son los top 2025 auriculares con cancelación de ruido?",
    "¿Cuáles son los aspectos económicos de la actual escasez mundial de huevos?",
    "¿Cuáles son algunos ETFs con la mayor oportunidad de crecimiento?",
    "¿Cuáles son buenos zapatos duraderos para correr largas distancias?"
  ];

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p>Cargando conversación...</p>
      </div>
    );
  }

  // Si no hay mensajes, muestra la interfaz de bienvenida.
  if (messages.length === 0 && !isResponding) {
      return <EmptyChat 
          onSendMessage={handleSendMessage} 
          newMessage={newMessage} 
          setNewMessage={setNewMessage} 
          isResponding={isResponding}
          isRecording={isRecording}
          isProcessingAudio={isProcessingAudio}
          isUploadingFile={isUploadingFile}
          isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
          isWebSearchActive={isWebSearchActive}
          isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
          isDeepResearchActive={isDeepResearchActive}
          onKeyDown={handleKeyDown}
          onToggleKnowledgeAnalysis={toggleKnowledgeAnalysis}
          onToggleWebSearch={toggleWebSearch}
          onToggleComprehensiveAnalysis={toggleComprehensiveAnalysis}
          onToggleDeepResearch={toggleDeepResearch}
          onStartRecording={startRecording}
          onStopRecording={stopRecording}
          onFileUpload={handleFileUpload}
          onRemoveContextItem={handleRemoveContextItem}
          onPaste={handlePaste}
          workspaceId={workspaceId}
      />;
  }

  return (
    <div className="flex h-full bg-background overflow-x-hidden">
      <div className="flex flex-col h-full w-full">
        <ScrollArea ref={scrollAreaRef} className="flex-1">
          <div className="p-4 md:p-6 space-y-6 w-full md:max-w-4xl mx-auto">
            <div>
              {filteredMessages.slice(-50).map((msg, index) => {
                const messageIndex = filteredMessages.length - 50 + index;
                
                return (
                  <div
                    key={`msg-${messageIndex}-${msg.created_at || 'temp'}`}
                  >
                    <ChatMessage
                      msg={{
                        text: msg.text,
                        sender: msg.sender,
                        image: msg.image_base64 || '',
                        document_url: msg.document_url || '',
                        ragContext: msg.ragContext,
                        sources: msg.sources,
                        chunks: msg.chunks,
                        tool_code: msg.tool_code,
                      }}
                      index={messageIndex}
                      handleCopyMessage={handleCopyMessage}
                      handleRetry={handleRetry}
                      handlePlayAudio={handlePlayAudio}
                      isAudioLoading={isAudioLoading}
                      playingMessageIndex={playingMessageIndex}
                      isAudioPaused={isAudioPaused}
                    />
                  </div>
                );
              })}
              {isThinking && (
                <div>
                  <LoadingIndicator
                    isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
                    isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
                    toolName={toolName ?? undefined}
                    reactState={reactState ?? undefined}
                  />
                </div>
              )}
              {backgroundTasks.map((task) => (
                <div
                  key={task.taskId}
                >
                  <BackgroundTaskIndicator task={task} />
                </div>
              ))}
            </div>
          </div>
        </ScrollArea>
        <div className="w-full md:max-w-4xl mx-auto px-4 pb-4">
          <div className="relative">
            <ChatInputBar
                newMessage={newMessage}
                isResponding={isResponding}
                isRecording={isRecording}
                isProcessingAudio={isProcessingAudio} // Añadir esta línea
                currentContext={selectedContext}
                isUploadingFile={isUploadingFile}
                isKnowledgeAnalysisActive={selectedContext.length > 0}
                isWebSearchActive={isWebSearchActive}
                isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
                isDeepResearchActive={isDeepResearchActive} // Pasar la nueva prop
                onMessageChange={setNewMessage}
                onSendMessage={handleSendMessage}
                onKeyDown={handleKeyDown}
                onToggleKnowledgeAnalysis={() => setIsContextSelectorOpen(!isContextSelectorOpen)} // Abre/cierra el selector de contexto
                onToggleWebSearch={toggleWebSearch}
                onToggleComprehensiveAnalysis={toggleComprehensiveAnalysis}
                onToggleDeepResearch={toggleDeepResearch} // Pasar la nueva prop
                onStartRecording={startRecording}
                onStopRecording={stopRecording}
                onFileUpload={handleFileUpload}
                onRemoveContextItem={handleRemoveContextItem}
                onPaste={handlePaste}
                isFixedPosition={false}
                workspaceId={workspaceId} // ¡NUEVO! Pasamos el workspaceId
            >
              {/* ContextSelectorButton ya no necesita onContextSelected aquí directamente */}
              <ContextSelectorButton
                onContextSelected={handleContextSelect}
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