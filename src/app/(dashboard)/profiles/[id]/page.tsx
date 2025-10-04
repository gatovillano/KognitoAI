'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, ArrowLeft, Edit, Mail, Phone, Tag, Calendar, ListTodo, FileText, Image, Info, MoreHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ViewNoteDialog } from '@/app/(dashboard)/notes/view-note-dialog';
import { EventDialog } from '@/app/(dashboard)/agenda/event-dialog';
import { TaskDialog } from '@/app/(dashboard)/agenda/task-dialog';
import { ManageLinkedObjectsDialog } from '@/app/(dashboard)/profiles/manage-linked-objects-dialog';
import { FormResponseDialog } from '@/components/forms/FormResponseDialog';

// Interfaces para los objetos vinculados (de api/contact_profiles.py)
interface LinkedNoteResponse {
  id: number;
  title: string | null;
  content: string;
  created_at: string;
}

interface LinkedAgendaEventResponse {
  id: number;
  description: string;
  event_datetime_utc: string;
  event_datetime_local: string;
}

interface LinkedTaskResponse {
  id: string;
  description: string;
  is_completed: boolean;
  due_date: string | null;
}

interface LinkedUserDocumentTopicResponse {
  id: string;
  name: string;
  description: string | null;
}

interface PhotoResponseForContactProfile {
  id: string;
  file_path: string;
  thumbnail_path: string | null;
}

interface LinkedAlbumResponse {
  id: string;
  name: string;
  description: string | null;
  cover_photo_id: string | null;
  created_at: string;
  total_photos: number;
  cover_photo: PhotoResponseForContactProfile | null;
}

import { LinkedFormResponse } from '@/types/form';

interface LinkedObjectsResponse {
  notes: LinkedNoteResponse[];
  agenda_events: LinkedAgendaEventResponse[];
  tasks: LinkedTaskResponse[];
  user_document_topics: LinkedUserDocumentTopicResponse[];
  albums: LinkedAlbumResponse[];
  form_responses: LinkedFormResponse[]; // Añadido
}

interface ContactProfile {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  tags: string[] | null;
  category: string | null;
  custom_fields: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export default function ProfileDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const profileId = params?.id as string;

  const [profile, setProfile] = useState<ContactProfile | null>(null);
  const [linkedObjects, setLinkedObjects] = useState<LinkedObjectsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showViewNoteDialog, setShowViewNoteDialog] = useState(false);
  const [selectedNote, setSelectedNote] = useState<LinkedNoteResponse | null>(null);

  const [showViewEventDialog, setShowViewEventDialog] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<LinkedAgendaEventResponse | null>(null);

  const [showViewTaskDialog, setShowViewTaskDialog] = useState(false);
  const [selectedTask, setSelectedTask] = useState<LinkedTaskResponse | null>(null);

  const [showManageLinkedObjectsDialog, setShowManageLinkedObjectsDialog] = useState(false);

  const [showFormResponseDialog, setShowFormResponseDialog] = useState(false);
  const [selectedFormResponse, setSelectedFormResponse] = useState<LinkedFormResponse | null>(null);

  const fetchProfileDetails = async () => {
    if (!profileId) return;
    setLoading(true);
    setError(null);
    try {
      const [profileRes, linkedObjectsRes] = await Promise.all([
        apiClient.get(`/api/contact-profiles/${profileId}`),
        apiClient.get(`/api/contact-profiles/${profileId}/linked-objects`),
      ]);
      setProfile(profileRes.data);
      setLinkedObjects(linkedObjectsRes.data);
    } catch (err) {
      setError('No se pudo cargar el perfil o sus objetos vinculados. Puede que no exista o haya ocurrido un error.');
      toast.error('Error al cargar los detalles del perfil.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfileDetails();
  }, [profileId]);

  if (loading) {
    return (
      <div className="p-4 sm:p-8 max-w-7xl mx-auto flex justify-center items-center">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-4">Cargando perfil...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 sm:p-8 max-w-7xl mx-auto text-center text-destructive">
        <h2 className="text-xl font-bold mb-4">Error</h2>
        <p>{error}</p>
        <Button onClick={() => router.push('/profiles')} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" /> Volver a Perfiles
        </Button>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="p-4 sm:p-8 max-w-7xl mx-auto text-center">
        <p className="text-muted-foreground">Perfil no encontrado.</p>
        <Button onClick={() => router.push('/profiles')} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" /> Volver a Perfiles
        </Button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
            <Info className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">{profile.name || 'Perfil sin nombre'}</h1>
            <p className="text-muted-foreground">Detalles y elementos vinculados a este contacto.</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push('/profiles')}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Volver a Perfiles
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <MoreHorizontal className="mr-2 h-4 w-4" /> Acciones
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => router.push(`/profiles/${profileId}/edit`)}>
                <Edit className="mr-2 h-4 w-4" />
                <span>Editar Perfil</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setShowManageLinkedObjectsDialog(true)}>
                <ListTodo className="mr-2 h-4 w-4" />
                <span>Gestionar Vinculaciones</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Columna de Información General */}
        <div className="lg:col-span-1 space-y-6">
          <h2 className="text-2xl font-semibold flex items-center mb-6">
            <Info className="mr-3 h-6 w-6 text-primary" />
            Información General
          </h2>
          <Card>
            <CardContent className="space-y-4 pt-6">
              {profile.email && (
                <p className="flex items-center gap-2 text-muted-foreground">
                  <Mail className="h-4 w-4 text-primary" /> {profile.email}
                </p>
              )}
              {profile.phone && (
                <p className="flex items-center gap-2 text-muted-foreground">
                  <Phone className="h-4 w-4 text-primary" /> {profile.phone}
                </p>
              )}
              {profile.category && (
                <p className="flex items-center gap-2 text-muted-foreground">
                  <Tag className="h-4 w-4 text-primary" /> Categoría: {profile.category}
                </p>
              )}
              {profile.tags && profile.tags.length > 0 && (
                <div>
                  <p className="font-semibold mb-2 flex items-center gap-2 text-muted-foreground">
                    <Tag className="h-4 w-4 text-primary" /> Etiquetas:
                  </p>
                  <div className="flex flex-wrap gap-2">
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
              {profile.custom_fields && Object.keys(profile.custom_fields).length > 0 && (
                <div>
                  <p className="font-semibold mb-2 text-muted-foreground">Campos Personalizados:</p>
                  {Object.entries(profile.custom_fields).map(([key, value]) => (
                    <p key={key} className="text-sm text-muted-foreground">
                      <span className="font-medium">{key}:</span> {String(value)}
                    </p>
                  ))}
                </div>
              )}
              <p className="text-xs text-muted-foreground pt-4 border-t border-border/50">
                Creado: {new Date(profile.created_at).toLocaleDateString()}
              </p>
              <p className="text-xs text-muted-foreground">
                Actualizado: {new Date(profile.updated_at).toLocaleDateString()}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Columna de Elementos Vinculados */}
        <div className="lg:col-span-2">
          <h2 className="text-2xl font-semibold flex items-center mb-6">
            <ListTodo className="mr-3 h-6 w-6 text-primary" />
            Elementos Vinculados
          </h2>
          <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-2">
            {/* Notas Vinculadas */}
            {(linkedObjects?.notes.length || 0) > 0 && linkedObjects?.notes.map(note => (
              <Card key={note.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => { setSelectedNote(note); setShowViewNoteDialog(true); }}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-yellow-500/10 flex items-center justify-center flex-shrink-0">
                        <FileText className="h-5 w-5 text-yellow-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm line-clamp-2">
                          {note.title || 'Sin título'}
                        </div>
                      </div>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                    {note.content}
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      Nota
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(note.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Eventos de Agenda Vinculados */}
            {(linkedObjects?.agenda_events.length || 0) > 0 && linkedObjects?.agenda_events.map(event => (
              <Card key={event.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => { setSelectedEvent(event); setShowViewEventDialog(true); }}>
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
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      Evento
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(event.event_datetime_local).toLocaleString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Tareas Vinculadas */}
            {(linkedObjects?.tasks.length || 0) > 0 && linkedObjects?.tasks.map(task => (
              <Card key={task.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => { setSelectedTask(task); setShowViewTaskDialog(true); }}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center flex-shrink-0">
                        <ListTodo className="h-5 w-5 text-green-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm line-clamp-2">
                          {task.description}
                        </div>
                      </div>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      Tarea
                    </span>
                    <div className="flex items-center gap-1">
                      <div className={`h-2 w-2 rounded-full ${task.is_completed ? 'bg-green-500' : 'bg-red-500'}`}></div>
                      <span className="text-xs text-muted-foreground">{task.is_completed ? 'Completada' : 'Pendiente'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Colecciones de Documentos Vinculadas */}
            {(linkedObjects?.user_document_topics.length || 0) > 0 && linkedObjects?.user_document_topics.map(topic => (
              <Card key={topic.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => router.push(`/workspaces/${profileId}/collections/${topic.id}`)}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
                        <FileText className="h-5 w-5 text-blue-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm line-clamp-2">
                          {topic.name}
                        </div>
                      </div>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                    {topic.description || 'Colección de documentos'}
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      Colección
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Álbumes Vinculados */}
            {(linkedObjects?.albums.length || 0) > 0 && linkedObjects?.albums.map(album => (
              <Card key={album.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col" onClick={() => router.push(`/galleries/albums/${album.id}`)}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-orange-500/10 flex items-center justify-center flex-shrink-0">
                        <Image className="h-5 w-5 text-orange-600" />
                      </div>
                      <span className="font-semibold text-lg truncate">{album.name}</span>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 flex-grow flex flex-col">
                  <div className="relative w-full aspect-square bg-muted rounded-md overflow-hidden mb-3">
                    {album.cover_photo?.file_path ? (
                      <img
                        src={`${process.env.NEXT_PUBLIC_API_URL}/media/${album.cover_photo.file_path}`}
                        alt={album.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                        <Image className="h-10 w-10 opacity-50" />
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
            ))}

            {/* Respuestas de Formulario Vinculadas */}
            {(linkedObjects?.form_responses.length || 0) > 0 && linkedObjects?.form_responses.map(response => (
              <Card key={response.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => { setSelectedFormResponse(response); setShowFormResponseDialog(true); }}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-cyan-500/10 flex items-center justify-center flex-shrink-0">
                        <FileText className="h-5 w-5 text-cyan-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm line-clamp-2">
                          Respuesta al formulario: {response.form_name || 'Sin nombre'}
                        </div>
                      </div>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground">
                      Respuesta
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(response.submitted_at).toLocaleDateString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* Diálogos para elementos vinculados */}
      {selectedNote && (
        <ViewNoteDialog
          note={selectedNote ? {
            ...selectedNote,
            category: '', // Add a default value for category
            team_shared: false,
            team_id: undefined,
            workspace_id: undefined,
            workspace_name: undefined,
            workspace_color: undefined,
          } : null}


          isOpen={showViewNoteDialog}
          onOpenChange={setShowViewNoteDialog}
          onNoteUpdated={fetchProfileDetails} // Para refrescar los datos después de una actualización
        />
      )}

      {selectedEvent && (
        <EventDialog
          isOpen={showViewEventDialog}
          onOpenChange={setShowViewEventDialog}
          onSaveSuccess={fetchProfileDetails} // Para refrescar los datos después de una actualización
          event={selectedEvent ? {
            ...selectedEvent,
            user_timezone: '', // Add a default value for user_timezone
            team_shared: false,
            workspace_id: undefined,
            workspace_name: undefined,
            workspace_color: undefined,
            linked_profiles: [],
          } : null}

        />
      )}

      {selectedTask && (
        <TaskDialog
          isOpen={showViewTaskDialog}
          onOpenChange={setShowViewTaskDialog}
          onSaveSuccess={fetchProfileDetails} // Para refrescar los datos después de una actualización
          task={selectedTask ? {
            ...selectedTask,
            due_date: selectedTask.due_date || undefined,
            created_at: '', // Add a default value for created_at
            updated_at: '', // Add a default value for updated_at
            account_id: '', // Add a default value for account_id
          } : null}


        />
      )}

      {showManageLinkedObjectsDialog && (
        <ManageLinkedObjectsDialog
          isOpen={showManageLinkedObjectsDialog}
          onOpenChange={setShowManageLinkedObjectsDialog}
          profile={profile}
          onLinkedObjectsUpdated={fetchProfileDetails}
        />
      )}

      <FormResponseDialog
        isOpen={showFormResponseDialog}
        onOpenChange={setShowFormResponseDialog}
        response={selectedFormResponse}
      />
    </div>
  );
}
