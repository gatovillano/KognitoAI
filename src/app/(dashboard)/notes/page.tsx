'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Plus, Notebook, Users, Edit, Trash2, MoreHorizontal, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { NoteDialog } from './note-dialog';
import { ViewNoteDialog } from './view-note-dialog';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';

export interface Note {
  id: number;
  title: string | null;
  content: string;
  category: string;
  created_at: string;
  team_shared?: boolean | string;
}

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [categoryView, setCategoryView] = useState(false);
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [deletingNote, setDeletingNote] = useState<Note | null>(null);
  const [isNoteDialogOpen, setIsNoteDialogOpen] = useState(false);
  const [viewingNote, setViewingNote] = useState<Note | null>(null);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);

  const fetchNotes = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/api/list-notes', {});
      setNotes(response.data.sort((a: Note, b: Note) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (error) {
      toast.error('Error al cargar las notas.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotes();
  }, []);

  const handleSaveSuccess = () => {
    fetchNotes();
  };

  const handleDeleteConfirm = async () => {
    if (!deletingNote) return;
    const toastId = toast.loading(`Eliminando nota...`);
    try {
      await apiClient.post('/api/delete-note', { note_id: deletingNote.id });
      toast.success('Nota eliminada', { id: toastId });
      setDeletingNote(null);
      fetchNotes();
    } catch (error) {
      toast.error('Error al eliminar la nota', { id: toastId });
    }
  };

  const updateNoteCategory = async (noteId: number, newCategory: string) => {
    try {
      const toastId = toast.loading(`Moviendo nota...`);
      await apiClient.post('/api/update-note', {
        note_id: noteId,
        category: newCategory
      });
      setNotes(prevNotes => prevNotes.map(note => note.id === noteId ? { ...note, category: newCategory } : note));
      toast.success('Nota movida a otra categoría', { id: toastId });
    } catch (error) {
      toast.error('Error al mover la nota');
      console.error(error);
    }
  };

  const NoteCard = ({ note }: { note: Note }) => {
    const [{ isDragging }, drag] = useDrag({
      type: 'NOTE',
      item: { id: note.id, category: note.category },
      collect: monitor => ({
        isDragging: !!monitor.isDragging(),
      }),
    });

    return (
      <motion.div
        layout
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        ref={drag as any}
        className="h-full"
      >
        <Card
          className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full min-h-[200px]"
          style={{ opacity: isDragging ? 0.5 : 1 }}
          onClick={() => {
            setViewingNote(note);
            setIsViewDialogOpen(true);
          }}
        >
          <CardHeader className="pb-3">
            <CardTitle className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Notebook className="h-5 w-5 text-primary" />
                </div>
                <span className="font-semibold text-lg">{note.title || 'Nota sin título'}</span>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 hover:bg-muted"
                  onClick={(e) => { e.stopPropagation(); setEditingNote(note); setIsNoteDialogOpen(true); }}
                  title="Editar nota"
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 hover:bg-destructive hover:text-destructive-foreground"
                  onClick={(e) => { e.stopPropagation(); setDeletingNote(note); }}
                  title="Eliminar nota"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 flex-grow">
            <div className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
              {note.content ? (
                <InlineMarkdownRenderer content={note.content} />
              ) : (
                <p>Sin contenido</p>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex justify-between items-center text-xs text-muted-foreground pt-3 mt-auto border-t border-border/50">
            <span>{note.category}</span>
            <div className="flex items-center gap-2">
              {note.team_shared && <span title="Compartido con equipo"><Users className="h-4 w-4" /></span>}
              <span>{new Date(note.created_at).toLocaleDateString()}</span>
            </div>
          </CardFooter>
        </Card>
      </motion.div>
    );
  };

  const CategoryDropZone = ({ category, children }: { category: string; children: React.ReactNode }) => {
    const [{ isOver }, drop] = useDrop({
      accept: 'NOTE',
      drop: (item: { id: number; category: string }) => {
        if (item.category !== category) {
          updateNoteCategory(item.id, category);
        }
      },
      collect: monitor => ({
        isOver: !!monitor.isOver(),
      }),
    });

    return (
      <div ref={drop as any} className="p-4 rounded-lg" style={{ backgroundColor: isOver ? 'rgba(147, 112, 219, 0.1)' : 'transparent' }}>
        <h2 className="text-xl font-semibold mb-4 px-2">{category}</h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
          {children}
        </div>
      </div>
    );
  };

  const renderNotes = () => {
    if (isLoading) {
      return <p className="text-center py-10">Cargando notas...</p>;
    }

    if (notes.length === 0) {
      return (
        <div className="text-center py-16">
          <Notebook className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
          <h3 className="text-xl font-semibold mb-2">No tienes notas aún</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Las notas te ayudan a capturar ideas, pensamientos y recordatorios. ¡Crea tu primera nota para empezar!
          </p>
          <Button onClick={() => { setEditingNote(null); setIsNoteDialogOpen(true); }} size="lg">
            <Plus className="mr-2 h-5 w-5" />
            Crear tu primera Nota
          </Button>
        </div>
      );
    }

    if (categoryView) {
      const groupedNotes = notes.reduce((groups, note) => {
        const key = note.category || 'Sin Categoría';
        if (!groups[key]) {
          groups[key] = [];
        }
        groups[key].push(note);
        return groups;
      }, {} as Record<string, Note[]>);

      return (
        <AnimatePresence>
          <motion.div layout className="space-y-8">
            {Object.entries(groupedNotes).map(([category, categoryNotes]) => (
              <CategoryDropZone key={category} category={category}>
                {categoryNotes.map((note) => (
                  <NoteCard key={note.id} note={note} />
                ))}
              </CategoryDropZone>
            ))}
          </motion.div>
        </AnimatePresence>
      );
    }

    return (
      <motion.div layout className="grid gap-6 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-3">
        <AnimatePresence>
          {notes.map((note) => (
            <NoteCard key={note.id} note={note} />
          ))}
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <Notebook className="mr-3 h-8 w-8 text-primary" />
              Mis Notas
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground">
                      <Info className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Captura y organiza tus ideas, pensamientos y recordatorios.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 px-2 md:px-4">
                  <span className="hidden md:inline">Acciones</span> <MoreHorizontal className="md:ml-2 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[180px]">
                <DropdownMenuItem onClick={() => { setEditingNote(null); setIsNoteDialogOpen(true); }}>
                  <Plus className="mr-2 h-4 w-4" />
                  Nueva Nota
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setCategoryView(!categoryView)}>
                  {categoryView ? "Vista General" : "Vista por Categoría"}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {renderNotes()}

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
              <AlertDialogAction onClick={handleDeleteConfirm} className="bg-destructive hover:bg-destructive/90">Sí, eliminar</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </DndProvider>
  );
}
