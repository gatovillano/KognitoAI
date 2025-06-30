'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { ArrowLeft, FolderKanban, Plus, MessageSquare, BookMarked, MoreVertical } from 'lucide-react';
import apiClient from '@/lib/api';

interface ChatThread {
  id: string;
  title: string;
  workspace_id: string;
  created_at?: string;
}

interface Document {
  id: string;
  title: string;
  file_name: string;
  uploaded_at: string;
}

interface Workspace {
  id: string;
  name: string;
}

export default function WorkspaceDashboard() {
  const router = useRouter();
  const params = useParams();
  const workspaceId = params.id as string;
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [chats, setChats] = useState<ChatThread[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchWorkspaceData = async () => {
      try {
        // Obtener información del workspace
        const workspaceResponse = await apiClient.get(`/api/workspaces/${workspaceId}`);
        setWorkspace(workspaceResponse.data);

        // Obtener chats asociados con el workspace
        const chatsResponse = await apiClient.get(`/api/threads?workspace_id=${workspaceId}`);
        setChats(chatsResponse.data);

        // Obtener documentos asociados con el workspace (asumiendo que existe un endpoint)
        const documentsResponse = await apiClient.get(`/api/documents?workspace_id=${workspaceId}`);
        setDocuments(documentsResponse.data);
      } catch (error) {
        console.error('Error fetching workspace data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchWorkspaceData();
  }, [workspaceId]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const filteredChats = searchTerm 
    ? chats.filter(chat => chat.title.toLowerCase().includes(searchTerm.toLowerCase()))
    : chats;

  const filteredDocuments = searchTerm 
    ? documents.filter(doc => doc.title.toLowerCase().includes(searchTerm.toLowerCase()) || doc.file_name.toLowerCase().includes(searchTerm.toLowerCase()))
    : documents;

  const handleNewChat = async () => {
    try {
      const response = await apiClient.post('/api/threads', { workspace_id: workspaceId });
      const newThread = response.data;
      setChats((prevChats) => [...prevChats, newThread]);
      router.push(`/chat/${newThread.id}`);
    } catch (error) {
      console.error('Error creating new chat:', error);
    }
  };

  const handleChatClick = (chatId: string) => {
    router.push(`/workspaces/${workspaceId}/chat/${chatId}`);
  };

  if (loading) {
    return (
      <div className="p-6">
        <p>Cargando datos del workspace...</p>
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
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <FolderKanban className="mr-2 h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">{workspace.name}</h1>
        </div>
        <Button onClick={() => router.push('/workspaces')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver a Workspaces
        </Button>
      </div>

      <div className="mb-6">
        <Input
          type="text"
          placeholder="Buscar en chats y documentos..."
          value={searchTerm}
          onChange={handleSearchChange}
          className="w-full p-2 rounded-md"
        />
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Chats en este Workspace</h2>
          <Button onClick={handleNewChat}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo Chat
          </Button>
        </div>
        {filteredChats.length === 0 ? (
          <p className="text-muted-foreground">No hay chats en este workspace que coincidan con la búsqueda.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredChats.map((chat) => (
              <Card key={chat.id} className="flex flex-col cursor-pointer hover:border-primary/50 transition-colors">
                <CardHeader className="flex flex-row items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center">
                      <MessageSquare className="mr-2 h-4 w-4" />
                      {chat.title}
                    </CardTitle>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleChatClick(chat.id); }}>
                        Abrir Chat
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">
                    Iniciado: {chat.created_at ? new Date(chat.created_at).toLocaleDateString() : 'Fecha no disponible'}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div className="mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Documentos en este Workspace</CardTitle>
          </CardHeader>
          <CardContent>
            {filteredDocuments.length === 0 ? (
              <p className="text-muted-foreground">No hay documentos en este workspace que coincidan con la búsqueda.</p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredDocuments.map((doc) => (
                  <Card key={doc.id} className="cursor-pointer hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <CardTitle className="flex items-center">
                        <BookMarked className="mr-2 h-4 w-4" />
                        {doc.title || doc.file_name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground">Subido: {new Date(doc.uploaded_at).toLocaleDateString()}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
