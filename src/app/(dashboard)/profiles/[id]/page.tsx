'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Mail, Phone, User, Notebook, Calendar, FolderKanban, ListTodo, ArrowLeft, MoreVertical, Edit, Trash2, Image as ImageIcon } from 'lucide-react'; // Import Image icon
import Link from 'next/link';
import Image from 'next/image';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ContactProfile } from '../page';
import { Note } from '../../notes/page';
import { AgendaEvent, TaskResponse } from '../../agenda/page';
import { ManageLinkedObjectsDialog } from '../manage-linked-objects-dialog';
import { NoteDialog } from '../../notes/note-dialog';
import { ViewNoteDialog } from '../../notes/view-note-dialog';
import { EventDialog } from '../../agenda/event-dialog';
import { ProfileDialog } from '../profile-dialog';
import { TaskDialog } from '../../agenda/task-dialog';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';

interface LinkedObject {
  id: string | number;
  description?: string;
  title?: string;
  name?: string;
}

// Define LinkedAlbumResponse interface
interface LinkedAlbumResponse {
  id: string;
  name: string;
  description: string | null;
  cover_photo_id: string | null;
  created_at: string;
  total_photos: number;
  cover_photo: {
    file_path: string;
    thumbnail_path: string;
  } | null;
}

interface LinkedObjects {
  notes: Note[];
  agenda_events: AgendaEvent[];
  tasks: TaskResponse[];
  user_document_topics: LinkedObject[];
  albums: LinkedAlbumResponse[]; // Add albums to linked objects
}

export default function ProfileDetailsPage() {
  console.log('ProfileDetailsPage component mounted.');
  const router = useRouter();
  const params = useParams();
  const profileId = (params?.id || '') as string;

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
  const [editingNoteForDialog, setEditingNoteForDialog] = useState<Note | null>(null);
  const [isProfileDialogOpen, setIsProfileDialogOpen] = useState(false);
  const [deletingProfile, setDeletingProfile] = useState<ContactProfile | null>(null);

  const fetchProfileDetails = useCallback(async () => {
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
  }, [profileId, router]);

  const fetchLinkedObjects = useCallback(async () => {
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
  }, [profileId]);

  useEffect(() => {
    console.log('useEffect triggered with profileId:', profileId);
    if (profileId) {
      fetchProfileDetails();
      fetchLinkedObjects();
    }
  }, [profileId, fetchProfileDetails, fetchLinkedObjects]);

  const handleEditProfile = () => {
    setIsProfileDialogOpen(true);
  };

  const handleDeleteProfile = async () => {
    if (!deletingProfile) return;
    const toastId = toast.loading(`Eliminando perfil...`);
    try {
      await apiClient.post('/api/delete-contact-profile', { profile_id: deletingProfile.id });
      toast.success('Perfil eliminado', { id: toastId });
      setDeletingProfile(null);
      router.push('/profiles');
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

      <Card className="mb-8 w-full">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-x-8 gap-y-6">
            {/* Columna de Información Principal */}
            <div className="lg:col-span-1 space-y-6">
              <h2 className="text-xl font-semibold border-b pb-2">Información General</h2>
              <div className="space-y-4">
                {profile.category && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground flex items-center"><FolderKanban className="h-4 w-4 mr-2" />Categoría</h3>
                    <p className="text-base font-semibold">{profile.category}</p>
                  </div>
                )}
                {profile.email && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground flex items-center"><Mail className="h-4 w-4 mr-2" />Email</h3>
                    <p className="text-base font-semibold break-all">{profile.email}</p>
                  </div>
                )}
                {profile.phone && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground flex items-center"><Phone className="h-4 w-4 mr-2" />Teléfono</h3>
                    <p className="text-base font-semibold">{profile.phone}</p>
                  </div>
                )}
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground flex items-center"><Calendar className="h-4 w-4 mr-2" />Creado</h3>
                  <p className="text-base font-semibold">{new Date(profile.created_at).toLocaleDateString()}</p>
                </div>
              </div>

              {profile.tags && profile.tags.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3 border-b pb-2">Etiquetas</h3>
                  <div className="flex flex-wrap gap-2 pt-2">
                    {profile.tags.map((tag, index) => {
                      const colors = ['bg-blue-100 text-blue-800', 'bg-green-100 text-green-800', 'bg-yellow-100 text-yellow-800', 'bg-purple-100 text-purple-800', 'bg-pink-100 text-pink-800'];
                      const colorClass = colors[index % colors.length];
                      return (
                        <span key={tag} className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
                          {tag}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {(profile.custom_fields && Object.keys(profile.custom_fields).length > 0) && (
                <div>
                  <h3 className="text-lg font-semibold mb-3 border-b pb-2">Campos Personalizados</h3>
                  <div className="space-y-3 pt-2">
                    {Object.entries(profile.custom_fields).map(([key, value]) => (
                       <div key={key}>
                        <h4 className="text-sm font-medium text-muted-foreground">{key}</h4>
                        <p className="text-base font-semibold">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Columna de Objetos Vinculados */}
            <div className="lg:col-span-2 space-y-6">
              <div className="flex items-center justify-between border-b pb-2">
                <h2 className="text-xl font-semibold">Actividad y Vinculaciones</h2>
                <Button variant="outline" size="sm" onClick={() => setIsManageLinkedObjectsDialogOpen(true)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Gestionar
                </Button>
              </div>

              {/* Álbumes */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center"><ImageIcon className="mr-2 h-5 w-5 text-primary" />Álbumes</h3>
                 {isLoadingLinkedObjects ? (
                  <p className="text-muted-foreground">Cargando...</p>
                ) : linkedObjects?.albums && linkedObjects.albums.length > 0 ? (
                  <div className="grid gap-6 md:grid-cols-2">
                    {linkedObjects.albums.map((album) => (
                      <Link href={`/galleries/${album.id}`} passHref key={album.id}>
                        <Card className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full min-h-[320px]">
                          <CardHeader className="pb-3">
                            <CardTitle className="flex items-start justify-between gap-3">
                              <div className="flex items-center gap-3 min-w-0 flex-1">
                                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                                  <ImageIcon className="h-5 w-5 text-primary" alt="Album icon" />
                                </div>
                                <span className="font-semibold text-lg truncate">{album.name}</span>
                              </div>
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="pt-0 flex-grow flex flex-col">
                            <div className="relative w-full h-40 bg-muted rounded-md overflow-hidden mb-3">
                              {album.cover_photo ? (
                                <Image
                                  src={`${process.env.NEXT_PUBLIC_API_URL}/media/${album.cover_photo.file_path}`}
                                  alt={album.name}
                                  width={500}
                                  height={500}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                                  <ImageIcon className="h-10 w-10 opacity-50" alt="No image placeholder" />
                                </div>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground line-clamp-2">
                              {album.description || 'Sin descripción'}
                            </p>
                          </CardContent>
                          <CardFooter className="flex justify-between items-center text-xs text-muted-foreground pt-3 mt-auto border-t border-border/50">
                            <span>{album.total_photos} foto(s)</span>
                            <span>{new Date(album.created_at).toLocaleDateString()}</span>
                          </CardFooter>
                        </Card>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground p-4 text-center bg-muted/50 rounded-md">No hay álbumes vinculados.</p>
                )}
              </div>
              <Separator />
              {/* Notas */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center"><Notebook className="mr-2 h-5 w-5 text-primary" />Notas</h3>
                {isLoadingLinkedObjects ? (
                  <p className="text-muted-foreground">Cargando...</p>
                ) : linkedObjects?.notes && linkedObjects.notes.length > 0 ? (
                  <div className="grid gap-6 md:grid-cols-2">
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
                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); setEditingNoteForDialog(note); setIsNoteDialogOpen(true); }}>
                                  <Edit className="mr-2 h-4 w-4" />Editar
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleNoteClick(note); }}>
                                  <Notebook className="mr-2 h-4 w-4" />Ver
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-0">
                          <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                            {note.content || 'Nota sin contenido.'}
                          </p>
                          <div className="flex items-center justify-between pt-2 border-t border-border/50">
                            <span className="text-xs text-muted-foreground">
                              {note.category || 'Sin categoría'}
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
                  <p className="text-sm text-muted-foreground p-4 text-center bg-muted/50 rounded-md">No hay notas vinculadas.</p>
                )}
              </div>
              <Separator />
              {/* Eventos */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center"><Calendar className="mr-2 h-5 w-5 text-primary" />Eventos</h3>
                 {isLoadingLinkedObjects ? (
                  <p className="text-muted-foreground">Cargando...</p>
                ) : linkedObjects?.agenda_events && linkedObjects.agenda_events.length > 0 ? (
                  <div className="grid gap-6 md:grid-cols-2">
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
                                  <Edit className="mr-2 h-4 w-4" />Editar
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-0">
                          <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                            Ver detalles al abrir.
                          </p>
                          <div className="flex items-center justify-between pt-2 border-t border-border/50">
                            <span className="text-xs text-muted-foreground">
                              {new Date(event.event_datetime_local).toLocaleString([], {dateStyle: 'short', timeStyle: 'short'})}
                            </span>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground p-4 text-center bg-muted/50 rounded-md">No hay eventos vinculados.</p>
                )}
              </div>
              <Separator />
              {/* Tareas */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center"><ListTodo className="mr-2 h-5 w-5 text-primary" />Tareas</h3>
                 {isLoadingLinkedObjects ? (
                  <p className="text-muted-foreground">Cargando...</p>
                ) : linkedObjects?.tasks && linkedObjects.tasks.length > 0 ? (
                  <div className="grid gap-6 md:grid-cols-2">
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
                                  <Edit className="mr-2 h-4 w-4" />Editar
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-0">
                          <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                            Ver detalles al abrir.
                          </p>
                          <div className="flex items-center justify-between pt-2 border-t border-border/50">
                            <span className="text-xs text-muted-foreground">
                              {task.due_date ? `Vence: ${new Date(task.due_date).toLocaleDateString()}` : 'Sin fecha límite'}
                            </span>
                            <div className="flex items-center gap-1">
                              <div className={`h-2 w-2 rounded-full ${task.is_completed ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
                              <span className="text-xs text-muted-foreground">
                                {task.is_completed ? 'Completada' : 'Pendiente'}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground p-4 text-center bg-muted/50 rounded-md">No hay tareas vinculadas.</p>
                )}
              </div>
              <Separator />
              {/* Colecciones */}
               <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center"><FolderKanban className="mr-2 h-5 w-5 text-primary" />Colecciones</h3>
                 {isLoadingLinkedObjects ? (
                  <p className="text-muted-foreground">Cargando...</p>
                ) : linkedObjects?.user_document_topics && linkedObjects.user_document_topics.length > 0 ? (
                  <div className="grid gap-6 md:grid-cols-2">
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
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-0">
                           <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                              {collection.description || 'Sin descripción.'}
                            </p>
                            <div className="flex items-center justify-between pt-2 border-t border-border/50">
                                <span className="text-xs text-muted-foreground">Colección de documentos</span>
                            </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground p-4 text-center bg-muted/50 rounded-md">No hay colecciones vinculadas.</p>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Diálogos de edición/visualización */}
      <ViewNoteDialog
        note={viewingNote}
        isOpen={isViewNoteDialogOpen}
        onOpenChange={setIsViewNoteDialogOpen}
        onNoteUpdated={fetchLinkedObjects}
      />
      <NoteDialog
        isOpen={isNoteDialogOpen}
        onOpenChange={setIsNoteDialogOpen}
        onSaveSuccess={fetchLinkedObjects}
        note={editingNoteForDialog}
      />
      <EventDialog
        isOpen={isEventDialogOpen}
        onOpenChange={setIsEventDialogOpen}
        onSaveSuccess={fetchLinkedObjects}
        event={editingEvent}
      />
      <TaskDialog
        isOpen={isTaskDialogOpen}
        onOpenChange={setIsTaskDialogOpen}
        onSaveSuccess={fetchLinkedObjects}
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

      {profile && (
        <ProfileDialog
          isOpen={isProfileDialogOpen}
          onOpenChange={setIsProfileDialogOpen}
          onSaveSuccess={fetchProfileDetails}
          profile={profile}
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