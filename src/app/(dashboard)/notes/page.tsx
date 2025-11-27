'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Plus, Notebook, Users, Edit, Trash2, MoreHorizontal, Info, Lightbulb, FileText, Link } from 'lucide-react'; // Añadido Link
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
import { ContactProfile } from '../profiles/page';
import { Analysis } from '@/lib/models';

export interface Note {
  id: number;
  title: string | null;
  content: string;
  category: string;
  created_at: string;
  team_shared?: boolean | string;
  team_id?: string;
  workspace_id?: string;
  workspace_name?: string; // NEW
  workspace_color?: string; // NEW
}

export default function NotesPage() {
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
      const fetchedNotes = response.data.notes.sort((a: Note, b: Note) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      if (append) {
        setNotes(prevNotes => [...prevNotes, ...fetchedNotes]);
      } else {
        setNotes(fetchedNotes);
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

  const NoteCard = ({ note, onAnalyzeNote, onLinkProfile, onSummarizeNote }: { note: Note, onAnalyzeNote: (note: Note) => void, onLinkProfile: (note: Note) => void, onSummarizeNote: (note: Note) => void }) => {
    const [{ isDragging }, drag] = useDrag({
      type: 'NOTE',
      item: { id: note.id, category: note.category },
      collect: monitor => ({
        isDragging: !!monitor.isDragging(),
      }),
    });

    return (
      <motion.div
        ref={drag as any}
        layout
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="h-full"
        style={{ opacity: isDragging ? 0.5 : 1 }}
      >
        <Card
          className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full min-h-[200px]"
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
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[180px]">
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    setEditingNote(note);
                    setIsNoteDialogOpen(true);
                  }}>
                    <Edit className="mr-2 h-4 w-4" />
                    Editar nota
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    setDeletingNote(note);
                  }}>
                    <Trash2 className="mr-2 h-4 w-4" />
                    Eliminar nota
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    onAnalyzeNote(note);
                  }}>
                    <Lightbulb className="mr-2 h-4 w-4" />
                    Analizar Nota
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    onSummarizeNote(note);
                  }}>
                    <FileText className="mr-2 h-4 w-4" />
                    Resumir Nota
                  </DropdownMenuItem>
                  <DropdownMenuSeparator /> {/* Separador para el nuevo botón */}
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    onLinkProfile(note);
                  }}> {/* Nuevo botón */}
                    <Link className="mr-2 h-4 w-4" />
                    Vincular a Perfil
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
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
            <span className="truncate pr-2">{note.category}</span>
            <div className="flex items-center gap-2 flex-shrink-0">
              {note.workspace_name && (
                <div
                  className="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor: note.workspace_color ? `${note.workspace_color}20` : '#f3f4f6', // bg-gray-100
                  }}
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: note.workspace_color || '#888888' }}
                  ></span>
                  <span style={{ color: note.workspace_color || '#374151' }}>
                    {note.workspace_name}
                  </span>
                </div>
              )}
              {note.team_shared && <span title="Compartido con equipo"><Users className="h-4 w-4" /></span>}
              <span>{new Date(note.created_at).toLocaleDateString()}</span>
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
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
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
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-xl font-bold text-primary">Módulo de Notas</SheetTitle>
            <SheetDescription className="text-sm text-muted-foreground">
              Captura, organiza y gestiona tus ideas, pensamientos y recordatorios de forma eficiente.
            </SheetDescription>
          </SheetHeader>
          <div className="py-4 text-sm text-gray-700 dark:text-gray-300 space-y-4">
            <p><strong>¿Qué puedes hacer en tus Notas?</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Crear y Editar Notas:</strong> Escribe y organiza tus ideas con títulos y contenido.</li>
              <li><strong>Categorizar Notas:</strong> Agrupa tus notas por categorías para una mejor organización.</li>
              <li><strong>Organizar por Workspaces:</strong> Asocia notas a diferentes workspaces para mantener la información segmentada.</li>
              <li><strong>Análisis de Notas:</strong> Obtén insights y resúmenes semánticos de tus notas, individualmente o en grupos.</li>
              <li><strong>Vincular a Perfiles:</strong> Conecta tus notas a perfiles de contacto para contextualizar la información.</li>
              <li><strong>Gestión de Notas:</strong> Edita, elimina y visualiza tus notas fácilmente.</li>
            </ul>

            <p><strong>Interacción con IA:</strong></p>
            <p>Además de la gestión manual, puedes interactuar con tus notas a través del chat de IA. Las notas se integran a la "memoria" de Kognito, enriqueciendo sus respuestas por relevancia con la consulta. La IA dispone de herramientas especializadas para:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Buscar y recuperar información específica de tus notas.</li>
              <li>Generar resúmenes y extraer ideas clave de tus notas.</li>
              <li>Responder preguntas utilizando el contenido de tus notas.</li>
              <li>Crear nuevas notas o expandir las existentes basándose en conversaciones.</li>
            </ul>

            <p><strong>Beneficios Clave:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Captura Rápida de Ideas:</strong> No pierdas ningún pensamiento importante.</li>
              <li><strong>Organización Flexible:</strong> Adapta la estructura de tus notas a tus necesidades.</li>
              <li><strong>Conocimiento Contextualizado:</strong> Conecta ideas y personas para una comprensión más profunda.</li>
              <li><strong>Potenciado por IA:</strong> Aprovecha la inteligencia artificial para analizar y gestionar tu conocimiento.</li>
            </ul>

            <p>¡Convierte tus ideas en conocimiento accionable con el Módulo de Notas!</p>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}