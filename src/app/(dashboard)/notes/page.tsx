// En: src/app/(dashboard)/notes/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { PlusCircle, MoreVertical } from 'lucide-react';
import { NoteDialog } from './note-dialog';
import { ViewNoteDialog } from './view-note-dialog';

export interface Note {
  id: number;
  title: string | null;
  content: string;
  category: string;
  created_at: string;
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

  const handleSaveSuccess = (savedNote: Note) => {
    const existingIndex = notes.findIndex(n => n.id === savedNote.id);
    if (existingIndex !== -1) {
      // Es una actualización
      const updatedNotes = [...notes];
      updatedNotes[existingIndex] = savedNote;
      setNotes(updatedNotes);
    } else {
      // Es una creación
      setNotes([savedNote, ...notes]);
    }
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
          <h1 className="text-3xl font-bold">Mis Notas</h1>
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
                  <CardTitle>{note.title || 'Nota sin título'}</CardTitle>
                  <CardDescription>Categoría: {note.category}</CardDescription>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon"><MoreVertical className="h-4 w-4" /></Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => handleOpenEdit(note)}>Editar</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setDeletingNote(note)} className="text-destructive">Eliminar</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </CardHeader>
              <CardContent className="flex-grow">
                <p className="text-sm text-muted-foreground line-clamp-4">{note.content}</p>
              </CardContent>
              <CardFooter>
                <p className="text-xs text-muted-foreground">Creada: {new Date(note.created_at).toLocaleDateString()}</p>
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
    </div>
  );
}
