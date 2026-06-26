'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Plus, Notebook, Users, Edit, Trash2, MoreHorizontal, Info, Lightbulb, FileText, Link, Bot, Star, CheckSquare, X, MessageSquare } from 'lucide-react'; // Añadido Link, Bot, Star, CheckSquare y X
import { Checkbox } from '@/components/ui/checkbox';
import { motion, AnimatePresence } from 'framer-motion';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { NoteDialog } from './note-dialog';
import { ViewNoteDialog } from './view-note-dialog';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'; // Importar Sheet
import { useDrag, useDrop } from 'react-dnd';
import { ManageLinkedProfilesDialog } from './ManageLinkedProfilesDialog';
import { AnalysisDetailDialog } from '../analysis/analysis-detail-dialog';
import { ContactProfile } from '../profiles/Profiles';
import { Analysis, Note } from '@/lib/models';
import { useAuth } from '@/contexts/AuthContext';
import { NoteSearch } from '@/components/NoteSearch';
import { ContextualChat } from '@/components/ContextualChat';

export type { Note };


export function Notes({ isEmbedded = false }: { isEmbedded?: boolean }) {
  const { user } = useAuth();
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [categoryView, setCategoryView] = useState(false);
  const [workspaceGroupView, setWorkspaceGroupView] = useState(false); // Nuevo estado para la vista agrupada por workspace
  const [workspaceView, setWorkspaceView] = useState<string | null>(null); // Nuevo estado para el workspace seleccionado
  const [availableWorkspaces, setAvailableWorkspaces] = useState<{ id: string; name: string; color?: string }[]>([]); // Nuevo estado para workspaces disponibles
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [deletingNote, setDeletingNote] = useState<Note | null>(null);
  const [isNoteDialogOpen, setIsNoteDialogOpen] = useState(false);
  const [viewingNote, setViewingNote] = useState<Note | null>(null);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [isLinkProfileDialogOpen, setIsLinkProfileDialogOpen] = useState(false);
  const [linkingNote, setLinkingNote] = useState<Note | null>(null);
  const [analysisResult, setAnalysisResult] = useState<Analysis | null>(null);
  const [isAnalysisResultDialogOpen, setIsAnalysisResultDialogOpen] = useState(false);
  const [currentAnalysisTaskId, setCurrentAnalysisTaskId] = useState<string | null>(null);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false); // Nuevo estado para controlar la visibilidad del Sheet

  // Estados para selección por lote
  const [selectedNoteIds, setSelectedNoteIds] = useState<number[]>([]);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [isBulkDeleteDialogOpen, setIsBulkDeleteDialogOpen] = useState(false);
  const [chatNote, setChatNote] = useState<Note | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  const handleToggleSelectNote = (noteId: number, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSelectedNoteIds(prev =>
      prev.includes(noteId) ? prev.filter(id => id !== noteId) : [...prev, noteId]
    );
  };

  const handleBulkDeleteConfirm = async () => {
    if (selectedNoteIds.length === 0) return;
    const toastId = toast.loading(`Eliminando ${selectedNoteIds.length} notas...`);
    try {
      const response = await apiClient.post('/api/notes/bulk-delete', { note_ids: selectedNoteIds });
      const count = response.data.deleted_count;
      toast.success(`${count} notas eliminadas`, { id: toastId });
      setSelectedNoteIds([]);
      setIsSelectionMode(false);
      setIsBulkDeleteDialogOpen(false);
      setSkip(0);
      setHasMore(true);
      fetchNotes(0, limit);
    } catch (error) {
      toast.error('Error al eliminar las notas por lote', { id: toastId });
    }
  };

  const handleBulkChangeCategory = async (newCategory: string) => {
    if (selectedNoteIds.length === 0) return;
    const toastId = toast.loading(`Cambiando categoría a ${newCategory}...`);
    try {
      const response = await apiClient.post('/api/notes/bulk-update', {
        note_ids: selectedNoteIds,
        category: newCategory
      });
      const count = response.data.updated_count;
      toast.success(`${count} notas movidas a '${newCategory}'`, { id: toastId });
      setSelectedNoteIds([]);
      setIsSelectionMode(false);
      setNotes(prevNotes =>
        prevNotes.map(note =>
          selectedNoteIds.includes(note.id) ? { ...note, category: newCategory } : note
        )
      );
    } catch (error) {
      toast.error('Error al cambiar la categoría', { id: toastId });
    }
  };

  const handleBulkChangeWorkspace = async (workspaceId: string | null) => {
    if (selectedNoteIds.length === 0) return;
    const isClearing = !workspaceId || workspaceId === "none";
    const toastId = toast.loading(isClearing ? 'Quitando notas del workspace...' : 'Moviendo notas al workspace...');
    try {
      const response = await apiClient.post('/api/notes/bulk-update', {
        note_ids: selectedNoteIds,
        workspace_id: isClearing ? "" : workspaceId
      });
      const count = response.data.updated_count;
      toast.success(
        isClearing 
          ? `${count} notas quitadas del workspace` 
          : `${count} notas asociadas al workspace`, 
        { id: toastId }
      );
      setSelectedNoteIds([]);
      setIsSelectionMode(false);
      fetchNotes(0, limit, false);
    } catch (error) {
      toast.error('Error al cambiar el workspace de las notas', { id: toastId });
    }
  };

  const handleBulkToggleStar = async (starStatus: boolean) => {
    if (selectedNoteIds.length === 0) return;
    const toastId = toast.loading(starStatus ? 'Destacando notas...' : 'Quitando destaque...');
    try {
      const response = await apiClient.post('/api/notes/bulk-update', {
        note_ids: selectedNoteIds,
        is_starred: starStatus
      });
      const count = response.data.updated_count;
      toast.success(
        starStatus 
          ? `${count} notas destacadas` 
          : `${count} notas desmarcadas`, 
        { id: toastId }
      );
      setSelectedNoteIds([]);
      setIsSelectionMode(false);
      setNotes(prevNotes => {
        const updated = prevNotes.map(note =>
          selectedNoteIds.includes(note.id) ? { ...note, is_starred: starStatus } : note
        );
        return updated.sort((a, b) => {
          if (a.is_starred && !b.is_starred) return -1;
          if (!a.is_starred && b.is_starred) return 1;
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
      });
    } catch (error) {
      toast.error('Error al actualizar las notas destacadas', { id: toastId });
    }
  };

  const handleBulkAnalyzeNotes = async () => {
    if (selectedNoteIds.length === 0) return;
    const toastId = toast.loading(`Iniciando análisis de ${selectedNoteIds.length} notas...`);
    try {
      const response = await apiClient.post('/api/analyze-note-collection', {
        note_ids: selectedNoteIds,
        collection_name: `Colección de ${selectedNoteIds.length} Notas`
      });
      toast.dismiss(toastId);
      toast.success('Análisis de colección completado.');
      
      const newAnalysis: Analysis = {
        id: response.data.task_id || `analysis-${Date.now()}`,
        type: 'note_collection_analysis',
        title: `Análisis de Selección (${selectedNoteIds.length} notas)`,
        created_at: new Date().toISOString(),
        result: response.data.result_payload
      };

      setAnalysisResult(newAnalysis);
      setIsAnalysisResultDialogOpen(true);
      setSelectedNoteIds([]);
      setIsSelectionMode(false);
    } catch (error) {
      toast.dismiss(toastId);
      toast.error('Error al analizar la selección de notas.');
      console.error(error);
    }
  };

  // Estados para paginación
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(20); // Mostrar 20 notas inicialmente
  const [hasMore, setHasMore] = useState(true);
  const [isFetchingMore, setIsFetchingMore] = useState(false); // Para evitar cargas múltiples


  const fetchNotes = async (newSkip: number, newLimit: number, append: boolean = false, selectedWorkspaceId: string | null = null) => {
    if (!append) {
      setIsLoading(true);
    } else {
      setIsFetchingMore(true);
    }
    try {
      const payload: { skip: number; limit: number; workspace_id?: string } = { skip: newSkip, limit: newLimit };
      if (selectedWorkspaceId) {
        payload.workspace_id = selectedWorkspaceId;
      }
      const response = await apiClient.post('/api/notes/list-notes', payload);
      console.log("API Response Data:", response.data);
      const fetchedNotes = response.data.notes.sort((a: Note, b: Note) => {
        if (a.is_starred && !b.is_starred) return -1;
        if (!a.is_starred && b.is_starred) return 1;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });

      // Obtener roles de workspace para cada nota
      const notesWithRoles = await Promise.all(
        fetchedNotes.map(async (note: Note) => {
          if (note.workspace_id) {
            try {
              const roleResponse = await apiClient.get(`/api/workspaces/${note.workspace_id}/my-role`);
              return { ...note, workspace_role: roleResponse.data.role };
            } catch (error) {
              console.error(`Error fetching role for workspace ${note.workspace_id}:`, error);
              return note;
            }
          }
          return note;
        })
      );

      if (append) {
        setNotes(prevNotes => [...prevNotes, ...notesWithRoles]);
      } else {
        setNotes(notesWithRoles);
      }
      setHasMore(fetchedNotes.length === newLimit);
      setSkip(newSkip + fetchedNotes.length); // Actualizar skip para la próxima carga

      // Extraer workspaces únicos de las notas cargadas
      const uniqueWorkspaces = Array.from(new Set(fetchedNotes.map((note: Note) => note.workspace_id)))
        .filter(Boolean) // Eliminar null/undefined
        .map(id => {
          const note = fetchedNotes.find((n: Note) => n.workspace_id === id);
          return { id: id as string, name: note?.workspace_name || `Workspace ${id}`, color: note?.workspace_color };
        });
      setAvailableWorkspaces(prev => {
        const existingIds = new Set(prev.map(ws => ws.id));
        const newWorkspaces = uniqueWorkspaces.filter(ws => !existingIds.has(ws.id));
        return [...prev, ...newWorkspaces];
      });

    } catch (error) {
      toast.error('Error al cargar las notas.');
    } finally {
      setIsLoading(false);
      setIsFetchingMore(false);
    }
  };

  useEffect(() => {
    fetchNotes(0, limit, false, workspaceView); // Carga inicial, ahora con workspaceView
  }, [limit, workspaceView]); // Añadir workspaceView como dependencia

  const handleLoadMore = () => {
    if (hasMore && !isFetchingMore) {
      fetchNotes(skip, limit, true);
    }
  };

  const handleSaveSuccess = (updatedNote: Note) => {
    setNotes(prevNotes => {
      const existingNoteIndex = prevNotes.findIndex(note => note.id === updatedNote.id);
      if (existingNoteIndex > -1) {
        // Actualizar nota existente
        const newNotes = [...prevNotes];
        newNotes[existingNoteIndex] = updatedNote;
        return newNotes;
      } else {
        // Añadir nueva nota al principio
        return [updatedNote, ...prevNotes];
      }
    });
    // Opcional: Si quieres recargar para asegurar consistencia con el backend después de la actualización optimista
    // fetchNotes(0, limit);
  };

  const pollAnalysisResult = async (taskId: string) => {
    const checkStatus = async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${taskId}`);
        const result = response.data;

        if (result.status === 'completed') {
          toast.success('Análisis completado. Mostrando resultados.');
          setAnalysisResult(result.result);
          setIsAnalysisResultDialogOpen(true);
          setCurrentAnalysisTaskId(null); // Limpiar el ID de la tarea actual
        } else if (result.status === 'failed') {
          toast.error('El análisis ha fallado.');
          setCurrentAnalysisTaskId(null); // Limpiar el ID de la tarea actual
        } else {
          // Si no ha terminado, seguir haciendo polling
          setTimeout(checkStatus, 3000); // Reintentar en 3 segundos
        }
      } catch (error) {
        console.error('Error al hacer polling del resultado del análisis:', error);
        toast.error('Error al obtener el resultado del análisis.');
        setCurrentAnalysisTaskId(null); // Limpiar el ID de la tarea actual
      }
    };
    checkStatus();
  };

  useEffect(() => {
    if (currentAnalysisTaskId) {
      pollAnalysisResult(currentAnalysisTaskId);
    }
  }, [currentAnalysisTaskId]);

  const handleDeleteConfirm = async () => {
    if (!deletingNote) return;
    const toastId = toast.loading(`Eliminando nota...`);
    try {
      await apiClient.post('/api/delete-note', { note_id: deletingNote.id });
      toast.success('Nota eliminada', { id: toastId });
      setDeletingNote(null);
      // Recargar todas las notas desde el principio después de eliminar
      setSkip(0);
      setHasMore(true);
      fetchNotes(0, limit);
    } catch (error) {
      toast.error('Error al eliminar la nota', { id: toastId });
    }
  };

  const handleAnalyzeAllNotes = async () => {
    if (notes.length === 0) {
      toast.info("No hay notas para analizar.");
      return;
    }

    const toastId = toast.loading("Iniciando análisis de todas las notas...");
    try {
      const noteIds = notes.map(note => note.id);
      const response = await apiClient.post('/api/analyze-note-collection', {
        note_ids: noteIds,
        collection_name: "Todas las Notas"
      });

      toast.dismiss(toastId);
      toast.success(`Análisis de notas completado.`);

      const newAnalysis: Analysis = {
        id: response.data.task_id || `analysis-${Date.now()}`,
        type: 'note_collection_analysis',
        title: "Análisis de Todas las Notas",
        created_at: new Date().toISOString(),
        result: response.data.result_payload
      };

      setAnalysisResult(newAnalysis);
      setIsAnalysisResultDialogOpen(true);
    } catch (error) {
      toast.dismiss(toastId);
      toast.error("Error al analizar las notas.");
      console.error("Error al analizar las notas:", error);
    }
  };

  const handleAnalyzeSingleNote = async (note: Note) => {
    const toastId = toast.loading("Iniciando análisis de la nota...");
    try {
      const response = await apiClient.post('/api/analyze-note', {
        note_id: note.id
      });

      toast.dismiss(toastId);
      toast.success(`Análisis de nota completado.`);

      const newAnalysis: Analysis = {
        id: response.data.task_id || `analysis-${Date.now()}`,
        type: 'note_analysis',
        title: `Análisis: ${note.title || "Nota sin título"}`,
        created_at: new Date().toISOString(),
        result: response.data.result_payload
      };

      setAnalysisResult(newAnalysis);
      setIsAnalysisResultDialogOpen(true);
    } catch (error) {
      toast.dismiss(toastId);
      toast.error("Error al analizar la nota.");
      console.error("Error al analizar la nota:", error);
    }
  };

  const handleLinkProfile = (note: Note) => { // Nueva función
    setLinkingNote(note);
    setIsLinkProfileDialogOpen(true);
  };

  const handleSummarizeSingleNote = async (note: Note) => {
    const toastId = toast.loading("Generando resumen semántico...");
    try {
      const response = await apiClient.post('/api/summarize-note', {
        note_id: note.id
      });

      toast.dismiss(toastId);
      toast.success(`Resumen de nota completado.`);

      // Aquí podrías decidir cómo mostrar el resumen.
      // Por ahora, lo mostraremos en el diálogo de análisis existente.
      const newAnalysis: Analysis = {
        id: response.data.task_id || `summary-${Date.now()}`,
        type: 'semantic',
        title: `Resumen: ${note.title || "Nota sin título"}`,
        created_at: new Date().toISOString(),
        result: response.data.result_payload,
      };

      setAnalysisResult(newAnalysis);
      setIsAnalysisResultDialogOpen(true);
    } catch (error) {
      toast.dismiss(toastId);
      toast.error("Error al generar el resumen de la nota.");
      console.error("Error al resumir la nota:", error);
    }
  };



  const handleAnalyzeGroupedNotes = async (notesToAnalyze: Note[], groupName: any) => {
    const groupNameStr = (typeof groupName === 'object' && groupName !== null)
      ? groupName.name
      : String(groupName);

    if (!groupNameStr || notesToAnalyze.length === 0) {
      toast.info(`No hay notas para analizar.`);
      return;
    }

    const toastId = toast.loading(`Iniciando análisis de notas en ${groupNameStr}...`);
    try {
      const noteIds = notesToAnalyze.map(note => note.id);
      const response = await apiClient.post('/api/analyze-note-collection', {
        note_ids: noteIds,
        collection_name: groupNameStr
      });

      toast.dismiss(toastId);
      toast.success(`Análisis de notas en ${groupNameStr} completado.`);

      const newAnalysis: Analysis = {
        id: response.data.task_id || `analysis-${Date.now()}`,
        type: 'note_collection_analysis',
        title: `Análisis de Colección: ${groupNameStr}`,
        created_at: new Date().toISOString(),
        result: response.data.result_payload
      };

      setAnalysisResult(newAnalysis);
      setIsAnalysisResultDialogOpen(true);
    } catch (error) {
      toast.dismiss(toastId);
      toast.error(`Error al analizar notas en ${groupNameStr}.`);
      console.error(`Error al analizar notas en ${groupNameStr}:`, error);
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

  const handleToggleStar = async (e: React.MouseEvent, note: Note) => {
    e.stopPropagation();
    const newStarredStatus = !note.is_starred;
    
    // Optimistic update
    setNotes(prevNotes => {
      const updatedNotes = prevNotes.map(n => n.id === note.id ? { ...n, is_starred: newStarredStatus } : n);
      return updatedNotes.sort((a, b) => {
        if (a.is_starred && !b.is_starred) return -1;
        if (!a.is_starred && b.is_starred) return 1;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
    });

    try {
      await apiClient.post('/api/update-note', {
        note_id: note.id,
        is_starred: newStarredStatus
      });
      toast.success(newStarredStatus ? 'Nota destacada' : 'Nota quitada de destacadas');
    } catch (error) {
      // Revert if error
      setNotes(prevNotes => {
        const updatedNotes = prevNotes.map(n => n.id === note.id ? { ...n, is_starred: !newStarredStatus } : n);
        return updatedNotes.sort((a, b) => {
          if (a.is_starred && !b.is_starred) return -1;
          if (!a.is_starred && b.is_starred) return 1;
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
      });
      toast.error('Error al destacar la nota.');
      console.error(error);
    }
  };

  const NoteCard = ({ note, onAnalyzeNote, onLinkProfile, onSummarizeNote }: { note: Note, onAnalyzeNote: (note: Note) => void, onLinkProfile: (note: Note) => void, onSummarizeNote: (note: Note) => void }) => {
    const [{ isDragging }, drag] = useDrag({
      type: 'NOTE',
      item: { id: note.id, category: note.category },
      collect: monitor => ({
        isDragging: !!monitor.isDragging(),
      }),
    });

    // Determinar si el usuario puede editar basándose en el rol del workspace
    const canEdit = !note.workspace_id || note.workspace_role !== 'viewer';

    return (
      <motion.div
        ref={drag as any}
        layout
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.3 }}
        className="h-full"
        style={{ opacity: isDragging ? 0.5 : 1 }}
      >
        <Card
          className={`group relative overflow-hidden h-[280px] transition-all duration-300 cursor-pointer ${
            selectedNoteIds.includes(note.id)
              ? 'bg-primary/5 border-primary shadow-lg ring-1 ring-primary/30'
              : 'hover:bg-card/60 border-border/60 shadow-sm'
          }`}
          onClick={() => {
            if (selectedNoteIds.length > 0 || isSelectionMode) {
              handleToggleSelectNote(note.id);
            } else {
              setViewingNote(note);
              setIsViewDialogOpen(true);
            }
          }}
        >
          {/* Efecto de resplandor en el hover */}
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

          <CardHeader className="pb-3 relative z-10">
            <CardTitle className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="relative flex-shrink-0">
                  <div className={`p-3 rounded-2xl bg-background/50 border border-border/40 shadow-inner transition-all duration-500 ${
                    (isSelectionMode || selectedNoteIds.length > 0) ? 'opacity-0 scale-75' : 'group-hover:scale-110'
                  }`}>
                    <Notebook className="h-5 w-5 text-primary" />
                  </div>
                  <div className={`absolute inset-0 flex items-center justify-center transition-all duration-300 ${
                    (isSelectionMode || selectedNoteIds.length > 0) 
                      ? 'opacity-100 scale-100' 
                      : 'opacity-0 scale-75 pointer-events-none group-hover:opacity-100 group-hover:scale-100 group-hover:pointer-events-auto bg-card rounded-2xl border border-primary/40 shadow-sm'
                  }`}
                  onClick={(e) => e.stopPropagation()}
                  >
                    <Checkbox
                      checked={selectedNoteIds.includes(note.id)}
                      onCheckedChange={() => handleToggleSelectNote(note.id)}
                      className="h-5 w-5 rounded-md border-primary text-primary focus:ring-primary z-30"
                    />
                  </div>
                </div>
                <span className="font-bold text-lg line-clamp-2 group-hover:text-primary transition-colors leading-tight tracking-tight">
                  {note.title || 'Nota sin título'}
                </span>
              </div>
              <div className="flex items-center gap-1 z-20">
                <Button
                  variant="ghost"
                  size="sm"
                  className={`h-8 w-8 p-0 rounded-xl transition-all duration-300 ${
                    note.is_starred 
                      ? 'opacity-100 text-amber-400 hover:bg-amber-500/10' 
                      : 'opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-amber-400 hover:bg-primary/10'
                  }`}
                  onClick={(e) => handleToggleStar(e, note)}
                >
                  <Star className={`h-4.5 w-4.5 transition-transform duration-300 active:scale-125 ${note.is_starred ? 'fill-amber-400 text-amber-400' : ''}`} />
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl hover:bg-primary/10"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-[180px] rounded-2xl border-border/40 bg-card/95 backdrop-blur-xl">
                  {canEdit && (
                    <>
                      <DropdownMenuItem onClick={(e) => {
                        e.stopPropagation();
                        setEditingNote(note);
                        setIsNoteDialogOpen(true);
                      }} className="rounded-xl">
                        <Edit className="mr-2 h-4 w-4" />
                        Editar nota
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={(e) => {
                        e.stopPropagation();
                        setDeletingNote(note);
                      }} className="rounded-xl">
                        <Trash2 className="mr-2 h-4 w-4" />
                        Eliminar nota
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                    </>
                  )}
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    setChatNote(note);
                    setIsChatOpen(true);
                  }} className="rounded-xl text-primary font-medium">
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Chatear con Nota
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    onAnalyzeNote(note);
                  }} className="rounded-xl">
                    <Lightbulb className="mr-2 h-4 w-4" />
                    Analizar Nota
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    onSummarizeNote(note);
                  }} className="rounded-xl">
                    <FileText className="mr-2 h-4 w-4" />
                    Resumir Nota
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    onLinkProfile(note);
                  }} className="rounded-xl">
                    <Link className="mr-2 h-4 w-4" />
                    Vincular a Perfil
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 flex-grow overflow-hidden relative z-10">
            <div className="text-xs text-muted-foreground/80 line-clamp-4 leading-relaxed font-medium">
              {note.content ? (
                <InlineMarkdownRenderer content={note.content} />
              ) : (
                <p className="text-muted-foreground/60 italic">Sin contenido</p>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-3 pt-3 mt-auto border-t border-border/20 relative z-10">
            <div className="flex justify-between items-center w-full text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-primary/40" />
                <span className="truncate pr-2">{note.category}</span>
              </div>
              <span className="flex-shrink-0">{new Date(note.created_at).toLocaleDateString('es-ES', {
                year: 'numeric', month: 'short', day: 'numeric'
              })}</span>
            </div>
            <div className="flex items-center gap-2 w-full justify-end">
              {note.workspace_name && (
                <div
                  className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-1 rounded-full border uppercase tracking-wider"
                  style={{
                    backgroundColor: note.workspace_color ? `${note.workspace_color}15` : '#f3f4f620',
                    borderColor: note.workspace_color ? `${note.workspace_color}40` : '#88888840',
                  }}
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ backgroundColor: note.workspace_color || '#888888' }}
                  ></span>
                  <span style={{ color: note.workspace_color || '#374151' }}>
                    {note.workspace_name}
                  </span>
                </div>
              )}
              {note.team_shared && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                        <Users className="h-3.5 w-3.5" />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Compartido con equipo</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          </CardFooter>
        </Card>
      </motion.div>
    );
  };

  const CategoryDropZone = ({ category, children, onAnalyzeGroup }: { category: string; children: React.ReactNode; onAnalyzeGroup: (notes: Note[], groupName: string) => void }) => {
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

    const categoryNotes = notes.filter(note => (note.category || 'Sin Categoría') === category);

    return (
      <div ref={drop as any} className="p-4 rounded-lg" style={{ backgroundColor: isOver ? 'rgba(147, 112, 219, 0.1)' : 'transparent' }}>
        <div className="flex justify-between items-center mb-4 px-2">
          <h2 className="text-xl font-semibold">{category}</h2>
          <Button variant="outline" size="sm" onClick={() => onAnalyzeGroup(categoryNotes, category)}>
            <Lightbulb className="mr-2 h-4 w-4" />
            Analizar Categoría
          </Button>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
          {children}
        </div>
      </div>
    );
  };

  const WorkspaceDropZone = ({ workspace, children, onAnalyzeGroup }: { workspace: { id: string; name: string; color?: string }; children: React.ReactNode; onAnalyzeGroup: (notes: Note[], groupName: string) => void }) => {
    const workspaceNotes = notes.filter(note => (note.workspace_id || 'no-workspace') === workspace.id);

    return (
      <div className="p-4 rounded-lg">
        <div className="flex justify-between items-center mb-4 px-2">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <span className="h-4 w-4 rounded-full" style={{ backgroundColor: workspace.color || '#888888' }}></span>
            {workspace.name}
          </h2>
          <Button variant="outline" size="sm" onClick={() => onAnalyzeGroup(workspaceNotes, workspace.name)}>
            <Lightbulb className="mr-2 h-4 w-4" />
            Analizar Workspace
          </Button>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
          {children}
        </div>
      </div>
    );
  };

  const renderNotes = () => {
    console.log("RenderNotes - notes.length:", notes.length, "isLoading:", isLoading, "workspaceView:", workspaceView, "workspaceGroupView:", workspaceGroupView); // Log para depuración

    const filteredNotes = workspaceView
      ? notes.filter(note => note.workspace_id === workspaceView)
      : notes;

    if (isLoading && filteredNotes.length === 0) { // Solo mostrar "Cargando notas..." si es la carga inicial y no hay notas
      return <p className="text-center py-10">Cargando notas...</p>;
    }

    if (filteredNotes.length === 0) {
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

    if (workspaceGroupView) {
      const groupedNotes = filteredNotes.reduce((groups, note) => {
        const key = note.workspace_id || 'no-workspace';
        if (!groups[key]) {
          groups[key] = [];
        }
        groups[key].push(note);
        return groups;
      }, {} as Record<string, Note[]>);

      return (
        <AnimatePresence>
          <motion.div layout className="space-y-8">
            {Object.entries(groupedNotes).map(([workspaceId, workspaceNotes]) => {
              const workspaceInfo = availableWorkspaces.find(ws => ws.id === workspaceId) || { id: workspaceId, name: 'Sin Workspace', color: '#888888' };
              return (
                <WorkspaceDropZone key={workspaceId} workspace={workspaceInfo} onAnalyzeGroup={handleAnalyzeGroupedNotes}>
                  {workspaceNotes.map((note) => (
                    <NoteCard key={note.id} note={note} onAnalyzeNote={handleAnalyzeSingleNote} onLinkProfile={handleLinkProfile} onSummarizeNote={handleSummarizeSingleNote} />
                  ))}
                </WorkspaceDropZone>
              );
            })}
          </motion.div>
        </AnimatePresence>
      );
    }

    if (categoryView) {
      const groupedNotes = filteredNotes.reduce((groups, note) => {
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
              <CategoryDropZone key={category} category={category} onAnalyzeGroup={handleAnalyzeGroupedNotes}>
                {categoryNotes.map((note) => (
                  <NoteCard key={note.id} note={note} onAnalyzeNote={handleAnalyzeSingleNote} onLinkProfile={handleLinkProfile} onSummarizeNote={handleSummarizeSingleNote} />
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
          {filteredNotes.map((note) => (
            <NoteCard key={note.id} note={note} onAnalyzeNote={handleAnalyzeSingleNote} onLinkProfile={handleLinkProfile} onSummarizeNote={handleSummarizeSingleNote} />
          ))}
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <div className={isEmbedded ? "space-y-6" : "p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden"}>
      {!isEmbedded ? (
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <Notebook className="mr-3 h-8 w-8 text-primary" />
              Mis Notas
              <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground" onClick={() => setIsInfoSheetOpen(true)}>
                <Info className="h-4 w-4" />
              </Button>
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={isSelectionMode ? "secondary" : "outline"}
              size="sm"
              onClick={() => {
                setIsSelectionMode(!isSelectionMode);
                if (isSelectionMode) {
                  setSelectedNoteIds([]);
                }
              }}
              className="h-8 px-2 md:px-4 rounded-xl gap-1.5"
            >
              <CheckSquare className="h-4 w-4 text-primary" />
              <span className="hidden md:inline">{isSelectionMode ? "Cancelar Selección" : "Seleccionar"}</span>
            </Button>
            {!workspaceGroupView && (
              <Select onValueChange={(value) => setWorkspaceView(value === "all" ? null : value)} value={workspaceView || "all"}>
                <SelectTrigger className="w-[180px] h-8">
                  <SelectValue placeholder="Filtrar por Workspace" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las Notas</SelectItem>
                  {availableWorkspaces.map((ws) => (
                    <SelectItem key={ws.id} value={ws.id}>
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: ws.color || '#888888' }}></span>
                        {ws.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
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
                <DropdownMenuItem onClick={() => {
                  setCategoryView(!categoryView);
                  if (workspaceGroupView) setWorkspaceGroupView(false); // Desactivar vista por workspace si se activa vista por categoría
                }}>
                  {categoryView ? "Vista General" : "Vista por Categoría"}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => {
                  setWorkspaceGroupView(!workspaceGroupView);
                  if (categoryView) setCategoryView(false); // Desactivar vista por categoría si se activa vista por workspace
                  setWorkspaceView(null); // Limpiar filtro de workspace al activar vista agrupada
                }}>
                  {workspaceGroupView ? "Vista General" : "Vista por Workspace"}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleAnalyzeAllNotes}>
                  <Lightbulb className="mr-2 h-4 w-4" />
                  Analizar Notas
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => toast.info(`Funcionalidad 'Resumen Semántico' en desarrollo.`)}>
                  <FileText className="mr-2 h-4 w-4" />
                  Resumen Semántico
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-black uppercase tracking-widest text-muted-foreground/70">Mis Notas</h2>
            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-xl bg-primary/5 text-primary hover:bg-primary/10 transition-all" onClick={() => setIsInfoSheetOpen(true)}>
              <Info className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={isSelectionMode ? "secondary" : "outline"}
              size="sm"
              onClick={() => {
                setIsSelectionMode(!isSelectionMode);
                if (isSelectionMode) {
                  setSelectedNoteIds([]);
                }
              }}
              className="h-8 px-2 md:px-4 rounded-xl gap-1.5"
            >
              <CheckSquare className="h-4 w-4 text-primary" />
              <span className="hidden md:inline">{isSelectionMode ? "Cancelar Selección" : "Seleccionar"}</span>
            </Button>
            {!workspaceGroupView && (
              <Select onValueChange={(value) => setWorkspaceView(value === "all" ? null : value)} value={workspaceView || "all"}>
                <SelectTrigger className="w-[180px] h-8">
                  <SelectValue placeholder="Filtrar por Workspace" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las Notas</SelectItem>
                  {availableWorkspaces.map((ws) => (
                    <SelectItem key={ws.id} value={ws.id}>
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: ws.color || '#888888' }}></span>
                        {ws.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
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
                <DropdownMenuItem onClick={() => {
                  setCategoryView(!categoryView);
                  if (workspaceGroupView) setWorkspaceGroupView(false); // Desactivar vista por workspace si se activa vista por categoría
                }}>
                  {categoryView ? "Vista General" : "Vista por Categoría"}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => {
                  setWorkspaceGroupView(!workspaceGroupView);
                  if (categoryView) setCategoryView(false); // Desactivar vista por categoría si se activa vista por workspace
                  setWorkspaceView(null); // Limpiar filtro de workspace al activar vista agrupada
                }}>
                  {workspaceGroupView ? "Vista General" : "Vista por Workspace"}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleAnalyzeAllNotes}>
                  <Lightbulb className="mr-2 h-4 w-4" />
                  Analizar Notas
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => toast.info(`Funcionalidad 'Resumen Semántico' en desarrollo.`)}>
                  <FileText className="mr-2 h-4 w-4" />
                  Resumen Semántico
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      )}

      <div className="mb-8">
        <NoteSearch
          accountId={user?.id || ''}
          workspaceId={workspaceView || undefined}
          onResultClick={async (result) => {
            const note = notes.find(n => String(n.id) === result.note_id);
            if (note) {
              setViewingNote(note);
              setIsViewDialogOpen(true);
            } else {
              const toastId = toast.loading('Cargando nota...');
              try {
                const response = await apiClient.get(`/api/notes/${result.note_id}`);
                const fetchedNote = response.data;
                
                // Si la nota tiene workspace_id, buscar el rol para los permisos
                if (fetchedNote.workspace_id) {
                  try {
                    const roleResponse = await apiClient.get(`/api/workspaces/${fetchedNote.workspace_id}/my-role`);
                    fetchedNote.workspace_role = roleResponse.data.role;
                  } catch (roleError) {
                    console.error(`Error fetching role for workspace ${fetchedNote.workspace_id}:`, roleError);
                  }
                }
                
                setViewingNote(fetchedNote);
                setIsViewDialogOpen(true);
                toast.dismiss(toastId);
              } catch (error) {
                console.error("Error fetching note from search result:", error);
                toast.error("No se pudo cargar la nota completa.", { id: toastId });
              }
            }
          }}
        />
      </div>

      {renderNotes()}

      {hasMore && (
        <div className="flex justify-center mt-8">
          <Button onClick={handleLoadMore} disabled={isFetchingMore}>
            {isFetchingMore ? "Cargando más..." : "Ver más"}
          </Button>
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
        onNoteUpdated={() => fetchNotes(0, limit, false)}
      />

      {linkingNote && ( // Renderizado condicional del diálogo de vinculación
        <ManageLinkedProfilesDialog
          isOpen={isLinkProfileDialogOpen}
          onOpenChange={setIsLinkProfileDialogOpen}
          item={{ id: String(linkingNote.id), name: linkingNote.title || undefined }} // Convertir id a string y pasar title como name
          itemType="note" // Especificar el tipo de item
          onLinkedProfilesUpdated={() => fetchNotes(0, limit, false)}
          onLink={async (profileId, noteId) => {
            try {
              await apiClient.post(`/api/notes/${noteId}/link-profile`, { profile_id: profileId });
              toast.success('Perfil vinculado exitosamente.');
              fetchNotes(0, limit, false);
            } catch (error) {
              toast.error('Error al vincular el perfil.');
              console.error('Error linking profile:', error);
            }
          }}
          onUnlink={async (profileId, noteId) => {
            try {
              await apiClient.post(`/api/notes/${noteId}/unlink-profile`, { profile_id: profileId });
              toast.success('Perfil desvinculado exitosamente.');
              fetchNotes(0, limit, false);
            } catch (error) {
              toast.error('Error al desvincular el perfil.');
              console.error('Error unlinking profile:', error);
            }
          }}
        />
      )}

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

      <AnalysisDetailDialog
        analysis={analysisResult}
        isOpen={isAnalysisResultDialogOpen}
        onOpenChange={setIsAnalysisResultDialogOpen}
      />

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-[400px] sm:w-[540px] overflow-y-auto">
          <SheetHeader className="pb-6 border-b">
            <SheetTitle className="text-2xl font-bold flex items-center gap-2">
              <Notebook className="h-6 w-6 text-primary" />
              Guía de Notas
            </SheetTitle>
            <SheetDescription>
              Captura ideas y genera conocimiento con ayuda de la IA.
            </SheetDescription>
          </SheetHeader>
          
          <div className="py-6 space-y-8">
            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Captura Inteligente</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                El módulo de Notas no es solo un editor de texto; es un receptor de ideas. Puedes organizar tus notas por <strong>Categorías</strong> (Concepto, Idea, Tarea) o por <strong>Workspaces</strong> para mantener el orden.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Interacción con el Agente</h3>
              <div className="bg-primary/5 rounded-2xl p-4 border border-primary/10 space-y-3">
                <p className="text-xs font-medium text-primary flex items-center gap-2">
                  <Bot className="h-4 w-4" /> El Agente puede ayudarte a:
                </p>
                <ul className="text-xs space-y-2 text-muted-foreground list-disc pl-4">
                  <li><strong>Resumir contenido extenso</strong> en puntos clave accionables.</li>
                  <li><strong>Extraer tareas y eventos</strong> directamente desde una nota y agendarlos.</li>
                  <li><strong>Mejorar la redacción</strong> o cambiar el tono de tus borradores.</li>
                  <li><strong>Vincular notas</strong> a perfiles de contacto específicos para tener contexto de reuniones.</li>
                </ul>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Organización Visual</h3>
              <div className="grid grid-cols-1 gap-2 text-[11px]">
                <div className="flex items-center gap-2 p-3 rounded-xl bg-yellow-500/5 text-yellow-600 border border-yellow-500/10">
                  <span className="font-bold">IDEA</span> Pequeños fragmentos de inspiración que el agente puede expandir.
                </div>
                <div className="flex items-center gap-2 p-3 rounded-xl bg-purple-500/5 text-purple-600 border border-purple-500/10">
                  <span className="font-bold">LINKED</span> Vincula notas a contactos para verlas en su perfil detallado.
                </div>
              </div>
            </section>
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog open={isBulkDeleteDialogOpen} onOpenChange={setIsBulkDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará {selectedNoteIds.length} notas permanentemente. Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleBulkDeleteConfirm} className="bg-destructive hover:bg-destructive/90">
              Sí, eliminar {selectedNoteIds.length} notas
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AnimatePresence>
        {selectedNoteIds.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 100 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 100 }}
            className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50 w-full max-w-4xl px-4"
          >
            <div className="bg-background/95 backdrop-blur-xl border border-border/60 shadow-2xl rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3 w-full md:w-auto">
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-xl h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-primary/10"
                  onClick={() => {
                    setSelectedNoteIds([]);
                    setIsSelectionMode(false);
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-foreground">
                    {selectedNoteIds.length} notas seleccionadas
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const filtered = workspaceView
                      ? notes.filter(note => note.workspace_id === workspaceView)
                      : notes;
                    setSelectedNoteIds(filtered.map(n => n.id));
                  }}
                  className="h-9 rounded-xl text-xs font-semibold"
                >
                  Seleccionar todas
                </Button>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="h-9 rounded-xl text-xs font-semibold gap-1.5">
                      <Star className="h-3.5 w-3.5 text-amber-500" />
                      <span>Destacar</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="rounded-xl bg-card/95 backdrop-blur-xl border-border/40">
                    <DropdownMenuItem onClick={() => handleBulkToggleStar(true)} className="rounded-lg">
                      Destacar seleccionadas
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleBulkToggleStar(false)} className="rounded-lg">
                      Quitar destacado
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="h-9 rounded-xl text-xs font-semibold gap-1.5">
                      <Notebook className="h-3.5 w-3.5 text-primary" />
                      <span>Categoría</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="rounded-xl bg-card/95 backdrop-blur-xl border-border/40">
                    {["Concepto", "Idea", "Tarea", "General"].map(cat => (
                      <DropdownMenuItem key={cat} onClick={() => handleBulkChangeCategory(cat)} className="rounded-lg">
                        Mover a {cat}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="h-9 rounded-xl text-xs font-semibold gap-1.5">
                      <Link className="h-3.5 w-3.5 text-blue-500" />
                      <span>Workspace</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="rounded-xl bg-card/95 backdrop-blur-xl border-border/40 max-h-60 overflow-y-auto">
                    <DropdownMenuItem onClick={() => handleBulkChangeWorkspace(null)} className="rounded-lg">
                      Ninguno (Personal)
                    </DropdownMenuItem>
                    {availableWorkspaces.map(ws => (
                      <DropdownMenuItem key={ws.id} onClick={() => handleBulkChangeWorkspace(ws.id)} className="rounded-lg">
                        {ws.name}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkAnalyzeNotes}
                  className="h-9 rounded-xl text-xs font-semibold text-primary hover:text-primary-foreground hover:bg-primary gap-1.5"
                >
                  <Lightbulb className="h-3.5 w-3.5" />
                  Analizar
                </Button>

                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setIsBulkDeleteDialogOpen(true)}
                  className="h-9 rounded-xl text-xs font-semibold gap-1.5"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Eliminar
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {chatNote && (
        <ContextualChat
          isOpen={isChatOpen}
          onClose={() => {
            setIsChatOpen(false);
            setChatNote(null);
          }}
          title={chatNote.title || "Nota sin título"}
          context={{
            type: 'note',
            id: chatNote.id.toString(),
            snapshot: {
              title: chatNote.title || "Nota sin título",
              content: chatNote.content,
              category: chatNote.category,
            }
          }}
        />
      )}
    </div>
  );
}