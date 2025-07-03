'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { ArrowLeft, Bot, Plus, MessageSquare, BookMarked, MoreVertical, Sparkles } from 'lucide-react';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import apiClient from '@/lib/api';
import { CreateWorkspaceCollectionDialog } from './CreateWorkspaceCollectionDialog';

interface ChatThread {
  id: string;
  title: string;
  workspace_id: string;
  created_at?: string;
}

interface Collection {
  id: string;
  title: string;
  topic?: string;
  workspace_id: string;
  created_at: string;
  description?: string;
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
  const [chatMessages, setChatMessages] = useState<{ [key: string]: any[] }>({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [selectedChat, setSelectedChat] = useState<ChatThread | null>(null);
  const [newChatTitle, setNewChatTitle] = useState('');
  const [collectionDialogOpen, setCollectionDialogOpen] = useState(false);
  const [createCollectionDialogOpen, setCreateCollectionDialogOpen] = useState(false);
  const [renameCollectionDialogOpen, setRenameCollectionDialogOpen] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);
  const [newCollectionTitle, setNewCollectionTitle] = useState('');
  const [newCollectionDescription, setNewCollectionDescription] = useState('');
  useEffect(() => {
    const fetchWorkspaceData = async () => {
      try {
        // Obtener información del workspace
        const workspaceResponse = await apiClient.get(`/api/workspaces/${workspaceId}`);
        setWorkspace(workspaceResponse.data);

        // Obtener chats asociados con el workspace
        const chatsResponse = await apiClient.get(`/api/threads?workspace_id=${workspaceId}`);
        const chatsData = chatsResponse.data;
        setChats(chatsData);

        // Obtener mensajes de los chats
        const messagesPromises = chatsData.map((chat: ChatThread) =>
          apiClient.get(`/api/threads/${chat.id}/messages`).then(res => ({ id: chat.id, messages: res.data }))
        );
        const messagesResults = await Promise.all(messagesPromises);
        const messagesMap = messagesResults.reduce((acc, { id, messages }) => {
          acc[id] = messages;
          return acc;
        }, {});
        setChatMessages(messagesMap);

        // Obtener colecciones asociadas con el workspace
        const collectionsResponse = await apiClient.get(`/api/workspaces/${workspaceId}/collections`);
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
    ? chats.filter(chat => {
        const titleMatch = chat.title.toLowerCase().includes(searchTerm.toLowerCase());
        const messages = chatMessages[chat.id] || [];
        const contentMatch = messages.some(msg => msg.text.toLowerCase().includes(searchTerm.toLowerCase()));
        return titleMatch || contentMatch;
      })
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

  const handleCollectionClick = (collectionId: string) => {
    // Aquí puedes implementar la navegación a una página de detalles de la colección si es necesario
    console.log(`Navigating to collection ${collectionId}`);
  };

  const handleCloseCollectionDialog = () => {
    setCollectionDialogOpen(false);
  };

  const handleCreateCollectionSuccess = (newTopic: string) => {
    // Actualizar la lista de colecciones después de crear una nueva
    const fetchCollections = async () => {
      try {
        const collectionsResponse = await apiClient.get(`/api/workspaces/${workspaceId}/collections`);
        setCollections(collectionsResponse.data);
      } catch (error) {
        console.error('Error fetching collections:', error);
      }
    };
    fetchCollections();
  };

  const handleCreateCollection = async () => {
    if (newCollectionTitle) {
      try {
        const response = await apiClient.post(`/api/workspaces/${workspaceId}/collections`, { 
          title: newCollectionTitle, 
          description: newCollectionDescription 
        });
        const newCollection = response.data;
        setCollections((prevCollections) => [...prevCollections, newCollection]);
      } catch (error) {
        console.error('Error al crear la colección:', error);
        alert('Error al crear la colección.');
      } finally {
        handleCloseCollectionDialog();
      }
    }
  };

  const [availableCollections, setAvailableCollections] = useState<Collection[]>([]);
  const [loadingCollections, setLoadingCollections] = useState(false);
  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null);

  const handleOpenAddExistingCollectionDialog = async () => {
    setLoadingCollections(true);
    try {
      const response = await apiClient.post('/api/list-collections', {});
      const allCollections = response.data.map((col: any) => ({
        id: col.topic || col.id || col.title || `collection-${Math.random().toString(36).substr(2, 9)}`,
        title: col.topic || col.title || 'Sin título',
        topic: col.topic || col.title || '',
        workspace_id: col.workspace_id || '',
        created_at: col.created_at || new Date().toISOString(),
        description: col.description || `Colección con ${col.document_count || 0} documentos`
      }));
      // Filtrar para mostrar solo las colecciones que no están ya en este workspace
      const filteredCollections = allCollections.filter(
        (col: Collection) => !collections.some(existingCol => existingCol.id === col.id)
      );
      setAvailableCollections(filteredCollections);
      setCollectionDialogOpen(true);
    } catch (error) {
      console.error('Error al cargar las colecciones disponibles:', error);
      alert('Error al cargar las colecciones disponibles.');
    } finally {
      setLoadingCollections(false);
    }
  };

  const handleAddExistingCollection = async () => {
    if (selectedCollectionId) {
      try {
        const collectionToAdd = availableCollections.find(col => col.id === selectedCollectionId);
        if (collectionToAdd) {
          // Usar el campo topic como identificador para la asociación, con un valor por defecto si no está definido
          const collectionIdentifier = encodeURIComponent(collectionToAdd.topic || collectionToAdd.title);
          const response = await apiClient.post(`/api/workspaces/${workspaceId}/collections/${collectionIdentifier}/associate`, {});
          const addedCollection = response.data;
          setCollections((prevCollections) => [...prevCollections, addedCollection]);
          handleCloseCollectionDialog();
        } else {
          alert('Colección no encontrada.');
        }
      } catch (error) {
        console.error('Error al asociar la colección existente:', error);
        alert('Error al asociar la colección existente. El identificador de la colección no es válido o no se puede asociar. Por favor, intenta crear una nueva colección con el mismo nombre si es necesario.');
      }
    }
  };

  const handleOpenRenameCollectionDialog = (collection: Collection) => {
    setSelectedCollection(collection);
    setNewCollectionTitle(collection.title);
    setNewCollectionDescription(collection.description || '');
    setRenameCollectionDialogOpen(true);
  };

  const handleCloseRenameCollectionDialog = () => {
    setRenameCollectionDialogOpen(false);
    setSelectedCollection(null);
    setNewCollectionTitle('');
    setNewCollectionDescription('');
  };

  const handleRenameCollection = async () => {
    if (selectedCollection && newCollectionTitle) {
      try {
        await apiClient.put(`/api/workspaces/${workspaceId}/collections/${selectedCollection.id}`, { 
          title: newCollectionTitle, 
          description: newCollectionDescription 
        });
        setCollections((prevCollections) =>
          prevCollections.map((col) =>
            col.id === selectedCollection.id ? { ...col, title: newCollectionTitle, description: newCollectionDescription } : col
          )
        );
      } catch (error) {
        console.error('Error al renombrar la colección:', error);
        alert('Error al renombrar la colección.');
      } finally {
        handleCloseRenameCollectionDialog();
      }
    } else {
      handleCloseRenameCollectionDialog();
    }
  };

  const handleDeleteCollection = async (collectionId: string) => {
    if (confirm('¿Estás seguro de que deseas eliminar esta colección? Esta acción no se puede deshacer.')) {
      try {
        await apiClient.delete(`/api/workspaces/${workspaceId}/collections/${collectionId}`);
        setCollections((prevCollections) => prevCollections.filter((col) => col.id !== collectionId));
      } catch (error) {
        console.error('Error al eliminar la colección:', error);
        alert('Error al eliminar la colección.');
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
  <Bot className="mr-2 h-8 w-8 text-primary" />
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
  <InlineMarkdownRenderer content={chat.title} />
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
          <div className="flex gap-2">
            <Button onClick={handleOpenAddExistingCollectionDialog}>
              <Plus className="mr-2 h-4 w-4" />
              Añadir Colección Existente
            </Button>
            <Button onClick={() => setCreateCollectionDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Crear Colección
            </Button>
          </div>
        </div>
        {filteredCollections.length === 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <Card 
              className="border-dashed hover:border-primary hover:text-primary transition-colors flex flex-col items-center justify-center text-center p-6 cursor-pointer h-full"
              onClick={() => setCreateCollectionDialogOpen(true)}
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
              onClick={() => setCreateCollectionDialogOpen(true)}
            >
              <Plus className="h-8 w-8 mb-2" />
              <p className="font-semibold">Crear Colección</p>
              <p className="text-sm text-muted-foreground">Define un nuevo tema para tus documentos.</p>
            </Card>
            {filteredCollections.map((collection) => (
              <Card key={collection.id} className="flex flex-col cursor-pointer hover:border-primary/50 transition-colors min-h-[150px]" onClick={() => handleCollectionClick(collection.id)}>
                <CardHeader className="flex flex-row items-start justify-between">
                  <div>
<CardTitle className="flex items-center text-base">
  <BookMarked className="mr-2 h-6 w-6 text-primary flex-shrink-0" />
  <InlineMarkdownRenderer content={collection.title} />
</CardTitle>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => e.stopPropagation()}>
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleCollectionClick(collection.id); }}>
                        Abrir Colección
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleOpenRenameCollectionDialog(collection); }}>
                        Renombrar
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDeleteCollection(collection.id); }}>
                        Eliminar
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
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

      <CreateWorkspaceCollectionDialog 
        isOpen={createCollectionDialogOpen} 
        onOpenChange={setCreateCollectionDialogOpen} 
        onCreateSuccess={handleCreateCollectionSuccess}
        workspaceId={workspaceId}
      />

      <Dialog open={collectionDialogOpen} onOpenChange={setCollectionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Añadir Colección Existente</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {loadingCollections ? (
                <p>Cargando colecciones...</p>
              ) : (
                availableCollections.map(col => (
                  <div
                    key={col.id}
                    className={`p-2 cursor-pointer rounded-md border ${selectedCollectionId === col.id ? 'border-primary bg-primary/10' : 'border-transparent'}`}
                    onClick={() => setSelectedCollectionId(col.id)}
                  >
                    <p className="font-medium">{col.title}</p>
                    {col.description && <p className="text-sm text-muted-foreground">{col.description}</p>}
                  </div>
                ))
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleCloseCollectionDialog}>
              Cancelar
            </Button>
            <Button onClick={handleAddExistingCollection} disabled={!selectedCollectionId}>
              Añadir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={renameCollectionDialogOpen} onOpenChange={setRenameCollectionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Renombrar Colección</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <Input
              value={newCollectionTitle}
              onChange={(e) => setNewCollectionTitle(e.target.value)}
              placeholder="Nuevo título de la colección"
              className="w-full"
            />
            <Input
              value={newCollectionDescription}
              onChange={(e) => setNewCollectionDescription(e.target.value)}
              placeholder="Nueva descripción (opcional)"
              className="w-full"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleCloseRenameCollectionDialog}>
              Cancelar
            </Button>
            <Button onClick={handleRenameCollection} disabled={!newCollectionTitle}>
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
