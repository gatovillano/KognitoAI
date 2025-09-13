'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Mail, Phone, User, Notebook, Calendar, FolderKanban, ListTodo, ArrowLeft, MoreVertical, Edit, Trash2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ContactProfile } from '../page';
import { Note } from '../../notes/page';
import { AgendaEvent, TaskResponse } from '../../agenda/page';
import { ManageLinkedObjectsDialog } from '../manage-linked-objects-dialog';
import { NoteDialog } from '../../notes/note-dialog';
import { ViewNoteDialog } from '../../notes/view-note-dialog';
import { EventDialog } from '../../agenda/event-dialog';
import { ProfileDialog } from '../profile-dialog'; // NUEVA IMPORTACIÓN
import { TaskDialog } from '../../agenda/task-dialog';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';

interface LinkedObject {
  id: string | number;
  description?: string;
  title?: string;
  name?: string;
}

interface LinkedObjects {
  notes: Note[]; // Usar la interfaz Note completa
  agenda_events: AgendaEvent[]; // Usar la interfaz AgendaEvent completa
  tasks: TaskResponse[]; // Usar la interfaz TaskResponse completa
  user_document_topics: LinkedObject[];
}

export default function ProfileDetailsPage() {
  console.log('ProfileDetailsPage component mounted.');
  const router = useRouter();
  const params = useParams();
  const profileId = params.id as string;

  console.log('Profile ID from params:', profileId);

  const [profile, setProfile] = useState<ContactProfile | null>(null);
  const [linkedObjects, setLinkedObjects] = useState<LinkedObjects | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingLinkedObjects, setIsLoadingLinkedObjects] = useState(false);
  const [isManageLinkedObjectsDialogOpen, setIsManageLinkedObjectsDialogOpen] = useState(false);

  // Estados para diálogos de edición/visualización
  const [isNoteDialogOpen, setIsNoteDialogOpen] = useState(false);
  const [viewingNote, setViewingNote] = useState<Note | null>(null);
  const [isViewNoteDialogOpen, setIsViewNoteDialogOpen] = useState(false);
  const [isEventDialogOpen, setIsEventDialogOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<AgendaEvent | null>(null);
  const [isTaskDialogOpen, setIsTaskDialogOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<TaskResponse | null>(null);
  const [editingNoteForDialog, setEditingNoteForDialog] = useState<Note | null>(null); // NUEVO ESTADO
  const [isProfileDialogOpen, setIsProfileDialogOpen] = useState(false); // NUEVO ESTADO
  const [deletingProfile, setDeletingProfile] = useState<ContactProfile | null>(null);

  useEffect(() => {
    console.log('useEffect triggered with profileId:', profileId);
    if (profileId) {
      fetchProfileDetails();
      fetchLinkedObjects();
    }
  }, [profileId]);

  const fetchProfileDetails = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get(`/api/contact-profiles/${profileId}`);
      setProfile(response.data);
    } catch (error) {
      toast.error('Error al cargar los detalles del perfil.');
      console.error('Error fetching profile details:', error);
      router.push('/profiles'); // Redirigir si el perfil no se encuentra
    } finally {
      setIsLoading(false);
    }
  };

  const fetchLinkedObjects = async () => {
    setIsLoadingLinkedObjects(true);
    try {
      const response = await apiClient.get(`/api/contact-profiles/${profileId}/linked-objects`);
      setLinkedObjects(response.data);
    } catch (error) {
      toast.error('Error al cargar objetos vinculados.');
      console.error('Error fetching linked objects:', error);
      setLinkedObjects(null);
    } finally {
      setIsLoadingLinkedObjects(false);
    }
  };

  const handleEditProfile = () => {
    setIsProfileDialogOpen(true); // Abrir el diálogo de edición
  };

  const handleDeleteProfile = async () => {
    if (!deletingProfile) return;
    const toastId = toast.loading(`Eliminando perfil...`);
    try {
      await apiClient.delete(`/api/contact-profiles/${deletingProfile.id}`);
      toast.success('Perfil eliminado', { id: toastId });
      setDeletingProfile(null);
      router.push('/profiles'); // Volver a la lista de perfiles
    } catch (error) {
      toast.error('Error al eliminar el perfil', { id: toastId });
      console.error('Error deleting profile:', error);
    }
  };

  const handleNoteClick = (note: Note) => {
    setViewingNote(note);
    setIsViewNoteDialogOpen(true);
  };

  const handleEventClick = (event: AgendaEvent) => {
    setEditingEvent(event);
    setIsEventDialogOpen(true);
  };

  const handleTaskClick = (task: TaskResponse) => {
    setEditingTask(task);
    setIsTaskDialogOpen(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Cargando detalles del perfil...</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="text-center py-16">
        <User className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
        <h3 className="text-xl font-semibold mb-2">Perfil no encontrado</h3>
        <p className="text-muted-foreground mb-6">
          No se pudo acceder a este perfil o no existe.
        </p>
        <Button onClick={() => router.push('/profiles')} size="lg">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver a Perfiles
        </Button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <User className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">{profile.name || 'Perfil sin nombre'}</h1>
            <p className="text-muted-foreground">Detalles completos del perfil de contacto</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.push('/profiles')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a Perfiles
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleEditProfile}>
                <Edit className="mr-2 h-4 w-4" />
                Editar Perfil
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setDeletingProfile(profile)} className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Eliminar Perfil
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Información General</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {profile.category && (
              <div>
                <div className="flex items-center space-x-2">
                  <FolderKanban className="h-4 w-4 text-muted-foreground" />
                  <h3 className="text-sm font-medium">Categoría</h3>
                </div>
                <p className="text-2xl font-bold">{profile.category}</p>
              </div>
            )}
            {profile.email && (
              <div>
                <div className="flex items-center space-x-2">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <h3 className="text-sm font-medium">Email</h3>
                </div>
                <p className="text-2xl font-bold break-all">{profile.email}</p>
              </div>
            )}
            {profile.phone && (
              <div>
                <div className="flex items-center space-x-2">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <h3 className="text-sm font-medium">Teléfono</h3>
                </div>
                <p className="text-2xl font-bold">{profile.phone}</p>
              </div>
            )}
            <div>
              <div className="flex items-center space-x-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">Creado</h3>
              </div>
              <p className="text-2xl font-bold">{new Date(profile.created_at).toLocaleDateString()}</p>
              <p className="text-xs text-muted-foreground">{new Date(profile.created_at).toLocaleTimeString()}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {profile.tags && profile.tags.length > 0 && (
        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">Etiquetas</h2>
          <div className="flex flex-wrap gap-2">
            {profile.tags.map((tag, index) => {
              const colors = ['bg-blue-100 text-blue-800', 'bg-green-100 text-green-800', 'bg-yellow-100 text-yellow-800', 'bg-purple-100 text-purple-800', 'bg-pink-100 text-pink-800'];
              const colorClass = colors[index % colors.length];
              return (
                <span key={tag} className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium ${colorClass}`}>
                  {tag}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {(profile.custom_fields && Object.keys(profile.custom_fields).length > 0) && (
        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">Campos Personalizados</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(profile.custom_fields).map(([key, value]) => (
              <Card key={key}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">{key}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-bold">{String(value)}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      <Separator className="my-8" />

      <div className="mb-12">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold flex items-center">
            <Notebook className="mr-3 h-6 w-6 text-primary" />
            Notas Vinculadas
          </h2>
          <Button variant="outline" onClick={() => setIsManageLinkedObjectsDialogOpen(true)}>
            <Edit className="mr-2 h-4 w-4" />
            Gestionar Vinculaciones
          </Button>
        </div>
        {isLoadingLinkedObjects ? (
          <p className="text-center text-muted-foreground py-8">Cargando notas vinculadas...</p>
        ) : linkedObjects?.notes && linkedObjects.notes.length > 0 ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {linkedObjects.notes.map((note) => (
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
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => {
                          e.stopPropagation();
                          setEditingNoteForDialog(note); // Establecer la nota para edición
                          setIsNoteDialogOpen(true); // Abrir el diálogo de edición
                        }}>
                          <Edit className="mr-2 h-4 w-4" />
                          Editar Nota
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleNoteClick(note); }}>
                          <Notebook className="mr-2 h-4 w-4" />
                          Ver Nota
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
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
        ) : (
          <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
            <Notebook className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
            <h3 className="text-xl font-semibold mb-2">No hay notas vinculadas</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Este perfil no tiene notas asociadas. Gestiona las vinculaciones para añadir algunas.
            </p>
          </div>
        )}
      </div>

      <div className="mb-12">
        <h2 className="text-2xl font-semibold flex items-center mb-6">
          <Calendar className="mr-3 h-6 w-6 text-primary" />
          Eventos Vinculados
        </h2>
        {isLoadingLinkedObjects ? (
          <p className="text-center text-muted-foreground py-8">Cargando eventos vinculados...</p>
        ) : linkedObjects?.agenda_events && linkedObjects.agenda_events.length > 0 ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {linkedObjects.agenda_events.map((event) => (
              <Card key={event.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => handleEventClick(event)}>
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
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleEventClick(event); }}>
                          <Edit className="mr-2 h-4 w-4" />
                          Editar Evento
                        </DropdownMenuItem>
                        {/* Add more event actions here if needed */}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      {new Date(event.event_datetime_utc).toLocaleDateString()} {new Date(event.event_datetime_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {/* Add status/team info if needed */}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
            <Calendar className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
            <h3 className="text-xl font-semibold mb-2">No hay eventos vinculados</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Este perfil no tiene eventos asociados. Gestiona las vinculaciones para añadir algunos.
            </p>
          </div>
        )}
      </div>

      <div className="mb-12">
        <h2 className="text-2xl font-semibold flex items-center mb-6">
          <ListTodo className="mr-3 h-6 w-6 text-primary" />
          Tareas Vinculadas
        </h2>
        {isLoadingLinkedObjects ? (
          <p className="text-center text-muted-foreground py-8">Cargando tareas vinculadas...</p>
        ) : linkedObjects?.tasks && linkedObjects.tasks.length > 0 ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {linkedObjects.tasks.map((task) => (
              <Card key={task.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => handleTaskClick(task)}>
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
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleTaskClick(task); }}>
                          <Edit className="mr-2 h-4 w-4" />
                          Editar Tarea
                        </DropdownMenuItem>
                        {/* Add more task actions here if needed */}
                      </DropdownMenuContent>
                    </DropdownMenu>
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
        ) : (
          <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
            <ListTodo className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
            <h3 className="text-xl font-semibold mb-2">No hay tareas vinculadas</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Este perfil no tiene tareas asociadas. Gestiona las vinculaciones para añadir algunas.
            </p>
          </div>
        )}
      </div>

      <div className="mb-12">
        <h2 className="text-2xl font-semibold flex items-center mb-6">
          <FolderKanban className="mr-3 h-6 w-6 text-primary" />
          Colecciones de Documentos Vinculadas
        </h2>
        {isLoadingLinkedObjects ? (
          <p className="text-center text-muted-foreground py-8">Cargando colecciones vinculadas...</p>
        ) : linkedObjects?.user_document_topics && linkedObjects.user_document_topics.length > 0 ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {linkedObjects.user_document_topics.map((collection) => (
              <Card key={collection.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
                        <FolderKanban className="h-5 w-5 text-blue-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm line-clamp-2">
                          {collection.name || collection.title || 'Colección sin nombre'}
                        </div>
                      </div>
                    </div>
                    {/* Add dropdown for actions if needed */}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                    {collection.description || 'Colección de documentos especializados'}
                  </p>
                  {/* Add more collection info if needed */}
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
            <FolderKanban className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
            <h3 className="text-xl font-semibold mb-2">No hay colecciones vinculadas</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Este perfil no tiene colecciones asociadas. Gestiona las vinculaciones para añadir algunas.
            </p>
          </div>
        )}
      </div>

      {/* Diálogos de edición/visualización */}
      <ViewNoteDialog
        note={viewingNote}
        isOpen={isViewNoteDialogOpen}
        onOpenChange={setIsViewNoteDialogOpen}
        onNoteUpdated={fetchLinkedObjects} // Refrescar objetos vinculados al actualizar nota
      />
      <NoteDialog
        isOpen={isNoteDialogOpen}
        onOpenChange={setIsNoteDialogOpen}
        onSaveSuccess={fetchLinkedObjects} // Refrescar objetos vinculados al guardar nota
        note={editingNoteForDialog} // Para edición
      />
      <EventDialog
        isOpen={isEventDialogOpen}
        onOpenChange={setIsEventDialogOpen}
        onSaveSuccess={fetchLinkedObjects} // Refrescar objetos vinculados al guardar evento
        event={editingEvent}
      />
      <TaskDialog
        isOpen={isTaskDialogOpen}
        onOpenChange={setIsTaskDialogOpen}
        onSaveSuccess={fetchLinkedObjects} // Refrescar objetos vinculados al guardar tarea
        task={editingTask}
      />

      {/* Diálogo de gestión de vinculaciones */}
      {profile && (
        <ManageLinkedObjectsDialog
          isOpen={isManageLinkedObjectsDialogOpen}
          onOpenChange={setIsManageLinkedObjectsDialogOpen}
          profile={profile}
          onLinkedObjectsUpdated={fetchLinkedObjects}
        />
      )}

      {profile && ( // Renderizar solo si hay un perfil cargado
        <ProfileDialog
          isOpen={isProfileDialogOpen}
          onOpenChange={setIsProfileDialogOpen}
          onSaveSuccess={fetchProfileDetails} // Refrescar los detalles del perfil después de guardar
          profile={profile} // Pasar el perfil actual para edición
        />
      )}

      <AlertDialog open={!!deletingProfile} onOpenChange={(open) => !open && setDeletingProfile(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción es irreversible y eliminará el perfil permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteProfile} className="bg-destructive hover:bg-destructive/90">Sí, eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
