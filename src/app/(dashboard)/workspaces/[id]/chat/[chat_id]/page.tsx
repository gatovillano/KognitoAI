'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowLeft, FolderKanban } from 'lucide-react';
import apiClient from '@/lib/api';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInputBar } from '@/components/ChatInputBar';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingIndicator } from '@/components/LoadingIndicator';

interface ChatMessageType {
  text: string;
  sender: 'user' | 'ai';
  created_at: string;
}

interface ChatThread {
  id: string;
  title: string;
  workspace_id: string;
  created_at?: string;
}

interface Workspace {
  id: string;
  name: string;
}

export default function WorkspaceChatPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.id as string;
  const chatId = params.chat_id as string;
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [loading, setLoading] = useState(true);
  const [sendingMessage, setSendingMessage] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchWorkspaceAndChatData = async () => {
      try {
        // Obtener información del workspace
        const workspaceResponse = await apiClient.get(`/api/workspaces/${workspaceId}`);
        setWorkspace(workspaceResponse.data);

        // Obtener mensajes del chat
        const messagesResponse = await apiClient.get(`/api/threads/${chatId}/messages`);
        setMessages(messagesResponse.data);
      } catch (error) {
        console.error('Error fetching workspace or chat data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchWorkspaceAndChatData();
  }, [workspaceId, chatId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const [newMessage, setNewMessage] = useState('');

  const { user } = useAuth();

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!newMessage.trim()) return;

    setSendingMessage(true);
    try {
      const userMessage = {
        text: newMessage,
        sender: 'user' as const,
        created_at: new Date().toISOString(),
      };
      setMessages((prevMessages) => [...prevMessages, userMessage]);
      setNewMessage('');

      console.log('Enviando mensaje al backend...');
      console.log('Usuario actual:', user);
      const response = await apiClient.post('/api/chat', {
        thread_id: chatId,
        account_id: user?.id || '',
        user_message: newMessage,
      });
      console.log('Respuesta del backend:', response.data);

      const aiResponse = {
        text: response.data.response_text,
        sender: 'ai' as const,
        created_at: new Date().toISOString(),
      };
      setMessages((prevMessages) => [...prevMessages, aiResponse]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setSendingMessage(false);
    }
  };

  const handleMessageChange = (value: string) => {
    setNewMessage(value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCopyMessage = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handlePlayAudio = (text: string, index: number) => {
    // Implementación para reproducir audio, si es necesario
    console.log(`Reproduciendo audio para el mensaje ${index}`);
  };

  const handleBackToWorkspace = () => {
    router.push(`/workspaces/${workspaceId}`);
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p>Cargando chat del workspace...</p>
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="p-6">
        <p>Workspace no encontrado o no tienes acceso a este workspace.</p>
        <Button onClick={() => router.push('/workspaces')} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver a Workspaces
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <div className="sticky top-0 z-10 bg-background p-4 border-b flex items-center justify-between">
        <div className="flex items-center">
          <FolderKanban className="mr-2 h-6 w-6 text-primary" />
          <h1 className="text-xl font-bold">{workspace.name}</h1>
        </div>
        <Button onClick={handleBackToWorkspace} variant="outline">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver al Workspace
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((message, index) => (
          <ChatMessage
            key={index}
            msg={{ text: message.text, sender: message.sender }}
            index={index}
            handleCopyMessage={handleCopyMessage}
            handlePlayAudio={handlePlayAudio}
            isAudioLoading={false}
            playingMessageIndex={null}
          />
        ))}
        {sendingMessage && (
          <div className="flex justify-center p-4">
            <LoadingIndicator isComprehensiveAnalysisActive={false} isKnowledgeAnalysisActive={false} />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="p-4">
        <ChatInputBar
          newMessage={newMessage}
          isResponding={sendingMessage}
          isRecording={false}
          isUploadingFile={false}
          isKnowledgeAnalysisActive={false}
          isWebSearchActive={false}
          isComprehensiveAnalysisActive={false}
          onMessageChange={handleMessageChange}
          onSendMessage={handleSendMessage}
          onKeyDown={handleKeyDown}
          onToggleKnowledgeAnalysis={() => console.log('Toggle Knowledge Analysis')}
          onToggleWebSearch={() => console.log('Toggle Web Search')}
          onToggleComprehensiveAnalysis={() => console.log('Toggle Comprehensive Analysis')}
          onStartRecording={() => console.log('Start Recording')}
          onStopRecording={() => console.log('Stop Recording')}
          onFileUpload={() => console.log('File Upload')}
          onPaste={() => console.log('Paste')}
        />
      </div>
    </div>
  );
}
