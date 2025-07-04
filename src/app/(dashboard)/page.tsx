 'use client';

import Image from 'next/image';
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import apiClient from '@/lib/api';
import { Send, Search, BookMarked, BrainCircuit, Upload, Mic, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

export default function ChatLandingPage() {
  const { user } = useAuth();
  const [chatInput, setChatInput] = useState('');
  const [isInputMoved, setIsInputMoved] = useState(false);
  const [isResponding, setIsResponding] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isKnowledgeAnalysisActive, setIsKnowledgeAnalysisActive] = useState(false);
  const [isWebSearchActive, setIsWebSearchActive] = useState(false);
  const [isComprehensiveAnalysisActive, setIsComprehensiveAnalysisActive] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const router = useRouter();
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (textAreaRef.current) {
      textAreaRef.current.style.height = 'auto';
      textAreaRef.current.style.height = `${textAreaRef.current.scrollHeight}px`;
    }
  }, [chatInput]);

  const startRecording = async () => {
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
          setChatInput(transcribedText);
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

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isResponding) return;

    setIsResponding(true);
    try {
      // Envía un cuerpo JSON vacío explícitamente
      const response = await apiClient.post('/api/threads', {}); 
      const newThread = response.data;
      // Send the first message to the new thread
      const mode = isKnowledgeAnalysisActive
        ? 'knowledgeAnalysis'
        : isWebSearchActive
        ? 'webSearch'
        : isComprehensiveAnalysisActive
        ? 'comprehensiveAnalysis'
        : '';
      if (!user || !user.id) {
        toast.error("Error: Usuario no autenticado o ID de usuario faltante.");
        setIsResponding(false);
        return;
      }
      if (!newThread.id) {
        toast.error("Error: ID del nuevo hilo de chat faltante.");
        setIsResponding(false);
        return;
      }
      
      // Ensure IDs are treated as strings
      const accountId = String(user.id);
      const threadId = String(newThread.id);

      console.log('New Thread ID:', newThread.id);
      console.log('User ID:', user.id);

      await apiClient.post('/api/chat', {
        thread_id: threadId,
        account_id: accountId,
        user_message: chatInput,
        mode: mode,
      });
      setIsInputMoved(true); // Trigger the animation to move input downwards
      router.push(`/chat/${newThread.id}`);
    } catch (error: any) {
      console.error('Error creating new chat thread or sending message:', error);
      let errorMessage = 'Error al iniciar el chat. Inténtalo de nuevo.';
      if (error.response && error.response.status === 422) {
        errorMessage = 'Error de validación: Asegúrate de que los datos sean correctos. Revisa la consola para más detalles.';
        console.error('Validation errors:', error.response.data.detail);
      }
      toast.error(errorMessage);
    } finally {
      setIsResponding(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSubmit(e as any);
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0 || isUploadingFile) return;
    setIsUploadingFile(true);
    try {
      const response = await apiClient.post('/api/threads');
      const newThread = response.data;
      const formData = new FormData();
      formData.append('thread_id', newThread.id);
      for (let i = 0; i < e.target.files.length; i++) {
        formData.append('files', e.target.files[i]);
      }
      await apiClient.post('/api/upload-chat-file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      toast.success('Archivo(s) subido(s) con éxito al contexto del chat.');
      router.push(`/chat/${newThread.id}`);
    } catch (error) {
      console.error('Error uploading file:', error);
      toast.error('Error al subir archivo(s). Inténtalo de nuevo.');
    } finally {
      setIsUploadingFile(false);
      e.target.value = ''; // Reset file input
    }
  };

  const exampleQuestions = [
    "¿Cuáles son los top 2025 auriculares con cancelación de ruido?",
    "¿Cuáles son los aspectos económicos de la actual escasez mundial de huevos?",
    "¿Cuáles son algunos ETFs con la mayor oportunidad de crecimiento?",
    "¿Cuáles son buenos zapatos duraderos para correr largas distancias?"
  ];

  return (
    <div className="flex flex-col h-full">
      <motion.div
        className="flex flex-col items-center justify-center flex-grow px-4"
        animate={{
          justifyContent: isInputMoved ? 'flex-start' : 'center',
          paddingTop: isInputMoved ? '8vh' : '0',
        }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        {/* Logo y Título */}
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Image src="/logo-simple.png" alt="Kognito AI Labs" width={120} height={120} />
            <h1 className="text-5xl font-bold tracking-tight">
              Kognito
            </h1>
          </div>
          <p className="text-lg text-muted-foreground">
            ¿Qué quieres saber?
          </p>
        </div>

        {/* Input Principal */}
        <form onSubmit={handleChatSubmit} className="w-full max-w-4xl">
          <div className="relative">
            <div className="rounded-3xl bg-card border border-border p-6 shadow-sm">
              <Textarea
                ref={textAreaRef}
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Pregúntame lo que quieras..."
                autoComplete="off"
                disabled={isResponding}
                className="w-full resize-none bg-transparent border-0 focus:ring-0 p-0 text-lg placeholder:text-muted-foreground/70"
                rows={1}
              />
              
              {/* Barra de acciones */}
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/50">
                {/* Botones de modo */}
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant={isKnowledgeAnalysisActive ? "default" : "outline"}
                    size="sm"
                    onClick={toggleKnowledgeAnalysis}
                    className="rounded-full"
                  >
                    <BookMarked className="h-4 w-4 mr-2" />
                    Conocimientos
                  </Button>
                  <Button
                    type="button"
                    variant={isWebSearchActive ? "default" : "outline"}
                    size="sm"
                    onClick={toggleWebSearch}
                    className="rounded-full"
                  >
                    <Search className="h-4 w-4 mr-2" />
                    Web
                  </Button>
                  <Button
                    type="button"
                    variant={isComprehensiveAnalysisActive ? "default" : "outline"}
                    size="sm"
                    onClick={toggleComprehensiveAnalysis}
                    className="rounded-full"
                  >
                    <BrainCircuit className="h-4 w-4 mr-2" />
                    Análisis
                  </Button>
                </div>

                {/* Botones de acción */}
                <div className="flex items-center gap-3">
                  <input
                    type="file"
                    multiple
                    onChange={handleFileUpload}
                    className="hidden"
                    id="file-upload"
                    disabled={isUploadingFile}
                  />
                  <label
                    htmlFor="file-upload"
                    className={`cursor-pointer p-2 rounded-full hover:bg-muted transition-colors ${isUploadingFile ? 'opacity-50' : ''}`}
                  >
                    <Upload className="h-5 w-5 text-muted-foreground" />
                  </label>
                  
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={isRecording ? stopRecording : startRecording}
                    className={`rounded-full ${isRecording ? 'text-red-500 bg-red-50 dark:bg-red-950' : ''}`}
                  >
                    <Mic className="h-5 w-5" />
                  </Button>
                  
                  <Button
                    type="submit"
                    disabled={isResponding || !chatInput.trim()}
                    className="rounded-full px-6"
                  >
                    {isResponding ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-background border-t-transparent" />
                    ) : (
                      <Send className="h-4 w-4 mr-2" />
                    )}
                    {isResponding ? 'Enviando...' : 'Enviar'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </form>

        {/* Preguntas de ejemplo */}
        {!isInputMoved && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="w-full max-w-4xl mt-8"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {exampleQuestions.map((question, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + index * 0.1 }}
                  onClick={() => setChatInput(question)}
                  className="p-4 text-left rounded-2xl bg-card/50 hover:bg-card border border-border/50 hover:border-border transition-all duration-200 group"
                >
                  <p className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                    {question}
                  </p>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
