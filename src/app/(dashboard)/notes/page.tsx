// En: src/app/(dashboard)/notes/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { PlusCircle, MoreVertical, Users, Notebook } from 'lucide-react';
import { NoteDialog } from './note-dialog';
import { ViewNoteDialog } from './view-note-dialog';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';

export interface Note {
  id: number;
  title: string | null;
  content: string;
  category: string;
  created_at: string;
  team_shared?: boolean | string; // Indicates if shared with a team, can be boolean or team name/id
}

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Estados para los diálogos
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [deletingNote, setDeletingNote] = useState<Note | null>(null);
  const [isNoteDialogOpen, setIsNoteDialogOpen] = useState(false);
  const [viewingNote, setViewingNote] = useState<Note | null>(null);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [sharingNote, setSharingNote] = useState<Note | null>(null);
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [teams, setTeams] = useState<any[]>([]);

  // Load shared notes from session storage on initial load
  useEffect(() => {
    const storedSharedNotes = sessionStorage.getItem('sharedNotes');
    if (storedSharedNotes) {
      const sharedNotes: Note[] = JSON.parse(storedSharedNotes);
      setNotes(prevNotes => {
        const combinedNotes = [...prevNotes];
        sharedNotes.forEach((sharedNote: Note) => {
          if (!combinedNotes.some(n => n.id === sharedNote.id)) {
            combinedNotes.push(sharedNote);
          }
        });
        return combinedNotes.sort((a: Note, b: Note) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      });
    }
  }, []);

  const fetchNotes = async () => {
    setIsLoading(true);
    try {
      // Ahora enviamos un cuerpo JSON, aunque esté vacío por ahora.
      // Esto coincide con el 'request: ListNotesRequest' del backend.
      const response = await apiClient.post('/api/list-notes', {
        search_term: null // Podríamos añadir una barra de búsqueda que llene esto
      });
      setNotes(response.data.sort((a: Note, b: Note) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (error) {
      toast.error('Error al cargar las notas.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchNotes(); }, []);

  const handleOpenCreate = () => {
    setEditingNote(null);
    setIsNoteDialogOpen(true);
  };
  
  const handleOpenEdit = (note: Note) => {
    setEditingNote(note);
    setIsNoteDialogOpen(true);
  };

  const handleOpenShareDialog = async (note: Note) => {
    setSharingNote(note);
    try {
      const response = await apiClient.get('/api/teams');
      const teamsData = response.data;
      if (teamsData.length === 0) {
        toast.error("No tienes equipos para compartir.");
        return;
      }
      setTeams(teamsData);
      setSelectedTeam(teamsData[0].id);
      setIsShareDialogOpen(true);
    } catch (error) {
      toast.error("Error al cargar los equipos.");
      console.error(error);
    }
  };

  const handleShareWithTeam = async () => {
    if (!sharingNote || !selectedTeam) return;
    try {
      const toastId = toast.loading(`Compartiendo nota con equipo...`);
      await apiClient.post(`/api/teams/${selectedTeam}/share/notes`, {
        noteIds: [sharingNote.id]
      });
      toast.success(`Nota compartida con equipo!`, { id: toastId });
      // Update the note in the list to reflect sharing status
      const updatedNote = { ...sharingNote, team_shared: true };
      setNotes(notes.map((n: Note) => n.id === sharingNote.id ? updatedNote : n));
      // Store the shared note in session storage to persist across page refreshes
      const storedSharedNotes = sessionStorage.getItem('sharedNotes');
      let sharedNotes: Note[] = storedSharedNotes ? JSON.parse(storedSharedNotes) : [];
      if (!sharedNotes.some((n: Note) => n.id === sharingNote.id)) {
        sharedNotes.push(updatedNote);
        sessionStorage.setItem('sharedNotes', JSON.stringify(sharedNotes));
      }
      // Fetch notes to refresh the list
      fetchNotes();
      setIsShareDialogOpen(false);
      setSharingNote(null);
    } catch (error) {
      toast.error("Error al compartir la nota con el equipo.");
      console.error(error);
    }
  };

  const handleManageTeamMembers = (teamId: string) => {
    toast.info("Función para gestionar miembros del equipo aún no implementada.");
    // Placeholder for future implementation to manage team members
    // This could open a new dialog or redirect to a team management page
    console.log(`Gestionar miembros para el equipo: ${teamId}`);
  };

  const handleSaveSuccess = (savedNote: Note) => {
    const existingIndex = notes.findIndex(n => n.id === savedNote.id);
    if (existingIndex !== -1) {
      // Es una actualización
      const updatedNotes = [...notes];
      updatedNotes[existingIndex] = { ...savedNote, team_shared: savedNote.team_shared || false };
      setNotes(updatedNotes);
    } else {
      // Es una creación
      setNotes([savedNote, ...notes]);
    }
    // Refresh the notes list to ensure team_shared status is updated
    fetchNotes();
  };

  const handleDeleteConfirm = async () => {
    if (!deletingNote) return;
    const toastId = toast.loading(`Eliminando nota "${deletingNote.title || 'sin título'}"...`);
    try {
      await apiClient.post('/api/delete-note', { note_id: deletingNote.id });
      setNotes(notes.filter(n => n.id !== deletingNote.id));
      toast.success('Nota eliminada', { id: toastId });
      setDeletingNote(null);
    } catch (error) {
      toast.error('Error al eliminar la nota', { id: toastId });
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
            <h1 className="text-3xl font-bold flex items-center">
                <Notebook className="mr-2 h-8 w-8 text-primary" />
                Mis Notas
            </h1>
          <p className="text-muted-foreground">Captura tus ideas, pensamientos y recordatorios.</p>
        </div>
        <Button onClick={handleOpenCreate}>
          <PlusCircle className="mr-2 h-4 w-4" />
          Crear Nota
        </Button>
      </div>

      {isLoading ? <p>Cargando notas...</p> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {notes.map((note) => (
            <Card key={note.id} className="flex flex-col cursor-pointer" onClick={() => {
              setViewingNote(note);
              setIsViewDialogOpen(true);
            }}>
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle className="flex items-center">
                    {note.title || 'Nota sin título'}
                  </CardTitle>
                  <CardDescription>Categoría: {note.category}</CardDescription>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon"><MoreVertical className="h-4 w-4" /></Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleOpenEdit(note); }}>Editar</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setDeletingNote(note)} className="text-destructive">Eliminar</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </CardHeader>
              <CardContent className="flex-grow">
                <div className="text-sm text-muted-foreground line-clamp-4">
                  {note.content ? (
                    <InlineMarkdownRenderer content={note.content} />
                  ) : (
                    <p>Sin contenido</p>
                  )}
                </div>
              </CardContent>
              <CardFooter className="flex justify-between items-center">
                <p className="text-xs text-muted-foreground">Creada: {new Date(note.created_at).toLocaleDateString()}</p>
                {note.team_shared && (
                  <span title="Compartido con equipo">
                    <Users className="h-4 w-4 text-blue-500" />
                  </span>
                )}
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
      
      {notes.length === 0 && !isLoading && (
        <div className="text-center py-10">
          <p className="text-muted-foreground">No tienes notas aún. ¡Crea una para empezar!</p>
        </div>
      )}

      <NoteDialog
        isOpen={isNoteDialogOpen}
        onOpenChange={setIsNoteDialogOpen}
        note={editingNote}
        onSaveSuccess={handleSaveSuccess}
      />

      <ViewNoteDialog
        isOpen={isViewDialogOpen}
        onOpenChange={setIsViewDialogOpen}
        note={viewingNote}
      />

      <AlertDialog open={!!deletingNote} onOpenChange={(open) => !open && setDeletingNote(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción es irreversible y eliminará la nota permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm}>Sí, eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={isShareDialogOpen} onOpenChange={(open) => !open && setIsShareDialogOpen(false)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Compartir con Equipo</AlertDialogTitle>
            <AlertDialogDescription>
              Selecciona el equipo con el que deseas compartir esta nota.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-4">
            <div className="flex flex-col gap-2">
              {teams.map(team => (
                <div key={team.id} className="flex items-center gap-2">
                  <Button
                    variant={selectedTeam === team.id ? "default" : "outline"}
                    onClick={() => setSelectedTeam(team.id)}
                    className="w-full text-left justify-start flex-grow"
                  >
                    {team.name}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleManageTeamMembers(team.id)}
                    title="Gestionar miembros"
                  >
                    Miembros
                  </Button>
                </div>
              ))}
            </div>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={handleShareWithTeam}>Compartir</AlertDialogAction>
            </AlertDialogFooter>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
