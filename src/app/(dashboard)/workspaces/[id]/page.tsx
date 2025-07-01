'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { ArrowLeft, FolderKanban, Plus, MessageSquare, BookMarked, MoreVertical, Sparkles } from 'lucide-react';
import apiClient from '@/lib/api';

interface ChatThread {
  id: string;
  title: string;
  workspace_id: string;
  created_at?: string;
}

interface Collection {
  id: string;
  title: string;
  workspace_id: string;
  created_at: string;
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
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [selectedChat, setSelectedChat] = useState<ChatThread | null>(null);
  const [newChatTitle, setNewChatTitle] = useState('');

  useEffect(() => {
    const fetchWorkspaceData = async () => {
      try {
        // Obtener información del workspace
        const workspaceResponse = await apiClient.get(`/api/workspaces/${workspaceId}`);
        setWorkspace(workspaceResponse.data);

        // Obtener chats asociados con el workspace
        const chatsResponse = await apiClient.get(`/api/threads?workspace_id=${workspaceId}`);
        setChats(chatsResponse.data);

        // Obtener colecciones asociadas con el workspace (asumiendo que existe un endpoint)
        // NOTA: Las colecciones generales de "Gestión de Documentos" no deben formar parte del contexto del LLM en este workspace.
        // Esto requiere ajustes en el backend para asegurar que solo las colecciones específicas del workspace sean consideradas en el contexto del LLM.
        const collectionsResponse = await apiClient.get(`/api/collections?workspace_id=${workspaceId}`);
        setCollections(collectionsResponse.data);
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

  const filteredCollections = searchTerm 
    ? collections.filter(col => col.title.toLowerCase().includes(searchTerm.toLowerCase()))
    : collections;

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

  const handleOpenRenameDialog = (chat: ChatThread) => {
    setSelectedChat(chat);
    setNewChatTitle(chat.title);
    setRenameDialogOpen(true);
  };

  const handleCloseRenameDialog = () => {
    setRenameDialogOpen(false);
    setSelectedChat(null);
    setNewChatTitle('');
  };

  const handleRenameChat = async () => {
    if (selectedChat && newChatTitle && newChatTitle !== selectedChat.title) {
      try {
        await apiClient.put(`/api/threads/${selectedChat.id}`, { title: newChatTitle });
        setChats((prevChats) =>
          prevChats.map((chat) =>
            chat.id === selectedChat.id ? { ...chat, title: newChatTitle } : chat
          )
        );
      } catch (error) {
        console.error('Error al renombrar el chat:', error);
        alert('Error al renombrar el chat.');
      } finally {
        handleCloseRenameDialog();
      }
    } else {
      handleCloseRenameDialog();
    }
  };

  const handleAutoRenameChat = async () => {
    if (selectedChat) {
      try {
        const response = await apiClient.post(`/api/threads/${selectedChat.id}/generate-title`);
        const newTitle = response.data.title;
        if (newTitle) {
          setChats((prevChats) =>
            prevChats.map((chat) =>
              chat.id === selectedChat.id ? { ...chat, title: newTitle } : chat
            )
          );
        }
      } catch (error) {
        console.error('Error al renombrar automáticamente el chat:', error);
        alert('Error al renombrar automáticamente el chat.');
      } finally {
        handleCloseRenameDialog();
      }
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    if (confirm('¿Estás seguro de que deseas eliminar este chat? Esta acción no se puede deshacer.')) {
      try {
        await apiClient.delete(`/api/threads/${chatId}`);
        setChats((prevChats) => prevChats.filter((chat) => chat.id !== chatId));
      } catch (error) {
        console.error('Error al eliminar el chat:', error);
        alert('Error al eliminar el chat.');
      }
    }
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
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center">
          <FolderKanban className="mr-2 h-8 w-8 text-primary" />
          <h1 className="text-3xl font-bold">{workspace.name}</h1>
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
          className="w-full p-2 pl-5 rounded-full bg-card border-none"
        />
      </div>

      <div className="mb-10">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold flex items-center">
            <MessageSquare className="mr-2 h-6 w-6 text-primary" />
            Chats en este Workspace
          </h2>
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
              <Card key={chat.id} className="flex flex-col cursor-pointer hover:border-primary/50 transition-colors min-h-[150px]" onClick={() => handleChatClick(chat.id)}>
                <CardHeader className="flex flex-row items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center text-base">
                      <MessageSquare className="mr-2 h-6 w-6 text-primary flex-shrink-0" />
                      <span className="flex-wrap">{chat.title}</span>
                    </CardTitle>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => e.stopPropagation()}>
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleChatClick(chat.id); }}>
                        Abrir Chat
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleOpenRenameDialog(chat); }}>
                        Nombrar
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDeleteChat(chat.id); }}>
                        Eliminar
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

      <div className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-semibold flex items-center">
            <BookMarked className="mr-2 h-6 w-6 text-primary" />
            Conocimientos del Workspace
          </h2>
          <Button onClick={() => alert('Funcionalidad para añadir colección aún no implementada')}>
            <Plus className="mr-2 h-4 w-4" />
            Añadir Colección
          </Button>
        </div>
        {filteredCollections.length === 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <Card 
              className="border-dashed hover:border-primary hover:text-primary transition-colors flex flex-col items-center justify-center text-center p-6 cursor-pointer h-full"
              onClick={() => alert('Funcionalidad para crear nueva colección aún no implementada')}
            >
              <Plus className="h-8 w-8 mb-2" />
              <p className="font-semibold">Crear Colección</p>
              <p className="text-sm text-muted-foreground">Define un nuevo tema para tus documentos.</p>
            </Card>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <Card 
              className="border-dashed hover:border-primary hover:text-primary transition-colors flex flex-col items-center justify-center text-center p-6 cursor-pointer h-full"
              onClick={() => alert('Funcionalidad para crear nueva colección aún no implementada')}
            >
              <Plus className="h-8 w-8 mb-2" />
              <p className="font-semibold">Crear Colección</p>
              <p className="text-sm text-muted-foreground">Define un nuevo tema para tus documentos.</p>
            </Card>
            {filteredCollections.map((collection) => (
              <Card key={collection.id} className="cursor-pointer hover:shadow-lg transition-shadow">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <BookMarked className="mr-2 h-4 w-4" />
                    {collection.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">Creado: {new Date(collection.created_at).toLocaleDateString()}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        <p className="text-xs text-muted-foreground mt-2">Nota: Las colecciones están aisladas y solo son accesibles dentro de este workspace.</p>
      </div>

      <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Renombrar Chat</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <Input
              value={newChatTitle}
              onChange={(e) => setNewChatTitle(e.target.value)}
              placeholder="Ingrese el nuevo nombre del chat"
              className="w-full"
            />
            <Button variant="outline" onClick={handleAutoRenameChat} className="w-full md:w-auto">
              <Sparkles className="mr-2 h-4 w-4 text-yellow-500" />
              Autonombrar con LLM
            </Button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleCloseRenameDialog}>
              Cancelar
            </Button>
            <Button onClick={handleRenameChat} disabled={!newChatTitle}>
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
