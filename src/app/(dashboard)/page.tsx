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

  return (
    <div className="flex flex-col h-full">
      <motion.div
        className="flex flex-col items-center justify-center flex-grow"
        animate={{
          justifyContent: isInputMoved ? 'flex-start' : 'center',
          paddingTop: isInputMoved ? '10vh' : '0',
        }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        <Image src="/logo-simple.png" alt="Kognito AI Labs" width={300} height={300} className="mt-8" />
        <h1 className="text-4xl font-bold -mt-16 tracking-tight flex items-center z-10">
            👋 ¡Hola! Soy KAI
        </h1>
        <form onSubmit={handleChatSubmit} className="mt-6 w-full max-w-3xl relative">
          <div className="rounded-2xl bg-card p-4 shadow-lg">
            <Textarea
              ref={textAreaRef}
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
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
                <div
                  onClick={isRecording ? stopRecording : startRecording}
                  className={`cursor-pointer flex items-center text-sm ${isRecording ? 'text-red-500' : 'text-muted-foreground'}`}
                >
                  <Mic className="h-4 w-4" />
                </div>
                <div
                  onClick={handleChatSubmit}
                  className={`cursor-pointer flex items-center text-sm ${isResponding || !chatInput.trim() ? 'text-gray-400' : 'text-gray-600 hover:text-primary'}`}
                >
                  <Send className="h-4 w-4" />
                </div>
              </div>
            </div>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
