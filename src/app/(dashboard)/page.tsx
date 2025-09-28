 'use client';

import Image from 'next/image';
import { useState, useRef, useEffect, ClipboardEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import apiClient from '@/lib/api';
import { Send, Search, BookMarked, BrainCircuit, Upload, Mic, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { EmptyChat } from '@/components/EmptyChat';

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
  const [isProcessingAudio, setIsProcessingAudio] = useState(false);
  const [isDeepResearchActive, setIsDeepResearchActive] = useState(false);
  const [workspaceId, setWorkspaceId] = useState<string | undefined>(undefined);
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
    e?.preventDefault();
    if (!chatInput.trim() || isResponding) return;

    setIsResponding(true);
    try {
      // Envía un cuerpo JSON vacío explícitamente
      let newThread;
      if (chatInput.trim()) { // Solo crea un hilo si hay un mensaje
        const response = await apiClient.post('/api/threads', {}); 
        newThread = response.data;
      } else {
        // Si no hay mensaje, no se crea un hilo y se sale de la función
        setIsResponding(false);
        return;
      }
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

  const onToggleDeepResearch = () => {
    setIsDeepResearchActive(!isDeepResearchActive);
  };

  const onRemoveContextItem = (item: any) => {
    console.log('Removing context item:', item);
    // Implement actual removal logic if needed
  };

  const onPaste = (e: any) => { // Changed to 'any' to resolve type incompatibility with ClipboardEvent
    console.log('Paste event:', e);
    // Implement actual paste logic if needed
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0 || isUploadingFile) return;
    setIsUploadingFile(true);
    try {
      const response = await apiClient.post('/api/threads'); // Crea el hilo solo si hay archivos
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
    <EmptyChat
      onSendMessage={handleChatSubmit}
      newMessage={chatInput}
      setNewMessage={setChatInput}
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
      onToggleDeepResearch={onToggleDeepResearch}
      onStartRecording={startRecording}
      onStopRecording={stopRecording}
      onFileUpload={handleFileUpload}
      onRemoveContextItem={onRemoveContextItem}
      onPaste={onPaste}
      workspaceId={workspaceId}
    />
  );
}
