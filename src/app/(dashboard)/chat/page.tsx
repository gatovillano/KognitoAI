'use client';

import Image from 'next/image';
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import apiClient from '@/lib/api';
import { Send, Search, BookMarked, BrainCircuit, Upload, Mic, MessageSquare } from 'lucide-react';
import { ChatInputBar } from '@/components/ChatInputBar';
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

  const handleChatSubmit = async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }
    if (!chatInput.trim() || isResponding) return;

    setIsResponding(true);
    try {
      const response = await apiClient.post('/api/threads', {});
      const newThread = response.data;
      console.log('New Thread ID:', newThread.id);
      if (!newThread.id) {
        throw new Error('ID del nuevo hilo de chat no encontrado en la respuesta de la API');
      }
      // Send the first message to the new thread
      const mode = isKnowledgeAnalysisActive
        ? 'knowledgeAnalysis'
        : isWebSearchActive
        ? 'webSearch'
        : isComprehensiveAnalysisActive
        ? 'comprehensiveAnalysis'
        : '';
      if (!user) {
        throw new Error('User not authenticated');
      }
      await apiClient.post('/api/chat', {
        thread_id: newThread.id,
        account_id: user.id,
        user_message: chatInput,
        mode: mode,
      });
      setIsInputMoved(true); // Trigger the animation to move input downwards
      router.push(`/chat/${newThread.id}`);
    } catch (error: any) {
      console.error('Error creating new chat thread or sending message:', error);
      let errorMessage = 'Error al iniciar el chat. Inténtalo de nuevo.';
      if (error.response && error.response.status === 422) {
        errorMessage = 'Error de validación al crear el hilo de chat. Por favor, intenta de nuevo o contacta al soporte.';
        console.error('Validation errors:', error.response?.data?.detail || 'No details available');
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
      toast.info('Iniciando subida de archivo(s)...');
      const formData = new FormData();
      for (let i = 0; i < e.target.files.length; i++) {
        formData.append('files', e.target.files[i]);
      }
      console.log('Datos del formulario a enviar:', formData);
      toast.info('Enviando archivo(s) al servidor...');
      const response = await apiClient.post('/api/threads', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      const newThread = response.data;
      console.log('Nuevo hilo creado con subida de archivos:', newThread);
      if (!newThread.id) {
        throw new Error('ID del hilo no encontrado en la respuesta de la API');
      }
      toast.success('Archivo(s) subido(s) con éxito al contexto del chat.');
      router.push(`/chat/${newThread.id}`);
    } catch (error: unknown) {
      console.error('Error uploading file:', error);
      let errorMessage = 'Error desconocido';
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      toast.error(`Error al subir archivo(s): ${errorMessage}. Inténtalo de nuevo.`);
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
          <Image src="/logo-simple.png" alt="Kognito AI Labs" width={120} height={120} className="mb-6" />
          <h1 className="text-5xl font-bold tracking-tight mb-4">
            ¡Hola!
          </h1>
          <p className="text-lg text-muted-foreground">
            ¿Cómo te puedo colaborar hoy?
          </p>
        </div>

        {/* Input usando ChatInputBar */}
        <motion.div 
          className="w-full max-w-4xl"
          animate={{
            y: isInputMoved ? 300 : 0,
          }}
          transition={{ duration: 0.6, ease: 'easeInOut' }}
        >
          <ChatInputBar
            newMessage={chatInput}
            isResponding={isResponding}
            isRecording={isRecording}
            isUploadingFile={isUploadingFile}
            isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
            isWebSearchActive={isWebSearchActive}
            isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
            files={[]}
            onMessageChange={setChatInput}
            onSendMessage={handleChatSubmit}
            onKeyDown={handleKeyDown}
            onToggleKnowledgeAnalysis={toggleKnowledgeAnalysis}
            onToggleWebSearch={toggleWebSearch}
            onToggleComprehensiveAnalysis={toggleComprehensiveAnalysis}
            onStartRecording={startRecording}
            onStopRecording={stopRecording}
            onFileUpload={handleFileUpload}
            onRemoveFile={() => {}}
            onPaste={() => {}}
            isFixedPosition={false}
          />
        </motion.div>

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
