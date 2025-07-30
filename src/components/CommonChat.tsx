'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useSearch } from '@/contexts/SearchContext';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ArrowLeft, FolderKanban, Bot, BrainCircuit, Search } from 'lucide-react';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInputBar } from '@/components/ChatInputBar';
import { BackgroundTaskIndicator } from '@/components/BackgroundTaskIndicator';
import { ArtifactPanel } from '@/components/ArtifactPanel';
import { useArtifactPanel } from '@/contexts/ArtifactPanelContext';
import { PanelRightOpen, PanelRightClose } from 'lucide-react';

interface ToolStatusMessage {
  type: 'tool_status';
  thread_id: string;
  tool_name: string;
  status: 'start' | 'end' | 'error';
  timestamp: string;
  error?: string;
}

interface ChatMessageType {
  text: string;
  sender: 'user' | 'ai';
  created_at: string;
  image_base64?: string;
  document_url?: string;
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
        <p className="text-sm text-muted-foreground flex items-center">
          {text}
          <span className="inline-block ml-1">.</span>
          <span className="inline-block">.</span>
          <span className="inline-block">.</span>
        </p>
        {/* Cola de la burbuja */}
        <div className="absolute left-[-8px] top-3 h-4 w-4 bg-muted rotate-45 transform origin-bottom-left"></div>
      </div>
    </div>
  );
}

export function CommonChat({ threadId }: CommonChatProps) {
  const { user, token } = useAuth();
  const [threadDetails, setThreadDetails] = useState<ThreadDetails | null>(null);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isResponding, setIsResponding] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isKnowledgeAnalysisActive, setIsKnowledgeAnalysisActive] = useState(false);
  const [isWebSearchActive, setIsWebSearchActive] = useState(false);
  const [isComprehensiveAnalysisActive, setIsComprehensiveAnalysisActive] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [backgroundTasks, setBackgroundTasks] = useState<{ taskId: string; type: string }[]>([]);
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  const [isAudioPaused, setIsAudioPaused] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const { isVisible: isArtifactPanelVisible, toggleVisibility } = useArtifactPanel();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const [toolName, setToolName] = useState<string | undefined>(undefined);
  const [reactState, setReactState] = useState<string | undefined>(undefined);
  const wsRef = useRef<WebSocket | null>(null);

  const handleRemoveFile = (index: number) => {
    setFiles((prevFiles) => prevFiles.filter((_, i) => i !== index));
  };

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

  useEffect(() => {
    if (!user || !token) return;

    const wsUrl = `${process.env.NEXT_PUBLIC_API_URL?.replace('http', 'ws') || 'ws://localhost:8889'}/ws?token=${token}`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
    };

    wsRef.current.onmessage = (event) => {
      try {
        const message: ToolStatusMessage = JSON.parse(event.data);
        if (message.type === 'tool_status' && message.thread_id === threadId) {
          if (message.status === 'start') {
            setToolName(message.tool_name);
            setReactState('ejecutando');
          } else if (message.status === 'end' || message.status === 'error') {
            setToolName(undefined);
            setReactState(undefined);
            if (message.status === 'error') {
              toast.error(`Error en herramienta ${message.tool_name}: ${message.error}`);
            }
          }
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    wsRef.current.onclose = () => {
      console.log('WebSocket disconnected');
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      wsRef.current?.close();
    };
  }, [user, threadId]);

  const handleStreamingResponse = useCallback(
    async (requestData: any, userMessage: ChatMessageType, signal?: AbortSignal) => {
      // Crear mensaje AI inicial vacío
      const initialAiMessage = {
        text: '',
        sender: 'ai' as const,
        created_at: new Date().toISOString(),
        image_base64: '',
        document_url: ''
      };
      
      setMessages((prev) => [...prev, initialAiMessage]);

      try {
        // Usar streaming real con la URL base correcta
        const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8889';
        const response = await fetch(`${baseURL}/api/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
          },
          body: JSON.stringify(requestData),
          signal: signal
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No reader available');
        }

        let fullResponse = '';
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.type === 'chunk') {
                  fullResponse += data.content;

                  // Actualizar mensaje en tiempo real
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const lastMessage = newMessages[newMessages.length - 1];
                    if (lastMessage && lastMessage.sender === 'ai') {
                      lastMessage.text = fullResponse;
                    }
                    return newMessages;
                  });
                } else if (data.type === 'info') {
                  // Opcional: mostrar información de herramientas
                  console.log('Tool info:', data.content);
                  // These are handled by WebSocket now:
                  // if (data.content.toolName) {
                  //   setToolName(data.content.toolName);
                  // }
                  // if (data.content.reactState) {
                  //   setReactState(data.content.reactState);
                  // }
                } else if (data.type === 'done') {
                  // Respuesta completada
                  break;
                } else if (data.type === 'error') {
                  throw new Error(data.message);
                }
              } catch (parseError) {
                console.warn('Error parsing streaming data:', parseError);
              }
            }
          }
        }

        // Verificar si hay ID de tarea en la respuesta final
        if (fullResponse && fullResponse.includes("ID de tarea:")) {
          const taskId = fullResponse.split("ID de tarea:")[1].trim().split(".")[0];
          setBackgroundTasks((prev) => [...prev, { taskId, type: 'mindmap' }]);
        }

        // Historial se actualiza automáticamente vía estado

      } catch (error: any) {
        console.error('Error en la solicitud de chat:', error);
        throw error;
      }
    },
    [threadId, artifacts]
  );

  const handleSendMessage = useCallback(
    async (e?: React.FormEvent, retryMessage?: string) => {
      if (e) e.preventDefault();
      const messageText = retryMessage || newMessage;
      if ((!messageText.trim() && files.length === 0) || isResponding) return;

      if (!user || !user.id) {
        toast.error('Error: Usuario no autenticado o ID de usuario faltante.');
        setIsResponding(false);
        return;
      }
      if (!threadId) {
        toast.error('Error: ID del hilo de chat faltante.');
        setIsResponding(false);
        return;
      }

      const userMessage = {
        text: messageText,
        sender: 'user' as const,
        created_at: new Date().toISOString(),
        image_base64: '',
        document_url: ''
      };
      setMessages((prev) => [...prev, userMessage]);

      // Mantener scroll al final inmediatamente después de agregar el mensaje del usuario
      requestAnimationFrame(() => {
        scrollToBottom(true);
      });

      const messageToSend = messageText;
      const filesToSend = [...files];
      if (!retryMessage) {
        setNewMessage('');
      }
      setFiles([]);
      setIsResponding(true);

      const currentComprehensiveAnalysisActive = isComprehensiveAnalysisActive;

      try {
        let imageBase64: string | null = null;
        let documentUrl: string | null = null;
        if (filesToSend.length > 0) {
          const imageFile = filesToSend.find((file) => file.type.startsWith('image/'));
          if (imageFile) {
            imageBase64 = await new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
              reader.onerror = reject;
              reader.readAsDataURL(imageFile);
            });
            userMessage.image_base64 = `data:image/${imageFile.type.split('/')[1]};base64,${imageBase64}`;
          } else {
            const documentFile = filesToSend[0];
            documentUrl = URL.createObjectURL(documentFile);
            userMessage.document_url = documentUrl;
          }
        }

        const mode = isKnowledgeAnalysisActive
          ? 'knowledgeAnalysis'
          : isWebSearchActive
          ? 'webSearch'
          : isComprehensiveAnalysisActive
          ? 'comprehensiveAnalysis'
          : '';

        // Timeouts aumentados para permitir operaciones largas del LLM
        // Análisis comprehensivo: 15 minutos, análisis normal: 10 minutos
        const timeout = isComprehensiveAnalysisActive ? 900000 : 600000;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        // Usar streaming para respuestas más rápidas
        await handleStreamingResponse({
          thread_id: threadId,
          account_id: user.id,
          user_message: messageToSend,
          image_base64: imageBase64,
          document_url: documentUrl,
          mode: mode,
        }, userMessage, controller.signal);

        clearTimeout(timeoutId);
      } catch (error: any) {
        console.error('Error sending message:', error);
        let errorText = 'Lo siento, ocurrió un error al procesar tu mensaje.';
        if (error && error.name === 'AbortError') {
          const timeoutMinutes = isComprehensiveAnalysisActive ? 15 : 10;
          errorText = `La solicitud ha tardado más de ${timeoutMinutes} minutos en completarse. Esto puede ocurrir con operaciones muy complejas como el análisis de repositorios grandes. Por favor, intenta de nuevo o reduce el alcance de la consulta.`;
        }
        const errorMessage = {
          text: errorText,
          sender: 'ai' as const,
          created_at: new Date().toISOString()
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsResponding(false);
        if (currentComprehensiveAnalysisActive) {
          setIsComprehensiveAnalysisActive(false);
        }
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
      threadId,
      handleStreamingResponse
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

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setFiles((prevFiles) => [...prevFiles, ...newFiles]);
      e.target.value = '';
    }
  }, []);

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
  }, []);

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
    if (threadId && user) {
      const fetchChatData = async () => {
        setIsResponding(true);
        try {
          const [threadRes, messagesRes] = await Promise.all([
            apiClient.get(`/api/threads/${threadId}`),
            apiClient.get(`/api/threads/${threadId}/messages`),
          ]);
          setThreadDetails(threadRes.data);
          setMessages(messagesRes.data);
        } catch (error) {
          console.error('Error fetching chat data:', error);
          setMessages([{ text: 'No se pudo cargar esta conversación.', sender: 'ai', created_at: new Date().toISOString() }]);
        } finally {
          setIsResponding(false);
        }
      };
      fetchChatData();
    }
  }, [threadId, user]);

  const { searchTerm } = useSearch();
  const filteredMessages = searchTerm
    ? messages.filter(msg => msg.text.toLowerCase().includes(searchTerm.toLowerCase()))
    : messages;

  // Función para mantener el scroll al final
  const scrollToBottom = useCallback((immediate = false) => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        if (immediate) {
          // Scroll inmediato sin animación
          scrollElement.scrollTop = scrollElement.scrollHeight;
        } else {
          // Scroll suave
          scrollElement.scrollTo({
            top: scrollElement.scrollHeight,
            behavior: 'smooth',
          });
        }
      }
    }
  }, []);

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

  if (!user && !isResponding) {
    return (
      <div className="flex h-full items-center justify-center">
        <p>Cargando conversación...</p>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-background -m-6">
      <div className="flex flex-col h-full w-full">
        <ScrollArea ref={scrollAreaRef} className="flex-1">
          <div className="p-4 md:p-6 space-y-6 w-full max-w-4xl mx-auto">
            <div>
              {filteredMessages.slice(-50).map((msg, index) => {
                const messageIndex = filteredMessages.length - 50 + index;
                
                return (
                  <div
                    key={`${msg.created_at}-${messageIndex}`}
                  >
                    <ChatMessage
                      msg={{
                        text: msg.text,
                        sender: msg.sender,
                        image: msg.image_base64 || '',
                        document_url: msg.document_url || ''
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
              {isResponding && (
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
        <div className="w-full max-w-4xl mx-auto">
            <ChatInputBar
                newMessage={newMessage}
                isResponding={isResponding}
                isRecording={isRecording}
                isUploadingFile={isUploadingFile}
                isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
                isWebSearchActive={isWebSearchActive}
                isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
                files={files}
                onMessageChange={setNewMessage}
                onSendMessage={handleSendMessage}
                onKeyDown={handleKeyDown}
                onToggleKnowledgeAnalysis={toggleKnowledgeAnalysis}
                onToggleWebSearch={toggleWebSearch}
                onToggleComprehensiveAnalysis={toggleComprehensiveAnalysis}
                onStartRecording={startRecording}
                onStopRecording={stopRecording}
                onFileUpload={handleFileUpload}
                onRemoveFile={handleRemoveFile}
                onPaste={handlePaste}
                isFixedPosition={false}
            />
        </div>
      </div>
      {isArtifactPanelVisible && (
        <div className="w-1/3 h-full hidden lg:block border-l border-border">
          <ArtifactPanel artifacts={artifacts} onCopyContent={handleCopyArtifactContent} isVisible={isArtifactPanelVisible} onToggleVisibility={toggleVisibility} />
        </div>
      )}
    </div>
  );
}
