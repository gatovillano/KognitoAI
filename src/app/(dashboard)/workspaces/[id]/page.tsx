'use client';

import { useState, useEffect, use } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { ArrowLeft, Bot, Plus, MessageSquare, BookMarked, MoreVertical, Sparkles, Calendar, Notebook, ListTodo } from 'lucide-react';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import apiClient from '@/lib/api';
import { CreateWorkspaceCollectionDialog } from './CreateWorkspaceCollectionDialog';
import { AgendaEvent, TaskResponse } from '../../agenda/page'; // Import types from agenda page
import { Note } from '../../notes/page'; // Import type from notes page
import { EventDialog } from '../../agenda/event-dialog'; // Import EventDialog
import { TaskDialog } from '../../agenda/task-dialog'; // Import TaskDialog
import { NoteDialog } from '../../notes/note-dialog'; // Import NoteDialog
import { ViewNoteDialog } from '../../notes/view-note-dialog'; // Import ViewNoteDialog
import { LoadingSpinner } from '@/components/LoadingSpinner';

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

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function WorkspaceDashboard({ params }: PageProps) {
  const router = useRouter();
  const resolvedParams = use(params);
  const { id: workspaceId } = resolvedParams;
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [chats, setChats] = useState<ChatThread[]>([]);
  const [hasMoreChats, setHasMoreChats] = useState(true);
  const [isFetchingMoreChats, setIsFetchingMoreChats] = useState(false);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [agendaEvents, setAgendaEvents] = useState<AgendaEvent[]>([]); // New state for agenda events
  const [tasks, setTasks] = useState<TaskResponse[]>([]); // New state for tasks
  const [notes, setNotes] = useState<Note[]>([]); // New state for notes
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
  const [isEventDialogOpen, setIsEventDialogOpen] = useState(false); // New state for EventDialog
  const [isTaskDialogOpen, setIsTaskDialogOpen] = useState(false); // New state for TaskDialog
  const [isNoteDialogOpen, setIsNoteDialogOpen] = useState(false); // New state for NoteDialog
  const [selectedNote, setSelectedNote] = useState<Note | null>(null); // New state for selected note
  const [isViewNoteDialogOpen, setIsViewNoteDialogOpen] = useState(false); // New state for ViewNoteDialog
  const [selectedNoteCategory, setSelectedNoteCategory] = useState<string>('Todas'); // New state for note category filter

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      // Fetch workspace info, collections, events, tasks, and notes in parallel
      const [wsResponse, collectionsResponse, eventsResponse, tasksResponse, notesResponse] = await Promise.all([
        apiClient.get(`/api/workspaces/${workspaceId}`),
        apiClient.get(`/api/collections?workspace_id=${workspaceId}`),
        apiClient.post('/api/list-events', { workspace_id: workspaceId }),
        apiClient.get('/api/tasks', { params: { workspace_id: workspaceId } }),
        apiClient.post('/api/list-notes', { workspace_id: workspaceId })
      ]);

      setWorkspace(wsResponse.data);
      setCollections(collectionsResponse.data);
      setAgendaEvents(eventsResponse.data.filter((event: AgendaEvent) => event.workspace_id === workspaceId));
      setTasks(tasksResponse.data.filter((task: TaskResponse) => task.workspace_id === workspaceId));
      setNotes(notesResponse.data.notes);

      // Fetch the first page of chats separately
      await fetchChats(0, true);

    } catch (error) {
      console.error('Error fetching initial workspace data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchChats = async (skip: number, initialLoad = false) => {
    if (!initialLoad) {
      setIsFetchingMoreChats(true);
    }
    try {
      const response = await apiClient.get(`/api/threads?workspace_id=${workspaceId}&skip=${skip}&limit=7`);
      const newChats = response.data.threads;
      setChats(prevChats => initialLoad ? newChats : [...prevChats, ...newChats]);
      setHasMoreChats(newChats.length === 7);
    } catch (error) {
      console.error('Error fetching chats:', error);
    } finally {
      if (!initialLoad) {
        setIsFetchingMoreChats(false);
      }
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, [workspaceId, fetchInitialData]);

  const handleLoadMoreChats = () => {
    if (hasMoreChats && !isFetchingMoreChats) {
      fetchChats(chats.length);
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const filteredChats = searchTerm 
    ? chats.filter(chat => chat.title.toLowerCase().includes(searchTerm.toLowerCase()))
    : chats;

  const filteredCollections = searchTerm
    ? collections.filter(col => (col.title || col.name || '').toLowerCase().includes(searchTerm.toLowerCase()))
    : collections;

  const filteredAgendaEvents = searchTerm
    ? agendaEvents.filter(event => event.description.toLowerCase().includes(searchTerm.toLowerCase()))
    : agendaEvents;

  const filteredTasks = searchTerm
    ? tasks.filter(task => task.description.toLowerCase().includes(searchTerm.toLowerCase()))
    : tasks;

  const filteredNotes = searchTerm
    ? notes.filter(note => (note.title || '').toLowerCase().includes(searchTerm.toLowerCase()) || note.content.toLowerCase().includes(searchTerm.toLowerCase()))
    : notes;

  const uniqueNoteCategories = ['Todas', ...Array.from(new Set(notes.map(note => note.category)))];

  const filteredNotesByCategory = selectedNoteCategory === 'Todas'
    ? filteredNotes
    : filteredNotes.filter(note => note.category === selectedNoteCategory);

  const handleNewChat = async () => {
    try {
      const response = await apiClient.post('/api/threads', { workspace_id: workspaceId });
      const newThread = response.data;
      setChats((prevChats) => [...prevChats, newThread]);
      router.push(`/workspaces/${workspaceId}/chat/${newThread.id}`);
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
    // Asegurarse de que el collectionId esté codificado para la URL
    const encodedCollectionId = encodeURIComponent(collectionId);
    router.push(`/workspaces/${workspaceId}/collections/${encodedCollectionId}`);
  };

  const handleCloseCollectionDialog = () => {
    setCollectionDialogOpen(false);
  };

  const handleCreateCollectionSuccess = (newTopic: string) => {
    console.log(`handleCreateCollectionSuccess called for new topic: ${newTopic}`);
    // Actualizar la lista de colecciones después de crear una nueva
    const fetchCollections = async () => {
      try {
        const collectionsResponse = await apiClient.get(`/api/collections?workspace_id=${workspaceId}`);
        console.log('Fetched collections after creation:', collectionsResponse.data);
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
        const response = await apiClient.get('/api/collections');
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
    // Asegurarse de que el collectionIdentifier tenga un valor válido
    const collectionIdentifier = encodeURIComponent(selectedCollection.topic || selectedCollection.title || selectedCollection.id || '');
    if (!collectionIdentifier) {
      console.error('DEBUG (Frontend): collectionIdentifier es nulo o vacío para renombrar.');
      alert('No se pudo identificar la colección para renombrar.');
      handleCloseRenameCollectionDialog();
      return;
    }
    const url = `/api/update-collection`; // Cambiar a la ruta POST
    const data = {
      old_topic: selectedCollection.topic || selectedCollection.name || selectedCollection.title || selectedCollection.id, // Usar el topic/nombre actual
      new_topic: newCollectionTitle,
      new_description: newCollectionDescription,
      workspace_id: workspaceId // Asegurarse de pasar el workspace_id
    };
    console.log('DEBUG (Frontend): Renaming collection POST request URL:', url);
    console.log('DEBUG (Frontend): Renaming collection POST request data:', data);
    console.log('DEBUG (Frontend): Selected collection for rename:', selectedCollection);
    try {
      await apiClient.post(url, data); // Cambiar a POST
      setCollections((prevCollections) =>
        prevCollections.map((col) =>
          col.id === selectedCollection.id ? { ...col, title: newCollectionTitle, name: newCollectionTitle, description: newCollectionDescription, topic: newCollectionTitle } : col
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
      const collectionToDelete = collections.find(col => col.id === collectionId);
      if (collectionToDelete) {
        // Asegurarse de que el collectionIdentifier tenga un valor válido
        const collectionIdentifier = encodeURIComponent(collectionToDelete.topic || collectionToDelete.title || collectionToDelete.id || '');
        if (!collectionIdentifier) {
          console.error('DEBUG (Frontend): collectionIdentifier es nulo o vacío para eliminar.');
          alert('No se pudo identificar la colección para eliminar.');
          return;
        }
        const url = `/api/delete-collection`; // Cambiar a la ruta POST para eliminar
        const data = {
          topic: collectionIdentifier,
          workspace_id: workspaceId // Asegurarse de pasar el workspace_id
        };
        console.log('DEBUG (Frontend): Deleting collection POST request URL:', url);
        console.log('DEBUG (Frontend): Collection to delete:', collectionToDelete);
        try {
          await apiClient.post(url, data); // Cambiar a POST
          setCollections((prevCollections) => prevCollections.filter((col) => col.id !== collectionId));
        } catch (error) {
          console.error('Error al eliminar la colección:', error);
          alert('Error al eliminar la colección.');
        }
      } else {
        alert('Colección no encontrada para eliminar.');
      }
    } catch (error) {
      console.error('Error general al eliminar la colección:', error);
      alert('Error general al eliminar la colección.');
    }
  }
};

  if (loading) {
    return <LoadingSpinner />;
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

  const handleEventSaveSuccess = (newEvent: AgendaEvent) => {
    setAgendaEvents(prev => [...prev, newEvent].sort((a,b) => new Date(a.event_datetime_utc).getTime() - new Date(b.event_datetime_utc).getTime()));
  };

  const handleTaskSaveSuccess = (newTask: TaskResponse) => {
    setTasks(prev => {
      const existingIndex = prev.findIndex(t => t.id === newTask.id);
      if (existingIndex > -1) {
        const updatedTasks = [...prev];
        updatedTasks[existingIndex] = newTask;
        return updatedTasks;
      } else {
        return [...prev, newTask];
      }
    });
  };

  const handleNoteSaveSuccess = (newNote: Note) => {
    setNotes(prev => [...prev, newNote].sort((a,b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
  };

  const handleNoteClick = (note: Note) => {
    setSelectedNote(note);
    setIsViewNoteDialogOpen(true);
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
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
            {[...filteredChats].reverse().map((chat) => (
              <Card key={chat.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 min-h-[180px] flex flex-col" onClick={() => handleChatClick(chat.id)}>
                <CardHeader className="pb-3 flex-1">
                  <CardTitle className="flex items-start justify-between gap-3 h-full">
                    <div className="flex items-start gap-3 min-w-0 flex-1 h-full">
                      <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center flex-shrink-0">
                        <MessageSquare className="h-5 w-5 text-green-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm leading-relaxed whitespace-normal break-words line-clamp-3">
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
        {hasMoreChats && !searchTerm && (
          <div className="flex justify-center mt-6">
            <Button onClick={handleLoadMoreChats} disabled={isFetchingMoreChats}>
              {isFetchingMoreChats ? "Cargando..." : "Cargar más chats"}
            </Button>
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
                      {collection.document_count !== undefined
                        ? `${collection.document_count} documento(s)`
                        : 'Calculando...'}
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

      {/* Agenda Section (NEW) */}
      <div className="mb-12">
        <div className="mb-6">
          <div>
            <h2 className="text-2xl font-semibold flex items-center">
              <Calendar className="mr-3 h-6 w-6 text-primary" />
              Agenda del Workspace
            </h2>
            <p className="text-muted-foreground mt-1">Eventos y tareas programadas para este espacio</p>
          </div>
        </div>
        {filteredAgendaEvents.length === 0 && filteredTasks.length === 0 ? (
          <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
            <Calendar className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
            <h3 className="text-xl font-semibold mb-2">
              {searchTerm ? 'No hay eventos ni tareas que coincidan' : 'No hay eventos ni tareas aún'}
            </h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Programa eventos y tareas específicas para este workspace.
            </p>
            {/* Add buttons to create new event/task if needed */}
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {/* Display Agenda Events */}
            {filteredAgendaEvents.map((event) => (
              <Card key={event.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center flex-shrink-0">
                        <Calendar className="h-5 w-5 text-purple-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm line-clamp-2">
                          {event.description}
                        </div>
                      </div>
                    </div>
                    {/* Add dropdown for actions if needed */}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      {new Date(event.event_datetime_local).toLocaleDateString()} {new Date(event.event_datetime_local).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {/* Add status/team info if needed */}
                  </div>
                </CardContent>
              </Card>
            ))}
            {/* Display Tasks */}
            {filteredTasks.map((task) => (
              <Card key={task.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-orange-500/10 flex items-center justify-center flex-shrink-0">
                        <ListTodo className="h-5 w-5 text-orange-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm line-clamp-2">
                          {task.description}
                        </div>
                      </div>
                    </div>
                    {/* Add dropdown for actions if needed */}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      {task.due_date ? new Date(task.due_date).toLocaleDateString() : 'Sin fecha límite'}
                    </span>
                    <div className="flex items-center gap-1">
                      <div className={`h-2 w-2 rounded-full ${task.is_completed ? 'bg-green-500' : 'bg-red-500'}`}></div>
                      <span className="text-xs text-muted-foreground">{task.is_completed ? 'Completada' : 'Pendiente'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Notes Section (NEW) */}
      <div className="mb-12">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold flex items-center">
              <Notebook className="mr-3 h-6 w-6 text-primary" />
              Notas del Workspace
            </h2>
            <p className="text-muted-foreground mt-1">Notas y apuntes específicos de este espacio</p>
          </div>
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  Categoría: {selectedNoteCategory}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {uniqueNoteCategories.map(category => (
                  <DropdownMenuItem key={category} onClick={() => setSelectedNoteCategory(category)}>
                    {category}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <Button variant="outline" onClick={() => setIsNoteDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Nueva Nota
            </Button>
          </div>
        </div>
        {filteredNotes.length === 0 ? (
          <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
            <Notebook className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
            <h3 className="text-xl font-semibold mb-2">
              {searchTerm ? 'No hay notas que coincidan' : 'No hay notas aún'}
            </h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Crea notas para organizar tus ideas y conocimientos en este workspace.
            </p>
            {!searchTerm && (
              <Button onClick={() => setIsNoteDialogOpen(true)} size="lg">
                <Plus className="mr-2 h-5 w-5" />
                Crear primera Nota
              </Button>
            )}
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredNotesByCategory.map((note) => (
              <Card key={note.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => handleNoteClick(note)}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-yellow-500/10 flex items-center justify-center flex-shrink-0">
                        <Notebook className="h-5 w-5 text-yellow-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm line-clamp-2">
                          {note.title || 'Nota sin título'}
                        </div>
                      </div>
                    </div>
                    {/* Add dropdown for actions if needed */}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                    {note.content}
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      {note.category}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(note.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
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

      {/* Dialogs for new items */}
      <EventDialog
        isOpen={isEventDialogOpen}
        onOpenChange={setIsEventDialogOpen}
        onSaveSuccess={handleEventSaveSuccess}
        workspaceId={workspaceId}
      />
      <TaskDialog
        isOpen={isTaskDialogOpen}
        onOpenChange={setIsTaskDialogOpen}
        onSaveSuccess={handleTaskSaveSuccess}
        workspaceId={workspaceId}
      />
      <NoteDialog
        isOpen={isNoteDialogOpen}
        onOpenChange={setIsNoteDialogOpen}
        onSaveSuccess={handleNoteSaveSuccess}
        workspaceId={workspaceId}
        note={null}
      />

      <ViewNoteDialog
        note={selectedNote}
        isOpen={isViewNoteDialogOpen}
        onOpenChange={setIsViewNoteDialogOpen}
        onNoteUpdated={fetchInitialData} // Llamar a fetchInitialData para recargar los datos
      />
    </div>
  );
}