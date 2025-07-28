'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Bot } from 'lucide-react';
import apiClient from '@/lib/api';
import { CommonChat } from '@/components/CommonChat';

interface Workspace {
  id: string;
  name: string;
}

export default function WorkspaceChatPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = (params?.id as string) || '';
  const chatId = (params?.chat_id as string) || '';
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWorkspaceData = async () => {
      try {
        const workspaceResponse = await apiClient.get(`/api/workspaces/${workspaceId}`);
        setWorkspace(workspaceResponse.data);
      } catch (error) {
        console.error('Error fetching workspace data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchWorkspaceData();
  }, [workspaceId]);

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
      <div className="flex-4 overflow-auto" style={{ height: '100vh' }}>
        <CommonChat threadId={chatId} />
      </div>
    </div>
  );
}
