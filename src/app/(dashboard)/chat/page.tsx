'use client';

import { useState, useCallback, useEffect } from 'react'; // Importar useEffect
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { useWorkspace } from '@/contexts/WorkspaceContext';
import { EmptyChat } from '@/components/EmptyChat';
import dynamic from 'next/dynamic'; // Importar dynamic

const WelcomeDialog = dynamic(() => import('@/components/WelcomeDialog').then(mod => mod.WelcomeDialog), { ssr: false });

interface SelectedContextItem {
  id: string;
  type: 'document' | 'collection';
  name: string;
  title?: string;
}

export default function NewChatPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { currentWorkspace } = useWorkspace();
  const workspaceId = currentWorkspace?.id;
  const [newMessage, setNewMessage] = useState('');
  const [isResponding, setIsResponding] = useState(false);
  const [selectedContext, setSelectedContext] = useState<SelectedContextItem[]>([]);
  const [isWelcomeDialogOpen, setIsWelcomeDialogOpen] = useState(false); // Nuevo estado para el diálogo de bienvenida

  // Efecto para mostrar el diálogo de bienvenida solo una vez
  useEffect(() => {
    const hasVisitedChat = localStorage.getItem('hasVisitedChat');
    if (!hasVisitedChat) {
      setIsWelcomeDialogOpen(true);
      localStorage.setItem('hasVisitedChat', 'true');
    }
  }, []);

  const handleSendMessage = useCallback(async (e?: React.FormEvent, messageTextFromInput?: string) => {
    if (e) e.preventDefault();
    const messageToProcess = messageTextFromInput || newMessage;
    if (!messageToProcess.trim() && selectedContext.length === 0) return;

    if (!user?.id) {
      toast.error('Error: Usuario no autenticado.');
      return;
    }

    setIsResponding(true);
    try {
      const threadResponse = await apiClient.post('/api/threads', {});
      const newThreadId = threadResponse.data.id;

      const initialMessage = messageToProcess;
      const initialRagContext = selectedContext.length > 0 ? JSON.stringify(selectedContext) : '';

      const newSearchParams = new URLSearchParams();
      if (initialMessage) {
        newSearchParams.set('initialMessage', initialMessage);
      }
      if (initialRagContext) {
        newSearchParams.set('initialRagContext', initialRagContext);
      }

      router.replace(`/chat/${newThreadId}?${newSearchParams.toString()}`);
    } catch (error) {
      console.error('Error creando nuevo hilo de chat:', error);
      toast.error('No se pudo iniciar una nueva conversación.');
      setIsResponding(false);
    }
  }, [user, newMessage, selectedContext, router]);

  return (
    <>
      <EmptyChat
        onSendMessage={handleSendMessage}
        newMessage={newMessage}
        setNewMessage={setNewMessage}
        isResponding={isResponding}
        isRecording={false}
        isProcessingAudio={false}
        isUploadingFile={false}
        isKnowledgeAnalysisActive={false}
        isWebSearchActive={false}
        isComprehensiveAnalysisActive={false}
        isDeepResearchActive={false}
        onKeyDown={() => {}}
        onToggleKnowledgeAnalysis={() => {}}
        onToggleWebSearch={() => {}}
        onToggleComprehensiveAnalysis={() => {}}
        onToggleDeepResearch={() => {}}
        onStartRecording={() => {}}
        onStopRecording={() => {}}
        onFileUpload={() => {}}
        onRemoveContextItem={() => {}}
        onPaste={() => {}}
        isUploadingImages={false}
        uploadedImagePreviews={[]}
        onRemoveImage={() => {}}
        onImageUpload={() => {}}
        selectedContext={selectedContext}
        onContextSelected={setSelectedContext}
        isVectorizingFile={false}
        workspaceId={workspaceId}
      />
      <WelcomeDialog isOpen={isWelcomeDialogOpen} onOpenChange={setIsWelcomeDialogOpen} />
    </>
  );
}
