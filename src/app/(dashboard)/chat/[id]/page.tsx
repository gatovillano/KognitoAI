// En: src/app/(dashboard)/chat/[id]/page.tsx

'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api';
import { motion } from 'framer-motion';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { toast } from 'sonner';

import { ArrowUp, User, Copy, Play, Loader2, Square, Search, BookMarked, BrainCircuit, Upload, Mic } from 'lucide-react';

interface Message {
  text: string;
  sender: 'user' | 'ai';
}

interface ThreadDetails {
    id: string;
    title: string;
}

export default function ChatPage() {
  const params = useParams();
  const threadId = params.id as string;
  const { user } = useAuth();

  const [threadDetails, setThreadDetails] = useState<ThreadDetails | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isResponding, setIsResponding] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isKnowledgeAnalysisActive, setIsKnowledgeAnalysisActive] = useState(false);
  const [isWebSearchActive, setIsWebSearchActive] = useState(false);
  const [isComprehensiveAnalysisActive, setIsComprehensiveAnalysisActive] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  
  // --- NUEVOS ESTADOS PARA EL AUDIO ---
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (threadId && user) {
      const fetchChatData = async () => {
        setIsResponding(true);
        try {
          const [threadRes, messagesRes] = await Promise.all([
            apiClient.get(`/api/threads/${threadId}`),
            apiClient.get(`/api/threads/${threadId}/messages`)
          ]);
          setThreadDetails(threadRes.data);
          setMessages(messagesRes.data);
        } catch (error) {
          console.error('Error fetching chat data:', error);
          setMessages([{ text: 'No se pudo cargar esta conversación.', sender: 'ai' }]);
        } finally {
          setIsResponding(false);
        }
      };
      fetchChatData();
    }
  }, [threadId, user]);

  // Real-time title update with animation
  const [animatedTitle, setAnimatedTitle] = useState(threadDetails?.title || 'Nuevo Chat');
  useEffect(() => {
    if (threadDetails && threadDetails.title !== animatedTitle) {
      let newTitle = threadDetails.title;
      let currentTitle = animatedTitle;
      let newChars = '';
      let i = 0;
      const animate = setInterval(() => {
        if (i < newTitle.length) {
          newChars += newTitle[i];
          setAnimatedTitle(newChars);
          i++;
        } else {
          clearInterval(animate);
        }
      }, 100); // Adjust speed of animation here
      return () => clearInterval(animate);
    }
  }, [threadDetails, animatedTitle]);

  // Update title based on messages
  useEffect(() => {
    if (messages.length > 0 && threadDetails && threadDetails.title === 'Nuevo Chat') {
      const lastMessage = messages[messages.length - 1].text;
      if (lastMessage.length > 10) {
        const newTitle = lastMessage.substring(0, 10) + '...';
        setThreadDetails({ ...threadDetails, title: newTitle });
      }
    }
  }, [messages, threadDetails]);
  
  useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector('div[data-radix-scroll-area-viewport]');
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [messages, isResponding]);

  useEffect(() => {
    if (textAreaRef.current) {
      textAreaRef.current.style.height = 'auto';
      textAreaRef.current.style.height = `${textAreaRef.current.scrollHeight}px`;
    }
  }, [newMessage]);

  const startRecording = async () => {
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
          stream.getTracks().forEach(track => track.stop());
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      toast.error('Error al acceder al micrófono. Verifica los permisos.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (items) {
        for (let i = 0; i < items.length; i++) {
          if (items[i].type.indexOf('image') !== -1) {
            e.preventDefault();
            const blob = items[i].getAsFile();
            if (blob) {
              const formData = new FormData();
              formData.append('thread_id', threadId);
              formData.append('files', blob, 'pasted-image.png');
              uploadPastedImage(formData);
            }
          }
        }
      }
    };

    const textArea = textAreaRef.current;
    if (textArea) {
      textArea.addEventListener('paste', handlePaste);
    }
    return () => {
      if (textArea) {
        textArea.removeEventListener('paste', handlePaste);
      }
    };
  }, [threadId]);

  const uploadPastedImage = async (formData: FormData) => {
    if (isUploadingFile) return;
    setIsUploadingFile(true);
    try {
      await apiClient.post('/api/upload-chat-file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      toast.success('Imagen pegada subida con éxito al contexto del chat.');
      const uploadMessage: Message = { text: 'Imagen pegada subida al contexto del chat.', sender: 'user' };
      setMessages((prev) => [...prev, uploadMessage]);
    } catch (error) {
      console.error('Error uploading pasted image:', error);
      toast.error('Error al subir imagen pegada. Inténtalo de nuevo.');
    } finally {
      setIsUploadingFile(false);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!newMessage.trim() || !user || isResponding) return;
    const userMessage: Message = { text: newMessage, sender: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    const messageToSend = newMessage;
    setNewMessage('');
    setIsResponding(true);
    // Guardar el estado actual de los modos para mantener el indicador visual correcto
    const currentComprehensiveAnalysisActive = isComprehensiveAnalysisActive;
    try {
      const mode = isKnowledgeAnalysisActive
        ? 'knowledgeAnalysis'
        : isWebSearchActive
        ? 'webSearch'
        : isComprehensiveAnalysisActive
        ? 'comprehensiveAnalysis'
        : '';
      // Configurar un timeout extendido para tareas largas como análisis comprensivo
      const timeout = isComprehensiveAnalysisActive ? 240000 : 60000; // 4 minutos para análisis comprensivo, 1 minuto para otros
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      
      const response = await apiClient.post('/api/chat', {
        thread_id: threadId,
        account_id: user.id,
        user_message: messageToSend,
        mode: mode,
      }, { signal: controller.signal });
      
      clearTimeout(timeoutId);
      const aiMessage: Message = { text: response.data.response_text, sender: 'ai' };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error: any) {
      console.error('Error sending message:', error);
      let errorText = 'Lo siento, ocurrió un error al procesar tu mensaje.';
      if (error && error.name === 'AbortError') {
        errorText = 'La solicitud ha tardado demasiado en completarse. Por favor, intenta de nuevo o reduce el alcance de la consulta.';
      }
      const errorMessage: Message = { text: errorText, sender: 'ai' };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsResponding(false);
      // No restaurar el estado del modo de análisis comprensivo automáticamente, mantenerlo para la próxima interacción si es necesario
      if (currentComprehensiveAnalysisActive) {
        setIsComprehensiveAnalysisActive(false);
      }
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0 || isUploadingFile) return;
    setIsUploadingFile(true);
    const formData = new FormData();
    formData.append('thread_id', threadId);
    for (let i = 0; i < e.target.files.length; i++) {
      formData.append('files', e.target.files[i]);
    }
    try {
      await apiClient.post('/api/upload-chat-file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      toast.success('Archivo(s) subido(s) con éxito al contexto del chat.');
      // Optionally, add a message to the chat indicating a file was uploaded
      const uploadMessage: Message = { text: 'Archivo(s) subido(s) al contexto del chat.', sender: 'user' };
      setMessages((prev) => [...prev, uploadMessage]);
    } catch (error) {
      console.error('Error uploading file:', error);
      toast.error('Error al subir archivo(s). Inténtalo de nuevo.');
    } finally {
      setIsUploadingFile(false);
      e.target.value = ''; // Reset file input
    }
  };

  const toggleKnowledgeAnalysis = () => {
    setIsKnowledgeAnalysisActive(!isKnowledgeAnalysisActive);
    if (isWebSearchActive) setIsWebSearchActive(false);
    if (isComprehensiveAnalysisActive) setIsComprehensiveAnalysisActive(false);
  };

  const toggleWebSearch = () => {
    setIsWebSearchActive(!isWebSearchActive);
    if (isKnowledgeAnalysisActive) setIsKnowledgeAnalysisActive(false);
    if (isComprehensiveAnalysisActive) setIsComprehensiveAnalysisActive(false);
  };

  const toggleComprehensiveAnalysis = () => {
    setIsComprehensiveAnalysisActive(!isComprehensiveAnalysisActive);
    if (isKnowledgeAnalysisActive) setIsKnowledgeAnalysisActive(false);
    if (isWebSearchActive) setIsWebSearchActive(false);
  };

  const handleCopyMessage = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success('Respuesta copiada al portapapeles');
    }).catch(err => {
      console.error('Error al copiar el mensaje: ', err);
      toast.error('No se pudo copiar el mensaje.');
    });
  };

  // --- NUEVA FUNCIÓN PARA REPRODUCIR AUDIO ---
  const handlePlayAudio = async (text: string, index: number) => {
    // Si ya hay un audio reproduciéndose, lo detenemos
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlayingMessageIndex(null);
    }
    
    // Si se hace clic en el mismo botón de "reproduciendo", actúa como un botón de stop
    if (playingMessageIndex === index) {
      return;
    }

    setIsAudioLoading(true);
    setPlayingMessageIndex(index); // Marcamos este mensaje como "cargando/reproduciendo"

    try {
      const response = await apiClient.post('/api/text-to-speech', { text }, {
        responseType: 'blob' // ¡MUY IMPORTANTE para recibir audio!
      });
      
      const audioBlob = new Blob([response.data], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(audioBlob);
      
      audioRef.current = new Audio(audioUrl);
      audioRef.current.play();
      setIsAudioLoading(false);

      audioRef.current.onended = () => {
        setPlayingMessageIndex(null); // Limpiamos el estado cuando termina
        URL.revokeObjectURL(audioUrl); // Liberamos memoria
      };

    } catch (error) {
      toast.error("No se pudo generar el audio.");
      console.error("Error en TTS:", error);
      setIsAudioLoading(false);
      setPlayingMessageIndex(null);
    }
  };

  if (!user && !isResponding) {
    return <div className="flex h-full items-center justify-center"><p>Cargando conversación...</p></div>;
  }
  
  return (
    <div className="flex flex-col h-full">
      <div className="flex-grow overflow-y-hidden">
        <ScrollArea className="h-full" ref={scrollAreaRef}>
          <div className="p-4 md:p-6 space-y-6">
            {messages.map((msg, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
              >
                {/* --- CAMBIO DE FLUJO: RENDERIZADO CONDICIONAL --- */}
                
                {/* VISTA PARA EL MENSAJE DEL USUARIO */}
                {msg.sender === 'user' && (
                  <div className="flex flex-col items-center">
                    <div className="w-full max-w-4xl mx-auto">
                      <div className="flex items-start gap-4 justify-end">
                        <div className="rounded-lg p-3 bg-secondary text-secondary-foreground max-w-[70%]">
                          <div className="text-base whitespace-pre-wrap">
                            <MarkdownRenderer content={msg.text} />
                          </div>
                        </div>
                        <Avatar className="h-8 w-8">
                          <AvatarFallback><User className="h-5 w-5"/></AvatarFallback>
                        </Avatar>
                      </div>
                    </div>
                  </div>
                )}

                {/* VISTA PARA EL MENSAJE DE LA IA */}
                {msg.sender === 'ai' && (
                  <div className="flex flex-col items-center">
                    <div className="w-full max-w-4xl mx-auto">
                      <div className="flex items-start gap-4">
                        <Avatar className="h-12 w-12 border">
                          <AvatarImage src="/logo-simple.png" alt="Kognito" />
                          <AvatarFallback>K</AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <div className="font-bold">Kognito</div>
                          <div className="break-words mt-1 text-base">
                            <MarkdownRenderer content={msg.text} />
                          </div>
                          {/* Barra de acciones para la IA */}
                          <div className="mt-2 flex items-center gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleCopyMessage(msg.text)}>
                              <Copy className="h-4 w-4 mr-2 text-gray-600" /> Copiar
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handlePlayAudio(msg.text, index)} disabled={isAudioLoading && playingMessageIndex === index}>
                              {isAudioLoading && playingMessageIndex === index && <Loader2 className="h-4 w-4 mr-2 animate-spin text-gray-600" />}
                              {playingMessageIndex === index && !isAudioLoading && <Square className="h-4 w-4 mr-2 text-gray-600" />}
                              {playingMessageIndex !== index && <Play className="h-4 w-4 mr-2 text-gray-600" />}
                              Escuchar
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
            {isResponding && 
              <>
                {(isComprehensiveAnalysisActive || isKnowledgeAnalysisActive) ? (
                  <div className="flex justify-center w-full py-4">
                    <div className="flex flex-col items-center">
                      <motion.div
                        className="h-12 w-12 border-4 border-t-primary border-b-primary border-l-transparent border-r-transparent rounded-full"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      />
                      <span className="mt-2 text-sm text-muted-foreground">
                        {isComprehensiveAnalysisActive ? "Buscando y analizando..." : "Analizando conocimientos..."}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-center w-full">
                    <div className="w-full max-w-3xl mx-auto">
                      <div className="flex items-start gap-4">
                        <Avatar className="h-8 w-8 border">
                          <AvatarImage src="/logo-simple.png" alt="Kognito" />
                          <AvatarFallback>K</AvatarFallback>
                        </Avatar>
                        <div className="rounded-lg p-3 bg-secondary flex justify-center items-center">
                          <motion.div
                            className="flex space-x-1"
                            animate={{
                              opacity: [1, 0.5, 1],
                            }}
                            transition={{
                              duration: 1.5,
                              repeat: Infinity,
                              ease: "easeInOut",
                            }}
                          >
                            <motion.div
                              className="h-2 w-6 bg-gray-600 rounded-full"
                              style={{ borderRadius: '10px' }}
                            />
                            <motion.div
                              className="h-2 w-6 bg-gray-600 rounded-full"
                              style={{ borderRadius: '10px' }}
                              animate={{ y: [0, -2, 0] }}
                              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
                            />
                            <motion.div
                              className="h-2 w-6 bg-gray-600 rounded-full"
                              style={{ borderRadius: '10px' }}
                              animate={{ y: [0, -2, 0] }}
                              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut", delay: 0.6 }}
                            />
                          </motion.div>
                          <span className="ml-2 text-sm text-muted-foreground">
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            }
          </div>
        </ScrollArea>
      </div>

      <footer className="p-4 w-full flex justify-center shrink-0 bg-transparent">
        <form onSubmit={handleSendMessage} className="relative w-full max-w-3xl">
          <div className="rounded-2xl bg-card p-4 shadow-lg">
            <Textarea
              ref={textAreaRef}
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="¿Cómo puedo ayudarte hoy?"
              autoComplete="off"
              disabled={isResponding}
              className="w-full resize-none bg-transparent border-0 focus:ring-0 p-0 text-base"
              rows={1}
            />
            <div className="mt-3 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div 
                  onClick={toggleKnowledgeAnalysis}
                  className={`cursor-pointer flex items-center gap-1.5 text-sm ${isKnowledgeAnalysisActive ? 'text-primary' : 'text-muted-foreground'}`}
                >
                  <BookMarked className="h-4 w-4" />
                  Análisis de Conocimientos
                </div>
                <div 
                  onClick={toggleWebSearch}
                  className={`cursor-pointer flex items-center gap-1.5 text-sm ${isWebSearchActive ? 'text-primary' : 'text-muted-foreground'}`}
                >
                  <Search className="h-4 w-4" />
                  Búsqueda Web
                </div>
                <div
                  onClick={toggleComprehensiveAnalysis}
                  className={`cursor-pointer flex items-center gap-1.5 text-sm ${isComprehensiveAnalysisActive ? 'text-primary' : 'text-muted-foreground'}`}
                >
                  <BrainCircuit className="h-4 w-4" />
                  Busqueda y Analisis
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="cursor-pointer flex items-center text-sm text-muted-foreground">
                  <Upload className="h-4 w-4" />
                  <label htmlFor="file-upload" className="cursor-pointer sr-only">Subir Archivo</label>
                  <input
                    id="file-upload"
                    type="file"
                    multiple
                    accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.gif"
                    className="hidden"
                    onChange={handleFileUpload}
                    disabled={isUploadingFile}
                  />
                </div>
                <div
                  onClick={isRecording ? stopRecording : startRecording}
                  className={`cursor-pointer flex items-center text-sm ${isRecording ? 'text-red-500' : 'text-muted-foreground'}`}
                >
                  <Mic className="h-4 w-4" />
                </div>
                <Button 
                  type="submit" 
                  size="icon" 
                  variant="ghost"
                  disabled={isResponding || !newMessage.trim()}
                >
                  <ArrowUp className="h-5 w-5" />
                </Button>
              </div>
            </div>
          </div>
        </form>
      </footer>
    </div>
  );
}
