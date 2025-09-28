'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, ArrowLeft, Edit, Mail, Phone, Tag, Calendar, ListTodo, FileText, Image, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ViewNoteDialog } from '@/app/(dashboard)/notes/view-note-dialog';
import { EventDialog } from '@/app/(dashboard)/agenda/event-dialog';
import { TaskDialog } from '@/app/(dashboard)/agenda/task-dialog';

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

interface LinkedFormResponse {
  id: string;
  form_id: string;
  submitted_at: string;
  answers: Record<string, any>;
}

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
          <Button onClick={() => router.push(`/profiles/${profileId}/edit`)}>
            <Edit className="mr-2 h-4 w-4" /> Editar Perfil
          </Button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Columna de Información General */}
        <div className="lg:col-span-5">
          <Card className="bg-card/50 border-dashed">
            <CardHeader>
              <CardTitle>Información General</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
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
              <p className="text-xs text-muted-foreground mt-4">
                Creado: {new Date(profile.created_at).toLocaleDateString()} | Actualizado: {new Date(profile.updated_at).toLocaleDateString()}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Columna de Elementos Vinculados */}
        <div className="lg:col-span-7 space-y-6">
          {/* Notas Vinculadas */}
          <Card className="bg-card/50 border-dashed hover:border-yellow-500/50 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-yellow-500">
                <FileText className="h-5 w-5" /> Notas Vinculadas ({linkedObjects?.notes.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {linkedObjects?.notes && linkedObjects.notes.length > 0 ? (
                linkedObjects.notes.map(note => (
                  <Card key={note.id} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => { setSelectedNote(note); setShowViewNoteDialog(true); }}>
                    <CardContent className="py-3">
                      <h3 className="font-semibold text-base">{note.title || 'Sin título'}</h3>
                      <p className="text-sm text-muted-foreground mt-1">{note.content.substring(0, 150) + (note.content.length > 150 ? '...' : '')}</p>
                      <p className="text-xs text-muted-foreground mt-1">Creado: {new Date(note.created_at).toLocaleDateString()}</p>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <p className="text-muted-foreground">No hay notas vinculadas.</p>
              )}
            </CardContent>
          </Card>

          {/* Eventos de Agenda Vinculados */}
          <Card className="bg-card/50 border-dashed hover:border-purple-500/50 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-purple-500">
                <Calendar className="h-5 w-5" /> Eventos de Agenda ({linkedObjects?.agenda_events.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {linkedObjects?.agenda_events && linkedObjects.agenda_events.length > 0 ? (
                linkedObjects.agenda_events.map(event => (
                  <Card key={event.id} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => { setSelectedEvent(event); setShowViewEventDialog(true); }}>
                    <CardContent className="py-3">
                      <h3 className="font-semibold text-base">{event.description}</h3>
                      <p className="text-sm text-muted-foreground mt-1">
                        Fecha/Hora: {new Date(event.event_datetime_local).toLocaleString()}
                      </p>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <p className="text-muted-foreground">No hay eventos de agenda vinculados.</p>
              )}
            </CardContent>
          </Card>

          {/* Tareas Vinculadas */}
          <Card className="bg-card/50 border-dashed hover:border-green-500/50 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-green-500">
                <ListTodo className="h-5 w-5" /> Tareas Vinculadas ({linkedObjects?.tasks.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {linkedObjects?.tasks && linkedObjects.tasks.length > 0 ? (
                linkedObjects.tasks.map(task => (
                  <Card key={task.id} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => { setSelectedTask(task); setShowViewTaskDialog(true); }}>
                    <CardContent className="py-3">
                      <h3 className="font-semibold text-base">{task.description}</h3>
                      <p className="text-sm text-muted-foreground mt-1">
                        Estado: {task.is_completed ? 'Completada' : 'Pendiente'}
                        {task.due_date && ` | Vence: ${new Date(task.due_date).toLocaleDateString()}`}
                      </p>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <p className="text-muted-foreground">No hay tareas vinculadas.</p>
              )}
            </CardContent>
          </Card>

          {/* Colecciones de Documentos Vinculadas */}
          <Card className="bg-card/50 border-dashed hover:border-blue-500/50 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-blue-500">
                <FileText className="h-5 w-5" /> Colecciones de Documentos ({linkedObjects?.user_document_topics.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {linkedObjects?.user_document_topics && linkedObjects.user_document_topics.length > 0 ? (
                linkedObjects.user_document_topics.map(topic => (
                  <Card key={topic.id} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => router.push(`/workspaces/${profileId}/collections/${topic.id}`)}> {/* Asumiendo que profileId puede usarse como workspaceId aquí */}
                    <CardContent className="py-3">
                      <h3 className="font-semibold text-base">{topic.name}</h3>
                      {topic.description && <p className="text-sm text-muted-foreground mt-1">{topic.description}</p>}
                    </CardContent>
                  </Card>
                ))
              ) : (
                <p className="text-muted-foreground">No hay colecciones de documentos vinculadas.</p>
              )}
            </CardContent>
          </Card>

          {/* Álbumes Vinculados */}
          <Card className="bg-card/50 border-dashed hover:border-orange-500/50 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-orange-500">
                <Image className="h-5 w-5" /> Álbumes Vinculados ({linkedObjects?.albums.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {linkedObjects?.albums && linkedObjects.albums.length > 0 ? (
                linkedObjects.albums.map(album => (
                  <Card key={album.id} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => router.push(`/galleries/albums/${album.id}`)}> {/* Navegar a la página de detalles del álbum */}
                    <CardContent className="py-3 flex items-center gap-4">
                      {album.cover_photo?.thumbnail_path && (
                        <img src={album.cover_photo.thumbnail_path} alt={album.name} className="w-16 h-16 object-cover rounded-md" />
                      )}
                      <div>
                        <h3 className="font-semibold text-base">{album.name}</h3>
                        {album.description && <p className="text-sm text-muted-foreground mt-1">{album.description}</p>}
                        <p className="text-xs text-muted-foreground mt-1">{album.total_photos} fotos</p>
                      </div>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <p className="text-muted-foreground">No hay álbumes vinculados.</p>
              )}
            </CardContent>
          </Card>

          {/* Respuestas de Formulario Vinculadas */}
          <Card className="bg-card/50 border-dashed hover:border-cyan-500/50 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-cyan-500">
                <FileText className="h-5 w-5" /> Respuestas de Formulario ({linkedObjects?.form_responses.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {linkedObjects?.form_responses && linkedObjects.form_responses.length > 0 ? (
                linkedObjects.form_responses.map(response => (
                  <Card key={response.id} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => router.push(`/forms/${response.form_id}/responses`)}> {/* Navegar a la página de respuestas del formulario */}
                    <CardContent className="py-3">
                      <h3 className="font-semibold text-base">Respuesta #{response.id.slice(-6)}</h3>
                      <p className="text-sm text-muted-foreground mt-1">
                        Enviado el: {new Date(response.submitted_at).toLocaleString()}
                      </p>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <p className="text-muted-foreground">No hay respuestas de formulario vinculadas.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Diálogos para elementos vinculados */}
      {selectedNote && (
        <ViewNoteDialog
          note={selectedNote}
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
          event={selectedEvent}
        />
      )}

      {selectedTask && (
        <TaskDialog
          isOpen={showViewTaskDialog}
          onOpenChange={setShowViewTaskDialog}
          onSaveSuccess={fetchProfileDetails} // Para refrescar los datos después de una actualización
          task={selectedTask}
        />
      )}
    </div>
  );
}
