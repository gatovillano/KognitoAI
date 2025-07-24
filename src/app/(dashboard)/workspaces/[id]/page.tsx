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
  title?: string;
  topic?: string;
  workspace_id: string;
  created_at: string;
  description?: string;
  name?: string;
  document_count?: number;
}

interface Workspace {
  id: string;
  name: string;
}

export default function WorkspaceDashboard() {
  const router = useRouter();
  const params = useParams();
  const workspaceId = (params?.id as string) || '';
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
  const [shareCollectionDialogOpen, setShareCollectionDialogOpen] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);
  const [newCollectionTitle, setNewCollectionTitle] = useState('');
  const [newCollectionDescription, setNewCollectionDescription] = useState('');
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [availableWorkspaces, setAvailableWorkspaces] = useState<Workspace[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  useEffect(() => {
    const fetchWorkspaceData = async () => {
      try {
        // Obtener información del workspace
        const workspaceResponse = await apiClient.get(`/api/workspaces/${workspaceId}`);
        setWorkspace(workspaceResponse.data);

        // Obtener chats asociados con el workspace
        const chatsResponse = await apiClient.get(`/api/threads?workspace_id=${workspaceId}`);
        const chatsData = chatsResponse.data.filter((chat: ChatThread) => chat.workspace_id === workspaceId);
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
    ? collections.filter(col => (col.title || col.name || '').toLowerCase().includes(searchTerm.toLowerCase()))
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
    router.push(`/workspaces/${workspaceId}/collections/${collectionId}`);
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
      // Obtener colecciones del contexto general (sin workspace_id)
      const response = await apiClient.post('/api/list-general-collections', {});

      // Obtener colecciones ya asociadas a este workspace
      const workspaceCollectionsResponse = await apiClient.get(`/api/workspaces/${workspaceId}/collections`);
      const workspaceCollectionIds = new Set(workspaceCollectionsResponse.data.map((col: any) => col.id));

      const allCollections = response.data.map((col: any) => ({
        id: col.topic || col.id || col.title || `collection-${Math.random().toString(36).substr(2, 9)}`,
        title: col.topic || col.title || 'Sin título',
        name: col.topic || col.title || 'Sin título',
        topic: col.topic || col.title || '',
        workspace_id: col.workspace_id || '',
        created_at: col.created_at || new Date().toISOString(),
        description: col.description || (col.document_count > 0 ? `${col.document_count} documentos` : 'Colección vacía'),
        document_count: col.document_count || 0
      }));

      // Filtrar para mostrar solo las colecciones del contexto general que no están ya en este workspace
      // Incluir tanto colecciones con documentos como colecciones vacías
      const filteredCollections = allCollections.filter(
        (col: Collection) => !workspaceCollectionIds.has(col.id)
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
          const collectionIdentifier = encodeURIComponent(collectionToAdd.topic || collectionToAdd.title || '');
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
    setNewCollectionTitle(collection.title || collection.name || '');
    setNewCollectionDescription(collection.description || '');
    setRenameCollectionDialogOpen(true);
  };

  const handleOpenShareCollectionDialog = (collection: Collection) => {
    setSelectedCollection(collection);
    setShareCollectionDialogOpen(true);
    loadAvailableWorkspaces();
  };

  const handleCloseShareCollectionDialog = () => {
    setShareCollectionDialogOpen(false);
    setSelectedCollection(null);
    setSelectedWorkspaceId(null);
  };

  const loadAvailableWorkspaces = async () => {
    setLoadingWorkspaces(true);
    try {
      const response = await apiClient.get('/api/workspaces');
      setAvailableWorkspaces(response.data);
    } catch (error) {
      console.error('Error al cargar los workspaces disponibles:', error);
      alert('Error al cargar los workspaces disponibles.');
    } finally {
      setLoadingWorkspaces(false);
    }
  };

  const handleShareCollection = async () => {
    if (selectedCollection && selectedWorkspaceId) {
      try {
        await apiClient.post(`/api/workspaces/${selectedWorkspaceId}/collections/${selectedCollection.id}/share`, {});
        alert('Colección compartida con éxito.');
        handleCloseShareCollectionDialog();
      } catch (error) {
        console.error('Error al compartir la colección:', error);
        alert('Error al compartir la colección.');
      }
    }
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
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Cargando datos del workspace...</p>
        </div>
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="text-center py-16">
        <Bot className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
        <h3 className="text-xl font-semibold mb-2">Workspace no encontrado</h3>
        <p className="text-muted-foreground mb-6">
          No se pudo acceder a este workspace o no tienes permisos para verlo.
        </p>
        <Button onClick={() => router.push('/workspaces')} size="lg">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver a Workspaces
        </Button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Bot className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">{workspace.name}</h1>
            <p className="text-muted-foreground">Espacio de trabajo especializado</p>
          </div>
        </div>
        <Button variant="outline" onClick={() => router.push('/workspaces')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver a Workspaces
        </Button>
      </div>

      <div className="mb-8">
        <div className="relative">
          <svg className="absolute left-4 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <Input
            type="text"
            placeholder="Buscar en chats y documentos..."
            value={searchTerm}
            onChange={handleSearchChange}
            className="pl-12 h-12 rounded-full bg-card border-0 shadow-sm focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      <div className="mb-12">
        <div className="mb-6">
          <div>
            <h2 className="text-2xl font-semibold flex items-center">
              <MessageSquare className="mr-3 h-6 w-6 text-primary" />
              Chats en este Workspace
            </h2>
            <p className="text-muted-foreground mt-1">Conversaciones específicas de este espacio</p>
          </div>
        </div>
        
        {filteredChats.length === 0 ? (
          <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
            <MessageSquare className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
            <h3 className="text-xl font-semibold mb-2">
              {searchTerm ? 'No se encontraron chats' : 'No hay chats aún'}
            </h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              {searchTerm 
                ? 'No hay chats que coincidan con tu búsqueda. Intenta con otros términos.'
                : 'Comienza una nueva conversación especializada en este workspace.'
              }
            </p>
            {!searchTerm && (
              <Button onClick={handleNewChat} size="lg">
                <Plus className="mr-2 h-5 w-5" />
                Crear primer Chat
              </Button>
            )}
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <Card 
              className="group border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 transition-all duration-200 flex flex-col items-center justify-center text-center p-6 cursor-pointer min-h-[180px]"
              onClick={handleNewChat}
            >
              <div className="h-12 w-12 rounded-full bg-green-500/10 flex items-center justify-center mb-3 group-hover:bg-green-500/20 transition-colors">
                <Plus className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="font-semibold text-lg mb-1">Nuevo Chat</h3>
              <p className="text-sm text-muted-foreground">Iniciar nueva conversación</p>
            </Card>
            {filteredChats.map((chat) => (
              <Card key={chat.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 min-h-[180px] flex flex-col" onClick={() => handleChatClick(chat.id)}>
                <CardHeader className="pb-3 flex-1">
                  <CardTitle className="flex items-start justify-between gap-3 h-full">
                    <div className="flex items-start gap-3 min-w-0 flex-1 h-full">
                      <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center flex-shrink-0">
                        <MessageSquare className="h-5 w-5 text-green-600" />
                      </div>
                      <div className="min-w-0 flex-1 flex flex-col justify-between h-full">
                        <div className="font-semibold text-sm leading-relaxed">
                          <InlineMarkdownRenderer content={chat.title} />
                        </div>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleChatClick(chat.id); }}>
                          <MessageSquare className="mr-2 h-4 w-4" />
                          Abrir Chat
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleOpenRenameDialog(chat); }}>
                          <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                          Renombrar
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDeleteChat(chat.id); }} className="text-destructive">
                          <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Eliminar
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 mt-auto">
                  <div className="flex items-center justify-between pt-3 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      {chat.created_at ? new Date(chat.created_at).toLocaleDateString() : 'Sin fecha'}
                    </span>
                    <div className="flex items-center gap-1">
                      <div className="h-2 w-2 rounded-full bg-green-500"></div>
                      <span className="text-xs text-muted-foreground">Activo</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div className="mb-12">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold flex items-center">
              <BookMarked className="mr-3 h-6 w-6 text-primary" />
              Conocimientos del Workspace
            </h2>
            <p className="text-muted-foreground mt-1">Documentos y colecciones especializadas</p>
          </div>
          <Button variant="outline" onClick={handleOpenAddExistingCollectionDialog}>
            <Plus className="mr-2 h-4 w-4" />
            Añadir Existente
          </Button>
        </div>
        
        {filteredCollections.length === 0 ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <Card 
              className="group border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 transition-all duration-200 flex flex-col items-center justify-center text-center p-8 cursor-pointer min-h-[200px]"
              onClick={() => setCreateCollectionDialogOpen(true)}
            >
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                <Plus className="h-8 w-8 text-primary" />
              </div>
              <h3 className="font-semibold text-lg mb-2">Crear Colección</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Define un nuevo tema para organizar tus documentos y conocimientos.
              </p>
            </Card>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <Card 
              className="group border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 transition-all duration-200 flex flex-col items-center justify-center text-center p-6 cursor-pointer"
              onClick={() => setCreateCollectionDialogOpen(true)}
            >
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
                <Plus className="h-6 w-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-1">Crear Colección</h3>
              <p className="text-xs text-muted-foreground">Nuevo tema de documentos</p>
            </Card>
            {filteredCollections.map((collection) => (
              <Card key={collection.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => handleCollectionClick(collection.id)}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
                        <BookMarked className="h-5 w-5 text-blue-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm line-clamp-2">
                          <InlineMarkdownRenderer content={collection.title || collection.name || ''} />
                        </div>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleCollectionClick(collection.id); }}>
                          <BookMarked className="mr-2 h-4 w-4" />
                          Abrir Colección
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleOpenRenameCollectionDialog(collection); }}>
                          <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                          Renombrar
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleOpenShareCollectionDialog(collection); }}>
                          <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                          </svg>
                          Compartir
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDeleteCollection(collection.id); }} className="text-destructive">
                          <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Eliminar
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                    {collection.description || 'Colección de documentos especializados'}
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      {collection.created_at ? new Date(collection.created_at).toLocaleDateString() : 'Sin fecha'}
                    </span>
                    <div className="flex items-center gap-1">
                      <div className="h-2 w-2 rounded-full bg-blue-500"></div>
                      <span className="text-xs text-muted-foreground">Disponible</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        <p className="text-xs text-muted-foreground/70 mt-4 text-center">
          Las colecciones están aisladas y solo son accesibles dentro de este workspace
        </p>
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
                    className={`p-3 cursor-pointer rounded-md border ${selectedCollectionId === col.id ? 'border-primary bg-primary/10' : 'border-transparent hover:bg-muted/50'}`}
                    onClick={() => setSelectedCollectionId(col.id)}
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{col.title}</p>
                      <span className="text-xs bg-muted px-2 py-1 rounded-full">
                        {col.document_count || 0} docs
                      </span>
                    </div>
                    {col.description && <p className="text-sm text-muted-foreground mt-1">{col.description}</p>}
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

      <Dialog open={shareCollectionDialogOpen} onOpenChange={setShareCollectionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Compartir Colección</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {loadingWorkspaces ? (
                <p>Cargando workspaces...</p>
              ) : (
                availableWorkspaces.map(workspace => (
                  <div
                    key={workspace.id}
                    className={`p-2 cursor-pointer rounded-md border ${selectedWorkspaceId === workspace.id ? 'border-primary bg-primary/10' : 'border-transparent'}`}
                    onClick={() => setSelectedWorkspaceId(workspace.id)}
                  >
                    <p className="font-medium">{workspace.name}</p>
                  </div>
                ))
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleCloseShareCollectionDialog}>
              Cancelar
            </Button>
            <Button onClick={handleShareCollection} disabled={!selectedWorkspaceId}>
              Compartir
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
